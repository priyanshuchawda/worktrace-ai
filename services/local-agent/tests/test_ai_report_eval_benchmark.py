from __future__ import annotations

import json
from collections.abc import Sequence

from worktrace_agent.evals.ai_report_benchmark import (
    AI_REPORT_BENCHMARK_MODES,
    StaticReportModel,
    evaluate_ai_report_benchmark,
    evaluate_ai_report_session,
    render_ai_report_benchmark_table,
)
from worktrace_agent.evals.golden_sessions import DEFAULT_GOLDEN_SESSIONS_PATH, load_golden_sessions


def test_ai_report_benchmark_includes_expected_modes_and_reproducible_table() -> None:
    first_results = evaluate_ai_report_benchmark(DEFAULT_GOLDEN_SESSIONS_PATH)
    second_results = evaluate_ai_report_benchmark(DEFAULT_GOLDEN_SESSIONS_PATH)

    assert AI_REPORT_BENCHMARK_MODES == (
        "deterministic_report",
        "fake_gemma_e2b",
        "fake_gemma_e4b_deep",
        "model_unavailable",
    )
    assert {result.mode for result in first_results.aggregate_results} == set(
        AI_REPORT_BENCHMARK_MODES
    )
    assert render_ai_report_benchmark_table(first_results) == render_ai_report_benchmark_table(
        second_results
    )
    assert "| mode | sessions | hallucinated_evidence_count |" in (
        render_ai_report_benchmark_table(first_results)
    )
    assert "estimated_latency_ms" in render_ai_report_benchmark_table(first_results)
    assert "estimated_memory_mb" in render_ai_report_benchmark_table(first_results)


def test_generated_ai_report_modes_cite_valid_evidence_and_leak_no_privacy() -> None:
    results = evaluate_ai_report_benchmark(DEFAULT_GOLDEN_SESSIONS_PATH)

    generated_results = [
        result
        for result in results.session_results
        if result.mode in {"fake_gemma_e2b", "fake_gemma_e4b_deep"}
    ]

    assert generated_results
    assert all(result.evidence_citation_valid for result in generated_results)
    assert all(result.generated_report_evidence_id_coverage > 0 for result in generated_results)
    assert all(result.hallucinated_evidence_count == 0 for result in generated_results)
    assert all(result.privacy_leak_count == 0 for result in generated_results)


def test_invalid_generated_evidence_ids_fail_ai_report_eval() -> None:
    session = load_golden_sessions(DEFAULT_GOLDEN_SESSIONS_PATH)[0]
    result = evaluate_ai_report_session(
        session,
        mode="fake_gemma_e2b",
        model=StaticReportModel([_report_json(evidence_event_ids=("not_a_real_evidence_id",))]),
    )

    assert result.passed is False
    assert result.evidence_citation_valid is False
    assert result.hallucinated_evidence_count == 1
    assert "unknown evidence" in (result.failure_reason or "")


def test_model_unavailable_fallback_is_recorded_without_model_call() -> None:
    results = evaluate_ai_report_benchmark(DEFAULT_GOLDEN_SESSIONS_PATH)
    unavailable_results = [
        result for result in results.session_results if result.mode == "model_unavailable"
    ]

    assert unavailable_results
    assert all(result.model_unavailable_fallback for result in unavailable_results)
    assert all(result.model_call_count == 0 for result in unavailable_results)
    assert all(result.passed for result in unavailable_results)


def test_ai_report_eval_records_no_model_run_during_recording() -> None:
    results = evaluate_ai_report_benchmark(DEFAULT_GOLDEN_SESSIONS_PATH)

    assert all(not result.model_called_during_recording for result in results.session_results)
    assert all(result.passed for result in results.session_results)


def _report_json(
    *,
    evidence_event_ids: Sequence[str],
) -> str:
    evidence = list(evidence_event_ids)
    return json.dumps(
        {
            "session_title": "Invalid evidence fixture",
            "summary": {
                "text": "This deliberately cites benchmark-supplied evidence.",
                "evidence_event_ids": evidence,
            },
            "timeline": [],
            "blockers": [],
            "repeated_actions": [],
            "important_files": [],
            "commands": [],
            "workflow_steps": [],
            "confidence": 0.5,
        }
    )
