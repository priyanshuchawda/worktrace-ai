from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from worktrace_agent.domain.raw_event import RawEvent

TimelineLabel = Literal[
    "coding",
    "terminal",
    "browser_research",
    "debugging",
    "testing",
    "deployment",
    "writing",
    "meeting",
    "idle",
    "unknown",
]
FindingSeverity = Literal["low", "medium", "high"]

TEST_COMMAND_MARKERS = ("pytest", "pnpm test", "npm test", "cargo test", "vitest", "ruff check")


@dataclass(frozen=True)
class NormalizedTimelineEvent:
    id: str
    session_id: str
    timestamp: str
    source: str
    type: str
    label: TimelineLabel
    summary: str
    evidence_event_id: str
    confidence: float
    metadata: dict[str, object]


@dataclass(frozen=True)
class ActivityBlock:
    id: str
    session_id: str
    start: str
    end: str
    label: TimelineLabel
    evidence_event_ids: tuple[str, ...]
    event_count: int
    confidence: float


@dataclass(frozen=True)
class TimelineChunk:
    id: str
    session_id: str
    start: str
    end: str
    label: TimelineLabel
    summary: str
    evidence_event_ids: tuple[str, ...]
    confidence: float


@dataclass(frozen=True)
class Finding:
    id: str
    session_id: str
    type: str
    title: str
    description: str
    evidence_event_ids: tuple[str, ...]
    severity: FindingSeverity
    confidence: float


@dataclass(frozen=True)
class DeterministicTimeline:
    normalized_events: list[NormalizedTimelineEvent]
    activity_blocks: list[ActivityBlock]
    chunks: list[TimelineChunk]
    findings: list[Finding]


def build_deterministic_timeline(raw_events: Sequence[RawEvent]) -> DeterministicTimeline:
    ordered_events = sorted(raw_events, key=lambda event: (event.timestamp, event.id))
    normalized_events = [normalize_raw_event(event) for event in ordered_events]
    activity_blocks = build_activity_blocks(normalized_events)
    chunks = [
        build_timeline_chunk(
            chunk_id=f"{block.session_id}-chunk-{index:03d}",
            session_id=block.session_id,
            start=block.start,
            end=block.end,
            label=block.label,
            summary=summarize_activity_block(block),
            evidence_event_ids=block.evidence_event_ids,
            confidence=block.confidence,
        )
        for index, block in enumerate(activity_blocks)
    ]
    findings = build_basic_findings(normalized_events)

    return DeterministicTimeline(
        normalized_events=normalized_events,
        activity_blocks=activity_blocks,
        chunks=chunks,
        findings=findings,
    )


def normalize_raw_event(event: RawEvent) -> NormalizedTimelineEvent:
    label = classify_event(event)
    return NormalizedTimelineEvent(
        id=f"{event.id}-normalized",
        session_id=event.session_id,
        timestamp=event.timestamp,
        source=event.source,
        type=event.type,
        label=label,
        summary=summarize_event(event, label),
        evidence_event_id=event.id,
        confidence=event.confidence,
        metadata=dict(event.metadata),
    )


def build_activity_blocks(events: Sequence[NormalizedTimelineEvent]) -> list[ActivityBlock]:
    if not events:
        return []

    blocks: list[ActivityBlock] = []
    current_events: list[NormalizedTimelineEvent] = [events[0]]

    for event in events[1:]:
        previous = current_events[-1]
        if event.session_id == previous.session_id and event.label == previous.label:
            current_events.append(event)
            continue

        blocks.append(_activity_block_from_events(current_events, len(blocks)))
        current_events = [event]

    blocks.append(_activity_block_from_events(current_events, len(blocks)))
    return blocks


def build_timeline_chunk(
    *,
    chunk_id: str,
    session_id: str,
    start: str,
    end: str,
    label: TimelineLabel,
    summary: str,
    evidence_event_ids: Sequence[str],
    confidence: float,
) -> TimelineChunk:
    return TimelineChunk(
        id=require_non_empty(chunk_id, "chunk_id"),
        session_id=require_non_empty(session_id, "session_id"),
        start=require_iso_datetime(start, "start"),
        end=require_iso_datetime(end, "end"),
        label=label,
        summary=require_non_empty(summary, "summary"),
        evidence_event_ids=require_evidence_event_ids(evidence_event_ids),
        confidence=require_confidence(confidence),
    )


def build_finding(
    *,
    finding_id: str,
    session_id: str,
    finding_type: str,
    title: str,
    description: str,
    evidence_event_ids: Sequence[str],
    severity: FindingSeverity,
    confidence: float,
) -> Finding:
    return Finding(
        id=require_non_empty(finding_id, "finding_id"),
        session_id=require_non_empty(session_id, "session_id"),
        type=require_non_empty(finding_type, "finding_type"),
        title=require_non_empty(title, "title"),
        description=require_non_empty(description, "description"),
        evidence_event_ids=require_evidence_event_ids(evidence_event_ids),
        severity=severity,
        confidence=require_confidence(confidence),
    )


def build_basic_findings(events: Sequence[NormalizedTimelineEvent]) -> list[Finding]:
    command_events_by_hash: dict[str, list[NormalizedTimelineEvent]] = defaultdict(list)
    for event in events:
        if event.type != "terminal_command":
            continue
        command_hash = event.metadata.get("command_hash")
        if isinstance(command_hash, str) and command_hash:
            command_events_by_hash[command_hash].append(event)

    findings: list[Finding] = []
    for index, command_events in enumerate(command_events_by_hash.values()):
        if len(command_events) < 3:
            continue

        first_event = command_events[0]
        findings.append(
            build_finding(
                finding_id=f"{first_event.session_id}-finding-repeated-command-{index:03d}",
                session_id=first_event.session_id,
                finding_type="repeated_command",
                title="Repeated terminal command",
                description=f"A terminal command appeared {len(command_events)} times.",
                evidence_event_ids=tuple(event.evidence_event_id for event in command_events),
                severity="medium",
                confidence=_average_confidence(command_events),
            )
        )

    return findings


def classify_event(event: RawEvent) -> TimelineLabel:
    if event.type == "terminal_command":
        return _classify_terminal_command(event)
    if event.type == "file_changed":
        return "coding"
    if event.type == "active_window_changed":
        return _classify_active_window(event)
    return "unknown"


def summarize_event(event: RawEvent, label: TimelineLabel) -> str:
    if event.type == "terminal_command":
        command = event.metadata.get("command")
        if isinstance(command, str) and command:
            return f"Ran terminal command: {command}"
        return "Ran terminal command."
    if event.type == "file_changed":
        operation = event.metadata.get("operation")
        path = event.metadata.get("path")
        if isinstance(operation, str) and isinstance(path, str):
            return f"File {operation}: {path}"
        return "File changed."
    if event.type == "active_window_changed":
        app = event.metadata.get("app")
        if isinstance(app, str) and app:
            return f"Active app: {app}"
        return "Active window changed."
    return f"{label.replace('_', ' ')} event."


def summarize_activity_block(block: ActivityBlock) -> str:
    label = block.label.replace("_", " ")
    event_word = "event" if block.event_count == 1 else "events"
    return (
        f"{label.title()} activity from {block.start} to {block.end} "
        f"using {block.event_count} {event_word}."
    )


def require_evidence_event_ids(evidence_event_ids: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(
        require_non_empty(event_id, "evidence_event_ids") for event_id in evidence_event_ids
    )
    if not normalized:
        raise ValueError("evidence_event_ids must contain at least one event ID")
    return normalized


def require_non_empty(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def require_iso_datetime(value: str, field_name: str) -> str:
    require_non_empty(value, field_name)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone offset")
    return value


def require_confidence(value: float) -> float:
    if value < 0 or value > 1:
        raise ValueError("confidence must be between 0 and 1")
    return value


def _activity_block_from_events(
    events: Sequence[NormalizedTimelineEvent],
    index: int,
) -> ActivityBlock:
    if not events:
        raise ValueError("activity block requires at least one event")

    first_event = events[0]
    last_event = events[-1]
    evidence_event_ids = tuple(event.evidence_event_id for event in events)

    return ActivityBlock(
        id=f"{first_event.session_id}-activity-block-{index:03d}",
        session_id=first_event.session_id,
        start=first_event.timestamp,
        end=last_event.timestamp,
        label=first_event.label,
        evidence_event_ids=require_evidence_event_ids(evidence_event_ids),
        event_count=len(events),
        confidence=_average_confidence(events),
    )


def _average_confidence(events: Sequence[NormalizedTimelineEvent]) -> float:
    if not events:
        raise ValueError("confidence requires at least one event")
    return sum(event.confidence for event in events) / len(events)


def _classify_terminal_command(event: RawEvent) -> TimelineLabel:
    command = event.metadata.get("command")
    command_text = command.lower() if isinstance(command, str) else ""
    exit_code = event.metadata.get("exit_code")
    if isinstance(exit_code, int) and exit_code != 0:
        return "debugging"
    if any(marker in command_text for marker in TEST_COMMAND_MARKERS):
        return "testing"
    return "terminal"


def _classify_active_window(event: RawEvent) -> TimelineLabel:
    app = event.metadata.get("app")
    app_name = app.lower() if isinstance(app, str) else ""
    if "chrome" in app_name or "browser" in app_name or "edge" in app_name:
        return "browser_research"
    if "code" in app_name or "visual studio" in app_name:
        return "coding"
    if "terminal" in app_name or "powershell" in app_name:
        return "terminal"
    return "unknown"
