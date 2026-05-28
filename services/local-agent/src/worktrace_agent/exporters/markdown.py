from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from worktrace_agent.db.raw_events_repository import list_raw_events
from worktrace_agent.db.repositories import load_session
from worktrace_agent.privacy.redaction import redact_text
from worktrace_agent.timeline.deterministic import (
    DeterministicTimeline,
    build_deterministic_timeline,
)


def export_session_markdown(
    connection: sqlite3.Connection,
    session_id: str,
    export_path: Path,
) -> Path:
    fake_session = load_session(connection, session_id)
    raw_events = list_raw_events(connection, session_id)
    timeline = build_deterministic_timeline(raw_events)
    markdown = render_session_markdown(fake_session.session, timeline)
    redacted_markdown = redact_text(markdown)

    resolved_path = Path(export_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = resolved_path.with_suffix(f"{resolved_path.suffix}.tmp")
    temporary_path.write_text(redacted_markdown, encoding="utf-8")
    temporary_path.replace(resolved_path)
    return resolved_path


def render_session_markdown(
    session: Mapping[str, object],
    timeline: DeterministicTimeline,
) -> str:
    lines = [
        "# WorkTrace Session Export",
        "",
        "Deterministic export generated from local session evidence. No LLM was used.",
        "",
        "## Session",
        "",
        f"- Session ID: `{_string_value(session.get('id'))}`",
        f"- Title: {_string_value(session.get('title'), default='Untitled session')}",
        f"- Goal: {_string_value(session.get('goal'), default='not set')}",
        f"- Project: {_string_value(session.get('project_label'), default='not set')}",
        f"- Tags: {_tags_value(session.get('tags'))}",
        f"- Status: `{_string_value(session.get('status'))}`",
        f"- Started: `{_string_value(session.get('started_at'))}`",
        f"- Ended: `{_string_value(session.get('ended_at'), default='not ended')}`",
        f"- Privacy mode: `{_string_value(session.get('privacy_mode'))}`",
        "",
        "## Timeline",
        "",
    ]

    if timeline.chunks:
        for chunk in timeline.chunks:
            lines.extend(
                [
                    f"- `{chunk.id}` **{chunk.label}**",
                    f"  - Time: `{chunk.start}` to `{chunk.end}`",
                    f"  - Summary: {chunk.summary}",
                    f"  - Evidence: {', '.join(chunk.evidence_event_ids)}",
                    f"  - Confidence: {chunk.confidence:.2f}",
                ]
            )
    else:
        lines.append("- No timeline chunks.")

    lines.extend(["", "## Findings", ""])
    if timeline.findings:
        for finding in timeline.findings:
            lines.extend(
                [
                    f"- `{finding.id}` **{finding.title}**",
                    f"  - Type: `{finding.type}`",
                    f"  - Severity: `{finding.severity}`",
                    f"  - Description: {finding.description}",
                    f"  - Evidence: {', '.join(finding.evidence_event_ids)}",
                    f"  - Confidence: {finding.confidence:.2f}",
                ]
            )
    else:
        lines.append("- No deterministic findings.")

    lines.extend(["", "## Evidence", ""])
    if timeline.normalized_events:
        for event in timeline.normalized_events:
            lines.append(
                "- "
                f"`{event.evidence_event_id}` "
                f"`{event.timestamp}` "
                f"`{event.source}/{event.type}` "
                f"`{event.label}` - {event.summary}"
            )
    else:
        lines.append("- No source events.")

    lines.append("")
    return "\n".join(lines)


def _string_value(value: object, *, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _tags_value(value: object) -> str:
    if not isinstance(value, list):
        return "none"
    raw_tags = cast(list[object], value)
    tags = [str(tag).strip() for tag in raw_tags if str(tag).strip()]
    return ", ".join(tags) if tags else "none"
