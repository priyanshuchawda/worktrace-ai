from __future__ import annotations

import json
from collections.abc import Sequence

from worktrace_agent.ai.local_report_runtime import LocalReportRuntimeConfig
from worktrace_agent.ai.reporting import LocalReportModel
from worktrace_agent.scripts.smoke_gemma_e2b_report import (
    CommandResult,
    run_gemma_e2b_smoke,
)


def test_gemma_e2b_smoke_skips_when_ollama_cli_is_missing() -> None:
    factory = FakeReportModelFactory()
    result = run_gemma_e2b_smoke(
        command_runner=MissingOllamaRunner(),
        report_model_factory=factory,
    )

    assert result.status == "skipped"
    assert result.model_name == "gemma4:e2b"
    assert "Ollama CLI is not available" in (result.reason or "")
    assert result.evidence_ids == ()
    assert result.privacy_leak_count == 0
    assert factory.configs == []


def test_gemma_e2b_smoke_skips_when_configured_model_is_missing() -> None:
    factory = FakeReportModelFactory()
    result = run_gemma_e2b_smoke(
        command_runner=StaticCommandRunner(
            {
                ("ollama", "--version"): CommandResult(
                    returncode=0,
                    stdout="ollama version is 0.23.1",
                    stderr="",
                ),
                ("ollama", "list"): CommandResult(
                    returncode=0,
                    stdout=(
                        "NAME          ID              SIZE      MODIFIED\n"
                        "gemma4:e4b    abc    9.6 GB    today"
                    ),
                    stderr="",
                ),
            }
        ),
        report_model_factory=factory,
    )

    assert result.status == "skipped"
    assert result.ollama_version == "ollama version is 0.23.1"
    assert "gemma4:e2b is not installed" in (result.reason or "")
    assert result.privacy_leak_count == 0
    assert factory.configs == []


def test_gemma_e2b_smoke_passes_with_fake_runtime_and_hides_prompt() -> None:
    factory = FakeReportModelFactory()
    result = run_gemma_e2b_smoke(
        command_runner=StaticCommandRunner(
            {
                ("ollama", "--version"): CommandResult(
                    returncode=0,
                    stdout="ollama version is 0.23.1",
                    stderr="",
                ),
                ("ollama", "list"): CommandResult(
                    returncode=0,
                    stdout=(
                        "NAME          ID              SIZE      MODIFIED\n"
                        "gemma4:e2b    7fbdbf8f5e45    7.2 GB    today"
                    ),
                    stderr="",
                ),
            }
        ),
        report_model_factory=factory,
    )

    serialized = json.dumps(result.to_public_dict(), sort_keys=True)

    assert result.status == "passed"
    assert result.model_name == "gemma4:e2b"
    assert result.ollama_version == "ollama version is 0.23.1"
    assert result.evidence_ids == ("evt_gemma_e2b_smoke_terminal",)
    assert result.privacy_leak_count == 0
    assert result.report_summary == "The local Gemma E2B smoke cited session evidence."
    assert factory.configs[0].base_url == "http://127.0.0.1:11434"
    assert factory.configs[0].model_name == "gemma4:e2b"
    assert factory.configs[0].timeout_seconds == 90
    assert factory.configs[0].max_output_tokens == 256
    assert factory.configs[0].context_budget_tokens == 4096
    assert "Known evidence" not in serialized
    assert "prompt" not in serialized.lower()


class MissingOllamaRunner:
    def __call__(self, args: Sequence[str], timeout_seconds: int) -> CommandResult:
        raise FileNotFoundError("ollama")


class StaticCommandRunner:
    def __init__(self, responses: dict[tuple[str, ...], CommandResult]) -> None:
        self.responses = responses

    def __call__(self, args: Sequence[str], timeout_seconds: int) -> CommandResult:
        key = tuple(args)
        if key not in self.responses:
            raise AssertionError(f"unexpected command: {key}")
        return self.responses[key]


class FakeReportModelFactory:
    def __init__(self) -> None:
        self.configs: list[LocalReportRuntimeConfig] = []

    def __call__(self, config: LocalReportRuntimeConfig) -> LocalReportModel:
        self.configs.append(config)
        return FakeReportModel()


class FakeReportModel:
    def generate(self, prompt: str) -> str:
        if "evt_gemma_e2b_smoke_terminal" not in prompt:
            raise AssertionError("smoke prompt did not include evidence ID")
        return json.dumps(
            {
                "session_title": "Gemma E2B local smoke",
                "summary": {
                    "text": "The local Gemma E2B smoke cited session evidence.",
                    "evidence_event_ids": ["evt_gemma_e2b_smoke_terminal"],
                },
                "timeline": [],
                "blockers": [],
                "repeated_actions": [],
                "important_files": [],
                "commands": [
                    {
                        "command": "uv run --python 3.13 pytest tests/test_local_report_runtime.py",
                        "evidence_event_ids": ["evt_gemma_e2b_smoke_terminal"],
                    }
                ],
                "workflow_steps": [],
                "confidence": 0.8,
            }
        )
