pub mod commands;
pub mod services;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            commands::sidecar::cancel_ai_report,
            commands::sidecar::delete_session,
            commands::sidecar::delete_session_screenshots,
            commands::sidecar::export_session_markdown,
            commands::sidecar::export_session_raw_json,
            commands::sidecar::generate_ai_report,
            commands::sidecar::get_ai_report_status,
            commands::sidecar::get_privacy_policy,
            commands::sidecar::get_sidecar_health,
            commands::sidecar::get_session_events,
            commands::sidecar::get_session_folder,
            commands::sidecar::get_session_screenshot_preview,
            commands::sidecar::get_session_screenshots,
            commands::sidecar::get_sessions,
            commands::sidecar::open_session_folder,
            commands::sidecar::pause_recording_session,
            commands::sidecar::resume_recording_session,
            commands::sidecar::start_recording_session,
            commands::sidecar::start_sidecar,
            commands::sidecar::stop_recording_session,
            commands::sidecar::stop_sidecar,
            commands::sidecar::update_privacy_policy
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
