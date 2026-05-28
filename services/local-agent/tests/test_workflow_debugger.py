from dataclasses import replace

from worktrace_agent.capture.file_watcher import normalize_file_event
from worktrace_agent.capture.terminal_command_detector import normalize_terminal_command
from worktrace_agent.domain.raw_event import RawEvent, build_raw_event
from worktrace_agent.privacy.redaction import (
    PRIVACY_TEST_CORPUS,
    REDACTION_TOKEN,
    count_privacy_leaks,
)
from worktrace_agent.timeline.deterministic import build_deterministic_timeline
from worktrace_agent.timeline.workflow_debugger import (
    WorkflowDebugFinding,
    build_workflow_debugger_report,
)

SESSION_ID = "sess_workflow_debugger_001"


def test_recipe_steps_all_cite_known_event_evidence() -> None:
    timeline = build_deterministic_timeline(golden_workflow_events())

    report = build_workflow_debugger_report(timeline)
    known_evidence_ids = {event.evidence_event_id for event in timeline.normalized_events}

    assert report.recipe.steps
    for step in report.recipe.steps:
        assert step.evidence_event_ids
        assert set(step.evidence_event_ids).issubset(known_evidence_ids)


def test_golden_workflow_fixture_has_no_invented_recipe_steps() -> None:
    timeline = build_deterministic_timeline(golden_workflow_events())

    report = build_workflow_debugger_report(timeline)
    recipe_evidence_ids = {
        evidence_id for step in report.recipe.steps for evidence_id in step.evidence_event_ids
    }
    source_evidence_ids = {event.evidence_event_id for event in timeline.normalized_events}

    assert recipe_evidence_ids == source_evidence_ids
    assert len(report.recipe.steps) <= len(timeline.normalized_events)


def test_workflow_debugger_detects_repeated_commands_and_blocker_period() -> None:
    timeline = build_deterministic_timeline(golden_workflow_events())

    report = build_workflow_debugger_report(timeline)

    repeated = finding_by_type(report.findings, "repeated_command")
    blocker = finding_by_type(report.findings, "blocker_period")

    assert repeated.evidence_event_ids == ("evt_test_fail_1", "evt_test_fail_2", "evt_test_pass")
    assert blocker.evidence_event_ids == ("evt_test_fail_1", "evt_test_fail_2")
    assert blocker.severity == "medium"


def test_workflow_debugger_detects_test_fix_test_loop() -> None:
    timeline = build_deterministic_timeline(golden_workflow_events())

    report = build_workflow_debugger_report(timeline)

    loop = finding_by_type(report.findings, "test_fix_test_loop")

    assert loop.evidence_event_ids == ("evt_test_fail_2", "evt_file_fix", "evt_test_pass")
    assert "test-fix-test" in loop.title.lower()


def test_workflow_debugger_detects_context_switching() -> None:
    timeline = build_deterministic_timeline(golden_workflow_events())

    report = build_workflow_debugger_report(timeline, context_switch_threshold=3)

    finding = finding_by_type(report.findings, "context_switching")

    assert finding.evidence_event_ids == (
        "evt_window_code_1",
        "evt_window_browser_1",
        "evt_window_code_2",
        "evt_window_terminal_1",
    )
    assert finding.severity == "low"


def test_workflow_debugger_detects_deployment_gap() -> None:
    timeline = build_deterministic_timeline(golden_workflow_events())

    report = build_workflow_debugger_report(timeline)

    finding = finding_by_type(report.findings, "deployment_gap")

    assert finding.evidence_event_ids == ("evt_deploy",)
    assert "verification" in finding.description.lower()


def test_recipe_redacts_secret_command_text() -> None:
    timeline = build_deterministic_timeline(
        [
            normalize_terminal_command(
                session_id=SESSION_ID,
                timestamp="2026-05-06T12:00:00+05:30",
                command=f"curl --api-key {PRIVACY_TEST_CORPUS[0]} https://example.test",
                shell="powershell",
                exit_code=0,
            )
        ]
    )

    report = build_workflow_debugger_report(timeline)
    command_step = report.recipe.steps[0]

    assert REDACTION_TOKEN in command_step.description
    assert count_privacy_leaks(command_step.description) == 0


def finding_by_type(
    findings: tuple[WorkflowDebugFinding, ...],
    finding_type: str,
) -> WorkflowDebugFinding:
    matches = [finding for finding in findings if finding.type == finding_type]
    if not matches:
        raise AssertionError(f"missing finding type: {finding_type}")
    return matches[0]


def golden_workflow_events() -> list[RawEvent]:
    return [
        active_window_event("evt_window_code_1", "2026-05-06T09:00:00+05:30", "VS Code"),
        active_window_event("evt_window_browser_1", "2026-05-06T09:01:00+05:30", "Chrome"),
        active_window_event("evt_window_code_2", "2026-05-06T09:02:00+05:30", "VS Code"),
        active_window_event(
            "evt_window_terminal_1",
            "2026-05-06T09:03:00+05:30",
            "Windows Terminal",
        ),
        terminal_event(
            "evt_test_fail_1",
            "2026-05-06T09:04:00+05:30",
            "uv run --python 3.13 pytest",
            exit_code=1,
        ),
        terminal_event(
            "evt_test_fail_2",
            "2026-05-06T09:05:00+05:30",
            "uv run --python 3.13 pytest",
            exit_code=1,
        ),
        file_event(
            "evt_file_fix",
            "2026-05-06T09:06:00+05:30",
            r"C:\Users\Admin\Desktop\screen-ai\services\local-agent\bug.py",
        ),
        terminal_event(
            "evt_test_pass",
            "2026-05-06T09:07:00+05:30",
            "uv run --python 3.13 pytest",
            exit_code=0,
        ),
        terminal_event(
            "evt_deploy",
            "2026-05-06T09:08:00+05:30",
            "pnpm --dir apps/desktop deploy",
            exit_code=0,
        ),
    ]


def active_window_event(event_id: str, timestamp: str, app: str) -> RawEvent:
    return build_raw_event(
        event_id=event_id,
        session_id=SESSION_ID,
        timestamp=timestamp,
        source="active_window",
        event_type="active_window_changed",
        privacy_level="safe",
        confidence=0.95,
        metadata={"app": app, "window_title": app},
    )


def terminal_event(event_id: str, timestamp: str, command: str, *, exit_code: int) -> RawEvent:
    event = normalize_terminal_command(
        session_id=SESSION_ID,
        timestamp=timestamp,
        command=command,
        shell="powershell",
        exit_code=exit_code,
    )
    return replace(event, id=event_id)


def file_event(event_id: str, timestamp: str, path: str) -> RawEvent:
    event = normalize_file_event(
        session_id=SESSION_ID,
        timestamp=timestamp,
        path=path,
        operation="modified",
    )
    return replace(event, id=event_id)
