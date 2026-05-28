import os
from pathlib import Path

from fastapi import FastAPI

from worktrace_agent import __version__
from worktrace_agent.ai.gemini_gemma_dev_provider import GeminiGemmaDevReportService
from worktrace_agent.ai.local_ollama_report_provider import LocalOllamaReportService
from worktrace_agent.ai.provider_config import (
    AiProviderConfig,
    AiReportProvider,
    read_ai_provider_config,
)
from worktrace_agent.api.ai_report_service import AiReportService, UnavailableAiReportService
from worktrace_agent.api.routes.health import router as health_router
from worktrace_agent.api.routes.privacy import router as privacy_router
from worktrace_agent.api.routes.sessions import router as sessions_router
from worktrace_agent.api.session_recorder_service import SessionRecorderService
from worktrace_agent.capture.active_window import ActiveWindowProvider
from worktrace_agent.capture.file_watcher import FileSnapshotProvider
from worktrace_agent.capture.screenshot_capture import ScreenshotProvider
from worktrace_agent.privacy.config import PrivacyPolicyConfigService


def default_db_path() -> Path:
    configured_path = os.environ.get("WORKTRACE_DB_PATH")
    if configured_path:
        return Path(configured_path)
    return Path.home() / ".worktrace" / "db" / "worktrace.sqlite"


def default_artifact_root(session_id: str) -> Path:
    base = default_db_path().parent
    if base.name == "db":
        base = base.parent
    return base / "sessions" / session_id


def default_privacy_policy_config_path(db_path: Path | None = None) -> Path:
    configured_path = os.environ.get("WORKTRACE_PRIVACY_POLICY_CONFIG_PATH")
    if configured_path:
        return Path(configured_path)
    selected_db_path = db_path or default_db_path()
    return selected_db_path.parent / "privacy-policy.json"


def create_app(
    *,
    db_path: Path | None = None,
    active_window_provider: ActiveWindowProvider | None = None,
    screenshot_provider: ScreenshotProvider | None = None,
    file_snapshot_provider: FileSnapshotProvider | None = None,
    recorder_poll_interval_seconds: float = 1,
    screenshot_interval_seconds: float = 5,
    file_watch_interval_seconds: float = 1,
    ai_report_service: AiReportService | None = None,
    ai_provider_config: AiProviderConfig | None = None,
    privacy_policy_config_service: PrivacyPolicyConfigService | None = None,
) -> FastAPI:
    selected_ai_provider_config = ai_provider_config or read_ai_provider_config()
    selected_db_path = db_path or default_db_path()
    selected_privacy_policy_config_service = (
        privacy_policy_config_service
        or PrivacyPolicyConfigService(
            config_path=default_privacy_policy_config_path(selected_db_path)
        )
    )
    app = FastAPI(
        title="WorkTrace Local Agent",
        version=__version__,
    )
    app.state.session_recorder_service = SessionRecorderService(
        db_path=selected_db_path,
        active_window_provider=active_window_provider,
        screenshot_provider=screenshot_provider,
        file_snapshot_provider=file_snapshot_provider,
        recorder_poll_interval_seconds=recorder_poll_interval_seconds,
        screenshot_interval_seconds=screenshot_interval_seconds,
        file_watch_interval_seconds=file_watch_interval_seconds,
        privacy_policy_config_service=selected_privacy_policy_config_service,
    )
    app.state.privacy_policy_config_service = selected_privacy_policy_config_service
    app.state.ai_provider_config = selected_ai_provider_config
    app.state.ai_report_service = ai_report_service or _default_ai_report_service(
        selected_ai_provider_config
    )
    app.include_router(health_router)
    app.include_router(privacy_router)
    app.include_router(sessions_router)
    return app


def _default_ai_report_service(config: AiProviderConfig) -> AiReportService:
    if config.can_use_gemini_dev_provider:
        return GeminiGemmaDevReportService(config=config)
    if config.provider is AiReportProvider.LOCAL_OLLAMA:
        return LocalOllamaReportService(config=config)
    return UnavailableAiReportService(provider_config=config)


app = create_app()
