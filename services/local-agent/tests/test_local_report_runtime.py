from __future__ import annotations

import json
import sys

import pytest

from worktrace_agent.ai.local_report_runtime import (
    JsonPostTransport,
    LocalReportRuntimeConfig,
    LocalReportRuntimeError,
    OllamaReportModel,
    UrllibJsonPostTransport,
)
from worktrace_agent.ai.reporting import generate_evidence_cited_report
from worktrace_agent.domain.raw_event import RawEvent, build_raw_event
from worktrace_agent.privacy.redaction import PRIVACY_TEST_CORPUS, count_privacy_leaks
from worktrace_agent.timeline.deterministic import build_deterministic_timeline

SESSION = {
    "id": "sess_local_runtime_001",
    "title": "Local runtime fixture",
    "started_at": "2026-05-07T09:14:00+05:30",
    "ended_at": "2026-05-07T09:20:00+05:30",
    "status": "stopped",
    "privacy_mode": "standard",
}
HEAVY_MODEL_MODULES = (
    "torch",
    "transformers",
    "llama_cpp",
    "ollama",
)


def test_ollama_report_runtime_rejects_non_localhost_base_url() -> None:
    with pytest.raises(ValueError, match="localhost"):
        OllamaReportModel(
            config=LocalReportRuntimeConfig(
                base_url="https://example.com",
                model_name="gemma-local",
            ),
            transport=FakeTransport({"response": valid_report_json()}),
        )


def test_urllib_report_transport_rejects_non_http_url_before_request() -> None:
    transport = UrllibJsonPostTransport()

    with pytest.raises(ValueError, match="local HTTP"):
        transport.post_json(
            url="file:///tmp/local-report-response.json",
            payload={"prompt": "redacted evidence prompt"},
            timeout_seconds=1,
        )


@pytest.mark.parametrize(
    "base_url",
    [
        "http://user:password@localhost:11434",
        "http://localhost:11434/provider",
    ],
)
def test_ollama_report_runtime_rejects_base_url_credentials_or_path(base_url: str) -> None:
    with pytest.raises(ValueError, match="base URL"):
        OllamaReportModel(
            config=LocalReportRuntimeConfig(
                base_url=base_url,
                model_name="gemma-local",
            ),
            transport=FakeTransport({"response": valid_report_json()}),
        )


def test_ollama_report_runtime_posts_prompt_to_localhost_transport() -> None:
    transport = FakeTransport({"response": valid_report_json()})
    model = OllamaReportModel(
        config=LocalReportRuntimeConfig(
            base_url="http://127.0.0.1:11434",
            model_name="gemma-local",
            timeout_seconds=12,
        ),
        transport=transport,
    )

    response = model.generate("redacted evidence prompt")

    assert response == valid_report_json()
    assert transport.requests == [
        {
            "url": "http://127.0.0.1:11434/api/generate",
            "payload": {
                "model": "gemma-local",
                "prompt": "redacted evidence prompt",
                "stream": False,
                "format": "json",
                "options": {
                    "num_ctx": 8192,
                    "num_predict": 512,
                    "temperature": 0.2,
                },
            },
            "timeout_seconds": 12,
        }
    ]


def test_ollama_report_runtime_applies_conservative_generation_budget() -> None:
    transport = FakeTransport({"response": valid_report_json()})
    model = OllamaReportModel(
        config=LocalReportRuntimeConfig(
            base_url="http://127.0.0.1:11434",
            model_name="gemma-local",
            max_input_chars=64,
            max_output_tokens=128,
            context_budget_tokens=4096,
            temperature=0.1,
            mode="default",
        ),
        transport=transport,
    )

    model.generate("redacted evidence prompt")

    assert transport.requests[0]["payload"] == {
        "model": "gemma-local",
        "prompt": "redacted evidence prompt",
        "stream": False,
        "format": "json",
        "options": {
            "num_ctx": 4096,
            "num_predict": 128,
            "temperature": 0.1,
        },
    }


def test_ollama_report_runtime_refuses_oversized_prompt_before_transport() -> None:
    transport = FakeTransport({"response": valid_report_json()})
    model = OllamaReportModel(
        config=LocalReportRuntimeConfig(
            base_url="http://127.0.0.1:11434",
            model_name="gemma-local",
            max_input_chars=10,
        ),
        transport=transport,
    )

    with pytest.raises(LocalReportRuntimeError, match="too large"):
        model.generate("this prompt is too long")

    assert transport.requests == []


@pytest.mark.parametrize("mode", ["deep", "default"])
def test_ollama_report_runtime_accepts_known_modes(mode: str) -> None:
    OllamaReportModel(
        config=LocalReportRuntimeConfig(
            base_url="http://127.0.0.1:11434",
            model_name="gemma-local",
            mode=mode,
        ),
        transport=FakeTransport({"response": valid_report_json()}),
    )


def test_ollama_report_runtime_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError, match="mode"):
        OllamaReportModel(
            config=LocalReportRuntimeConfig(
                base_url="http://127.0.0.1:11434",
                model_name="gemma-local",
                mode="experimental",
            ),
            transport=FakeTransport({"response": valid_report_json()}),
        )


def test_ollama_report_runtime_rejects_full_long_context_by_default() -> None:
    with pytest.raises(ValueError, match="default mode context"):
        OllamaReportModel(
            config=LocalReportRuntimeConfig(
                base_url="http://127.0.0.1:11434",
                model_name="gemma-local",
                context_budget_tokens=128000,
            ),
            transport=FakeTransport({"response": valid_report_json()}),
        )


def test_ollama_report_runtime_caps_deep_mode_to_tested_budget() -> None:
    with pytest.raises(ValueError, match="deep mode context"):
        OllamaReportModel(
            config=LocalReportRuntimeConfig(
                base_url="http://127.0.0.1:11434",
                model_name="gemma-local",
                mode="deep",
                context_budget_tokens=128000,
            ),
            transport=FakeTransport({"response": valid_report_json()}),
        )


def test_ollama_report_runtime_failure_is_safe_and_redacted() -> None:
    model = OllamaReportModel(
        config=LocalReportRuntimeConfig(
            base_url="http://localhost:11434",
            model_name=f"gemma-local {PRIVACY_TEST_CORPUS[0]}",
        ),
        transport=FailingTransport(RuntimeError(f"provider failed {PRIVACY_TEST_CORPUS[1]}")),
    )

    with pytest.raises(LocalReportRuntimeError) as error:
        model.generate("prompt")

    assert str(error.value) == "Local report runtime failed safely."
    assert count_privacy_leaks(str(error.value)) == 0


def test_evidence_report_can_use_ollama_runtime_with_fake_transport() -> None:
    timeline = build_deterministic_timeline(report_fixture_events())
    model = OllamaReportModel(
        config=LocalReportRuntimeConfig(
            base_url="http://127.0.0.1:11434",
            model_name="gemma-local",
        ),
        transport=FakeTransport({"response": valid_report_json()}),
    )

    report = generate_evidence_cited_report(
        session=SESSION,
        timeline=timeline,
        model=model,
        model_name=model.model_name,
        model_version="ollama-localhost",
        generated_at="2026-05-07T09:21:00+05:30",
    )

    assert report.summary.evidence_event_ids == ("evt_runtime_terminal",)
    assert report.model_metadata.model_name == "gemma-local"
    assert report.model_metadata.model_version == "ollama-localhost"


def test_local_report_runtime_does_not_import_heavy_model_modules() -> None:
    for module_name in HEAVY_MODEL_MODULES:
        sys.modules.pop(module_name, None)

    OllamaReportModel(
        config=LocalReportRuntimeConfig(
            base_url="http://127.0.0.1:11434",
            model_name="gemma-local",
        ),
        transport=FakeTransport({"response": valid_report_json()}),
    ).generate("prompt")

    assert not any(module_name in sys.modules for module_name in HEAVY_MODEL_MODULES)


class FakeTransport(JsonPostTransport):
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.requests: list[dict[str, object]] = []

    def post_json(
        self,
        *,
        url: str,
        payload: dict[str, object],
        timeout_seconds: int,
    ) -> dict[str, object]:
        self.requests.append(
            {
                "url": url,
                "payload": payload,
                "timeout_seconds": timeout_seconds,
            }
        )
        return self.response


class FailingTransport(JsonPostTransport):
    def __init__(self, error: Exception) -> None:
        self.error = error

    def post_json(
        self,
        *,
        url: str,
        payload: dict[str, object],
        timeout_seconds: int,
    ) -> dict[str, object]:
        raise self.error


def report_fixture_events() -> list[RawEvent]:
    return [
        build_raw_event(
            event_id="evt_runtime_terminal",
            session_id=str(SESSION["id"]),
            timestamp="2026-05-07T09:15:00+05:30",
            source="terminal_command_detector",
            event_type="terminal_command",
            privacy_level="safe",
            confidence=1,
            metadata={
                "command": "uv run --python 3.13 pytest",
                "shell": "powershell",
                "exit_code": 0,
                "command_hash": "hash-runtime-terminal",
            },
        )
    ]


def valid_report_json() -> str:
    return json.dumps(
        {
            "session_title": "Local runtime fixture",
            "summary": {
                "text": "The session ran tests through a local runtime.",
                "evidence_event_ids": ["evt_runtime_terminal"],
            },
            "timeline": [],
            "blockers": [],
            "repeated_actions": [],
            "important_files": [],
            "commands": [
                {
                    "command": "uv run --python 3.13 pytest",
                    "evidence_event_ids": ["evt_runtime_terminal"],
                }
            ],
            "workflow_steps": [],
            "confidence": 0.8,
        }
    )
