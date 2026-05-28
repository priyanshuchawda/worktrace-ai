from __future__ import annotations

import json
import subprocess  # nosec B404
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Literal, Protocol

from worktrace_agent.ai.gemma_manifest import (
    DEFAULT_GEMMA_REPORT_MODEL,
    build_gemma_report_runtime_config,
)
from worktrace_agent.ai.local_report_runtime import LocalReportRuntimeConfig, OllamaReportModel
from worktrace_agent.ai.reporting import (
    LocalReportModel,
    ReportGenerationError,
    generate_evidence_cited_report,
)
from worktrace_agent.domain.raw_event import RawEvent, build_raw_event
from worktrace_agent.privacy.redaction import count_privacy_leaks, redact_text
from worktrace_agent.timeline.deterministic import build_deterministic_timeline

SmokeStatus = Literal["passed", "skipped", "failed"]
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
SMOKE_GENERATED_AT = "2026-05-08T00:00:00+05:30"
SMOKE_CONTEXT_BUDGET_TOKENS = 4096
SMOKE_MAX_OUTPUT_TOKENS = 256
SMOKE_TIMEOUT_SECONDS = 90


class CommandRunner(Protocol):
    def __call__(self, args: Sequence[str], timeout_seconds: int) -> CommandResult:
        """Run a fixed command without a shell and return captured text."""
        ...


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class GemmaE2BSmokeResult:
    status: SmokeStatus
    model_name: str
    ollama_version: str | None
    evidence_ids: tuple[str, ...]
    privacy_leak_count: int
    generated_at: str
    reason: str | None
    report_summary: str | None

    def to_public_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "model_name": self.model_name,
            "ollama_version": self.ollama_version,
            "evidence_ids": list(self.evidence_ids),
            "privacy_leak_count": self.privacy_leak_count,
            "generated_at": self.generated_at,
            "reason": self.reason,
            "report_summary": self.report_summary,
        }


ReportModelFactory = Callable[[LocalReportRuntimeConfig], LocalReportModel]


def run_gemma_e2b_smoke(
    *,
    command_runner: CommandRunner | None = None,
    report_model_factory: ReportModelFactory | None = None,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
) -> GemmaE2BSmokeResult:
    selected_command_runner = command_runner or _run_command
    selected_report_model_factory = report_model_factory or _build_ollama_report_model
    model_name = DEFAULT_GEMMA_REPORT_MODEL.ollama_model
    version_result = _run_ollama_command(selected_command_runner, ("ollama", "--version"))
    if version_result is None:
        return _skipped(model_name=model_name, reason="Ollama CLI is not available.")
    if version_result.returncode != 0:
        return _skipped(
            model_name=model_name,
            reason="Ollama CLI is unavailable or returned an error.",
            ollama_version=_first_non_empty_line(version_result.stdout),
        )

    ollama_version = _first_non_empty_line(version_result.stdout)
    list_result = _run_ollama_command(selected_command_runner, ("ollama", "list"))
    if list_result is None or list_result.returncode != 0:
        return _skipped(
            model_name=model_name,
            reason="Ollama model list is unavailable.",
            ollama_version=ollama_version,
        )

    installed_models = _parse_ollama_model_names(list_result.stdout)
    if model_name not in installed_models:
        return _skipped(
            model_name=model_name,
            reason=f"{model_name} is not installed in Ollama.",
            ollama_version=ollama_version,
        )

    timeline = build_deterministic_timeline(_smoke_events())
    try:
        config = replace(
            build_gemma_report_runtime_config(base_url=base_url),
            context_budget_tokens=SMOKE_CONTEXT_BUDGET_TOKENS,
            max_output_tokens=SMOKE_MAX_OUTPUT_TOKENS,
            timeout_seconds=SMOKE_TIMEOUT_SECONDS,
        )
        report = generate_evidence_cited_report(
            session=_smoke_session(),
            timeline=timeline,
            model=selected_report_model_factory(config),
            model_name=model_name,
            model_version="ollama-local-smoke",
            generated_at=SMOKE_GENERATED_AT,
        )
    except (ReportGenerationError, ValueError) as error:
        reason = redact_text(str(error))
        return GemmaE2BSmokeResult(
            status="failed",
            model_name=model_name,
            ollama_version=ollama_version,
            evidence_ids=(),
            privacy_leak_count=count_privacy_leaks(reason),
            generated_at=SMOKE_GENERATED_AT,
            reason=reason,
            report_summary=None,
        )

    evidence_ids = tuple(
        evidence_id for claim in report.all_claims() for evidence_id in claim.evidence_event_ids
    )
    public_result = GemmaE2BSmokeResult(
        status="passed",
        model_name=model_name,
        ollama_version=ollama_version,
        evidence_ids=tuple(dict.fromkeys(evidence_ids)),
        privacy_leak_count=count_privacy_leaks(report.model_dump(mode="json")),
        generated_at=SMOKE_GENERATED_AT,
        reason=None,
        report_summary=report.summary.text,
    )
    return public_result


def main() -> int:
    result = run_gemma_e2b_smoke()
    print(json.dumps(result.to_public_dict(), sort_keys=True, indent=2))
    return 1 if result.status == "failed" else 0


def _run_command(args: Sequence[str], timeout_seconds: int) -> CommandResult:
    completed = subprocess.run(
        list(args),
        capture_output=True,
        check=False,
        shell=False,  # nosec B603
        text=True,
        timeout=timeout_seconds,
    )
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _run_ollama_command(
    command_runner: CommandRunner,
    args: Sequence[str],
) -> CommandResult | None:
    try:
        return command_runner(args, 20)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None


def _parse_ollama_model_names(output: str) -> set[str]:
    names: set[str] = set()
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped or stripped.lower().startswith("name "):
            continue
        names.add(stripped.split()[0])
    return names


def _first_non_empty_line(output: str) -> str | None:
    for line in output.splitlines():
        stripped = line.strip()
        if stripped:
            return redact_text(stripped)
    return None


def _build_ollama_report_model(config: LocalReportRuntimeConfig) -> LocalReportModel:
    return OllamaReportModel(config=config)


def _skipped(
    *,
    model_name: str,
    reason: str,
    ollama_version: str | None = None,
) -> GemmaE2BSmokeResult:
    redacted_reason = redact_text(reason)
    return GemmaE2BSmokeResult(
        status="skipped",
        model_name=model_name,
        ollama_version=ollama_version,
        evidence_ids=(),
        privacy_leak_count=count_privacy_leaks(redacted_reason),
        generated_at=SMOKE_GENERATED_AT,
        reason=redacted_reason,
        report_summary=None,
    )


def _smoke_session() -> dict[str, object]:
    return {
        "id": "sess_gemma_e2b_smoke",
        "title": "Gemma E2B local smoke",
        "status": "stopped",
        "privacy_mode": "standard",
    }


def _smoke_events() -> list[RawEvent]:
    return [
        build_raw_event(
            event_id="evt_gemma_e2b_smoke_terminal",
            session_id="sess_gemma_e2b_smoke",
            timestamp="2026-05-08T09:00:00+05:30",
            source="terminal_command_detector",
            event_type="terminal_command",
            privacy_level="safe",
            confidence=1,
            metadata={
                "command": "uv run --python 3.13 pytest tests/test_local_report_runtime.py",
                "shell": "powershell",
                "exit_code": 0,
                "command_hash": "hash-gemma-e2b-smoke",
            },
        )
    ]


if __name__ == "__main__":
    raise SystemExit(main())
