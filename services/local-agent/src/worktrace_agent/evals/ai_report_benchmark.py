from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, cast

from pydantic import ValidationError

from worktrace_agent.ai.gemma_manifest import (
    DEEP_GEMMA_REPORT_MODEL,
    DEFAULT_GEMMA_REPORT_MODEL,
)
from worktrace_agent.ai.reporting import (
    EvidenceClaim,
    HallucinationGuardError,
    LocalReportModel,
    ReportGenerationError,
    generate_evidence_cited_report,
    parse_report_json,
)
from worktrace_agent.evals.golden_sessions import (
    DEFAULT_GOLDEN_SESSIONS_PATH,
    GoldenSession,
    load_golden_sessions,
)
from worktrace_agent.privacy.redaction import count_privacy_leaks, redact_text
from worktrace_agent.timeline.deterministic import (
    DeterministicTimeline,
    build_deterministic_timeline,
)
from worktrace_agent.timeline.workflow_debugger import (
    WorkflowDebuggerReport,
    build_workflow_debugger_report,
)

AiReportBenchmarkMode = Literal[
    "deterministic_report",
    "fake_gemma_e2b",
    "fake_gemma_e4b_deep",
    "model_unavailable",
]

AI_REPORT_BENCHMARK_MODES: tuple[AiReportBenchmarkMode, ...] = (
    "deterministic_report",
    "fake_gemma_e2b",
    "fake_gemma_e4b_deep",
    "model_unavailable",
)
GENERATED_AT = "2026-05-08T00:00:00+05:30"


@dataclass(frozen=True)
class AiReportSessionResult:
    session_id: str
    title: str
    mode: AiReportBenchmarkMode
    hallucinated_evidence_count: int
    evidence_citation_valid: bool
    privacy_leak_count: int
    generated_report_evidence_id_coverage: float
    model_unavailable_fallback: bool
    summary_usefulness_proxy: float
    blocker_precision_proxy: float
    blocker_recall_proxy: float
    estimated_latency_ms: float
    estimated_memory_mb: float
    model_call_count: int
    model_called_during_recording: bool
    passed: bool
    failure_reason: str | None = None


@dataclass(frozen=True)
class AiReportAggregateResult:
    mode: AiReportBenchmarkMode
    sessions: int
    hallucinated_evidence_count: int
    evidence_citation_valid: bool
    privacy_leak_count: int
    generated_report_evidence_id_coverage: float
    model_unavailable_fallback: bool
    summary_usefulness_proxy: float
    blocker_precision_proxy: float
    blocker_recall_proxy: float
    estimated_latency_ms: float
    estimated_memory_mb: float
    model_call_count: int
    model_called_during_recording: bool
    passed: bool


@dataclass(frozen=True)
class AiReportBenchmarkResults:
    session_results: tuple[AiReportSessionResult, ...]
    aggregate_results: tuple[AiReportAggregateResult, ...]


class StaticReportModel:
    def __init__(self, responses: Sequence[str]) -> None:
        self._responses = list(responses)
        self.prompts: list[str] = []
        self.outputs: list[str] = []

    @property
    def call_count(self) -> int:
        return len(self.prompts)

    def generate(self, prompt: str) -> str:
        self.prompts.append(redact_text(prompt))
        if not self._responses:
            raise ReportGenerationError("Static report model has no responses left.")
        output = self._responses.pop(0)
        self.outputs.append(output)
        return output


def evaluate_ai_report_benchmark(
    path: Path = DEFAULT_GOLDEN_SESSIONS_PATH,
) -> AiReportBenchmarkResults:
    session_results = tuple(
        evaluate_ai_report_session(session, mode=mode)
        for session in load_golden_sessions(path)
        for mode in AI_REPORT_BENCHMARK_MODES
    )
    return AiReportBenchmarkResults(
        session_results=session_results,
        aggregate_results=tuple(
            _aggregate_mode_results(mode, session_results) for mode in AI_REPORT_BENCHMARK_MODES
        ),
    )


def evaluate_ai_report_session(
    session: GoldenSession,
    *,
    mode: AiReportBenchmarkMode,
    model: LocalReportModel | None = None,
) -> AiReportSessionResult:
    timeline = build_deterministic_timeline(session.events)
    workflow_report = build_workflow_debugger_report(timeline)
    known_evidence_ids = _known_evidence_ids(timeline)
    blocker_precision, blocker_recall = _blocker_precision_recall(
        workflow_report=workflow_report,
        expected_blockers=set(session.expectations.blocker_event_ids),
    )

    if mode == "deterministic_report":
        cited_ids = _workflow_report_evidence_ids(workflow_report)
        hallucinated_count = _count_unknown_evidence(cited_ids, known_evidence_ids)
        privacy_leak_count = count_privacy_leaks(
            {
                "session": session.raw_payload,
                "workflow_report": asdict(workflow_report),
            }
        )
        return _result(
            session=session,
            mode=mode,
            hallucinated_evidence_count=hallucinated_count,
            evidence_citation_valid=hallucinated_count == 0 and bool(cited_ids),
            privacy_leak_count=privacy_leak_count,
            coverage=_coverage(cited_ids, known_evidence_ids),
            fallback=False,
            summary_usefulness_proxy=_summary_usefulness_proxy(cited_ids),
            blocker_precision_proxy=blocker_precision,
            blocker_recall_proxy=blocker_recall,
            estimated_latency_ms=float(len(session.events) * 2),
            estimated_memory_mb=_estimated_memory_mb(session.raw_payload),
            model_call_count=0,
            failure_reason=None,
        )

    if mode == "model_unavailable":
        return _result(
            session=session,
            mode=mode,
            hallucinated_evidence_count=0,
            evidence_citation_valid=True,
            privacy_leak_count=count_privacy_leaks(session.raw_payload),
            coverage=0,
            fallback=True,
            summary_usefulness_proxy=0.5,
            blocker_precision_proxy=blocker_precision,
            blocker_recall_proxy=blocker_recall,
            estimated_latency_ms=1.0,
            estimated_memory_mb=0.0,
            model_call_count=0,
            failure_reason=None,
        )

    report_model = model or StaticReportModel(
        [_fake_report_json(session=session, timeline=timeline, workflow_report=workflow_report)]
    )
    model_name = (
        DEFAULT_GEMMA_REPORT_MODEL.ollama_model
        if mode == "fake_gemma_e2b"
        else DEEP_GEMMA_REPORT_MODEL.ollama_model
    )
    model_version = (
        DEFAULT_GEMMA_REPORT_MODEL.key if mode == "fake_gemma_e2b" else DEEP_GEMMA_REPORT_MODEL.key
    )
    try:
        report = generate_evidence_cited_report(
            session=_session_payload(session),
            timeline=timeline,
            model=report_model,
            model_name=model_name,
            model_version=model_version,
            generated_at=GENERATED_AT,
        )
    except (HallucinationGuardError, ReportGenerationError, ValidationError) as error:
        cited_ids = _last_model_evidence_ids(report_model)
        hallucinated_count = _count_unknown_evidence(cited_ids, known_evidence_ids)
        return _result(
            session=session,
            mode=mode,
            hallucinated_evidence_count=hallucinated_count,
            evidence_citation_valid=False,
            privacy_leak_count=count_privacy_leaks(_safe_model_outputs(report_model)),
            coverage=_coverage(cited_ids, known_evidence_ids),
            fallback=False,
            summary_usefulness_proxy=0,
            blocker_precision_proxy=blocker_precision,
            blocker_recall_proxy=blocker_recall,
            estimated_latency_ms=_estimated_model_latency_ms(mode, session),
            estimated_memory_mb=_estimated_model_memory_mb(mode),
            model_call_count=_model_call_count(report_model),
            failure_reason=redact_text(str(error)),
        )

    cited_ids = tuple(
        evidence_id for claim in report.all_claims() for evidence_id in claim.evidence_event_ids
    )
    hallucinated_count = _count_unknown_evidence(cited_ids, known_evidence_ids)
    return _result(
        session=session,
        mode=mode,
        hallucinated_evidence_count=hallucinated_count,
        evidence_citation_valid=hallucinated_count == 0 and bool(cited_ids),
        privacy_leak_count=count_privacy_leaks(report.model_dump(mode="json")),
        coverage=_coverage(cited_ids, known_evidence_ids),
        fallback=False,
        summary_usefulness_proxy=_summary_usefulness_proxy(report.summary.text or ""),
        blocker_precision_proxy=blocker_precision,
        blocker_recall_proxy=blocker_recall,
        estimated_latency_ms=_estimated_model_latency_ms(mode, session),
        estimated_memory_mb=_estimated_model_memory_mb(mode),
        model_call_count=_model_call_count(report_model),
        failure_reason=None,
    )


def render_ai_report_benchmark_table(results: AiReportBenchmarkResults) -> str:
    rows = [
        "| mode | sessions | hallucinated_evidence_count | evidence_citation_valid | "
        "privacy_leak_count | generated_report_evidence_id_coverage | "
        "model_unavailable_fallback | summary_usefulness_proxy | "
        "blocker_precision_proxy | blocker_recall_proxy | estimated_latency_ms | "
        "estimated_memory_mb | model_call_count | model_called_during_recording | passed |",
        "| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | "
        "---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    rows.extend(_aggregate_row(result) for result in results.aggregate_results)
    return "\n".join(rows)


def _result(
    *,
    session: GoldenSession,
    mode: AiReportBenchmarkMode,
    hallucinated_evidence_count: int,
    evidence_citation_valid: bool,
    privacy_leak_count: int,
    coverage: float,
    fallback: bool,
    summary_usefulness_proxy: float,
    blocker_precision_proxy: float,
    blocker_recall_proxy: float,
    estimated_latency_ms: float,
    estimated_memory_mb: float,
    model_call_count: int,
    failure_reason: str | None,
) -> AiReportSessionResult:
    model_called_during_recording = False
    passed = (
        hallucinated_evidence_count == 0
        and evidence_citation_valid
        and privacy_leak_count == 0
        and not model_called_during_recording
        and (failure_reason is None)
    )
    return AiReportSessionResult(
        session_id=session.id,
        title=session.title,
        mode=mode,
        hallucinated_evidence_count=hallucinated_evidence_count,
        evidence_citation_valid=evidence_citation_valid,
        privacy_leak_count=privacy_leak_count,
        generated_report_evidence_id_coverage=round(coverage, 3),
        model_unavailable_fallback=fallback,
        summary_usefulness_proxy=round(summary_usefulness_proxy, 3),
        blocker_precision_proxy=round(blocker_precision_proxy, 3),
        blocker_recall_proxy=round(blocker_recall_proxy, 3),
        estimated_latency_ms=round(estimated_latency_ms, 3),
        estimated_memory_mb=round(estimated_memory_mb, 3),
        model_call_count=model_call_count,
        model_called_during_recording=model_called_during_recording,
        passed=passed,
        failure_reason=failure_reason,
    )


def _aggregate_mode_results(
    mode: AiReportBenchmarkMode,
    results: Sequence[AiReportSessionResult],
) -> AiReportAggregateResult:
    mode_results = [result for result in results if result.mode == mode]
    if not mode_results:
        raise ValueError(f"no AI report benchmark results for mode {mode}")
    return AiReportAggregateResult(
        mode=mode,
        sessions=len(mode_results),
        hallucinated_evidence_count=sum(
            result.hallucinated_evidence_count for result in mode_results
        ),
        evidence_citation_valid=all(result.evidence_citation_valid for result in mode_results),
        privacy_leak_count=sum(result.privacy_leak_count for result in mode_results),
        generated_report_evidence_id_coverage=_average(
            [result.generated_report_evidence_id_coverage for result in mode_results]
        ),
        model_unavailable_fallback=all(
            result.model_unavailable_fallback for result in mode_results
        ),
        summary_usefulness_proxy=_average(
            [result.summary_usefulness_proxy for result in mode_results]
        ),
        blocker_precision_proxy=_average(
            [result.blocker_precision_proxy for result in mode_results]
        ),
        blocker_recall_proxy=_average([result.blocker_recall_proxy for result in mode_results]),
        estimated_latency_ms=sum(result.estimated_latency_ms for result in mode_results),
        estimated_memory_mb=_average([result.estimated_memory_mb for result in mode_results]),
        model_call_count=sum(result.model_call_count for result in mode_results),
        model_called_during_recording=any(
            result.model_called_during_recording for result in mode_results
        ),
        passed=all(result.passed for result in mode_results),
    )


def _aggregate_row(result: AiReportAggregateResult) -> str:
    return (
        f"| {result.mode} "
        f"| {result.sessions} "
        f"| {result.hallucinated_evidence_count} "
        f"| {'yes' if result.evidence_citation_valid else 'no'} "
        f"| {result.privacy_leak_count} "
        f"| {result.generated_report_evidence_id_coverage:.3f} "
        f"| {'yes' if result.model_unavailable_fallback else 'no'} "
        f"| {result.summary_usefulness_proxy:.3f} "
        f"| {result.blocker_precision_proxy:.3f} "
        f"| {result.blocker_recall_proxy:.3f} "
        f"| {result.estimated_latency_ms:.3f} "
        f"| {result.estimated_memory_mb:.3f} "
        f"| {result.model_call_count} "
        f"| {'yes' if result.model_called_during_recording else 'no'} "
        f"| {'yes' if result.passed else 'no'} |"
    )


def _fake_report_json(
    *,
    session: GoldenSession,
    timeline: DeterministicTimeline,
    workflow_report: WorkflowDebuggerReport,
) -> str:
    first_evidence_id = timeline.normalized_events[0].evidence_event_id
    timeline_claims = tuple(
        EvidenceClaim(
            title=chunk.label.replace("_", " ").title(),
            text=chunk.summary,
            evidence_event_ids=chunk.evidence_event_ids,
        )
        for chunk in timeline.chunks
    )
    blocker_claims = tuple(
        EvidenceClaim(
            title=finding.title,
            text=finding.description,
            evidence_event_ids=finding.evidence_event_ids,
        )
        for finding in workflow_report.findings
        if finding.type == "blocker_period"
    )
    repeated_claims = tuple(
        EvidenceClaim(
            title=finding.title,
            text=finding.description,
            evidence_event_ids=finding.evidence_event_ids,
        )
        for finding in workflow_report.findings
        if finding.type == "repeated_command"
    )
    important_files = tuple(
        EvidenceClaim(path=step.file_path, evidence_event_ids=step.evidence_event_ids)
        for step in workflow_report.recipe.steps
        if step.file_path is not None
    )
    commands = tuple(
        EvidenceClaim(command=step.command, evidence_event_ids=step.evidence_event_ids)
        for step in workflow_report.recipe.steps
        if step.command is not None
    )
    workflow_steps = tuple(
        EvidenceClaim(
            title=step.title,
            text=step.description,
            evidence_event_ids=step.evidence_event_ids,
        )
        for step in workflow_report.recipe.steps
    )
    payload = {
        "session_title": redact_text(session.title),
        "summary": {
            "text": f"Evidence-backed local report for {redact_text(session.title)}.",
            "evidence_event_ids": [first_evidence_id],
        },
        "timeline": [claim.model_dump(mode="json") for claim in timeline_claims],
        "blockers": [claim.model_dump(mode="json") for claim in blocker_claims],
        "repeated_actions": [claim.model_dump(mode="json") for claim in repeated_claims],
        "important_files": [claim.model_dump(mode="json") for claim in important_files],
        "commands": [claim.model_dump(mode="json") for claim in commands],
        "workflow_steps": [claim.model_dump(mode="json") for claim in workflow_steps],
        "confidence": 0.82,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _session_payload(session: GoldenSession) -> Mapping[str, object]:
    return {
        "id": session.id,
        "title": session.title,
        "status": "stopped",
    }


def _known_evidence_ids(timeline: DeterministicTimeline) -> set[str]:
    return {event.evidence_event_id for event in timeline.normalized_events}


def _workflow_report_evidence_ids(report: WorkflowDebuggerReport) -> tuple[str, ...]:
    evidence_ids = [
        evidence_id for step in report.recipe.steps for evidence_id in step.evidence_event_ids
    ]
    evidence_ids.extend(
        evidence_id for finding in report.findings for evidence_id in finding.evidence_event_ids
    )
    return tuple(evidence_ids)


def _last_model_evidence_ids(model: LocalReportModel) -> tuple[str, ...]:
    outputs = _safe_model_outputs(model)
    if not outputs:
        return ()
    try:
        payload = parse_report_json(outputs[-1])
    except (ValidationError, ValueError):
        return ()
    return tuple(
        evidence_id
        for claim in (
            payload.summary,
            *payload.timeline,
            *payload.blockers,
            *payload.repeated_actions,
            *payload.important_files,
            *payload.commands,
            *payload.workflow_steps,
        )
        for evidence_id in claim.evidence_event_ids
    )


def _safe_model_outputs(model: LocalReportModel) -> tuple[str, ...]:
    if isinstance(model, StaticReportModel):
        return tuple(model.outputs)
    return ()


def _model_call_count(model: LocalReportModel) -> int:
    call_count = getattr(model, "call_count", 0)
    return int(call_count) if isinstance(call_count, int) else 0


def _count_unknown_evidence(evidence_ids: Sequence[str], known_ids: set[str]) -> int:
    return sum(1 for evidence_id in evidence_ids if evidence_id not in known_ids)


def _coverage(evidence_ids: Sequence[str], known_ids: set[str]) -> float:
    if not evidence_ids:
        return 0
    cited_known_ids = {evidence_id for evidence_id in evidence_ids if evidence_id in known_ids}
    return len(cited_known_ids) / len(known_ids) if known_ids else 0


def _summary_usefulness_proxy(value: object) -> float:
    if isinstance(value, str):
        return 1.0 if len(value.strip()) >= 20 else 0.5
    if isinstance(value, list | tuple):
        sequence_value = cast(Sequence[object], value)
        return 1.0 if len(sequence_value) > 0 else 0.0
    return 0.0


def _blocker_precision_recall(
    *,
    workflow_report: WorkflowDebuggerReport,
    expected_blockers: set[str],
) -> tuple[float, float]:
    actual = {
        evidence_id
        for finding in workflow_report.findings
        if finding.type == "blocker_period"
        for evidence_id in finding.evidence_event_ids
    }
    if not actual and not expected_blockers:
        return (1, 1)
    true_positive_count = len(actual & expected_blockers)
    precision = true_positive_count / len(actual) if actual else 0
    recall = true_positive_count / len(expected_blockers) if expected_blockers else 1
    return (precision, recall)


def _estimated_model_latency_ms(mode: AiReportBenchmarkMode, session: GoldenSession) -> float:
    multiplier = 7 if mode == "fake_gemma_e2b" else 11
    return float(len(session.events) * multiplier)


def _estimated_model_memory_mb(mode: AiReportBenchmarkMode) -> float:
    if mode == "fake_gemma_e2b":
        return 3276.8
    if mode == "fake_gemma_e4b_deep":
        return 5120.0
    return 0.0


def _estimated_memory_mb(payload: Mapping[str, object]) -> float:
    storage_bytes = len(json.dumps(payload, sort_keys=True).encode("utf-8"))
    return storage_bytes / (1024 * 1024)


def _average(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("cannot average empty AI report benchmark values")
    return round(sum(values) / len(values), 3)
