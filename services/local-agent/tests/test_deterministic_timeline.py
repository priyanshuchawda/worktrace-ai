import pytest

from worktrace_agent.capture.file_watcher import normalize_file_event
from worktrace_agent.capture.terminal_command_detector import normalize_terminal_command
from worktrace_agent.domain.raw_event import RawEvent, build_raw_event
from worktrace_agent.timeline.deterministic import (
    build_deterministic_timeline,
    build_finding,
    build_timeline_chunk,
)

SESSION_ID = "sess_timeline_001"


def test_golden_raw_events_produce_expected_chunks_and_findings() -> None:
    events = build_golden_events()

    timeline = build_deterministic_timeline(events)

    assert [chunk.label for chunk in timeline.chunks] == [
        "coding",
        "debugging",
        "testing",
        "browser_research",
    ]
    assert [chunk.evidence_event_ids for chunk in timeline.chunks] == [
        (events[0].id, events[1].id),
        (events[2].id, events[3].id),
        (events[4].id,),
        (events[5].id,),
    ]
    assert all(chunk.evidence_event_ids for chunk in timeline.chunks)
    assert all(chunk.confidence > 0 for chunk in timeline.chunks)

    assert [block.label for block in timeline.activity_blocks] == [
        "coding",
        "debugging",
        "testing",
        "browser_research",
    ]
    assert [event.label for event in timeline.normalized_events] == [
        "coding",
        "coding",
        "debugging",
        "debugging",
        "testing",
        "browser_research",
    ]

    assert len(timeline.findings) == 1
    finding = timeline.findings[0]
    assert finding.type == "repeated_command"
    assert finding.severity == "medium"
    assert finding.evidence_event_ids == (events[2].id, events[3].id, events[4].id)


def test_empty_raw_events_produce_empty_timeline() -> None:
    timeline = build_deterministic_timeline([])

    assert timeline.normalized_events == []
    assert timeline.activity_blocks == []
    assert timeline.chunks == []
    assert timeline.findings == []


def test_timeline_chunk_requires_evidence_event_ids() -> None:
    with pytest.raises(ValueError, match="evidence_event_ids"):
        build_timeline_chunk(
            chunk_id="chunk_missing_evidence",
            session_id=SESSION_ID,
            start="2026-05-06T09:14:00+05:30",
            end="2026-05-06T09:15:00+05:30",
            label="coding",
            summary="Coding activity.",
            evidence_event_ids=(),
            confidence=0.9,
        )


def test_finding_requires_evidence_event_ids() -> None:
    with pytest.raises(ValueError, match="evidence_event_ids"):
        build_finding(
            finding_id="finding_missing_evidence",
            session_id=SESSION_ID,
            finding_type="repeated_command",
            title="Repeated command",
            description="Command repeated without evidence.",
            evidence_event_ids=(),
            severity="medium",
            confidence=0.9,
        )


def build_golden_events() -> list[RawEvent]:
    return [
        build_raw_event(
            event_id="evt_active_code",
            session_id=SESSION_ID,
            timestamp="2026-05-06T09:14:00+05:30",
            source="active_window",
            event_type="active_window_changed",
            privacy_level="safe",
            confidence=0.95,
            metadata={"app": "VS Code", "window_title": "timeline.py"},
        ),
        normalize_file_event(
            session_id=SESSION_ID,
            timestamp="2026-05-06T09:15:00+05:30",
            path=r"C:\Users\Admin\Desktop\screen-ai\services\local-agent\timeline.py",
            operation="modified",
        ),
        normalize_terminal_command(
            session_id=SESSION_ID,
            timestamp="2026-05-06T09:16:00+05:30",
            command="uv run --python 3.13 pytest",
            shell="powershell",
            exit_code=1,
        ),
        normalize_terminal_command(
            session_id=SESSION_ID,
            timestamp="2026-05-06T09:17:00+05:30",
            command="uv run --python 3.13 pytest",
            shell="powershell",
            exit_code=1,
        ),
        normalize_terminal_command(
            session_id=SESSION_ID,
            timestamp="2026-05-06T09:18:00+05:30",
            command="uv run --python 3.13 pytest",
            shell="powershell",
            exit_code=0,
        ),
        build_raw_event(
            event_id="evt_active_browser",
            session_id=SESSION_ID,
            timestamp="2026-05-06T09:19:00+05:30",
            source="active_window",
            event_type="active_window_changed",
            privacy_level="safe",
            confidence=0.9,
            metadata={"app": "Chrome", "window_title": "pytest docs"},
        ),
    ]
