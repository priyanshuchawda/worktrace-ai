# Laptop Readiness Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a short real-machine readiness benchmark that proves the recorder can run on a Windows laptop for a 5-10 minute portfolio smoke without storing private artifacts in the repository.

**Architecture:** Add a Python benchmark runner under `worktrace_agent.performance` that starts the existing `SessionRecorderService` in a temporary workspace, samples process CPU/RAM/storage while active-window and screenshot workers run, evaluates the existing resource budget model with a duration-specific budget, and renders a safe Markdown/JSON report. Expose it through a small console script and document the exact 5-minute command.

**Tech Stack:** Python 3.13, asyncio, existing FastAPI sidecar service modules, SQLite WAL, existing resource budget evaluator, pytest.

---

### Task 1: Benchmark Core

**Files:**
- Create: `services/local-agent/tests/test_laptop_readiness_benchmark.py`
- Create: `services/local-agent/src/worktrace_agent/performance/laptop_readiness.py`

- [ ] **Step 1: Write failing tests for result rendering and safe defaults**

```python
def test_laptop_readiness_markdown_is_safe_and_honest() -> None:
    result = benchmark_result_fixture(passed=True, cleaned=True)

    markdown = render_laptop_readiness_markdown(result)

    assert "Short Laptop Readiness Benchmark" in markdown
    assert "This is a short 5-10 minute readiness smoke, not a 30-minute production benchmark." in markdown
    assert "raw active-window titles are not included" in markdown
    assert "| average_cpu_percent | 4.00 | 15.00 | yes |" in markdown
    assert "C:\\Users" not in markdown
```

- [ ] **Step 2: Run the new test and verify RED**

Run: `uv run --python 3.13 pytest tests/test_laptop_readiness_benchmark.py -q`

Expected: FAIL with `ModuleNotFoundError` for `worktrace_agent.performance.laptop_readiness`.

- [ ] **Step 3: Implement dataclasses, safe Markdown rendering, process RAM helper, and budget evaluation wrapper**

```python
@dataclass(frozen=True)
class LaptopReadinessBenchmarkResult:
    session_id: str
    started_at: str
    finished_at: str
    duration_seconds: float
    sample_interval_seconds: float
    event_count: int
    screenshot_count: int
    temp_workspace_cleaned: bool
    artifact_root_retained: str | None
    report: RecordingResourceBudgetReport

def render_laptop_readiness_markdown(result: LaptopReadinessBenchmarkResult) -> str:
    ...
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `uv run --python 3.13 pytest tests/test_laptop_readiness_benchmark.py -q`

Expected: PASS.

### Task 2: Async Recorder Runner

**Files:**
- Modify: `services/local-agent/tests/test_laptop_readiness_benchmark.py`
- Modify: `services/local-agent/src/worktrace_agent/performance/laptop_readiness.py`

- [ ] **Step 1: Write failing test using fake active-window and screenshot providers**

```python
def test_laptop_readiness_benchmark_runs_with_fake_capture_and_cleans_workspace(tmp_path: Path) -> None:
    result = asyncio.run(
        run_laptop_readiness_benchmark(
            duration_seconds=0.05,
            sample_interval_seconds=0.01,
            workspace_root=tmp_path / "bench",
            active_window_provider=StaticActiveWindowProvider(),
            screenshot_provider=StaticScreenshotProvider(),
        )
    )

    assert result.event_count >= 1
    assert result.screenshot_count >= 1
    assert result.temp_workspace_cleaned is True
    assert not (tmp_path / "bench").exists()
    assert result.report.budget.recording_duration_minutes == 0.05 / 60
```

- [ ] **Step 2: Run focused test and verify RED**

Run: `uv run --python 3.13 pytest tests/test_laptop_readiness_benchmark.py -q`

Expected: FAIL because `run_laptop_readiness_benchmark` is not implemented.

- [ ] **Step 3: Implement async runner**

Use the existing `SessionRecorderService`, start a temporary recording session, sample `estimate_storage_growth`, stop workers, evaluate resource budget, close the service, then delete the workspace unless `keep_artifacts=True`.

- [ ] **Step 4: Run focused test and verify GREEN**

Run: `uv run --python 3.13 pytest tests/test_laptop_readiness_benchmark.py -q`

Expected: PASS.

### Task 3: CLI and Documentation

**Files:**
- Create: `services/local-agent/src/worktrace_agent/scripts/run_laptop_readiness_benchmark.py`
- Modify: `services/local-agent/pyproject.toml`
- Modify: `README.md`

- [ ] **Step 1: Write failing CLI test**

```python
def test_laptop_readiness_cli_help_lists_duration_option() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "worktrace_agent.scripts.run_laptop_readiness_benchmark",
            "--help",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--duration-seconds" in result.stdout
    assert "--keep-artifacts" in result.stdout
```

- [ ] **Step 2: Run focused test and verify RED**

Run: `uv run --python 3.13 pytest tests/test_laptop_readiness_benchmark.py -q`

Expected: FAIL because CLI module is missing.

- [ ] **Step 3: Implement CLI and README command**

Add script entry `worktrace-laptop-readiness = "worktrace_agent.scripts.run_laptop_readiness_benchmark:main"` and document:

```powershell
cd services/local-agent
uv run --python 3.13 worktrace-laptop-readiness --duration-seconds 300 --output ..\..\docs\evidence\laptop-readiness-2026-05-13.md
```

- [ ] **Step 4: Run focused test and verify GREEN**

Run: `uv run --python 3.13 pytest tests/test_laptop_readiness_benchmark.py -q`

Expected: PASS.

### Task 4: Verification and Evidence

**Files:**
- Generate: `docs/evidence/laptop-readiness-2026-05-13.md`

- [ ] **Step 1: Run full Python gates**

Run:

```powershell
uv run --python 3.13 ruff check .
uv run --python 3.13 ruff format --check .
uv run --python 3.13 pyright
uv run --python 3.13 pytest
```

- [ ] **Step 2: Run the short real benchmark**

Run:

```powershell
uv run --python 3.13 worktrace-laptop-readiness --duration-seconds 300 --sample-interval-seconds 10 --output ..\..\docs\evidence\laptop-readiness-2026-05-13.md
```

Expected: command exits 0 and writes a safe Markdown evidence file with aggregate metrics only.

- [ ] **Step 3: Re-run tests that cover public claims**

Run:

```powershell
uv run --python 3.13 pytest tests/test_laptop_readiness_benchmark.py tests/test_portfolio_claim_discipline.py -q
```

Expected: PASS.
