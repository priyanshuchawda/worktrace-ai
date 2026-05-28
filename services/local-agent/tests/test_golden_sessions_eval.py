from pathlib import Path

from worktrace_agent.evals.golden_sessions import (
    DEFAULT_GOLDEN_SESSIONS_PATH,
    evaluate_golden_sessions,
    load_golden_sessions,
    render_benchmark_table,
)


def test_golden_dataset_contains_twenty_unique_sessions() -> None:
    sessions = load_golden_sessions(DEFAULT_GOLDEN_SESSIONS_PATH)

    assert len(sessions) == 20
    assert len({session.id for session in sessions}) == 20
    assert all(session.events for session in sessions)


def test_eval_runner_returns_one_result_per_golden_session() -> None:
    results = evaluate_golden_sessions(DEFAULT_GOLDEN_SESSIONS_PATH)

    assert len(results.session_results) == 20
    assert results.aggregate.session_id == "aggregate"
    assert results.aggregate.hallucinated_event_count == 0
    assert results.aggregate.privacy_leak_count == 0


def test_benchmark_table_is_reproducible() -> None:
    first_table = render_benchmark_table(evaluate_golden_sessions(DEFAULT_GOLDEN_SESSIONS_PATH))
    second_table = render_benchmark_table(evaluate_golden_sessions(DEFAULT_GOLDEN_SESSIONS_PATH))

    assert first_table == second_table
    assert "| session_id | timeline_accuracy | blocker_precision | blocker_recall |" in first_table
    assert "estimated_latency_ms" in first_table
    assert "estimated_ram_mb" in first_table
    assert "storage_bytes" in first_table


def test_every_recipe_step_uses_known_event_evidence() -> None:
    results = evaluate_golden_sessions(DEFAULT_GOLDEN_SESSIONS_PATH)

    assert all(result.hallucinated_event_count == 0 for result in results.session_results)


def test_privacy_leak_count_is_zero_for_all_golden_sessions() -> None:
    results = evaluate_golden_sessions(DEFAULT_GOLDEN_SESSIONS_PATH)

    assert all(result.privacy_leak_count == 0 for result in results.session_results)


def test_loader_rejects_dataset_without_twenty_sessions(tmp_path: Path) -> None:
    bad_dataset = tmp_path / "bad.json"
    bad_dataset.write_text('{"sessions": []}', encoding="utf-8")

    try:
        load_golden_sessions(bad_dataset)
    except ValueError as error:
        assert "20 golden sessions" in str(error)
    else:
        raise AssertionError("expected invalid golden dataset to fail")
