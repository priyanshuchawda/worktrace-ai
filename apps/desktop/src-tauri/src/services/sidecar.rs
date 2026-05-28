use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{
    env, fs,
    io::{Read, Write},
    net::{TcpStream, ToSocketAddrs},
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::{Mutex, OnceLock},
    time::Duration,
};

const MISSING_MESSAGE: &str = "Local agent sidecar binary is not configured yet.";
const NOT_RUNNING_MESSAGE: &str = "Local agent sidecar is not running.";
const SIDECAR_URL_ENV: &str = "WORKTRACE_SIDECAR_URL";
const SIDECAR_PORT_ENV: &str = "WORKTRACE_SIDECAR_PORT";
const SIDECAR_BIN_ENV: &str = "WORKTRACE_SIDECAR_BIN";
const SIDECAR_ARGS_ENV: &str = "WORKTRACE_SIDECAR_ARGS";
const DEFAULT_SIDECAR_PORT: u16 = 8765;
const MAX_FILE_WATCH_ROOTS: usize = 16;
const MAX_POLICY_ENTRY_COUNT: usize = 64;
const MAX_SESSION_TAGS: usize = 12;
#[cfg(windows)]
const BUNDLED_SIDECAR_NAME: &str = "worktrace-local-agent.exe";
#[cfg(not(windows))]
const BUNDLED_SIDECAR_NAME: &str = "worktrace-local-agent";
const HTTP_TIMEOUT: Duration = Duration::from_secs(2);
const REDACTION_TOKEN: &str = "[REDACTED]";
const SECRET_FRAGMENTS: &[&str] = &[
    "OPENAI_API_KEY=sk-test",
    "GITHUB_TOKEN=ghp_test",
    "AWS_SECRET_ACCESS_KEY=test",
    "password=mysecret",
    "email@example.com",
    "+91 9876543210",
    "-----BEGIN PRIVATE KEY-----",
    "sk-test",
    "ghp_test",
    "mysecret",
];

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum SidecarStatus {
    Healthy,
    Unhealthy,
    Missing,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SidecarHealth {
    pub status: SidecarStatus,
    pub app_version: Option<String>,
    pub schema_version: Option<String>,
    pub message: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum SessionEventsStatus {
    Available,
    Unavailable,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SessionEventsResult {
    pub status: SessionEventsStatus,
    pub events: Vec<SessionTimelineEvent>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SessionTimelineEvent {
    pub id: String,
    pub timestamp: String,
    pub app: String,
    pub window_title: String,
    pub source: String,
    #[serde(rename = "type")]
    pub event_type: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum RecorderControlStatus {
    Available,
    Unavailable,
}

#[derive(Clone, Debug, Eq, PartialEq, Deserialize, Serialize)]
#[serde(rename_all(serialize = "camelCase", deserialize = "snake_case"))]
pub struct RecorderSession {
    pub id: String,
    pub started_at: String,
    pub ended_at: Option<String>,
    pub status: String,
    pub title: Option<String>,
    pub goal: Option<String>,
    pub project_label: Option<String>,
    #[serde(default)]
    pub tags: Vec<String>,
    pub storage_path: Option<String>,
    pub privacy_mode: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RecorderControlResult {
    pub status: RecorderControlStatus,
    pub message: String,
    pub session: Option<RecorderSession>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StartRecordingSessionRequest {
    pub session_id: String,
    pub started_at: String,
    pub title: Option<String>,
    pub goal: Option<String>,
    pub project_label: Option<String>,
    pub tags: Vec<String>,
    pub privacy_mode: String,
    pub file_watch_roots: Vec<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum SessionListStatus {
    Available,
    Unavailable,
}

#[derive(Clone, Debug, Eq, PartialEq, Deserialize, Serialize)]
#[serde(rename_all(serialize = "camelCase", deserialize = "snake_case"))]
pub struct SessionSummary {
    pub id: String,
    pub started_at: String,
    pub ended_at: Option<String>,
    pub status: String,
    pub title: Option<String>,
    pub goal: Option<String>,
    pub project_label: Option<String>,
    #[serde(default)]
    pub tags: Vec<String>,
    pub storage_path: Option<String>,
    pub privacy_mode: String,
    pub event_count: i64,
    pub screenshot_count: i64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SessionListResult {
    pub status: SessionListStatus,
    pub message: String,
    pub sessions: Vec<SessionSummary>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum SessionDeletionStatus {
    Available,
    Unavailable,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SessionDeletionResult {
    pub status: SessionDeletionStatus,
    pub message: String,
    pub deleted_session_rows: i64,
    pub deleted_screenshot_files: i64,
    pub missing_screenshot_files: i64,
    pub deleted_screenshot_rows: i64,
    pub removed_artifact_root: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Deserialize, Serialize)]
#[serde(rename_all(serialize = "camelCase", deserialize = "snake_case"))]
pub struct PrivacyPolicyConfig {
    pub allowlist: Vec<String>,
    pub blocklist: Vec<String>,
    pub clipboard_safe_mode: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum PrivacyPolicyConfigStatus {
    Available,
    Unavailable,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct PrivacyPolicyConfigResult {
    pub status: PrivacyPolicyConfigStatus,
    pub message: String,
    pub policy: Option<PrivacyPolicyConfig>,
}

#[derive(Debug, Deserialize)]
struct SidecarSessionsResponse {
    sessions: Vec<SessionSummary>,
}

#[derive(Debug, Deserialize)]
struct SidecarSessionDeletionResponse {
    deleted_session_rows: i64,
    deleted_screenshot_files: i64,
    missing_screenshot_files: i64,
    deleted_screenshot_rows: i64,
    removed_artifact_root: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum SessionExportStatus {
    Available,
    Unavailable,
}

#[derive(Clone, Debug, Eq, PartialEq, Deserialize, Serialize)]
#[serde(rename_all(serialize = "camelCase", deserialize = "snake_case"))]
pub struct SessionExportPreview {
    pub format: String,
    pub path: String,
    pub preview: String,
    pub evidence_ids: Vec<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SessionExportResult {
    pub status: SessionExportStatus,
    pub message: String,
    pub export: Option<SessionExportPreview>,
}

#[derive(Clone, Debug, Eq, PartialEq, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum AiReportStatus {
    NotInstalled,
    RuntimeUnavailable,
    Loading,
    Ready,
    Running,
    FailedSafely,
    Complete,
    TooSlow,
    Cancelled,
}

#[derive(Clone, Debug, Eq, PartialEq, Deserialize, Serialize)]
#[serde(rename_all(serialize = "camelCase", deserialize = "snake_case"))]
pub struct AiReportClaim {
    pub title: Option<String>,
    pub text: Option<String>,
    pub path: Option<String>,
    pub command: Option<String>,
    pub evidence_event_ids: Vec<String>,
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
#[serde(rename_all(serialize = "camelCase", deserialize = "snake_case"))]
pub struct AiReportPayload {
    pub session_id: String,
    pub session_title: String,
    pub summary: AiReportClaim,
    #[serde(default)]
    pub observed_work: Vec<AiReportClaim>,
    pub timeline: Vec<AiReportClaim>,
    pub blockers: Vec<AiReportClaim>,
    #[serde(default)]
    pub context_switches: Vec<AiReportClaim>,
    #[serde(default)]
    pub unfinished_work: Vec<AiReportClaim>,
    pub repeated_actions: Vec<AiReportClaim>,
    pub important_files: Vec<AiReportClaim>,
    pub commands: Vec<AiReportClaim>,
    pub workflow_steps: Vec<AiReportClaim>,
    #[serde(default)]
    pub continuation_notes: Vec<AiReportClaim>,
    pub confidence: f64,
    pub known_evidence_event_ids: Vec<String>,
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
#[serde(rename_all(serialize = "camelCase", deserialize = "snake_case"))]
pub struct AiReportResult {
    pub status: AiReportStatus,
    pub message: String,
    pub can_generate: bool,
    pub report: Option<AiReportPayload>,
    pub evidence_ids: Vec<String>,
    pub model_name: Option<String>,
    pub model_version: Option<String>,
    pub provider: Option<String>,
    pub requested_model: Option<String>,
    pub actual_model: Option<String>,
    #[serde(default)]
    pub fallback_used: bool,
    pub runtime_ms: Option<i64>,
    pub input_hash: Option<String>,
    pub generated_at: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum SessionFolderStatus {
    Available,
    Unavailable,
}

#[derive(Clone, Debug, Eq, PartialEq, Deserialize)]
struct SidecarSessionFolderResponse {
    path: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SessionFolderResult {
    pub status: SessionFolderStatus,
    pub message: String,
    pub path: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum SessionScreenshotsStatus {
    Available,
    Unavailable,
}

#[derive(Clone, Debug, Eq, PartialEq, Deserialize, Serialize)]
#[serde(rename_all(serialize = "camelCase", deserialize = "snake_case"))]
pub struct SessionScreenshot {
    pub id: String,
    pub session_id: String,
    pub source_event_id: Option<String>,
    pub timestamp: String,
    pub width: i64,
    pub height: i64,
    pub stored_width: i64,
    pub stored_height: i64,
    pub byte_size: i64,
    pub content_hash: String,
    pub visual_hash: String,
    pub storage_path: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Deserialize, Serialize)]
#[serde(rename_all(serialize = "camelCase", deserialize = "snake_case"))]
pub struct SessionScreenshotPreview {
    pub screenshot_id: String,
    pub image_data_url: String,
    pub ocr_snippets: Vec<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum SessionScreenshotPreviewStatus {
    Available,
    Unavailable,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SessionScreenshotPreviewResult {
    pub status: SessionScreenshotPreviewStatus,
    pub message: String,
    pub preview: Option<SessionScreenshotPreview>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SessionScreenshotsResult {
    pub status: SessionScreenshotsStatus,
    pub message: String,
    pub screenshots: Vec<SessionScreenshot>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum ScreenshotDeletionStatus {
    Available,
    Unavailable,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all(serialize = "camelCase", deserialize = "snake_case"))]
pub struct ScreenshotDeletionResult {
    pub status: ScreenshotDeletionStatus,
    pub message: String,
    pub deleted_files: i64,
    pub missing_files: i64,
    pub deleted_rows: i64,
}

#[derive(Debug, Deserialize)]
struct SidecarScreenshotsResponse {
    screenshots: Vec<SessionScreenshot>,
}

#[derive(Debug, Deserialize)]
struct SidecarScreenshotPreviewResponse {
    screenshot_id: String,
    image_data_url: String,
    ocr_snippets: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct SidecarScreenshotDeletionResponse {
    deleted_files: i64,
    missing_files: i64,
    deleted_rows: i64,
}

#[derive(Debug, Deserialize)]
struct SidecarEventsResponse {
    events: Vec<SidecarRawEvent>,
}

#[derive(Debug, Deserialize)]
struct SidecarRawEvent {
    id: String,
    timestamp: String,
    source: String,
    #[serde(rename = "type")]
    event_type: String,
    metadata: Value,
}

#[derive(Debug, Deserialize)]
struct SidecarHealthResponse {
    app_version: String,
    schema_version: String,
    status: String,
}

#[derive(Clone, Debug)]
pub struct SidecarService;

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SidecarProcessKillCommand {
    pub program: String,
    pub args: Vec<String>,
}

impl SidecarService {
    pub fn health(&self) -> SidecarHealth {
        let Some(base_url) = configured_base_url() else {
            return missing_health(MISSING_MESSAGE);
        };

        self.health_from_base_url(&base_url)
    }

    pub fn start(&self) -> SidecarHealth {
        let Some(base_url) = configured_base_url() else {
            return missing_health(MISSING_MESSAGE);
        };

        let health = self.health_from_base_url(&base_url);
        if health.status == SidecarStatus::Healthy {
            return health;
        }

        let Some(binary_path) = configured_sidecar_binary() else {
            return missing_health(MISSING_MESSAGE);
        };

        start_managed_sidecar(binary_path)
    }

    pub fn stop(&self) -> SidecarHealth {
        if stop_managed_sidecar() || stop_pid_file_sidecar() {
            return missing_health("Local agent sidecar was stopped.");
        }

        missing_health(NOT_RUNNING_MESSAGE)
    }

    pub fn events(&self, session_id: String) -> SessionEventsResult {
        let Some(base_url) = configured_base_url() else {
            return unavailable_events();
        };

        self.events_from_base_url(session_id, &base_url)
    }

    pub fn start_recording_session(
        &self,
        request: StartRecordingSessionRequest,
    ) -> RecorderControlResult {
        let Some(base_url) = configured_base_url() else {
            return unavailable_recorder_control_with_message(
                "Recorder sidecar URL is not configured.",
            );
        };

        self.start_recording_session_from_base_url(request, &base_url)
    }

    pub fn start_recording_session_from_base_url(
        &self,
        request: StartRecordingSessionRequest,
        base_url: &str,
    ) -> RecorderControlResult {
        if request.session_id.trim().is_empty()
            || request.started_at.trim().is_empty()
            || request.privacy_mode.trim().is_empty()
        {
            return unavailable_recorder_control_with_message(
                "Recorder request is missing required session fields.",
            );
        }

        self.post_session_control(
            base_url,
            "/sessions/start".to_string(),
            json!({
                "session_id": request.session_id,
                "started_at": request.started_at,
                "title": request.title,
                "goal": request.goal,
                "project_label": request.project_label,
                "tags": sanitize_session_tags(request.tags),
                "privacy_mode": request.privacy_mode,
                "file_watch_roots": sanitize_file_watch_roots(request.file_watch_roots),
            }),
            "Recording session started.",
        )
    }

    pub fn pause_recording_session(
        &self,
        session_id: String,
        paused_at: String,
    ) -> RecorderControlResult {
        let Some(base_url) = configured_base_url() else {
            return unavailable_recorder_control_with_message(
                "Recorder sidecar URL is not configured.",
            );
        };

        self.pause_recording_session_from_base_url(session_id, paused_at, &base_url)
    }

    pub fn pause_recording_session_from_base_url(
        &self,
        session_id: String,
        paused_at: String,
        base_url: &str,
    ) -> RecorderControlResult {
        if session_id.trim().is_empty() || paused_at.trim().is_empty() {
            return unavailable_recorder_control_with_message(
                "Recorder request is missing required session fields.",
            );
        }

        self.post_session_control(
            base_url,
            format!("/sessions/{}/pause", encode_path_segment(&session_id)),
            json!({ "paused_at": paused_at }),
            "Recording session paused.",
        )
    }

    pub fn resume_recording_session(
        &self,
        session_id: String,
        resumed_at: String,
        file_watch_roots: Vec<String>,
    ) -> RecorderControlResult {
        let Some(base_url) = configured_base_url() else {
            return unavailable_recorder_control_with_message(
                "Recorder sidecar URL is not configured.",
            );
        };

        self.resume_recording_session_from_base_url(
            session_id,
            resumed_at,
            file_watch_roots,
            &base_url,
        )
    }

    pub fn resume_recording_session_from_base_url(
        &self,
        session_id: String,
        resumed_at: String,
        file_watch_roots: Vec<String>,
        base_url: &str,
    ) -> RecorderControlResult {
        if session_id.trim().is_empty() || resumed_at.trim().is_empty() {
            return unavailable_recorder_control_with_message(
                "Recorder request is missing required session fields.",
            );
        }

        self.post_session_control(
            base_url,
            format!("/sessions/{}/resume", encode_path_segment(&session_id)),
            json!({
                "resumed_at": resumed_at,
                "file_watch_roots": sanitize_file_watch_roots(file_watch_roots),
            }),
            "Recording session resumed.",
        )
    }

    pub fn stop_recording_session(
        &self,
        session_id: String,
        stopped_at: String,
    ) -> RecorderControlResult {
        let Some(base_url) = configured_base_url() else {
            return unavailable_recorder_control_with_message(
                "Recorder sidecar URL is not configured.",
            );
        };

        self.stop_recording_session_from_base_url(session_id, stopped_at, &base_url)
    }

    pub fn stop_recording_session_from_base_url(
        &self,
        session_id: String,
        stopped_at: String,
        base_url: &str,
    ) -> RecorderControlResult {
        if session_id.trim().is_empty() || stopped_at.trim().is_empty() {
            return unavailable_recorder_control_with_message(
                "Recorder request is missing required session fields.",
            );
        }

        self.post_session_control(
            base_url,
            format!("/sessions/{}/stop", encode_path_segment(&session_id)),
            json!({ "stopped_at": stopped_at }),
            "Recording session stopped.",
        )
    }

    pub fn sessions(&self) -> SessionListResult {
        let Some(base_url) = configured_base_url() else {
            return unavailable_sessions();
        };

        self.sessions_from_base_url(&base_url)
    }

    pub fn sessions_from_base_url(&self, base_url: &str) -> SessionListResult {
        let Some(endpoint) = LocalHttpEndpoint::parse(base_url) else {
            return unavailable_sessions();
        };
        let Ok(body_text) = request_local_json(&endpoint, "GET", "/sessions", None) else {
            return unavailable_sessions();
        };
        let Ok(response) = serde_json::from_str::<SidecarSessionsResponse>(&body_text) else {
            return unavailable_sessions();
        };

        SessionListResult {
            status: SessionListStatus::Available,
            message: "Sessions loaded.".to_string(),
            sessions: response
                .sessions
                .into_iter()
                .map(SessionSummary::redacted)
                .collect(),
        }
    }

    pub fn delete_session(&self, session_id: String) -> SessionDeletionResult {
        let Some(base_url) = configured_base_url() else {
            return unavailable_session_deletion();
        };

        self.delete_session_from_base_url(session_id, &base_url)
    }

    pub fn delete_session_from_base_url(
        &self,
        session_id: String,
        base_url: &str,
    ) -> SessionDeletionResult {
        if session_id.trim().is_empty() {
            return unavailable_session_deletion();
        }

        let Some(endpoint) = LocalHttpEndpoint::parse(base_url) else {
            return unavailable_session_deletion();
        };
        let path = format!("/sessions/{}", encode_path_segment(&session_id));
        let Ok(body_text) = request_local_json(&endpoint, "DELETE", &path, None) else {
            return unavailable_session_deletion();
        };
        let Ok(response) = serde_json::from_str::<SidecarSessionDeletionResponse>(&body_text)
        else {
            return unavailable_session_deletion();
        };

        SessionDeletionResult {
            status: SessionDeletionStatus::Available,
            message: "Session deleted.".to_string(),
            deleted_session_rows: response.deleted_session_rows,
            deleted_screenshot_files: response.deleted_screenshot_files,
            missing_screenshot_files: response.missing_screenshot_files,
            deleted_screenshot_rows: response.deleted_screenshot_rows,
            removed_artifact_root: response.removed_artifact_root,
        }
    }

    pub fn privacy_policy(&self) -> PrivacyPolicyConfigResult {
        let Some(base_url) = configured_base_url() else {
            return unavailable_privacy_policy();
        };

        self.privacy_policy_from_base_url(&base_url)
    }

    pub fn privacy_policy_from_base_url(&self, base_url: &str) -> PrivacyPolicyConfigResult {
        let Some(endpoint) = LocalHttpEndpoint::parse(base_url) else {
            return unavailable_privacy_policy();
        };
        let Ok(body_text) = request_local_json(&endpoint, "GET", "/privacy/policy", None) else {
            return unavailable_privacy_policy();
        };
        let Ok(policy) = serde_json::from_str::<PrivacyPolicyConfig>(&body_text) else {
            return unavailable_privacy_policy();
        };

        PrivacyPolicyConfigResult {
            status: PrivacyPolicyConfigStatus::Available,
            message: "Privacy policy loaded.".to_string(),
            policy: Some(policy.redacted()),
        }
    }

    pub fn update_privacy_policy(
        &self,
        allowlist: Vec<String>,
        blocklist: Vec<String>,
        clipboard_safe_mode: bool,
    ) -> PrivacyPolicyConfigResult {
        let Some(base_url) = configured_base_url() else {
            return unavailable_privacy_policy();
        };

        self.update_privacy_policy_from_base_url(
            allowlist,
            blocklist,
            clipboard_safe_mode,
            &base_url,
        )
    }

    pub fn update_privacy_policy_from_base_url(
        &self,
        allowlist: Vec<String>,
        blocklist: Vec<String>,
        clipboard_safe_mode: bool,
        base_url: &str,
    ) -> PrivacyPolicyConfigResult {
        let Some(endpoint) = LocalHttpEndpoint::parse(base_url) else {
            return unavailable_privacy_policy();
        };
        let Ok(body_text) = request_local_json(
            &endpoint,
            "PUT",
            "/privacy/policy",
            Some(json!({
                "allowlist": sanitize_policy_entries(allowlist),
                "blocklist": sanitize_policy_entries(blocklist),
                "clipboard_safe_mode": clipboard_safe_mode,
            })),
        ) else {
            return unavailable_privacy_policy();
        };
        let Ok(policy) = serde_json::from_str::<PrivacyPolicyConfig>(&body_text) else {
            return unavailable_privacy_policy();
        };

        PrivacyPolicyConfigResult {
            status: PrivacyPolicyConfigStatus::Available,
            message: "Privacy policy saved.".to_string(),
            policy: Some(policy.redacted()),
        }
    }

    pub fn export_session_markdown(&self, session_id: String) -> SessionExportResult {
        let Some(base_url) = configured_base_url() else {
            return unavailable_export();
        };

        self.export_session_markdown_from_base_url(session_id, &base_url)
    }

    pub fn export_session_markdown_from_base_url(
        &self,
        session_id: String,
        base_url: &str,
    ) -> SessionExportResult {
        self.export_session_from_base_url(
            session_id,
            base_url,
            "markdown",
            "Markdown export generated.",
        )
    }

    pub fn export_session_raw_json(&self, session_id: String) -> SessionExportResult {
        let Some(base_url) = configured_base_url() else {
            return unavailable_export();
        };

        self.export_session_raw_json_from_base_url(session_id, &base_url)
    }

    pub fn export_session_raw_json_from_base_url(
        &self,
        session_id: String,
        base_url: &str,
    ) -> SessionExportResult {
        self.export_session_from_base_url(
            session_id,
            base_url,
            "raw-json",
            "Raw JSON export generated.",
        )
    }

    pub fn ai_report_status(&self, session_id: String) -> AiReportResult {
        let Some(base_url) = configured_base_url() else {
            return unavailable_ai_report();
        };

        self.ai_report_status_from_base_url(session_id, &base_url)
    }

    pub fn ai_report_status_from_base_url(
        &self,
        session_id: String,
        base_url: &str,
    ) -> AiReportResult {
        self.ai_report_from_base_url(session_id, base_url, "GET", "status")
    }

    pub fn generate_ai_report(&self, session_id: String) -> AiReportResult {
        let Some(base_url) = configured_base_url() else {
            return unavailable_ai_report();
        };

        self.generate_ai_report_from_base_url(session_id, &base_url)
    }

    pub fn generate_ai_report_from_base_url(
        &self,
        session_id: String,
        base_url: &str,
    ) -> AiReportResult {
        self.ai_report_from_base_url(session_id, base_url, "POST", "generate")
    }

    pub fn cancel_ai_report(&self, session_id: String) -> AiReportResult {
        let Some(base_url) = configured_base_url() else {
            return cancelled_ai_report();
        };

        self.cancel_ai_report_from_base_url(session_id, &base_url)
    }

    pub fn cancel_ai_report_from_base_url(
        &self,
        session_id: String,
        base_url: &str,
    ) -> AiReportResult {
        self.ai_report_from_base_url(session_id, base_url, "POST", "cancel")
    }

    pub fn session_folder(&self, session_id: String) -> SessionFolderResult {
        let Some(base_url) = configured_base_url() else {
            return unavailable_folder();
        };

        self.session_folder_from_base_url(session_id, &base_url)
    }

    pub fn open_session_folder(&self, session_id: String) -> SessionFolderResult {
        let Some(base_url) = configured_base_url() else {
            return unavailable_folder();
        };

        self.open_session_folder_from_base_url(session_id, &base_url)
    }

    pub fn session_screenshots(&self, session_id: String) -> SessionScreenshotsResult {
        let Some(base_url) = configured_base_url() else {
            return unavailable_screenshots();
        };

        self.session_screenshots_from_base_url(session_id, &base_url)
    }

    pub fn session_screenshot_preview(
        &self,
        session_id: String,
        screenshot_id: String,
    ) -> SessionScreenshotPreviewResult {
        let Some(base_url) = configured_base_url() else {
            return unavailable_screenshot_preview();
        };

        self.session_screenshot_preview_from_base_url(session_id, screenshot_id, &base_url)
    }

    pub fn session_screenshots_from_base_url(
        &self,
        session_id: String,
        base_url: &str,
    ) -> SessionScreenshotsResult {
        if session_id.trim().is_empty() {
            return unavailable_screenshots();
        }

        let Some(endpoint) = LocalHttpEndpoint::parse(base_url) else {
            return unavailable_screenshots();
        };
        let path = format!("/sessions/{}/screenshots", encode_path_segment(&session_id));
        let Ok(body_text) = request_local_json(&endpoint, "GET", &path, None) else {
            return unavailable_screenshots();
        };
        let Ok(response) = serde_json::from_str::<SidecarScreenshotsResponse>(&body_text) else {
            return unavailable_screenshots();
        };

        SessionScreenshotsResult {
            status: SessionScreenshotsStatus::Available,
            message: "Screenshot metadata loaded.".to_string(),
            screenshots: response
                .screenshots
                .into_iter()
                .map(SessionScreenshot::redacted)
                .collect(),
        }
    }

    pub fn session_screenshot_preview_from_base_url(
        &self,
        session_id: String,
        screenshot_id: String,
        base_url: &str,
    ) -> SessionScreenshotPreviewResult {
        if session_id.trim().is_empty() || screenshot_id.trim().is_empty() {
            return unavailable_screenshot_preview();
        }

        let Some(endpoint) = LocalHttpEndpoint::parse(base_url) else {
            return unavailable_screenshot_preview();
        };
        let path = format!(
            "/sessions/{}/screenshots/{}/preview",
            encode_path_segment(&session_id),
            encode_path_segment(&screenshot_id)
        );
        let Ok(body_text) = request_local_json(&endpoint, "GET", &path, None) else {
            return unavailable_screenshot_preview();
        };
        let Ok(response) = serde_json::from_str::<SidecarScreenshotPreviewResponse>(&body_text)
        else {
            return unavailable_screenshot_preview();
        };

        SessionScreenshotPreviewResult {
            status: SessionScreenshotPreviewStatus::Available,
            message: "Screenshot preview loaded locally.".to_string(),
            preview: Some(SessionScreenshotPreview {
                screenshot_id: redact_text(&response.screenshot_id),
                image_data_url: response.image_data_url,
                ocr_snippets: response
                    .ocr_snippets
                    .into_iter()
                    .map(|snippet| redact_text(&snippet))
                    .collect(),
            }),
        }
    }

    pub fn delete_session_screenshots(&self, session_id: String) -> ScreenshotDeletionResult {
        let Some(base_url) = configured_base_url() else {
            return unavailable_screenshot_deletion();
        };

        self.delete_session_screenshots_from_base_url(session_id, &base_url)
    }

    pub fn delete_session_screenshots_from_base_url(
        &self,
        session_id: String,
        base_url: &str,
    ) -> ScreenshotDeletionResult {
        if session_id.trim().is_empty() {
            return unavailable_screenshot_deletion();
        }

        let Some(endpoint) = LocalHttpEndpoint::parse(base_url) else {
            return unavailable_screenshot_deletion();
        };
        let path = format!("/sessions/{}/screenshots", encode_path_segment(&session_id));
        let Ok(body_text) = request_local_json(&endpoint, "DELETE", &path, None) else {
            return unavailable_screenshot_deletion();
        };
        let Ok(response) = serde_json::from_str::<SidecarScreenshotDeletionResponse>(&body_text)
        else {
            return unavailable_screenshot_deletion();
        };

        ScreenshotDeletionResult {
            status: ScreenshotDeletionStatus::Available,
            message: "Screenshots deleted.".to_string(),
            deleted_files: response.deleted_files,
            missing_files: response.missing_files,
            deleted_rows: response.deleted_rows,
        }
    }

    pub fn session_folder_from_base_url(
        &self,
        session_id: String,
        base_url: &str,
    ) -> SessionFolderResult {
        let Some(folder) = self.session_folder_response_from_base_url(session_id, base_url) else {
            return unavailable_folder();
        };

        SessionFolderResult {
            status: SessionFolderStatus::Available,
            message: "Session folder is available.".to_string(),
            path: Some(redact_text(&folder.path)),
        }
    }

    pub fn open_session_folder_from_base_url(
        &self,
        session_id: String,
        base_url: &str,
    ) -> SessionFolderResult {
        self.open_session_folder_from_base_url_with_launcher(session_id, base_url, launch_folder)
    }

    pub fn open_session_folder_from_base_url_with_launcher(
        &self,
        session_id: String,
        base_url: &str,
        launcher: impl Fn(&PathBuf) -> bool,
    ) -> SessionFolderResult {
        let Some(folder) = self.session_folder_response_from_base_url(session_id, base_url) else {
            return unavailable_folder();
        };
        let path = PathBuf::from(&folder.path);
        if !path.is_dir() {
            return SessionFolderResult {
                status: SessionFolderStatus::Unavailable,
                message: "Session folder does not exist.".to_string(),
                path: None,
            };
        }
        if !launcher(&path) {
            return SessionFolderResult {
                status: SessionFolderStatus::Unavailable,
                message: "Session folder could not be opened.".to_string(),
                path: Some(redact_text(&folder.path)),
            };
        }

        SessionFolderResult {
            status: SessionFolderStatus::Available,
            message: "Session folder opened in File Explorer.".to_string(),
            path: Some(redact_text(&folder.path)),
        }
    }

    fn session_folder_response_from_base_url(
        &self,
        session_id: String,
        base_url: &str,
    ) -> Option<SidecarSessionFolderResponse> {
        if session_id.trim().is_empty() {
            return None;
        }

        let endpoint = LocalHttpEndpoint::parse(base_url)?;
        let path = format!("/sessions/{}/folder", encode_path_segment(&session_id));
        let Ok(body_text) = request_local_json(&endpoint, "GET", &path, None) else {
            return None;
        };
        let Ok(folder) = serde_json::from_str::<SidecarSessionFolderResponse>(&body_text) else {
            return None;
        };

        Some(folder)
    }

    pub fn events_from_base_url(&self, session_id: String, base_url: &str) -> SessionEventsResult {
        if session_id.trim().is_empty() {
            return unavailable_events();
        }

        let Some(endpoint) = LocalHttpEndpoint::parse(base_url) else {
            return unavailable_events();
        };

        let path = format!("/sessions/{}/events", encode_path_segment(&session_id));
        let Ok(body) = request_local_json(&endpoint, "GET", &path, None) else {
            return unavailable_events();
        };

        let Ok(response) = serde_json::from_str::<SidecarEventsResponse>(&body) else {
            return unavailable_events();
        };

        SessionEventsResult {
            status: SessionEventsStatus::Available,
            events: response
                .events
                .into_iter()
                .filter(is_timeline_event)
                .map(SessionTimelineEvent::from)
                .collect(),
        }
    }

    pub fn health_from_base_url(&self, base_url: &str) -> SidecarHealth {
        let Some(endpoint) = LocalHttpEndpoint::parse(base_url) else {
            return unhealthy_health("Local agent sidecar URL must use localhost.");
        };
        let Ok(body) = request_local_json(&endpoint, "GET", "/health", None) else {
            return unhealthy_health("Local agent sidecar health check failed.");
        };
        let Ok(response) = serde_json::from_str::<SidecarHealthResponse>(&body) else {
            return unhealthy_health("Local agent sidecar health response was invalid.");
        };
        if response.status != "ok" {
            return unhealthy_health("Local agent sidecar reported unhealthy status.");
        }

        SidecarHealth {
            status: SidecarStatus::Healthy,
            app_version: Some(redact_text(&response.app_version)),
            schema_version: Some(redact_text(&response.schema_version)),
            message: "Local agent sidecar is healthy.".to_string(),
        }
    }

    fn post_session_control(
        &self,
        base_url: &str,
        path: String,
        body: Value,
        message: &str,
    ) -> RecorderControlResult {
        let Some(endpoint) = LocalHttpEndpoint::parse(base_url) else {
            return unavailable_recorder_control_with_message(
                "Recorder sidecar URL must use localhost.",
            );
        };
        let Ok(body_text) = request_local_json(&endpoint, "POST", &path, Some(body)) else {
            return unavailable_recorder_control_with_message("Recorder sidecar request failed.");
        };
        let Ok(session) = serde_json::from_str::<RecorderSession>(&body_text) else {
            return unavailable_recorder_control_with_message(
                "Recorder response contract mismatch.",
            );
        };

        RecorderControlResult {
            status: RecorderControlStatus::Available,
            message: message.to_string(),
            session: Some(session.redacted()),
        }
    }

    fn export_session_from_base_url(
        &self,
        session_id: String,
        base_url: &str,
        format_path: &str,
        message: &str,
    ) -> SessionExportResult {
        if session_id.trim().is_empty() {
            return unavailable_export();
        }

        let Some(endpoint) = LocalHttpEndpoint::parse(base_url) else {
            return unavailable_export();
        };
        let path = format!(
            "/sessions/{}/exports/{}",
            encode_path_segment(&session_id),
            format_path
        );
        let Ok(body_text) = request_local_json(&endpoint, "POST", &path, None) else {
            return unavailable_export();
        };
        let Ok(export) = serde_json::from_str::<SessionExportPreview>(&body_text) else {
            return unavailable_export();
        };

        SessionExportResult {
            status: SessionExportStatus::Available,
            message: message.to_string(),
            export: Some(export.redacted()),
        }
    }

    fn ai_report_from_base_url(
        &self,
        session_id: String,
        base_url: &str,
        method: &str,
        action: &str,
    ) -> AiReportResult {
        if session_id.trim().is_empty() {
            return unavailable_ai_report();
        }

        let Some(endpoint) = LocalHttpEndpoint::parse(base_url) else {
            return unavailable_ai_report();
        };
        let path = format!(
            "/sessions/{}/ai-report/{}",
            encode_path_segment(&session_id),
            action
        );
        let Ok(body_text) = request_local_json(&endpoint, method, &path, None) else {
            return unavailable_ai_report();
        };
        let Ok(result) = serde_json::from_str::<AiReportResult>(&body_text) else {
            return unavailable_ai_report();
        };

        result.redacted()
    }
}

fn missing_health(message: &str) -> SidecarHealth {
    SidecarHealth {
        status: SidecarStatus::Missing,
        app_version: None,
        schema_version: None,
        message: message.to_string(),
    }
}

fn unhealthy_health(message: &str) -> SidecarHealth {
    SidecarHealth {
        status: SidecarStatus::Unhealthy,
        app_version: None,
        schema_version: None,
        message: message.to_string(),
    }
}

fn starting_health() -> SidecarHealth {
    SidecarHealth {
        status: SidecarStatus::Unhealthy,
        app_version: None,
        schema_version: None,
        message: "Local agent sidecar process started; health check is still pending.".to_string(),
    }
}

fn unavailable_events() -> SessionEventsResult {
    SessionEventsResult {
        status: SessionEventsStatus::Unavailable,
        events: Vec::new(),
    }
}

fn unavailable_recorder_control_with_message(message: &str) -> RecorderControlResult {
    RecorderControlResult {
        status: RecorderControlStatus::Unavailable,
        message: message.to_string(),
        session: None,
    }
}

fn unavailable_sessions() -> SessionListResult {
    SessionListResult {
        status: SessionListStatus::Unavailable,
        message: "Session browser bridge is unavailable.".to_string(),
        sessions: Vec::new(),
    }
}

fn unavailable_privacy_policy() -> PrivacyPolicyConfigResult {
    PrivacyPolicyConfigResult {
        status: PrivacyPolicyConfigStatus::Unavailable,
        message: "Privacy policy bridge is unavailable.".to_string(),
        policy: None,
    }
}

fn unavailable_session_deletion() -> SessionDeletionResult {
    SessionDeletionResult {
        status: SessionDeletionStatus::Unavailable,
        message: "Session delete bridge is unavailable.".to_string(),
        deleted_session_rows: 0,
        deleted_screenshot_files: 0,
        missing_screenshot_files: 0,
        deleted_screenshot_rows: 0,
        removed_artifact_root: false,
    }
}

fn unavailable_export() -> SessionExportResult {
    SessionExportResult {
        status: SessionExportStatus::Unavailable,
        message: "Session export bridge is unavailable.".to_string(),
        export: None,
    }
}

fn unavailable_ai_report() -> AiReportResult {
    AiReportResult {
        status: AiReportStatus::RuntimeUnavailable,
        message: "Local AI report bridge is unavailable.".to_string(),
        can_generate: false,
        report: None,
        evidence_ids: Vec::new(),
        model_name: None,
        model_version: None,
        provider: None,
        requested_model: None,
        actual_model: None,
        fallback_used: false,
        runtime_ms: None,
        input_hash: None,
        generated_at: None,
    }
}

fn cancelled_ai_report() -> AiReportResult {
    AiReportResult {
        status: AiReportStatus::Cancelled,
        message: "Local AI report generation cancelled.".to_string(),
        can_generate: true,
        report: None,
        evidence_ids: Vec::new(),
        model_name: None,
        model_version: None,
        provider: None,
        requested_model: None,
        actual_model: None,
        fallback_used: false,
        runtime_ms: None,
        input_hash: None,
        generated_at: None,
    }
}

fn unavailable_folder() -> SessionFolderResult {
    SessionFolderResult {
        status: SessionFolderStatus::Unavailable,
        message: "Session folder bridge is unavailable.".to_string(),
        path: None,
    }
}

fn unavailable_screenshots() -> SessionScreenshotsResult {
    SessionScreenshotsResult {
        status: SessionScreenshotsStatus::Unavailable,
        message: "Screenshot metadata bridge is unavailable.".to_string(),
        screenshots: Vec::new(),
    }
}

fn unavailable_screenshot_preview() -> SessionScreenshotPreviewResult {
    SessionScreenshotPreviewResult {
        status: SessionScreenshotPreviewStatus::Unavailable,
        message: "Screenshot preview bridge is unavailable.".to_string(),
        preview: None,
    }
}

fn unavailable_screenshot_deletion() -> ScreenshotDeletionResult {
    ScreenshotDeletionResult {
        status: ScreenshotDeletionStatus::Unavailable,
        message: "Screenshot delete bridge is unavailable.".to_string(),
        deleted_files: 0,
        missing_files: 0,
        deleted_rows: 0,
    }
}

impl RecorderSession {
    fn redacted(self) -> Self {
        Self {
            id: redact_text(&self.id),
            started_at: redact_text(&self.started_at),
            ended_at: self.ended_at.map(|ended_at| redact_text(&ended_at)),
            status: redact_text(&self.status),
            title: self.title.map(|title| redact_text(&title)),
            goal: self.goal.map(|goal| redact_text(&goal)),
            project_label: self
                .project_label
                .map(|project_label| redact_text(&project_label)),
            tags: self.tags.into_iter().map(|tag| redact_text(&tag)).collect(),
            storage_path: self.storage_path.map(|path| redact_text(&path)),
            privacy_mode: redact_text(&self.privacy_mode),
        }
    }
}

impl SessionSummary {
    fn redacted(self) -> Self {
        Self {
            id: redact_text(&self.id),
            started_at: redact_text(&self.started_at),
            ended_at: self.ended_at.map(|ended_at| redact_text(&ended_at)),
            status: redact_text(&self.status),
            title: self.title.map(|title| redact_text(&title)),
            goal: self.goal.map(|goal| redact_text(&goal)),
            project_label: self
                .project_label
                .map(|project_label| redact_text(&project_label)),
            tags: self.tags.into_iter().map(|tag| redact_text(&tag)).collect(),
            storage_path: self.storage_path.map(|path| redact_text(&path)),
            privacy_mode: redact_text(&self.privacy_mode),
            event_count: self.event_count,
            screenshot_count: self.screenshot_count,
        }
    }
}

impl PrivacyPolicyConfig {
    fn redacted(self) -> Self {
        Self {
            allowlist: self
                .allowlist
                .into_iter()
                .map(|entry| redact_text(&entry))
                .collect(),
            blocklist: self
                .blocklist
                .into_iter()
                .map(|entry| redact_text(&entry))
                .collect(),
            clipboard_safe_mode: self.clipboard_safe_mode,
        }
    }
}

impl SessionExportPreview {
    fn redacted(self) -> Self {
        Self {
            format: redact_text(&self.format),
            path: redact_text(&self.path),
            preview: redact_text(&self.preview),
            evidence_ids: self
                .evidence_ids
                .into_iter()
                .map(|evidence_id| redact_text(&evidence_id))
                .collect(),
        }
    }
}

impl AiReportResult {
    fn redacted(self) -> Self {
        Self {
            status: self.status,
            message: redact_text(&self.message),
            can_generate: self.can_generate,
            report: self.report.map(AiReportPayload::redacted),
            evidence_ids: self
                .evidence_ids
                .into_iter()
                .map(|evidence_id| redact_text(&evidence_id))
                .collect(),
            model_name: self.model_name.map(|model_name| redact_text(&model_name)),
            model_version: self
                .model_version
                .map(|model_version| redact_text(&model_version)),
            provider: self.provider.map(|provider| redact_text(&provider)),
            requested_model: self
                .requested_model
                .map(|requested_model| redact_text(&requested_model)),
            actual_model: self
                .actual_model
                .map(|actual_model| redact_text(&actual_model)),
            fallback_used: self.fallback_used,
            runtime_ms: self.runtime_ms,
            input_hash: self.input_hash.map(|input_hash| redact_text(&input_hash)),
            generated_at: self
                .generated_at
                .map(|generated_at| redact_text(&generated_at)),
        }
    }
}

impl AiReportPayload {
    fn redacted(self) -> Self {
        Self {
            session_id: redact_text(&self.session_id),
            session_title: redact_text(&self.session_title),
            summary: self.summary.redacted(),
            observed_work: self
                .observed_work
                .into_iter()
                .map(AiReportClaim::redacted)
                .collect(),
            timeline: self
                .timeline
                .into_iter()
                .map(AiReportClaim::redacted)
                .collect(),
            blockers: self
                .blockers
                .into_iter()
                .map(AiReportClaim::redacted)
                .collect(),
            context_switches: self
                .context_switches
                .into_iter()
                .map(AiReportClaim::redacted)
                .collect(),
            unfinished_work: self
                .unfinished_work
                .into_iter()
                .map(AiReportClaim::redacted)
                .collect(),
            repeated_actions: self
                .repeated_actions
                .into_iter()
                .map(AiReportClaim::redacted)
                .collect(),
            important_files: self
                .important_files
                .into_iter()
                .map(AiReportClaim::redacted)
                .collect(),
            commands: self
                .commands
                .into_iter()
                .map(AiReportClaim::redacted)
                .collect(),
            workflow_steps: self
                .workflow_steps
                .into_iter()
                .map(AiReportClaim::redacted)
                .collect(),
            continuation_notes: self
                .continuation_notes
                .into_iter()
                .map(AiReportClaim::redacted)
                .collect(),
            confidence: self.confidence,
            known_evidence_event_ids: self
                .known_evidence_event_ids
                .into_iter()
                .map(|evidence_id| redact_text(&evidence_id))
                .collect(),
        }
    }
}

impl AiReportClaim {
    fn redacted(self) -> Self {
        Self {
            title: self.title.map(|title| redact_text(&title)),
            text: self.text.map(|text| redact_text(&text)),
            path: self.path.map(|path| redact_text(&path)),
            command: self.command.map(|command| redact_text(&command)),
            evidence_event_ids: self
                .evidence_event_ids
                .into_iter()
                .map(|evidence_id| redact_text(&evidence_id))
                .collect(),
        }
    }
}

impl SessionScreenshot {
    fn redacted(self) -> Self {
        Self {
            id: redact_text(&self.id),
            session_id: redact_text(&self.session_id),
            source_event_id: self
                .source_event_id
                .map(|source_event_id| redact_text(&source_event_id)),
            timestamp: redact_text(&self.timestamp),
            width: self.width,
            height: self.height,
            stored_width: self.stored_width,
            stored_height: self.stored_height,
            byte_size: self.byte_size,
            content_hash: redact_text(&self.content_hash),
            visual_hash: redact_text(&self.visual_hash),
            storage_path: redact_text(&self.storage_path),
        }
    }
}

impl From<SidecarRawEvent> for SessionTimelineEvent {
    fn from(event: SidecarRawEvent) -> Self {
        let (app, window_title) = timeline_display_text(&event);

        Self {
            id: redact_text(&event.id),
            timestamp: redact_text(&event.timestamp),
            app,
            window_title,
            source: event.source,
            event_type: event.event_type,
        }
    }
}

fn is_timeline_event(event: &SidecarRawEvent) -> bool {
    matches!(
        (event.source.as_str(), event.event_type.as_str()),
        ("active_window", "active_window_changed")
            | ("file_watcher", "file_changed")
            | ("terminal_command_detector", "terminal_command")
    )
}

fn timeline_display_text(event: &SidecarRawEvent) -> (String, String) {
    if event.source == "terminal_command_detector" && event.event_type == "terminal_command" {
        let command = event
            .metadata
            .get("command")
            .and_then(Value::as_str)
            .unwrap_or("unknown command");
        let shell = event
            .metadata
            .get("shell")
            .and_then(Value::as_str)
            .unwrap_or("terminal");
        let exit_code = event
            .metadata
            .get("exit_code")
            .and_then(Value::as_i64)
            .map(|code| format!(" exit {code}"))
            .unwrap_or_default();
        return (
            "Terminal command".to_string(),
            redact_text(&format!("{shell}{exit_code}: {command}")),
        );
    }

    if event.source == "file_watcher" && event.event_type == "file_changed" {
        let operation = event
            .metadata
            .get("operation")
            .and_then(Value::as_str)
            .unwrap_or("changed");
        let path = event
            .metadata
            .get("path")
            .and_then(Value::as_str)
            .unwrap_or("unknown path");
        return (
            "File change".to_string(),
            redact_text(&format!("{operation} {path}")),
        );
    }

    let app = event
        .metadata
        .get("app")
        .and_then(Value::as_str)
        .unwrap_or("Unknown app");
    let window_title = event
        .metadata
        .get("window_title")
        .and_then(Value::as_str)
        .unwrap_or("Untitled window");
    (redact_text(app), redact_text(window_title))
}

#[derive(Debug)]
struct LocalHttpEndpoint {
    host: String,
    port: u16,
}

impl LocalHttpEndpoint {
    fn parse(base_url: &str) -> Option<Self> {
        let without_scheme = base_url.strip_prefix("http://")?;
        let authority = without_scheme.split('/').next()?.trim();
        let (host, port_text) = authority.rsplit_once(':')?;
        if host != "127.0.0.1" && host != "localhost" {
            return None;
        }
        let port = port_text.parse::<u16>().ok()?;
        Some(Self {
            host: host.to_string(),
            port,
        })
    }
}

fn configured_base_url() -> Option<String> {
    if let Ok(base_url) = env::var(SIDECAR_URL_ENV) {
        if LocalHttpEndpoint::parse(&base_url).is_some() {
            return Some(base_url);
        }
        return None;
    }

    let port = configured_sidecar_port()?;
    Some(sidecar_base_url_from_port(port))
}

fn configured_sidecar_port() -> Option<u16> {
    if let Ok(port) = env::var(SIDECAR_PORT_ENV) {
        return port.parse::<u16>().ok();
    }
    if configured_sidecar_binary().is_some() {
        return Some(DEFAULT_SIDECAR_PORT);
    }
    None
}

fn configured_sidecar_binary() -> Option<PathBuf> {
    let configured_path = env::var(SIDECAR_BIN_ENV).ok().map(PathBuf::from);
    let app_dir = env::current_exe().ok()?.parent()?.to_path_buf();

    resolve_sidecar_binary(configured_path, app_dir)
}

pub fn sidecar_base_url_from_port(port: u16) -> String {
    format!("http://127.0.0.1:{port}")
}

pub fn resolve_sidecar_binary(
    configured_path: Option<PathBuf>,
    app_dir: PathBuf,
) -> Option<PathBuf> {
    if let Some(path) = configured_path {
        if path.is_file() {
            return Some(path);
        }
    }

    bundled_sidecar_binary_in_dir(app_dir)
}

fn bundled_sidecar_binary_in_dir(app_dir: PathBuf) -> Option<PathBuf> {
    let candidates = [
        app_dir.join("sidecars").join(BUNDLED_SIDECAR_NAME),
        app_dir.join(BUNDLED_SIDECAR_NAME),
    ];

    candidates.into_iter().find(|candidate| candidate.is_file())
}

fn launch_folder(path: &PathBuf) -> bool {
    if cfg!(windows) {
        return Command::new("explorer")
            .arg(path)
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .is_ok();
    }

    false
}

pub fn sidecar_launch_environment(port: u16) -> [(String, String); 2] {
    [
        (
            "WORKTRACE_SIDECAR_HOST".to_string(),
            "127.0.0.1".to_string(),
        ),
        ("WORKTRACE_SIDECAR_PORT".to_string(), port.to_string()),
    ]
}

fn start_managed_sidecar(binary_path: PathBuf) -> SidecarHealth {
    let process_lock = managed_sidecar_process();
    let Ok(mut process) = process_lock.lock() else {
        return unhealthy_health("Local agent sidecar process state is unavailable.");
    };

    if let Some(child) = process.as_mut() {
        match child.try_wait() {
            Ok(None) => return starting_health(),
            Ok(Some(_)) | Err(_) => {
                *process = None;
            }
        }
    }

    let mut command = Command::new(binary_path);
    command
        .args(configured_sidecar_args())
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    for (key, value) in
        sidecar_launch_environment(configured_sidecar_port().unwrap_or(DEFAULT_SIDECAR_PORT))
    {
        command.env(key, value);
    }

    let Ok(child) = command.spawn() else {
        return unhealthy_health("Local agent sidecar process could not be started.");
    };
    write_sidecar_pid_file(child.id());

    *process = Some(child);
    starting_health()
}

fn stop_managed_sidecar() -> bool {
    let process_lock = managed_sidecar_process();
    let Ok(mut process) = process_lock.lock() else {
        return false;
    };
    let Some(mut child) = process.take() else {
        return false;
    };

    let pid = child.id();
    kill_sidecar_process_tree(pid);
    let _ = child.kill();
    let _ = child.wait();
    remove_sidecar_pid_file(pid);
    true
}

fn stop_pid_file_sidecar() -> bool {
    let Some(pid) = read_sidecar_pid_file() else {
        return false;
    };

    kill_sidecar_process_tree(pid);
    remove_sidecar_pid_file(pid);
    true
}

fn kill_sidecar_process_tree(pid: u32) {
    let command = sidecar_process_tree_kill_command(pid);
    let _ = Command::new(command.program)
        .args(command.args)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status();
}

fn sidecar_process_tree_kill_command(pid: u32) -> SidecarProcessKillCommand {
    if cfg!(windows) {
        return SidecarProcessKillCommand {
            program: "taskkill".to_string(),
            args: vec![
                "/PID".to_string(),
                pid.to_string(),
                "/T".to_string(),
                "/F".to_string(),
            ],
        };
    }

    SidecarProcessKillCommand {
        program: "kill".to_string(),
        args: vec!["-TERM".to_string(), pid.to_string()],
    }
}

pub fn sidecar_process_tree_kill_command_for_test(pid: u32) -> SidecarProcessKillCommand {
    sidecar_process_tree_kill_command(pid)
}

fn managed_sidecar_process() -> &'static Mutex<Option<Child>> {
    static PROCESS: OnceLock<Mutex<Option<Child>>> = OnceLock::new();
    PROCESS.get_or_init(|| Mutex::new(None))
}

fn sidecar_pid_file_path(port: u16) -> PathBuf {
    env::temp_dir().join(format!("worktrace-local-agent-{port}.pid"))
}

fn write_sidecar_pid_file(pid: u32) {
    let port = configured_sidecar_port().unwrap_or(DEFAULT_SIDECAR_PORT);
    let path = sidecar_pid_file_path(port);
    let _ = fs::write(path, pid.to_string());
}

fn read_sidecar_pid_file() -> Option<u32> {
    let port = configured_sidecar_port().unwrap_or(DEFAULT_SIDECAR_PORT);
    let path = sidecar_pid_file_path(port);
    let pid_text = fs::read_to_string(path).ok()?;
    pid_text.trim().parse::<u32>().ok()
}

fn remove_sidecar_pid_file(pid: u32) {
    let port = configured_sidecar_port().unwrap_or(DEFAULT_SIDECAR_PORT);
    let path = sidecar_pid_file_path(port);
    if let Ok(pid_text) = fs::read_to_string(&path) {
        if pid_text.trim() != pid.to_string() {
            return;
        }
    }
    let _ = fs::remove_file(path);
}

pub fn sidecar_pid_file_path_for_test(port: u16) -> PathBuf {
    sidecar_pid_file_path(port)
}

pub fn forget_managed_sidecar_for_test() {
    if let Ok(mut process) = managed_sidecar_process().lock() {
        *process = None;
    }
}

fn configured_sidecar_args() -> Vec<String> {
    env::var(SIDECAR_ARGS_ENV)
        .ok()
        .map(|args| args.split_whitespace().map(str::to_string).collect())
        .unwrap_or_default()
}

fn request_local_json(
    endpoint: &LocalHttpEndpoint,
    method: &str,
    path: &str,
    body: Option<Value>,
) -> Result<String, ()> {
    let address = (endpoint.host.as_str(), endpoint.port)
        .to_socket_addrs()
        .map_err(|_| ())?
        .next()
        .ok_or(())?;
    let mut stream = TcpStream::connect_timeout(&address, HTTP_TIMEOUT).map_err(|_| ())?;
    stream
        .set_read_timeout(Some(HTTP_TIMEOUT))
        .map_err(|_| ())?;
    stream
        .set_write_timeout(Some(HTTP_TIMEOUT))
        .map_err(|_| ())?;
    let body_text = body.map(|value| value.to_string()).unwrap_or_default();
    let request = if body_text.is_empty() {
        format!(
            "{method} {path} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\nAccept: application/json\r\n\r\n",
            endpoint.host
        )
    } else {
        format!(
            "{method} {path} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\nAccept: application/json\r\nContent-Type: application/json\r\nContent-Length: {}\r\n\r\n{}",
            endpoint.host,
            body_text.len(),
            body_text
        )
    };
    stream.write_all(request.as_bytes()).map_err(|_| ())?;

    let mut response = String::new();
    stream.read_to_string(&mut response).map_err(|_| ())?;
    if !response.starts_with("HTTP/1.1 200") && !response.starts_with("HTTP/1.0 200") {
        return Err(());
    }

    response
        .split_once("\r\n\r\n")
        .map(|(_, body)| body.to_string())
        .ok_or(())
}

fn encode_path_segment(value: &str) -> String {
    value
        .bytes()
        .map(|byte| match byte {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' => (byte as char).to_string(),
            _ => format!("%{byte:02X}"),
        })
        .collect()
}

fn sanitize_file_watch_roots(file_watch_roots: Vec<String>) -> Vec<String> {
    let mut sanitized = Vec::new();
    for root in file_watch_roots {
        let trimmed = root.trim();
        if trimmed.is_empty() || sanitized.iter().any(|existing| existing == trimmed) {
            continue;
        }
        sanitized.push(trimmed.to_string());
        if sanitized.len() >= MAX_FILE_WATCH_ROOTS {
            break;
        }
    }
    sanitized
}

fn sanitize_session_tags(tags: Vec<String>) -> Vec<String> {
    let mut sanitized = Vec::new();
    for tag in tags {
        let trimmed = tag.trim();
        if trimmed.is_empty() || sanitized.iter().any(|existing| existing == trimmed) {
            continue;
        }
        sanitized.push(trimmed.to_string());
        if sanitized.len() >= MAX_SESSION_TAGS {
            break;
        }
    }
    sanitized
}

fn sanitize_policy_entries(entries: Vec<String>) -> Vec<String> {
    let mut sanitized = Vec::new();
    for entry in entries {
        let trimmed = entry.trim();
        if trimmed.is_empty() || sanitized.iter().any(|existing| existing == trimmed) {
            continue;
        }
        sanitized.push(trimmed.to_string());
        if sanitized.len() >= MAX_POLICY_ENTRY_COUNT {
            break;
        }
    }
    sanitized
}

fn redact_text(value: &str) -> String {
    let mut redacted = value.to_string();
    for secret in SECRET_FRAGMENTS {
        redacted = redacted.replace(secret, REDACTION_TOKEN);
    }
    redacted
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sanitize_file_watch_roots_trims_deduplicates_and_caps_roots() {
        let mut roots = vec![
            " C:\\repo ".to_string(),
            "".to_string(),
            "C:\\repo".to_string(),
        ];
        roots.extend((0..20).map(|index| format!("C:\\repo-{index}")));

        let sanitized = sanitize_file_watch_roots(roots);

        assert_eq!(sanitized[0], "C:\\repo");
        assert_eq!(sanitized.len(), MAX_FILE_WATCH_ROOTS);
        assert_eq!(
            sanitized.iter().filter(|root| *root == "C:\\repo").count(),
            1
        );
    }

    #[test]
    fn sanitize_policy_entries_trims_deduplicates_and_caps_entries() {
        let mut entries = vec![
            " Code.exe ".to_string(),
            "".to_string(),
            "Code.exe".to_string(),
        ];
        entries.extend((0..80).map(|index| format!("app-{index}.exe")));

        let sanitized = sanitize_policy_entries(entries);

        assert_eq!(sanitized[0], "Code.exe");
        assert_eq!(sanitized.len(), MAX_POLICY_ENTRY_COUNT);
        assert_eq!(
            sanitized
                .iter()
                .filter(|entry| *entry == "Code.exe")
                .count(),
            1
        );
    }
}
