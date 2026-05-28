import { invoke } from "@tauri-apps/api/core";

export type SidecarStatus = "loading" | "healthy" | "unhealthy" | "missing";

export type SidecarHealth = {
  status: SidecarStatus;
  appVersion: string | null;
  schemaVersion: string | null;
  message: string;
};

export type SessionTimelineEvent = {
  id: string;
  timestamp: string;
  app: string;
  windowTitle: string;
  source: "active_window" | "file_watcher" | "terminal_command_detector";
  type: "active_window_changed" | "file_changed" | "terminal_command";
};

export type SessionEventsResult =
  | { status: "available"; events: SessionTimelineEvent[] }
  | { status: "unavailable"; events: [] };

export type RecorderSessionStatus = "recording" | "paused" | "stopped" | "interrupted";

export type RecorderSession = {
  id: string;
  startedAt: string;
  endedAt: string | null;
  status: RecorderSessionStatus;
  title: string | null;
  goal: string | null;
  projectLabel: string | null;
  tags: string[];
  storagePath: string | null;
  privacyMode: string;
};

export type RecorderControlResult =
  | { status: "available"; message: string; session: RecorderSession }
  | { status: "unavailable"; message: string; session: null };

export type StartRecordingSessionInput = {
  sessionId: string;
  startedAt: string;
  title: string | null;
  goal: string | null;
  projectLabel: string | null;
  tags: string[];
  privacyMode: string;
  fileWatchRoots: string[];
};

export type PauseRecordingSessionInput = {
  sessionId: string;
  pausedAt: string;
};

export type ResumeRecordingSessionInput = {
  sessionId: string;
  resumedAt: string;
  fileWatchRoots: string[];
};

export type StopRecordingSessionInput = {
  sessionId: string;
  stoppedAt: string;
};

export type SessionExportPreview = {
  format: "markdown" | "raw_json" | string;
  path: string;
  preview: string;
  evidenceIds: string[];
};

export type SessionExportResult =
  | { status: "available"; message: string; export: SessionExportPreview }
  | { status: "unavailable"; message: string; export: null };

export type AiReportStatus =
  | "not_installed"
  | "runtime_unavailable"
  | "loading"
  | "ready"
  | "running"
  | "failed_safely"
  | "complete"
  | "too_slow"
  | "cancelled";

export type AiReportClaim = {
  title?: string | null;
  text?: string | null;
  path?: string | null;
  command?: string | null;
  evidenceEventIds: string[];
};

export type AiReportPayload = {
  sessionId: string;
  sessionTitle: string;
  summary: AiReportClaim;
  observedWork?: AiReportClaim[];
  timeline: AiReportClaim[];
  blockers: AiReportClaim[];
  contextSwitches?: AiReportClaim[];
  unfinishedWork?: AiReportClaim[];
  repeatedActions: AiReportClaim[];
  importantFiles: AiReportClaim[];
  commands: AiReportClaim[];
  workflowSteps: AiReportClaim[];
  continuationNotes?: AiReportClaim[];
  confidence: number;
  knownEvidenceEventIds: string[];
};

export type AiReportResult = {
  status: AiReportStatus;
  message: string;
  canGenerate: boolean;
  report: AiReportPayload | null;
  evidenceIds: string[];
  modelName: string | null;
  modelVersion: string | null;
  provider?: "local_ollama" | "gemini_gemma_dev" | null;
  requestedModel?: string | null;
  actualModel?: string | null;
  fallbackUsed?: boolean;
  runtimeMs: number | null;
  inputHash: string | null;
  generatedAt: string | null;
};

export type SessionFolderResult =
  | { status: "available"; message: string; path: string }
  | { status: "unavailable"; message: string; path: null };

export type SessionScreenshot = {
  id: string;
  sessionId: string;
  sourceEventId: string | null;
  timestamp: string;
  width: number;
  height: number;
  storedWidth: number;
  storedHeight: number;
  byteSize: number;
  contentHash: string;
  visualHash: string;
  storagePath: string;
};

export type SessionScreenshotsResult =
  | { status: "available"; message: string; screenshots: SessionScreenshot[] }
  | { status: "unavailable"; message: string; screenshots: [] };

export type SessionScreenshotPreview = {
  screenshotId: string;
  imageDataUrl: string;
  ocrSnippets: string[];
};

export type SessionScreenshotPreviewResult =
  | { status: "available"; message: string; preview: SessionScreenshotPreview }
  | { status: "unavailable"; message: string; preview: null };

export type ScreenshotDeletionResult =
  | {
      status: "available";
      message: string;
      deletedFiles: number;
      missingFiles: number;
      deletedRows: number;
    }
  | {
      status: "unavailable";
      message: string;
      deletedFiles: 0;
      missingFiles: 0;
      deletedRows: 0;
    };

export type SessionSummary = {
  id: string;
  startedAt: string;
  endedAt: string | null;
  status: string;
  title: string | null;
  goal: string | null;
  projectLabel: string | null;
  tags: string[];
  storagePath: string | null;
  privacyMode: string;
  eventCount: number;
  screenshotCount: number;
};

export type SessionListResult =
  | { status: "available"; message: string; sessions: SessionSummary[] }
  | { status: "unavailable"; message: string; sessions: [] };

export type SessionDeletionResult =
  | {
      status: "available";
      message: string;
      deletedSessionRows: number;
      deletedScreenshotFiles: number;
      missingScreenshotFiles: number;
      deletedScreenshotRows: number;
      removedArtifactRoot: boolean;
    }
  | {
      status: "unavailable";
      message: string;
      deletedSessionRows: 0;
      deletedScreenshotFiles: 0;
      missingScreenshotFiles: 0;
      deletedScreenshotRows: 0;
      removedArtifactRoot: false;
    };

export type PrivacyPolicyConfig = {
  allowlist: string[];
  blocklist: string[];
  clipboardSafeMode: boolean;
};

export type PrivacyPolicyConfigResult =
  | { status: "available"; message: string; policy: PrivacyPolicyConfig }
  | { status: "unavailable"; message: string; policy: null };

const SIDE_CAR_COMMANDS = {
  health: "get_sidecar_health",
  start: "start_sidecar",
  stop: "stop_sidecar",
  sessionEvents: "get_session_events",
  startRecordingSession: "start_recording_session",
  pauseRecordingSession: "pause_recording_session",
  resumeRecordingSession: "resume_recording_session",
  stopRecordingSession: "stop_recording_session",
  exportSessionMarkdown: "export_session_markdown",
  exportSessionRawJson: "export_session_raw_json",
  aiReportStatus: "get_ai_report_status",
  generateAiReport: "generate_ai_report",
  cancelAiReport: "cancel_ai_report",
  sessionFolder: "get_session_folder",
  openSessionFolder: "open_session_folder",
  sessionScreenshotPreview: "get_session_screenshot_preview",
  sessionScreenshots: "get_session_screenshots",
  deleteSessionScreenshots: "delete_session_screenshots",
  sessions: "get_sessions",
  deleteSession: "delete_session",
  privacyPolicy: "get_privacy_policy",
  updatePrivacyPolicy: "update_privacy_policy",
} as const;

const UNHEALTHY_FALLBACK: SidecarHealth = {
  status: "unhealthy",
  appVersion: null,
  schemaVersion: null,
  message: "Could not reach the local sidecar command.",
};

const RECORDER_CONTROL_FALLBACK: RecorderControlResult = {
  status: "unavailable",
  message: "Recorder desktop command failed before reaching the local agent.",
  session: null,
};

const SESSION_EXPORT_FALLBACK: SessionExportResult = {
  status: "unavailable",
  message: "Session export bridge is unavailable.",
  export: null,
};

const AI_REPORT_FALLBACK: AiReportResult = {
  status: "runtime_unavailable",
  message: "Local AI report bridge is unavailable.",
  canGenerate: false,
  report: null,
  evidenceIds: [],
  modelName: null,
  modelVersion: null,
  provider: null,
  requestedModel: null,
  actualModel: null,
  fallbackUsed: false,
  runtimeMs: null,
  inputHash: null,
  generatedAt: null,
};

const SESSION_FOLDER_FALLBACK: SessionFolderResult = {
  status: "unavailable",
  message: "Session folder bridge is unavailable.",
  path: null,
};

const SESSION_SCREENSHOTS_FALLBACK: SessionScreenshotsResult = {
  status: "unavailable",
  message: "Screenshot metadata bridge is unavailable.",
  screenshots: [],
};

const SESSION_SCREENSHOT_PREVIEW_FALLBACK: SessionScreenshotPreviewResult = {
  status: "unavailable",
  message: "Screenshot preview bridge is unavailable.",
  preview: null,
};

const SCREENSHOT_DELETION_FALLBACK: ScreenshotDeletionResult = {
  status: "unavailable",
  message: "Screenshot delete bridge is unavailable.",
  deletedFiles: 0,
  missingFiles: 0,
  deletedRows: 0,
};

const SESSION_LIST_FALLBACK: SessionListResult = {
  status: "unavailable",
  message: "Session list bridge is unavailable.",
  sessions: [],
};

const SESSION_DELETION_FALLBACK: SessionDeletionResult = {
  status: "unavailable",
  message: "Session delete bridge is unavailable.",
  deletedSessionRows: 0,
  deletedScreenshotFiles: 0,
  missingScreenshotFiles: 0,
  deletedScreenshotRows: 0,
  removedArtifactRoot: false,
};

const PRIVACY_POLICY_FALLBACK: PrivacyPolicyConfigResult = {
  status: "unavailable",
  message: "Privacy policy bridge is unavailable.",
  policy: null,
};

export async function getSidecarHealth(): Promise<SidecarHealth> {
  return invokeSidecarCommand(SIDE_CAR_COMMANDS.health);
}

export async function startSidecar(): Promise<SidecarHealth> {
  return invokeSidecarCommand(SIDE_CAR_COMMANDS.start);
}

export async function stopSidecar(): Promise<SidecarHealth> {
  return invokeSidecarCommand(SIDE_CAR_COMMANDS.stop);
}

export async function getSessionEvents(sessionId = "latest"): Promise<SessionEventsResult> {
  try {
    return await invoke<SessionEventsResult>(SIDE_CAR_COMMANDS.sessionEvents, { sessionId });
  } catch {
    return { status: "unavailable", events: [] };
  }
}

export async function startRecordingSession(
  input: StartRecordingSessionInput,
): Promise<RecorderControlResult> {
  try {
    return await invoke<RecorderControlResult>(SIDE_CAR_COMMANDS.startRecordingSession, input);
  } catch {
    return RECORDER_CONTROL_FALLBACK;
  }
}

export async function pauseRecordingSession(
  input: PauseRecordingSessionInput,
): Promise<RecorderControlResult> {
  try {
    return await invoke<RecorderControlResult>(SIDE_CAR_COMMANDS.pauseRecordingSession, input);
  } catch {
    return RECORDER_CONTROL_FALLBACK;
  }
}

export async function resumeRecordingSession(
  input: ResumeRecordingSessionInput,
): Promise<RecorderControlResult> {
  try {
    return await invoke<RecorderControlResult>(SIDE_CAR_COMMANDS.resumeRecordingSession, input);
  } catch {
    return RECORDER_CONTROL_FALLBACK;
  }
}

export async function stopRecordingSession(
  input: StopRecordingSessionInput,
): Promise<RecorderControlResult> {
  try {
    return await invoke<RecorderControlResult>(SIDE_CAR_COMMANDS.stopRecordingSession, input);
  } catch {
    return RECORDER_CONTROL_FALLBACK;
  }
}

export async function exportSessionMarkdown(sessionId: string): Promise<SessionExportResult> {
  try {
    return await invoke<SessionExportResult>(SIDE_CAR_COMMANDS.exportSessionMarkdown, {
      sessionId,
    });
  } catch {
    return SESSION_EXPORT_FALLBACK;
  }
}

export async function exportSessionRawJson(sessionId: string): Promise<SessionExportResult> {
  try {
    return await invoke<SessionExportResult>(SIDE_CAR_COMMANDS.exportSessionRawJson, {
      sessionId,
    });
  } catch {
    return SESSION_EXPORT_FALLBACK;
  }
}

export async function getAiReportStatus(sessionId: string): Promise<AiReportResult> {
  try {
    return await invoke<AiReportResult>(SIDE_CAR_COMMANDS.aiReportStatus, { sessionId });
  } catch {
    return AI_REPORT_FALLBACK;
  }
}

export async function generateAiReport(sessionId: string): Promise<AiReportResult> {
  try {
    return await invoke<AiReportResult>(SIDE_CAR_COMMANDS.generateAiReport, { sessionId });
  } catch {
    return AI_REPORT_FALLBACK;
  }
}

export async function cancelAiReport(sessionId: string): Promise<AiReportResult> {
  try {
    return await invoke<AiReportResult>(SIDE_CAR_COMMANDS.cancelAiReport, { sessionId });
  } catch {
    return {
      ...AI_REPORT_FALLBACK,
      status: "cancelled",
      message: "Local AI report generation cancelled.",
      canGenerate: true,
    };
  }
}

export async function getSessionFolder(sessionId: string): Promise<SessionFolderResult> {
  try {
    return await invoke<SessionFolderResult>(SIDE_CAR_COMMANDS.sessionFolder, { sessionId });
  } catch {
    return SESSION_FOLDER_FALLBACK;
  }
}

export async function openSessionFolder(sessionId: string): Promise<SessionFolderResult> {
  try {
    return await invoke<SessionFolderResult>(SIDE_CAR_COMMANDS.openSessionFolder, { sessionId });
  } catch {
    return SESSION_FOLDER_FALLBACK;
  }
}

export async function getSessionScreenshots(
  sessionId: string,
): Promise<SessionScreenshotsResult> {
  try {
    return await invoke<SessionScreenshotsResult>(SIDE_CAR_COMMANDS.sessionScreenshots, {
      sessionId,
    });
  } catch {
    return SESSION_SCREENSHOTS_FALLBACK;
  }
}

export async function getSessionScreenshotPreview(
  sessionId: string,
  screenshotId: string,
): Promise<SessionScreenshotPreviewResult> {
  try {
    return await invoke<SessionScreenshotPreviewResult>(
      SIDE_CAR_COMMANDS.sessionScreenshotPreview,
      { sessionId, screenshotId },
    );
  } catch {
    return SESSION_SCREENSHOT_PREVIEW_FALLBACK;
  }
}

export async function deleteSessionScreenshots(
  sessionId: string,
): Promise<ScreenshotDeletionResult> {
  try {
    return await invoke<ScreenshotDeletionResult>(SIDE_CAR_COMMANDS.deleteSessionScreenshots, {
      sessionId,
    });
  } catch {
    return SCREENSHOT_DELETION_FALLBACK;
  }
}

export async function getSessions(): Promise<SessionListResult> {
  try {
    return await invoke<SessionListResult>(SIDE_CAR_COMMANDS.sessions);
  } catch {
    return SESSION_LIST_FALLBACK;
  }
}

export async function deleteSession(sessionId: string): Promise<SessionDeletionResult> {
  try {
    return await invoke<SessionDeletionResult>(SIDE_CAR_COMMANDS.deleteSession, { sessionId });
  } catch {
    return SESSION_DELETION_FALLBACK;
  }
}

export async function getPrivacyPolicy(): Promise<PrivacyPolicyConfigResult> {
  try {
    return await invoke<PrivacyPolicyConfigResult>(SIDE_CAR_COMMANDS.privacyPolicy);
  } catch {
    return PRIVACY_POLICY_FALLBACK;
  }
}

export async function updatePrivacyPolicy(
  policy: PrivacyPolicyConfig,
): Promise<PrivacyPolicyConfigResult> {
  try {
    return await invoke<PrivacyPolicyConfigResult>(SIDE_CAR_COMMANDS.updatePrivacyPolicy, {
      allowlist: policy.allowlist,
      blocklist: policy.blocklist,
      clipboardSafeMode: policy.clipboardSafeMode,
    });
  } catch {
    return PRIVACY_POLICY_FALLBACK;
  }
}

async function invokeSidecarCommand(command: string): Promise<SidecarHealth> {
  try {
    return await invoke<SidecarHealth>(command);
  } catch {
    return UNHEALTHY_FALLBACK;
  }
}
