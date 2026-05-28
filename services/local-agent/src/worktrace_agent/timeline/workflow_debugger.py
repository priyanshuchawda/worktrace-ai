from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from worktrace_agent.privacy.redaction import redact_text
from worktrace_agent.timeline.deterministic import (
    DeterministicTimeline,
    FindingSeverity,
    NormalizedTimelineEvent,
    require_confidence,
    require_evidence_event_ids,
    require_non_empty,
)

WorkflowFindingType = Literal[
    "repeated_command",
    "context_switching",
    "test_fix_test_loop",
    "blocker_period",
    "deployment_gap",
]

DEPLOYMENT_MARKERS = ("deploy", "release", "publish")
VERIFICATION_MARKERS = ("test", "pytest", "vitest", "health", "verify", "smoke", "check")


@dataclass(frozen=True)
class WorkflowDebugFinding:
    id: str
    session_id: str
    type: WorkflowFindingType
    title: str
    description: str
    evidence_event_ids: tuple[str, ...]
    severity: FindingSeverity
    confidence: float


@dataclass(frozen=True)
class RecipeStep:
    id: str
    title: str
    description: str
    evidence_event_ids: tuple[str, ...]
    command: str | None = None
    file_path: str | None = None


@dataclass(frozen=True)
class WorkflowRecipe:
    id: str
    session_id: str
    title: str
    steps: tuple[RecipeStep, ...]


@dataclass(frozen=True)
class WorkflowDebuggerReport:
    session_id: str
    findings: tuple[WorkflowDebugFinding, ...]
    recipe: WorkflowRecipe


def build_workflow_debugger_report(
    timeline: DeterministicTimeline,
    *,
    context_switch_threshold: int = 6,
) -> WorkflowDebuggerReport:
    session_id = _session_id_from_timeline(timeline)
    findings = (
        *detect_repeated_command_findings(timeline.normalized_events),
        *detect_context_switching_findings(
            timeline.normalized_events,
            switch_threshold=context_switch_threshold,
        ),
        *detect_test_fix_test_loop_findings(timeline.normalized_events),
        *detect_blocker_period_findings(timeline.normalized_events),
        *detect_deployment_gap_findings(timeline.normalized_events),
    )
    return WorkflowDebuggerReport(
        session_id=session_id,
        findings=findings,
        recipe=build_workflow_recipe(session_id=session_id, events=timeline.normalized_events),
    )


def build_workflow_recipe(
    *,
    session_id: str,
    events: Sequence[NormalizedTimelineEvent],
) -> WorkflowRecipe:
    steps = tuple(
        build_recipe_step(index=index, event=event)
        for index, event in enumerate(events)
        if _is_recipe_event(event)
    )
    return WorkflowRecipe(
        id=f"{session_id}-workflow-recipe",
        session_id=session_id,
        title="Evidence-cited workflow recipe",
        steps=steps,
    )


def build_recipe_step(*, index: int, event: NormalizedTimelineEvent) -> RecipeStep:
    command = _metadata_string(event, "command") if event.type == "terminal_command" else None
    file_path = _metadata_string(event, "path") if event.type == "file_changed" else None
    return RecipeStep(
        id=f"{event.session_id}-recipe-step-{index:03d}",
        title=_recipe_step_title(event),
        description=redact_text(event.summary),
        evidence_event_ids=require_evidence_event_ids((event.evidence_event_id,)),
        command=redact_text(command) if command is not None else None,
        file_path=redact_text(file_path) if file_path is not None else None,
    )


def detect_repeated_command_findings(
    events: Sequence[NormalizedTimelineEvent],
) -> tuple[WorkflowDebugFinding, ...]:
    command_events_by_hash: dict[str, list[NormalizedTimelineEvent]] = defaultdict(list)
    for event in events:
        if event.type != "terminal_command":
            continue
        command_hash = _metadata_string(event, "command_hash")
        if command_hash is not None:
            command_events_by_hash[command_hash].append(event)

    findings: list[WorkflowDebugFinding] = []
    for index, command_events in enumerate(command_events_by_hash.values()):
        if len(command_events) < 3:
            continue
        first_event = command_events[0]
        findings.append(
            build_workflow_finding(
                finding_id=f"{first_event.session_id}-workflow-repeated-command-{index:03d}",
                session_id=first_event.session_id,
                finding_type="repeated_command",
                title="Repeated terminal command",
                description=f"A terminal command appeared {len(command_events)} times.",
                evidence_event_ids=tuple(event.evidence_event_id for event in command_events),
                severity="medium",
                confidence=_average_confidence(command_events),
            )
        )
    return tuple(findings)


def detect_context_switching_findings(
    events: Sequence[NormalizedTimelineEvent],
    *,
    switch_threshold: int,
) -> tuple[WorkflowDebugFinding, ...]:
    window_events = [event for event in events if event.type == "active_window_changed"]
    app_sequence = [_metadata_string(event, "app") for event in window_events]
    app_switch_count = sum(
        1
        for previous, current in zip(app_sequence, app_sequence[1:], strict=False)
        if previous is not None and current is not None and previous != current
    )
    if len(window_events) < switch_threshold or app_switch_count < switch_threshold - 1:
        return ()

    first_event = window_events[0]
    return (
        build_workflow_finding(
            finding_id=f"{first_event.session_id}-workflow-context-switching-000",
            session_id=first_event.session_id,
            finding_type="context_switching",
            title="Frequent context switching",
            description=f"Active app changed {app_switch_count} times across nearby events.",
            evidence_event_ids=tuple(event.evidence_event_id for event in window_events),
            severity="low",
            confidence=_average_confidence(window_events),
        ),
    )


def detect_test_fix_test_loop_findings(
    events: Sequence[NormalizedTimelineEvent],
) -> tuple[WorkflowDebugFinding, ...]:
    for fix_index, fix_event in enumerate(events):
        if fix_event.type != "file_changed":
            continue
        previous_failures = [
            event for event in events[:fix_index] if _is_failed_test_command(event)
        ]
        if not previous_failures:
            continue
        first_event = previous_failures[-1]
        for final_event in events[fix_index + 1 :]:
            if _is_passing_test_command(final_event):
                return (
                    build_workflow_finding(
                        finding_id=f"{first_event.session_id}-workflow-test-fix-test-000",
                        session_id=first_event.session_id,
                        finding_type="test_fix_test_loop",
                        title="Test-fix-test loop",
                        description="A failed test was followed by a file change and passing test.",
                        evidence_event_ids=(
                            first_event.evidence_event_id,
                            fix_event.evidence_event_id,
                            final_event.evidence_event_id,
                        ),
                        severity="medium",
                        confidence=_average_confidence((first_event, fix_event, final_event)),
                    ),
                )
    return ()


def detect_blocker_period_findings(
    events: Sequence[NormalizedTimelineEvent],
) -> tuple[WorkflowDebugFinding, ...]:
    failed_commands = [event for event in events if _is_failed_terminal_command(event)]
    if len(failed_commands) < 2:
        return ()

    first_event = failed_commands[0]
    return (
        build_workflow_finding(
            finding_id=f"{first_event.session_id}-workflow-blocker-period-000",
            session_id=first_event.session_id,
            finding_type="blocker_period",
            title="Repeated failed command period",
            description=(
                f"{len(failed_commands)} failed terminal commands suggest a blocker period."
            ),
            evidence_event_ids=tuple(event.evidence_event_id for event in failed_commands),
            severity="medium",
            confidence=_average_confidence(failed_commands),
        ),
    )


def detect_deployment_gap_findings(
    events: Sequence[NormalizedTimelineEvent],
) -> tuple[WorkflowDebugFinding, ...]:
    findings: list[WorkflowDebugFinding] = []
    for event in events:
        if not _is_deployment_command(event):
            continue
        following_events = events[events.index(event) + 1 :]
        has_verification = any(
            _is_verification_command(candidate) for candidate in following_events
        )
        if has_verification:
            continue
        findings.append(
            build_workflow_finding(
                finding_id=f"{event.session_id}-workflow-deployment-gap-{len(findings):03d}",
                session_id=event.session_id,
                finding_type="deployment_gap",
                title="Deployment verification gap",
                description="Deployment command was not followed by an obvious verification step.",
                evidence_event_ids=(event.evidence_event_id,),
                severity="high",
                confidence=event.confidence,
            )
        )
    return tuple(findings)


def build_workflow_finding(
    *,
    finding_id: str,
    session_id: str,
    finding_type: WorkflowFindingType,
    title: str,
    description: str,
    evidence_event_ids: Sequence[str],
    severity: FindingSeverity,
    confidence: float,
) -> WorkflowDebugFinding:
    return WorkflowDebugFinding(
        id=require_non_empty(finding_id, "finding_id"),
        session_id=require_non_empty(session_id, "session_id"),
        type=finding_type,
        title=redact_text(require_non_empty(title, "title")),
        description=redact_text(require_non_empty(description, "description")),
        evidence_event_ids=require_evidence_event_ids(evidence_event_ids),
        severity=severity,
        confidence=require_confidence(confidence),
    )


def _session_id_from_timeline(timeline: DeterministicTimeline) -> str:
    for event in timeline.normalized_events:
        return event.session_id
    return "empty-session"


def _is_recipe_event(event: NormalizedTimelineEvent) -> bool:
    return event.type in {"active_window_changed", "file_changed", "terminal_command"}


def _recipe_step_title(event: NormalizedTimelineEvent) -> str:
    if event.type == "terminal_command":
        exit_code = event.metadata.get("exit_code")
        if isinstance(exit_code, int) and exit_code != 0:
            return "Run failing command"
        return "Run command"
    if event.type == "file_changed":
        return "Change file"
    if event.type == "active_window_changed":
        return "Open workspace context"
    return "Review evidence"


def _metadata_string(event: NormalizedTimelineEvent, key: str) -> str | None:
    value = event.metadata.get(key)
    if isinstance(value, str) and value.strip():
        return value
    return None


def _is_failed_terminal_command(event: NormalizedTimelineEvent) -> bool:
    if event.type != "terminal_command":
        return False
    exit_code = event.metadata.get("exit_code")
    return isinstance(exit_code, int) and exit_code != 0


def _is_failed_test_command(event: NormalizedTimelineEvent) -> bool:
    return _is_failed_terminal_command(event) and _is_test_command(event)


def _is_passing_test_command(event: NormalizedTimelineEvent) -> bool:
    if event.type != "terminal_command" or not _is_test_command(event):
        return False
    exit_code = event.metadata.get("exit_code")
    return isinstance(exit_code, int) and exit_code == 0


def _is_test_command(event: NormalizedTimelineEvent) -> bool:
    command = _metadata_string(event, "command")
    return command is not None and any(marker in command.lower() for marker in VERIFICATION_MARKERS)


def _is_deployment_command(event: NormalizedTimelineEvent) -> bool:
    if event.type != "terminal_command":
        return False
    command = _metadata_string(event, "command")
    return command is not None and any(marker in command.lower() for marker in DEPLOYMENT_MARKERS)


def _is_verification_command(event: NormalizedTimelineEvent) -> bool:
    if event.type != "terminal_command":
        return False
    command = _metadata_string(event, "command")
    return command is not None and any(marker in command.lower() for marker in VERIFICATION_MARKERS)


def _average_confidence(events: Sequence[NormalizedTimelineEvent]) -> float:
    if not events:
        raise ValueError("confidence requires at least one event")
    return sum(event.confidence for event in events) / len(events)
