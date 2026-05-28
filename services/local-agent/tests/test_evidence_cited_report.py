import json
from collections.abc import Sequence
from typing import cast

import pytest
from pydantic import ValidationError

from worktrace_agent.ai.reporting import (
    HallucinationGuardError,
    ReportGenerationError,
    build_report_prompt,
    generate_evidence_cited_report,
    parse_report_json,
)
from worktrace_agent.domain.raw_event import RawEvent, build_raw_event
from worktrace_agent.privacy.redaction import PRIVACY_TEST_CORPUS, count_privacy_leaks
from worktrace_agent.timeline.deterministic import build_deterministic_timeline

SESSION = {
    "id": "sess_report_001",
    "title": "Report fixture",
    "started_at": "2026-05-06T09:14:00+05:30",
    "ended_at": "2026-05-06T09:20:00+05:30",
    "status": "stopped",
    "privacy_mode": "standard",
}


def test_invalid_json_retries_once_and_returns_evidence_cited_report() -> None:
    timeline = build_deterministic_timeline(report_fixture_events())
    model = FakeLocalReportModel(["{not-json", valid_report_json()])

    report = generate_evidence_cited_report(
        session=SESSION,
        timeline=timeline,
        model=model,
        model_name="fake-local-report-model",
        model_version="test-v1",
        generated_at="2026-05-06T09:21:00+05:30",
    )

    assert model.call_count == 2
    assert report.session_id == SESSION["id"]
    assert report.summary.evidence_event_ids == ("evt_report_terminal",)
    assert report.model_metadata.model_name == "fake-local-report-model"


def test_hallucination_guard_rejects_unknown_evidence_ids() -> None:
    timeline = build_deterministic_timeline(report_fixture_events())
    model = FakeLocalReportModel([valid_report_json(evidence_event_ids=["evt_missing"])])

    with pytest.raises(HallucinationGuardError, match="unknown evidence"):
        generate_evidence_cited_report(
            session=SESSION,
            timeline=timeline,
            model=model,
            model_name="fake-local-report-model",
            generated_at="2026-05-06T09:21:00+05:30",
        )


def test_report_claim_without_evidence_is_rejected_by_pydantic_schema() -> None:
    payload = valid_report_payload()
    summary = cast(dict[str, object], payload["summary"])
    summary["evidence_event_ids"] = []

    with pytest.raises(ValidationError):
        parse_report_json(json.dumps(payload))


def test_every_report_claim_cites_known_evidence_ids() -> None:
    timeline = build_deterministic_timeline(report_fixture_events())
    model = FakeLocalReportModel([valid_report_json()])

    report = generate_evidence_cited_report(
        session=SESSION,
        timeline=timeline,
        model=model,
        model_name="fake-local-report-model",
        generated_at="2026-05-06T09:21:00+05:30",
    )

    all_claims = [
        report.summary,
        *report.timeline,
        *report.blockers,
        *report.repeated_actions,
        *report.important_files,
        *report.commands,
        *report.workflow_steps,
    ]

    assert all(claim.evidence_event_ids for claim in all_claims)
    assert all(
        evidence_id in report.known_evidence_event_ids
        for claim in all_claims
        for evidence_id in claim.evidence_event_ids
    )


def test_daily_review_sections_are_validated_and_cited() -> None:
    timeline = build_deterministic_timeline(report_fixture_events())
    payload = valid_report_payload()
    payload["observed_work"] = [
        {
            "title": "Worked in the local-agent report tests",
            "text": "The session included report test activity in the editor.",
            "evidence_event_ids": ["evt_report_window"],
        }
    ]
    payload["context_switches"] = [
        {
            "title": "Editor to terminal",
            "text": "The activity moved from VS Code to a terminal test run.",
            "evidence_event_ids": ["evt_report_window", "evt_report_terminal"],
        }
    ]
    payload["unfinished_work"] = [
        {
            "title": "Review remaining report UX",
            "text": "The captured evidence shows report test work, with more UI review still open.",
            "evidence_event_ids": ["evt_report_window"],
        }
    ]
    payload["continuation_notes"] = [
        {
            "title": "Suggested next step",
            "text": (
                "Suggestion: review the desktop report preview using the cited session evidence."
            ),
            "evidence_event_ids": ["evt_report_window", "evt_report_terminal"],
        }
    ]
    model = FakeLocalReportModel([json.dumps(payload)])

    report = generate_evidence_cited_report(
        session=SESSION,
        timeline=timeline,
        model=model,
        model_name="fake-local-report-model",
        generated_at="2026-05-06T09:21:00+05:30",
    )

    assert report.observed_work[0].evidence_event_ids == ("evt_report_window",)
    assert report.context_switches[0].evidence_event_ids == (
        "evt_report_window",
        "evt_report_terminal",
    )
    assert report.unfinished_work[0].title == "Review remaining report UX"
    assert report.continuation_notes[0].title == "Suggested next step"
    assert all(claim.evidence_event_ids for claim in report.all_claims())


def test_completion_claim_without_completion_evidence_is_rejected() -> None:
    timeline = build_deterministic_timeline(report_fixture_events())
    payload = valid_report_payload(evidence_event_ids=["evt_report_window"])
    summary = cast(dict[str, object], payload["summary"])
    summary["text"] = "Completed the report UX implementation."
    model = FakeLocalReportModel([json.dumps(payload)])

    with pytest.raises(HallucinationGuardError, match="completion claim"):
        generate_evidence_cited_report(
            session=SESSION,
            timeline=timeline,
            model=model,
            model_name="fake-local-report-model",
            generated_at="2026-05-06T09:21:00+05:30",
        )


def test_report_prompt_redacts_secrets_and_lists_evidence_ids() -> None:
    timeline = build_deterministic_timeline(report_fixture_events())

    prompt = build_report_prompt(session=SESSION, timeline=timeline)

    assert "evt_report_terminal" in prompt
    assert "evt_report_window" in prompt
    assert count_privacy_leaks(prompt) == 0


def test_report_generation_failure_after_retry_is_safe_and_redacted() -> None:
    timeline = build_deterministic_timeline(report_fixture_events())
    model = FakeLocalReportModel(
        [
            f"not json {PRIVACY_TEST_CORPUS[0]}",
            f"still not json {PRIVACY_TEST_CORPUS[1]}",
        ]
    )

    with pytest.raises(ReportGenerationError) as error:
        generate_evidence_cited_report(
            session=SESSION,
            timeline=timeline,
            model=model,
            model_name="fake-local-report-model",
            generated_at="2026-05-06T09:21:00+05:30",
        )

    assert model.call_count == 2
    assert count_privacy_leaks(str(error.value)) == 0


class FakeLocalReportModel:
    def __init__(self, responses: Sequence[str]) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []

    @property
    def call_count(self) -> int:
        return len(self.prompts)

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.responses:
            raise AssertionError("fake model has no responses left")
        return self.responses.pop(0)


def report_fixture_events() -> list[RawEvent]:
    return [
        build_raw_event(
            event_id="evt_report_window",
            session_id=str(SESSION["id"]),
            timestamp="2026-05-06T09:14:00+05:30",
            source="active_window",
            event_type="active_window_changed",
            privacy_level="safe",
            confidence=0.95,
            metadata={"app": "VS Code", "window_title": "reporting.py"},
        ),
        build_raw_event(
            event_id="evt_report_terminal",
            session_id=str(SESSION["id"]),
            timestamp="2026-05-06T09:15:00+05:30",
            source="terminal_command_detector",
            event_type="terminal_command",
            privacy_level="sensitive",
            confidence=1,
            metadata={
                "command": f"uv run --python 3.13 pytest {PRIVACY_TEST_CORPUS[0]}",
                "shell": "powershell",
                "exit_code": 0,
                "command_hash": "hash-report-terminal",
            },
        ),
    ]


def valid_report_json(*, evidence_event_ids: Sequence[str] = ("evt_report_terminal",)) -> str:
    return json.dumps(valid_report_payload(evidence_event_ids=evidence_event_ids))


def valid_report_payload(
    *,
    evidence_event_ids: Sequence[str] = ("evt_report_terminal",),
) -> dict[str, object]:
    evidence = list(evidence_event_ids)
    return {
        "session_title": "Report fixture",
        "summary": {
            "text": "The session ran the Python test suite.",
            "evidence_event_ids": evidence,
        },
        "timeline": [
            {
                "title": "Testing",
                "text": "Ran pytest from the terminal.",
                "evidence_event_ids": evidence,
            }
        ],
        "blockers": [],
        "repeated_actions": [],
        "important_files": [
            {
                "path": "services/local-agent/tests/test_evidence_cited_report.py",
                "evidence_event_ids": ["evt_report_window"],
            }
        ],
        "commands": [
            {
                "command": "uv run --python 3.13 pytest",
                "evidence_event_ids": evidence,
            }
        ],
        "workflow_steps": [
            {
                "title": "Run local-agent tests",
                "text": "Use uv with Python 3.13 for pytest.",
                "evidence_event_ids": evidence,
            }
        ],
        "confidence": 0.86,
    }
