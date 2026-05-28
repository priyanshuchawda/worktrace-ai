from __future__ import annotations

import json
from collections.abc import Sequence

from worktrace_agent.ai.local_ollama_report_provider import LocalOllamaReportService
from worktrace_agent.ai.local_report_runtime import (
    LocalReportRuntimeConfig,
    LocalReportRuntimeError,
)
from worktrace_agent.ai.provider_config import AiProviderConfig, AiReportProvider
from worktrace_agent.domain.raw_event import RawEvent, build_raw_event


def test_status_is_ready_when_ollama_has_default_gemma_model() -> None:
    service = LocalOllamaReportService(
        config=local_config(),
        model_lister=FakeModelLister(("gemma4:e2b",)),
    )

    result = service.status(session_id="sess_local_report")

    assert result["status"] == "ready"
    assert result["can_generate"] is True
    assert result["provider"] == "local_ollama"
    assert result["model_name"] == "gemma4:e2b"
    assert result["requested_model"] == "gemma4:e2b"


def test_status_explains_missing_ollama_without_generating() -> None:
    service = LocalOllamaReportService(
        config=local_config(),
        model_lister=FakeModelLister(error=LocalReportRuntimeError("down")),
    )

    result = service.status(session_id="sess_local_report")

    assert result["status"] == "runtime_unavailable"
    assert result["can_generate"] is False
    assert "Local Ollama is not reachable" in str(result["message"])
    assert "gemma4:e2b" in str(result["message"])


def test_status_explains_missing_gemma_model() -> None:
    service = LocalOllamaReportService(
        config=local_config(),
        model_lister=FakeModelLister(("gemma4:e4b",)),
    )

    result = service.status(session_id="sess_local_report")

    assert result["status"] == "runtime_unavailable"
    assert result["can_generate"] is False
    assert "gemma4:e2b is not installed" in str(result["message"])


def test_generate_uses_local_ollama_model_and_evidence_ids() -> None:
    factory = FakeReportModelFactory([valid_report_json()])
    service = LocalOllamaReportService(
        config=local_config(),
        model_lister=FakeModelLister(("gemma4:e2b",)),
        report_model_factory=factory,
    )

    result = service.generate(session_id="sess_local_report", events=report_events())

    assert result["status"] == "complete"
    assert result["provider"] == "local_ollama"
    assert result["model_name"] == "gemma4:e2b"
    assert result["actual_model"] == "gemma4:e2b"
    assert result["fallback_used"] is False
    assert result["evidence_ids"] == ["evt_report_terminal"]
    assert factory.configs[0].base_url == "http://127.0.0.1:11434"
    assert factory.configs[0].model_name == "gemma4:e2b"


def test_generate_does_not_call_model_when_runtime_unavailable() -> None:
    factory = FakeReportModelFactory([valid_report_json()])
    service = LocalOllamaReportService(
        config=local_config(),
        model_lister=FakeModelLister(()),
        report_model_factory=factory,
    )

    result = service.generate(session_id="sess_local_report", events=report_events())

    assert result["status"] == "runtime_unavailable"
    assert result["can_generate"] is False
    assert factory.configs == []


def test_generate_fails_safely_for_unknown_evidence_ids() -> None:
    factory = FakeReportModelFactory([valid_report_json(evidence_event_ids=("evt_missing",))])
    service = LocalOllamaReportService(
        config=local_config(),
        model_lister=FakeModelLister(("gemma4:e2b",)),
        report_model_factory=factory,
    )

    result = service.generate(session_id="sess_local_report", events=report_events())

    assert result["status"] == "failed_safely"
    assert result["provider"] == "local_ollama"
    assert result["actual_model"] is None


def local_config() -> AiProviderConfig:
    return AiProviderConfig(
        provider=AiReportProvider.LOCAL_OLLAMA,
        dev_cloud_enabled=False,
        local_ollama_base_url="http://127.0.0.1:11434",
    )


class FakeModelLister:
    def __init__(
        self,
        models: Sequence[str] = (),
        *,
        error: LocalReportRuntimeError | None = None,
    ) -> None:
        self.models = tuple(models)
        self.error = error
        self.calls: list[str] = []

    def list_model_names(self, *, base_url: str, timeout_seconds: int) -> tuple[str, ...]:
        self.calls.append(base_url)
        if self.error is not None:
            raise self.error
        return self.models


class FakeReportModelFactory:
    def __init__(self, responses: Sequence[str]) -> None:
        self.responses = list(responses)
        self.configs: list[LocalReportRuntimeConfig] = []

    def __call__(self, config: LocalReportRuntimeConfig) -> FakeLocalReportModel:
        self.configs.append(config)
        return FakeLocalReportModel(self.responses)


class FakeLocalReportModel:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses

    def generate(self, prompt: str) -> str:
        if not self.responses:
            raise AssertionError("fake model has no responses left")
        return self.responses.pop(0)


def report_events() -> list[RawEvent]:
    return [
        build_raw_event(
            event_id="evt_report_terminal",
            session_id="sess_local_report",
            timestamp="2026-05-06T09:15:00+05:30",
            source="terminal_command_detector",
            event_type="terminal_command",
            privacy_level="safe",
            confidence=1,
            metadata={"command": "uv run --python 3.13 pytest", "shell": "powershell"},
        )
    ]


def valid_report_json(*, evidence_event_ids: Sequence[str] = ("evt_report_terminal",)) -> str:
    evidence = list(evidence_event_ids)
    return json.dumps(
        {
            "session_title": "Local report fixture",
            "summary": {
                "text": "The session ran local tests.",
                "evidence_event_ids": evidence,
            },
            "timeline": [],
            "blockers": [],
            "repeated_actions": [],
            "important_files": [],
            "commands": [
                {
                    "command": "uv run --python 3.13 pytest",
                    "evidence_event_ids": evidence,
                }
            ],
            "workflow_steps": [],
            "confidence": 0.8,
        }
    )
