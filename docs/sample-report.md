# Sample Report

This is a portfolio-safe sample report for the current repository foundations.
No LLM was used for this sample report. It is based on deterministic fixture-style
events and exists to show the evidence-citation format.

## Session

- Session ID: `sess_portfolio_sample_001`
- Title: Portfolio test fix sample
- Status: `stopped`
- Runtime: `2026-05-06T09:14:00+05:30` to `2026-05-06T09:22:00+05:30`

## Summary

The session shows a short coding and test loop: the user edited a local project
file, ran a failing Python test command, made a follow-up change, and reran the
test successfully.

Evidence: evt_sample_code, evt_sample_test_fail, evt_sample_test_pass

## Timeline

- `chunk_sample_001` coding
  - Time: `2026-05-06T09:14:00+05:30` to `2026-05-06T09:16:00+05:30`
  - Summary: Edited a local Python module in the project.
  - Evidence: evt_sample_code
  - Confidence: 0.90
- `chunk_sample_002` testing
  - Time: `2026-05-06T09:16:00+05:30` to `2026-05-06T09:22:00+05:30`
  - Summary: Ran the focused test, saw a failure, then reran it successfully.
  - Evidence: evt_sample_test_fail, evt_sample_test_pass
  - Confidence: 0.88

## Findings

- Repeated verification loop
  - Type: `test_fix_test_loop`
  - Severity: `low`
  - Description: The same focused test command was used before and after the fix.
  - Evidence: evt_sample_test_fail, evt_sample_test_pass
  - Confidence: 0.86

## Evidence

- `evt_sample_code` `active_window/active_window_changed` - VS Code was active on a local WorkTrace module.
- `evt_sample_test_fail` `terminal/command` - `uv run --python 3.13 pytest tests/test_example.py` exited with failure.
- `evt_sample_test_pass` `terminal/command` - `uv run --python 3.13 pytest tests/test_example.py` exited successfully.

## Known limitations

- This is not a real captured Windows session.
- It does not prove live capture, OCR, audio, embeddings, vision, or model runtime behavior.
- It demonstrates the intended evidence-cited report shape only.
