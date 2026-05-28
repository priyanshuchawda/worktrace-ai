from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

FORBIDDEN_PUBLIC_CLAIMS = (
    "ai understands your full workflow perfectly",
    "automatically knows everything you did",
    "fully secure",
    "production-ready ai",
    "never misses blockers",
    "real windows capture profiling passed",
)


def test_readme_has_two_minute_viewer_section_and_current_limits() -> None:
    readme = read_text("README.md")

    assert "working local-first private-beta candidate for internal and" in readme
    assert "controlled testing. It is not a public Windows release yet." in readme
    assert "## How To Test The App Manually" in readme
    assert "docs/manual-testing.md" in readme
    assert "docs/private-beta.md" in readme
    assert "docs/security/private-beta-security-review-2026-05-26.md" in readme
    assert "The core private-beta loop is implemented:" in readme
    assert "Public distribution is still deferred." in readme
    assert "Planning + Phase 0 foundation" not in readme
    assert "## Two-Minute Review" in readme
    assert "## Evidence and Verification" in readme
    assert "## Current Limitations" in readme
    assert "desktop session dashboard foundation" in readme
    assert "recorder start/pause/resume/stop controls for a configured local sidecar" in readme
    assert "Tauri sidecar launch abstraction for a configured local sidecar binary" in readme
    assert "real Windows active-window polling" in readme
    assert "compressed PNG artifact storage" in readme
    assert "bounded retention cleanup" in readme
    assert "JPEG/WebP screenshot encoding" in readme
    assert "configured localhost sidecar URL or configured local sidecar binary/port" in readme
    assert "real Windows screenshot capture" in readme
    assert "metadata-only file watcher capture" in readme
    assert "explicit safe terminal command ingestion" in readme
    assert "prompt/export/log redaction helpers" in readme
    assert "private-mode suppression for active-window/screenshot/file-watcher workers" in readme
    assert "sidecar-backed desktop privacy policy persistence" in readme
    assert "session deletion clears session/event/screenshot/OCR rows" in readme
    assert "selective OCR worker/runtime foundation" in readme
    assert "PaddleOCR is not bundled, downloaded, or required" in readme
    assert "PaddleOCR sample smoke command exists and skips safely here" in readme
    assert "no real PaddleOCR pass has been recorded yet" in readme
    assert "metadata-only model cache manager" in readme
    assert "does not perform network downloads or load models" in readme
    assert "Qwen3 embedding smoke command exists and skips safely here" in readme
    assert "no real Qwen3 embedding pass has been recorded yet" in readme
    assert "Qwen3-VL selected-frame smoke command exists and skips safely here" in readme
    assert "no real Qwen3-VL selected-frame pass has been recorded yet" in readme
    assert "faster-whisper local-path smoke command exists and skips safely here" in readme
    assert "no real faster-whisper pass has been recorded yet" in readme
    assert "localhost-only Ollama-style report runtime adapter" in readme
    assert "tiny real local Gemma E2B smoke passed" in readme
    assert "does not spy on terminals, keylog, or capture commands unless" in readme
    assert "deterministic Markdown/raw JSON export review" in readme
    assert "Windows Explorer folder-open integration" in readme
    assert "redacted OCR snippets for stored screenshot previews" in readme
    assert "docs/models/runtime-strategy.md" in readme
    assert "Gemini/Gemma hosted inference is a development-only report shortcut" in readme
    assert "Qwen embeddings, Qwen-VL, faster-whisper, and PaddleOCR remain local-only" in readme
    assert (
        "desktop AI report UI is wired through React, Tauri, and FastAPI boundary commands"
        in readme
    )
    assert "current development default is `gemini_gemma_dev`" in readme
    assert "Qwen embeddings, Qwen-VL, faster-whisper" in readme
    assert "WorkTrace still does not download models or start a model server" in readme
    assert "Python sidecar packaging is not bundled" in readme
    assert "installer install/run QA passed locally" in readme
    assert "Direct sidecar QA exposed a cleanup caveat" in readme
    assert "Tauri-managed sidecar stop now uses Windows process-tree cleanup" in readme
    assert "30-minute local recorder readiness benchmark profile" in readme
    assert "short 5-10 minute live laptop readiness smoke" in readme
    assert "docs/evidence/production-readiness-30-minute-2026-05-26.md" in readme
    assert "docs/release-hardening.md" in readme
    assert "docs/release-channels.md" in readme
    assert "docs/release-checklist.md" in readme
    assert "release-channel decision" in readme
    assert "source-only alpha milestones" in readme
    assert "future Microsoft Store MSIX/AppX distribution decision" in readme
    assert "public unsigned GitHub Release installer" in readme
    assert ".github/workflows/ci.yml" in readme
    assert "without secrets, hosted model calls, local model downloads" in readme


def test_private_beta_acceptance_criteria_maps_user_flow_and_blockers() -> None:
    readme = read_text("README.md")
    private_beta = read_text("docs/private-beta.md")
    installed_smoke = read_text("docs/private-beta-installed-smoke.md")
    plan = read_text("plan.md")
    architecture = read_text("docs/architecture.md")

    assert "Primary beta users" in private_beta
    assert "developers" in private_beta
    assert "students" in private_beta
    assert "Record a work session locally" in private_beta
    assert "Primary Demo Flow" in private_beta
    assert "Private Beta Ready Means" in private_beta
    assert "Private Beta Foundation Status" in private_beta
    assert "#159" in private_beta
    assert "#160" in private_beta
    assert "#161" in private_beta
    assert "#162" in private_beta
    assert "#163" in private_beta
    assert "External Beta Release Blockers" in private_beta
    assert "#132" in private_beta
    assert "Secret-free deterministic GitHub Actions implemented in #132" in private_beta
    assert "#179" in private_beta
    assert "#165" in private_beta
    assert "local artifact guard implemented in #165" in private_beta
    assert "Do not spend money" in private_beta
    assert "Microsoft Store-compatible" in private_beta
    assert "Current NSIS artifacts remain local/internal QA only" in private_beta
    assert "No hidden cloud upload" in private_beta
    assert "AI claims must cite known evidence IDs" in private_beta
    assert "scripts/validation/run-installed-beta-smoke.ps1" in private_beta
    assert "pwsh -File scripts/validation/run-installed-beta-smoke.ps1 -Build" in installed_smoke
    assert "docs/evidence/private-beta-installed-smoke-2026-05-26.json" in readme
    assert "docs/evidence/private-beta-installed-smoke-2026-05-26.json" in installed_smoke
    assert "Do not call Gemini/Gemma live APIs" in installed_smoke
    assert "Do not download Gemma, Qwen, PaddleOCR, faster-whisper" in installed_smoke
    assert "no application code yet" not in plan
    assert "no longer planning-only" in plan
    assert "docs/private-beta.md" in architecture


def test_public_docs_avoid_forbidden_overclaims() -> None:
    public_docs = [
        "README.md",
        "docs/private-beta.md",
        "docs/private-beta-installed-smoke.md",
        "docs/demo-script.md",
        "docs/packaging.md",
        "docs/sample-report.md",
        "docs/eval-results.md",
        "docs/privacy.md",
        "docs/architecture.md",
    ]

    combined_text = "\n".join(read_text(path) for path in public_docs).lower()

    for forbidden_claim in FORBIDDEN_PUBLIC_CLAIMS:
        assert forbidden_claim not in combined_text


def test_privacy_doc_describes_current_controls_and_deletion_contract() -> None:
    privacy_doc = read_text("docs/privacy.md")

    assert "Current Capture Boundaries" in privacy_doc
    assert "First-run onboarding must be accepted before recording" in privacy_doc
    assert "Private mode suppresses implemented capture workers" in privacy_doc
    assert "Persisted allow/block policy controls are applied" in privacy_doc
    assert "Deleting a session must remove" in privacy_doc
    assert "OCR rows linked to the session/screenshots" in privacy_doc
    assert "services/local-agent/tests/api/test_sessions.py" in privacy_doc
    assert "live recorder and complete privacy center are still not implemented" not in privacy_doc


def test_private_beta_security_review_records_boundaries_and_blockers() -> None:
    review = read_text("docs/security/private-beta-security-review-2026-05-26.md")

    assert "local session database and WAL files" in review
    assert "React desktop UI to Tauri IPC commands" in review
    assert "development-only Gemini/Gemma provider" in review
    assert "no arbitrary remote model endpoint" in review
    assert "report claims cite known evidence IDs" in review
    assert "No new P0/P1 security defect" in review
    assert "#132" in review
    assert "#179" in review
    assert "#165" in review
    assert "Microsoft Store-compatible MSIX/AppX channel" in review
    assert "No real `.env`, API key" in review


def test_model_runtime_strategy_keeps_cloud_development_only() -> None:
    strategy = read_text("docs/models/runtime-strategy.md")

    assert "Local report runtime" in strategy
    assert "Development hosted report runtime" in strategy
    assert "Current development default" in strategy
    assert "gemma-4-31b-it" in strategy
    assert "gemma-4-26b-a4b-it" in strategy
    assert "Do not commit `.env`, API keys" in strategy
    assert "Qwen, faster-whisper, PaddleOCR, and Qwen-VL remain local-only" in strategy


def test_packaging_docs_and_desktop_script_define_windows_nsis_build() -> None:
    package_json = json.loads(read_text("apps/desktop/package.json"))
    tauri_config = json.loads(read_text("apps/desktop/src-tauri/tauri.conf.json"))
    packaging_doc = read_text("docs/packaging.md")
    release_hardening_doc = read_text("docs/release-hardening.md")
    local_validation_doc = read_text("docs/development/local-validation.md")
    installed_smoke_script = read_text("scripts/validation/run-installed-beta-smoke.ps1")
    release_evidence = json.loads(
        read_text("docs/evidence/release-hardening-decision-2026-05-26.json")
    )
    private_beta_smoke_evidence = json.loads(
        read_text("docs/evidence/private-beta-installed-smoke-2026-05-26.json")
    )

    assert package_json["scripts"]["package:windows"] == "tauri build --bundles nsis"
    assert package_json["scripts"]["package:sidecar"] == "node scripts/build-sidecar.mjs"
    assert tauri_config["bundle"]["targets"] == ["nsis"]
    assert tauri_config["bundle"]["externalBin"] == ["binaries/worktrace-local-agent"]
    assert tauri_config["bundle"]["windows"]["nsis"]["installMode"] == "currentUser"
    assert "pnpm --dir apps/desktop package:windows" in packaging_doc
    assert "pnpm --dir apps/desktop package:sidecar" in packaging_doc
    assert "not code-signed and is local/internal QA only" in packaging_doc
    assert "does not bundle the Python sidecar yet" in packaging_doc
    assert "configured sidecar launch path exists" in packaging_doc
    assert "Packaging-ready sidecar binary lookup exists" in packaging_doc
    assert "worktrace-local-agent-x86_64-pc-windows-msvc.exe" in packaging_doc
    assert "WORKTRACE_DB_PATH" in packaging_doc
    assert "Release hardening decision" in packaging_doc
    assert (
        "future public Windows channel is a Microsoft Store-compatible MSIX/AppX path"
        in release_hardening_doc
    )
    assert "must not be published as a public unsigned installer" in release_hardening_doc
    assert "GitHub Releases may be used for release notes" in release_hardening_doc
    assert "Automatic updates stay disabled" in release_hardening_doc
    assert "Store-managed updates" in release_hardening_doc
    assert "do not publish updater artifacts" in release_hardening_doc
    assert "docs/release-channels.md" in release_hardening_doc
    assert "scripts/release/validate-release-artifacts.ps1" in release_hardening_doc
    assert "worktrace-local-agent-x86_64-pc-windows-msvc.exe" in release_hardening_doc
    assert "run-installed-beta-smoke.ps1 -Build" in local_validation_doc
    assert ".github/workflows/ci.yml" in local_validation_doc
    assert "WORKTRACE_ENABLE_DEV_CLOUD_AI=false" in local_validation_doc
    assert ".github/workflows/packaging-smoke.yml" in local_validation_doc
    assert "package:sidecar" in installed_smoke_script
    assert "package:windows" in installed_smoke_script
    assert "live_gemini_called = $false" in installed_smoke_script
    assert "model_downloads_started = $false" in installed_smoke_script
    assert private_beta_smoke_evidence["result"] == "passed"
    assert private_beta_smoke_evidence["no_paid_actions"] is True
    assert private_beta_smoke_evidence["live_gemini_called"] is False
    assert private_beta_smoke_evidence["model_downloads_started"] is False
    assert private_beta_smoke_evidence["installer_signed"] is False
    assert release_evidence["code_signing"]["configured"] is False
    assert release_evidence["updater"]["configured"] is False
    assert (
        "Microsoft Store-compatible MSIX/AppX"
        in release_evidence["installer_status"]["public_distribution_target"]
    )
    assert (
        "Do not publish unsigned NSIS/MSI/EXE installers"
        in release_evidence["code_signing"]["direct_distribution_policy"]
    )
    assert "Store-managed" in release_evidence["updater"]["decision"]
    assert release_evidence["sidecar_bundle_assumptions"]["runtime_boundary"] == (
        "The sidecar must bind to 127.0.0.1 and must not expose hosted AI credentials "
        "through React or Rust."
    )
    assert release_evidence["privacy_evidence"]["contains_api_keys"] is False


def test_release_channels_and_artifact_guard_prevent_unsigned_public_binaries() -> None:
    release_channels = read_text("docs/release-channels.md")
    release_checklist = read_text("docs/release-checklist.md")
    alpha_template = read_text("docs/release-notes/alpha-template.md")
    artifact_guard = read_text("scripts/release/validate-release-artifacts.ps1")

    assert "`dev`" in release_channels
    assert "`alpha`" in release_channels
    assert "`store-beta`" in release_channels
    assert "`store-stable`" in release_channels
    assert "v0.x.y-alpha.n" in release_channels
    assert "source/release-notes" in release_channels
    assert "source-only engineering milestones" in release_channels
    assert "no unsigned installable Windows binaries" in release_channels
    assert "Forbidden alpha release contents" in release_channels
    assert "Tauri updater remains disabled" in release_channels
    assert "Microsoft Store-managed updates" in release_channels
    assert "no installable Windows binary is attached" in release_checklist
    assert "public Windows installer distribution remains" in release_checklist
    assert "deferred to the future Microsoft Store MSIX/AppX path" in release_checklist
    assert "source-only engineering prerelease" in alpha_template
    assert "No installable Windows binary is\nattached" in alpha_template
    assert 'ValidateSet("dev", "alpha", "store-beta", "store-stable")' in artifact_guard
    assert '".exe"' in artifact_guard
    assert '".msixbundle"' in artifact_guard
    assert '".zip"' in artifact_guard
    assert "WORKTRACE_APPROVE_INSTALLER_RELEASE" in artifact_guard
    assert "I_UNDERSTAND_STORE_OR_SIGNED_CHANNEL" in artifact_guard
    assert "Do not attach unsigned installer/update artifacts" in artifact_guard


def test_github_ci_is_deterministic_secret_free_and_does_not_publish_binaries() -> None:
    ci_workflow = read_text(".github/workflows/ci.yml")
    packaging_smoke = read_text(".github/workflows/packaging-smoke.yml")

    assert "pull_request:" in ci_workflow
    assert "branches:" in ci_workflow
    assert 'WORKTRACE_ENABLE_DEV_CLOUD_AI: "false"' in ci_workflow
    assert "pnpm --dir packages/shared typecheck" in ci_workflow
    assert "pnpm --dir packages/shared test" in ci_workflow
    assert "pnpm --dir apps/desktop typecheck" in ci_workflow
    assert "pnpm --dir apps/desktop lint" in ci_workflow
    assert "pnpm --dir apps/desktop test" in ci_workflow
    assert "pnpm --dir apps/desktop build" in ci_workflow
    assert "uv run --python 3.13 ruff format --check ." in ci_workflow
    assert "uv run --python 3.13 ruff check ." in ci_workflow
    assert "uv run --python 3.13 pyright" in ci_workflow
    assert "uv run --python 3.13 pytest" in ci_workflow
    assert "runs-on: windows-latest" in ci_workflow
    assert "cargo fmt --all -- --check" in ci_workflow
    assert "cargo clippy --workspace --all-targets -- -D warnings" in ci_workflow
    assert "cargo test --workspace" in ci_workflow
    assert "pnpm --dir apps/desktop package:sidecar" in ci_workflow
    assert "GEMINI_API_KEY" not in ci_workflow
    assert "package:windows" not in ci_workflow
    assert "gh release" not in ci_workflow
    assert "upload-artifact" not in ci_workflow

    assert "workflow_dispatch:" in packaging_smoke
    assert 'WORKTRACE_ENABLE_DEV_CLOUD_AI: "false"' in packaging_smoke
    assert "package:sidecar" in packaging_smoke
    assert "package:windows" in packaging_smoke
    assert "validate-release-artifacts.ps1" in packaging_smoke
    assert "does not upload artifacts" in packaging_smoke
    assert "upload-artifact" not in packaging_smoke
    assert "gh release" not in packaging_smoke
    assert "GEMINI_API_KEY" not in packaging_smoke


def test_demo_script_is_truthful_about_current_implemented_demo() -> None:
    demo_script = read_text("docs/demo-script.md")

    assert "WorkTrace AI Demo Script" in demo_script
    assert "private-beta product demo" in demo_script
    assert "## Live Demo Flow" in demo_script
    assert "Start recording." in demo_script
    assert "Click report evidence IDs" in demo_script
    assert "Preview share-safe Markdown" in demo_script
    assert "privacy-safe diagnostics bundle" in demo_script
    assert "No keylogging." in demo_script
    assert "No global terminal spying." in demo_script
    assert "Hosted Gemini/Gemma is development-only and report-only." in demo_script
    assert "NSIS packaging is internal QA only." in demo_script
    assert "manual-testing.md" in demo_script
    assert "This is not a live recording demo yet." not in demo_script
    assert "live capture workers are not implemented yet" not in demo_script


def test_sample_report_uses_cited_evidence_and_clear_limitations() -> None:
    sample_report = read_text("docs/sample-report.md")

    assert "No LLM was used for this sample report." in sample_report
    assert "Evidence: evt_" in sample_report
    assert "Known limitations" in sample_report
    assert "not a real captured Windows session" in sample_report


def test_eval_results_document_reproducible_command_and_aggregate() -> None:
    eval_results = read_text("docs/eval-results.md")

    assert "uv run --python 3.13 python scripts/evaluate_model.py" in eval_results
    assert "| aggregate | 1.00 | 1.00 | 1.00 | 0 | 0 |" in eval_results
    assert "deterministic estimates" in eval_results
    assert "not real Windows profiling" in eval_results
    assert "30-minute local recorder readiness benchmark" in eval_results
    assert "Real Gemma E2B smoke" in eval_results
    assert "Qwen3-VL selected-frame smoke" in eval_results
    assert "faster-whisper local-path smoke" in eval_results
    assert "not a quality benchmark" in eval_results


def read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")
