from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from worktrace_agent.domain.raw_event import RawEvent, build_raw_event
from worktrace_agent.privacy.redaction import count_privacy_leaks
from worktrace_agent.timeline.deterministic import build_deterministic_timeline
from worktrace_agent.timeline.workflow_debugger import (
    WorkflowDebugFinding,
    build_workflow_debugger_report,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_GOLDEN_SESSIONS_PATH = (
    REPO_ROOT / "datasets" / "golden-sessions" / "worktrace_golden_sessions.json"
)
EXPECTED_GOLDEN_SESSION_COUNT = 20


@dataclass(frozen=True)
class GoldenExpectations:
    timeline_labels: tuple[str, ...]
    finding_types: tuple[str, ...]
    blocker_event_ids: tuple[str, ...]


@dataclass(frozen=True)
class GoldenSession:
    id: str
    title: str
    events: tuple[RawEvent, ...]
    expectations: GoldenExpectations
    raw_payload: Mapping[str, object]


@dataclass(frozen=True)
class EvalSessionResult:
    session_id: str
    title: str
    timeline_accuracy: float
    blocker_precision: float
    blocker_recall: float
    hallucinated_event_count: int
    privacy_leak_count: int
    estimated_latency_ms: float
    estimated_ram_mb: float
    storage_bytes: int
    passed: bool


@dataclass(frozen=True)
class EvalResults:
    session_results: tuple[EvalSessionResult, ...]
    aggregate: EvalSessionResult


def load_golden_sessions(path: Path = DEFAULT_GOLDEN_SESSIONS_PATH) -> tuple[GoldenSession, ...]:
    raw_payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw_payload, dict):
        raise ValueError("golden sessions dataset must be a JSON object")

    payload = cast(Mapping[str, object], raw_payload)
    sessions_payload = _required_list(payload, "sessions")
    if len(sessions_payload) != EXPECTED_GOLDEN_SESSION_COUNT:
        raise ValueError("dataset must contain exactly 20 golden sessions")

    sessions = tuple(
        _parse_golden_session(cast(Mapping[str, object], session_payload))
        for session_payload in sessions_payload
    )
    session_ids = [session.id for session in sessions]
    if len(set(session_ids)) != len(session_ids):
        raise ValueError("golden session IDs must be unique")
    return sessions


def evaluate_golden_sessions(
    path: Path = DEFAULT_GOLDEN_SESSIONS_PATH,
) -> EvalResults:
    session_results = tuple(
        evaluate_golden_session(session) for session in load_golden_sessions(path)
    )
    return EvalResults(
        session_results=session_results,
        aggregate=_aggregate_results(session_results),
    )


def evaluate_golden_session(session: GoldenSession) -> EvalSessionResult:
    timeline = build_deterministic_timeline(session.events)
    workflow_report = build_workflow_debugger_report(timeline)
    known_event_ids = {event.id for event in session.events}
    actual_finding_types = {finding.type for finding in workflow_report.findings}
    actual_blocker_event_ids = _finding_event_ids_by_type(
        workflow_report.findings,
        finding_type="blocker_period",
    )
    hallucinated_event_count = _count_hallucinated_evidence(
        known_event_ids=known_event_ids,
        workflow_report=workflow_report,
    )
    privacy_leak_count = count_privacy_leaks(
        {
            "session": session.raw_payload,
            "recipe": asdict(workflow_report.recipe),
            "findings": [asdict(finding) for finding in workflow_report.findings],
        }
    )
    storage_bytes = len(
        json.dumps(session.raw_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )

    timeline_accuracy = _timeline_accuracy(
        actual_labels=tuple(chunk.label for chunk in timeline.chunks),
        expected_labels=session.expectations.timeline_labels,
    )
    blocker_precision, blocker_recall = _precision_recall(
        actual=set(actual_blocker_event_ids),
        expected=set(session.expectations.blocker_event_ids),
    )
    expected_finding_types = set(session.expectations.finding_types)
    finding_types_pass = expected_finding_types.issubset(actual_finding_types)

    return EvalSessionResult(
        session_id=session.id,
        title=session.title,
        timeline_accuracy=timeline_accuracy,
        blocker_precision=blocker_precision,
        blocker_recall=blocker_recall,
        hallucinated_event_count=hallucinated_event_count,
        privacy_leak_count=privacy_leak_count,
        estimated_latency_ms=float(len(session.events) * 2),
        estimated_ram_mb=round(storage_bytes / (1024 * 1024), 3),
        storage_bytes=storage_bytes,
        passed=(
            timeline_accuracy == 1
            and blocker_precision == 1
            and blocker_recall == 1
            and hallucinated_event_count == 0
            and privacy_leak_count == 0
            and finding_types_pass
        ),
    )


def render_benchmark_table(results: EvalResults) -> str:
    rows = [
        "| session_id | timeline_accuracy | blocker_precision | blocker_recall | "
        "hallucinated_event_count | privacy_leak_count | estimated_latency_ms | "
        "estimated_ram_mb | storage_bytes | passed |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for result in (*results.session_results, results.aggregate):
        rows.append(_result_row(result))
    return "\n".join(rows)


def _result_row(result: EvalSessionResult) -> str:
    return (
        f"| {result.session_id} "
        f"| {result.timeline_accuracy:.2f} "
        f"| {result.blocker_precision:.2f} "
        f"| {result.blocker_recall:.2f} "
        f"| {result.hallucinated_event_count} "
        f"| {result.privacy_leak_count} "
        f"| {result.estimated_latency_ms:.2f} "
        f"| {result.estimated_ram_mb:.3f} "
        f"| {result.storage_bytes} "
        f"| {'yes' if result.passed else 'no'} |"
    )


def _parse_golden_session(payload: Mapping[str, object]) -> GoldenSession:
    events_payload = _required_list(payload, "events")
    expectations_payload = _required_mapping(payload, "expectations")
    return GoldenSession(
        id=_required_string(payload, "id"),
        title=_required_string(payload, "title"),
        events=tuple(
            _parse_raw_event(cast(Mapping[str, object], event_payload))
            for event_payload in events_payload
        ),
        expectations=GoldenExpectations(
            timeline_labels=_string_tuple(expectations_payload, "timeline_labels"),
            finding_types=_string_tuple(expectations_payload, "finding_types"),
            blocker_event_ids=_string_tuple(expectations_payload, "blocker_event_ids"),
        ),
        raw_payload=payload,
    )


def _parse_raw_event(payload: Mapping[str, object]) -> RawEvent:
    return build_raw_event(
        event_id=_required_string(payload, "id"),
        session_id=_required_string(payload, "session_id"),
        timestamp=_required_string(payload, "timestamp"),
        source=_required_string(payload, "source"),
        event_type=_required_string(payload, "type"),
        privacy_level=_required_string(payload, "privacy_level"),
        confidence=_required_float(payload, "confidence"),
        metadata=_required_dict(payload, "metadata"),
    )


def _aggregate_results(results: Sequence[EvalSessionResult]) -> EvalSessionResult:
    if not results:
        raise ValueError("cannot aggregate empty eval results")
    return EvalSessionResult(
        session_id="aggregate",
        title="Aggregate",
        timeline_accuracy=_average([result.timeline_accuracy for result in results]),
        blocker_precision=_average([result.blocker_precision for result in results]),
        blocker_recall=_average([result.blocker_recall for result in results]),
        hallucinated_event_count=sum(result.hallucinated_event_count for result in results),
        privacy_leak_count=sum(result.privacy_leak_count for result in results),
        estimated_latency_ms=sum(result.estimated_latency_ms for result in results),
        estimated_ram_mb=round(sum(result.estimated_ram_mb for result in results), 3),
        storage_bytes=sum(result.storage_bytes for result in results),
        passed=all(result.passed for result in results),
    )


def _timeline_accuracy(*, actual_labels: Sequence[str], expected_labels: Sequence[str]) -> float:
    if not actual_labels and not expected_labels:
        return 1
    denominator = max(len(actual_labels), len(expected_labels))
    matches = sum(
        1
        for actual, expected in zip(actual_labels, expected_labels, strict=False)
        if actual == expected
    )
    return matches / denominator


def _precision_recall(*, actual: set[str], expected: set[str]) -> tuple[float, float]:
    if not actual and not expected:
        return (1, 1)
    true_positive_count = len(actual & expected)
    precision = true_positive_count / len(actual) if actual else 0
    recall = true_positive_count / len(expected) if expected else 1
    return (precision, recall)


def _count_hallucinated_evidence(
    *,
    known_event_ids: set[str],
    workflow_report: Any,
) -> int:
    evidence_ids = [
        evidence_id
        for step in workflow_report.recipe.steps
        for evidence_id in step.evidence_event_ids
    ]
    evidence_ids.extend(
        evidence_id
        for finding in workflow_report.findings
        for evidence_id in finding.evidence_event_ids
    )
    return sum(1 for evidence_id in evidence_ids if evidence_id not in known_event_ids)


def _finding_event_ids_by_type(
    findings: Sequence[WorkflowDebugFinding],
    *,
    finding_type: str,
) -> tuple[str, ...]:
    event_ids: list[str] = []
    for finding in findings:
        if finding.type == finding_type:
            event_ids.extend(finding.evidence_event_ids)
    return tuple(event_ids)


def _required_mapping(payload: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return cast(Mapping[str, object], value)


def _required_list(payload: Mapping[str, object], key: str) -> list[object]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    return cast(list[object], value)


def _required_dict(payload: Mapping[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return cast(dict[str, object], value)


def _required_string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _required_float(payload: Mapping[str, object], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, int | float):
        raise ValueError(f"{key} must be a number")
    return float(value)


def _string_tuple(payload: Mapping[str, object], key: str) -> tuple[str, ...]:
    values = _required_list(payload, key)
    if not all(isinstance(value, str) and value.strip() for value in values):
        raise ValueError(f"{key} must contain only non-empty strings")
    return tuple(cast(list[str], values))


def _average(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("cannot average empty values")
    return sum(values) / len(values)
