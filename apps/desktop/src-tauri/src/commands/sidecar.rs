use crate::services::sidecar::{
    AiReportResult, PrivacyPolicyConfigResult, RecorderControlResult, ScreenshotDeletionResult,
    SessionDeletionResult, SessionEventsResult, SessionExportResult, SessionFolderResult,
    SessionListResult, SessionScreenshotPreviewResult, SessionScreenshotsResult, SidecarHealth,
    SidecarService, StartRecordingSessionRequest,
};

#[tauri::command]
pub fn get_sidecar_health() -> SidecarHealth {
    SidecarService.health()
}

#[tauri::command]
pub fn start_sidecar() -> SidecarHealth {
    SidecarService.start()
}

#[tauri::command]
pub fn stop_sidecar() -> SidecarHealth {
    SidecarService.stop()
}

#[tauri::command]
pub fn get_session_events(session_id: String) -> SessionEventsResult {
    SidecarService.events(session_id)
}

#[tauri::command]
#[allow(clippy::too_many_arguments)]
pub fn start_recording_session(
    session_id: String,
    started_at: String,
    title: Option<String>,
    goal: Option<String>,
    project_label: Option<String>,
    tags: Option<Vec<String>>,
    privacy_mode: String,
    file_watch_roots: Option<Vec<String>>,
) -> RecorderControlResult {
    SidecarService.start_recording_session(StartRecordingSessionRequest {
        session_id,
        started_at,
        title,
        goal,
        project_label,
        tags: tags.unwrap_or_default(),
        privacy_mode,
        file_watch_roots: file_watch_roots.unwrap_or_default(),
    })
}

#[tauri::command]
pub fn pause_recording_session(session_id: String, paused_at: String) -> RecorderControlResult {
    SidecarService.pause_recording_session(session_id, paused_at)
}

#[tauri::command]
pub fn resume_recording_session(
    session_id: String,
    resumed_at: String,
    file_watch_roots: Option<Vec<String>>,
) -> RecorderControlResult {
    SidecarService.resume_recording_session(
        session_id,
        resumed_at,
        file_watch_roots.unwrap_or_default(),
    )
}

#[tauri::command]
pub fn stop_recording_session(session_id: String, stopped_at: String) -> RecorderControlResult {
    SidecarService.stop_recording_session(session_id, stopped_at)
}

#[tauri::command]
pub fn export_session_markdown(session_id: String) -> SessionExportResult {
    SidecarService.export_session_markdown(session_id)
}

#[tauri::command]
pub fn export_session_raw_json(session_id: String) -> SessionExportResult {
    SidecarService.export_session_raw_json(session_id)
}

#[tauri::command]
pub fn get_ai_report_status(session_id: String) -> AiReportResult {
    SidecarService.ai_report_status(session_id)
}

#[tauri::command]
pub fn generate_ai_report(session_id: String) -> AiReportResult {
    SidecarService.generate_ai_report(session_id)
}

#[tauri::command]
pub fn cancel_ai_report(session_id: String) -> AiReportResult {
    SidecarService.cancel_ai_report(session_id)
}

#[tauri::command]
pub fn get_session_folder(session_id: String) -> SessionFolderResult {
    SidecarService.session_folder(session_id)
}

#[tauri::command]
pub fn open_session_folder(session_id: String) -> SessionFolderResult {
    SidecarService.open_session_folder(session_id)
}

#[tauri::command]
pub fn get_session_screenshots(session_id: String) -> SessionScreenshotsResult {
    SidecarService.session_screenshots(session_id)
}

#[tauri::command]
pub fn get_session_screenshot_preview(
    session_id: String,
    screenshot_id: String,
) -> SessionScreenshotPreviewResult {
    SidecarService.session_screenshot_preview(session_id, screenshot_id)
}

#[tauri::command]
pub fn delete_session_screenshots(session_id: String) -> ScreenshotDeletionResult {
    SidecarService.delete_session_screenshots(session_id)
}

#[tauri::command]
pub fn get_sessions() -> SessionListResult {
    SidecarService.sessions()
}

#[tauri::command]
pub fn delete_session(session_id: String) -> SessionDeletionResult {
    SidecarService.delete_session(session_id)
}

#[tauri::command]
pub fn get_privacy_policy() -> PrivacyPolicyConfigResult {
    SidecarService.privacy_policy()
}

#[tauri::command]
pub fn update_privacy_policy(
    allowlist: Vec<String>,
    blocklist: Vec<String>,
    clipboard_safe_mode: bool,
) -> PrivacyPolicyConfigResult {
    SidecarService.update_privacy_policy(allowlist, blocklist, clipboard_safe_mode)
}
