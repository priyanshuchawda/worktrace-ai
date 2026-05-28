import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import App from "./App";
import { RecoveryBanner } from "./features/recovery/RecoveryBanner";
import {
  cancelAiReport,
  deleteSession,
  deleteSessionScreenshots,
  exportSessionMarkdown,
  exportSessionRawJson,
  generateAiReport,
  getAiReportStatus,
  getSessionEvents,
  getSessionScreenshotPreview,
  getSessionScreenshots,
  getSessions,
  getPrivacyPolicy,
  getSidecarHealth,
  openSessionFolder,
  pauseRecordingSession,
  resumeRecordingSession,
  startRecordingSession,
  startSidecar,
  stopRecordingSession,
  stopSidecar,
  updatePrivacyPolicy,
  type AiReportResult,
  type PrivacyPolicyConfigResult,
  type RecorderControlResult,
  type ScreenshotDeletionResult,
  type SessionDeletionResult,
  type SessionExportResult,
  type SessionEventsResult,
  type SessionFolderResult,
  type SessionListResult,
  type SessionScreenshotsResult,
  type SidecarHealth,
} from "./lib/tauri-client";

vi.mock("./lib/tauri-client", () => ({
  cancelAiReport: vi.fn(),
  deleteSession: vi.fn(),
  deleteSessionScreenshots: vi.fn(),
  exportSessionMarkdown: vi.fn(),
  exportSessionRawJson: vi.fn(),
  generateAiReport: vi.fn(),
  getAiReportStatus: vi.fn(),
  getSessionEvents: vi.fn(),
  getSessionScreenshotPreview: vi.fn(),
  getSessionScreenshots: vi.fn(),
  getSessions: vi.fn(),
  getPrivacyPolicy: vi.fn(),
  getSidecarHealth: vi.fn(),
  openSessionFolder: vi.fn(),
  pauseRecordingSession: vi.fn(),
  resumeRecordingSession: vi.fn(),
  startRecordingSession: vi.fn(),
  startSidecar: vi.fn(),
  stopRecordingSession: vi.fn(),
  stopSidecar: vi.fn(),
  updatePrivacyPolicy: vi.fn(),
}));

const missingSidecar: SidecarHealth = {
  status: "missing",
  appVersion: null,
  schemaVersion: null,
  message: "Local agent sidecar binary is not configured yet.",
};

const unhealthySidecar: SidecarHealth = {
  status: "unhealthy",
  appVersion: null,
  schemaVersion: null,
  message: "Could not reach the local sidecar command.",
};

const healthySidecar: SidecarHealth = {
  status: "healthy",
  appVersion: "0.0.0",
  schemaVersion: "001_initial.sql",
  message: "Local agent sidecar is healthy.",
};

const persistedPrivacyPolicy: PrivacyPolicyConfigResult = {
  status: "available",
  message: "Privacy policy loaded.",
  policy: {
    allowlist: ["Code.exe", "Windows Terminal"],
    blocklist: ["chrome.exe", "msedge.exe"],
    clipboardSafeMode: true,
  },
};

const getSidecarHealthMock = vi.mocked(getSidecarHealth);
const getAiReportStatusMock = vi.mocked(getAiReportStatus);
const generateAiReportMock = vi.mocked(generateAiReport);
const cancelAiReportMock = vi.mocked(cancelAiReport);
const getSessionEventsMock = vi.mocked(getSessionEvents);
const getSessionScreenshotPreviewMock = vi.mocked(getSessionScreenshotPreview);
const getSessionScreenshotsMock = vi.mocked(getSessionScreenshots);
const deleteSessionScreenshotsMock = vi.mocked(deleteSessionScreenshots);
const getSessionsMock = vi.mocked(getSessions);
const getPrivacyPolicyMock = vi.mocked(getPrivacyPolicy);
const updatePrivacyPolicyMock = vi.mocked(updatePrivacyPolicy);
const deleteSessionMock = vi.mocked(deleteSession);
const exportSessionMarkdownMock = vi.mocked(exportSessionMarkdown);
const exportSessionRawJsonMock = vi.mocked(exportSessionRawJson);
const openSessionFolderMock = vi.mocked(openSessionFolder);
const startRecordingSessionMock = vi.mocked(startRecordingSession);
const pauseRecordingSessionMock = vi.mocked(pauseRecordingSession);
const resumeRecordingSessionMock = vi.mocked(resumeRecordingSession);
const stopRecordingSessionMock = vi.mocked(stopRecordingSession);
const startSidecarMock = vi.mocked(startSidecar);
const stopSidecarMock = vi.mocked(stopSidecar);

const recordingControl: RecorderControlResult = {
  status: "available",
  message: "Recording session started.",
  session: {
    id: "sess_desktop_001",
    startedAt: "2026-05-06T09:14:00+05:30",
    endedAt: null,
    status: "recording",
    title: "Desktop recording",
    goal: null,
    projectLabel: null,
    tags: [],
    storagePath: null,
    privacyMode: "standard",
  },
};

const pausedControl: RecorderControlResult = {
  ...recordingControl,
  message: "Recording session paused.",
  session: {
    ...recordingControl.session!,
    status: "paused",
  },
};

const stoppedControl: RecorderControlResult = {
  ...recordingControl,
  message: "Recording session stopped.",
  session: {
    ...recordingControl.session!,
    endedAt: "2026-05-06T09:17:00+05:30",
    status: "stopped",
  },
};

const markdownExport: SessionExportResult = {
  status: "available",
  message: "Markdown export generated.",
  export: {
    format: "markdown",
    path: "C:/WorkTrace/sessions/sess_live_001/exports/session.md",
    preview:
      "# WorkTrace Session Export\n\nDeterministic export generated from local session evidence. No LLM was used.\n\nEvidence: evt_live_001",
    evidenceIds: ["evt_live_001"],
  },
};

const rawJsonExport: SessionExportResult = {
  status: "available",
  message: "Raw JSON export generated.",
  export: {
    format: "raw_json",
    path: "C:/WorkTrace/sessions/sess_live_001/exports/session.raw.json",
    preview: '{\n  "events": [\n    { "id": "evt_live_001" }\n  ]\n}',
    evidenceIds: ["evt_live_001"],
  },
};

const folderResult: SessionFolderResult = {
  status: "available",
  message: "Session folder is available.",
  path: "C:/WorkTrace/sessions/sess_live_001",
};

const readyAiReportStatus: AiReportResult = {
  status: "ready",
  message: "Local AI report runtime is ready.",
  canGenerate: true,
  report: null,
  evidenceIds: [],
  modelName: "fake-local-report-model",
  modelVersion: "fake-v1",
  runtimeMs: null,
  inputHash: null,
  generatedAt: null,
};

const completeAiReport: AiReportResult = {
  status: "complete",
  message: "Local AI report generated.",
  canGenerate: true,
  report: {
    sessionId: "sess_live_001",
    sessionTitle: "AI report UI fixture",
    summary: {
      text: "Tests ran successfully.",
      evidenceEventIds: ["evt_ai_ui_001"],
    },
    observedWork: [
      {
        title: "Tested desktop report generation",
        text: "The session included a local test run for the report workflow.",
        evidenceEventIds: ["evt_ai_ui_001"],
      },
    ],
    timeline: [],
    blockers: [],
    contextSwitches: [
      {
        title: "Editor to terminal",
        text: "The report moved from review to a terminal test run.",
        evidenceEventIds: ["evt_ai_ui_001"],
      },
    ],
    unfinishedWork: [
      {
        title: "Review report UX",
        text: "More report preview review is suggested from the observed test activity.",
        evidenceEventIds: ["evt_ai_ui_001"],
      },
    ],
    repeatedActions: [],
    importantFiles: [],
    commands: [
      {
        command: "pnpm test",
        evidenceEventIds: ["evt_ai_ui_001"],
      },
    ],
    workflowSteps: [],
    continuationNotes: [
      {
        title: "Suggested next step",
        text: "Suggestion: inspect the cited evidence before sharing the report.",
        evidenceEventIds: ["evt_ai_ui_001"],
      },
    ],
    confidence: 0.8,
    knownEvidenceEventIds: ["evt_ai_ui_001"],
  },
  evidenceIds: ["evt_ai_ui_001"],
  modelName: "fake-local-report-model",
  modelVersion: "fake-v1",
  runtimeMs: 42,
  inputHash: "sha256:fake-input-hash",
  generatedAt: "2026-05-06T09:15:10+05:30",
};

const completeDevelopmentCloudAiReport: AiReportResult = {
  ...completeAiReport,
  message: "Gemini/Gemma development AI report generated.",
  provider: "gemini_gemma_dev",
  requestedModel: "gemma-4-31b-it",
  actualModel: "gemma-4-26b-a4b-it",
  fallbackUsed: true,
  modelName: "gemma-4-31b-it",
};

const screenshotMetadata: SessionScreenshotsResult = {
  status: "available",
  message: "Screenshot metadata loaded.",
  screenshots: [
    {
      id: "shot_001",
      sessionId: "sess_live_001",
      sourceEventId: "evt_screen_001",
      timestamp: "2026-05-06T09:14:10+05:30",
      width: 1920,
      height: 1080,
      storedWidth: 960,
      storedHeight: 540,
      byteSize: 12345,
      contentHash: "content_hash_001",
      visualHash: "visual_hash_001",
      storagePath: "screenshots/shot_001.png",
    },
  ],
};

const screenshotDeletion: ScreenshotDeletionResult = {
  status: "available",
  message: "Screenshots deleted.",
  deletedFiles: 1,
  missingFiles: 0,
  deletedRows: 1,
};

const screenshotPreview = {
  status: "available" as const,
  message: "Screenshot preview loaded locally.",
  preview: {
    screenshotId: "shot_001",
    imageDataUrl:
      "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAFgwJ/lz3S9QAAAABJRU5ErkJggg==",
    ocrSnippets: ["pytest failure near worktrace_agent/api/routes/sessions.py"],
  },
};

const onboardingStorageKey = "worktrace.firstRunOnboarding.v1";

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem(
    onboardingStorageKey,
    JSON.stringify({ accepted: true, selectedPreset: "coding" }),
  );
  getAiReportStatusMock.mockReset();
  getAiReportStatusMock.mockResolvedValue({
    status: "runtime_unavailable",
    message: "Local AI report runtime is unavailable. Recording, timeline, and export continue.",
    canGenerate: false,
    report: null,
    evidenceIds: [],
    modelName: null,
    modelVersion: null,
    runtimeMs: null,
    inputHash: null,
    generatedAt: null,
  });
  generateAiReportMock.mockReset();
  generateAiReportMock.mockResolvedValue({
    status: "runtime_unavailable",
    message: "Local AI report runtime is unavailable. Recording, timeline, and export continue.",
    canGenerate: false,
    report: null,
    evidenceIds: [],
    modelName: null,
    modelVersion: null,
    runtimeMs: null,
    inputHash: null,
    generatedAt: null,
  });
  cancelAiReportMock.mockReset();
  cancelAiReportMock.mockResolvedValue({
    status: "cancelled",
    message: "Local AI report generation cancelled.",
    canGenerate: true,
    report: null,
    evidenceIds: [],
    modelName: null,
    modelVersion: null,
    runtimeMs: null,
    inputHash: null,
    generatedAt: null,
  });
  getSessionEventsMock.mockReset();
  getSessionEventsMock.mockResolvedValue({ status: "unavailable", events: [] });
  getSessionScreenshotPreviewMock.mockReset();
  getSessionScreenshotPreviewMock.mockResolvedValue({
    status: "unavailable",
    message: "Screenshot preview bridge is unavailable.",
    preview: null,
  });
  getSessionScreenshotsMock.mockReset();
  getSessionScreenshotsMock.mockResolvedValue({
    status: "unavailable",
    message: "Screenshot metadata bridge is unavailable.",
    screenshots: [],
  });
  deleteSessionScreenshotsMock.mockReset();
  deleteSessionScreenshotsMock.mockResolvedValue({
    status: "unavailable",
    message: "Screenshot delete bridge is unavailable.",
    deletedFiles: 0,
    missingFiles: 0,
    deletedRows: 0,
  });
  getSessionsMock.mockReset();
  getSessionsMock.mockResolvedValue({
    status: "unavailable",
    message: "Session list bridge is unavailable.",
    sessions: [],
  });
  getPrivacyPolicyMock.mockReset();
  getPrivacyPolicyMock.mockResolvedValue(persistedPrivacyPolicy);
  updatePrivacyPolicyMock.mockReset();
  updatePrivacyPolicyMock.mockResolvedValue({
    status: "available",
    message: "Privacy policy saved.",
    policy: persistedPrivacyPolicy.policy,
  });
  deleteSessionMock.mockReset();
  deleteSessionMock.mockResolvedValue({
    status: "unavailable",
    message: "Session delete bridge is unavailable.",
    deletedSessionRows: 0,
    deletedScreenshotFiles: 0,
    missingScreenshotFiles: 0,
    deletedScreenshotRows: 0,
    removedArtifactRoot: false,
  });
  exportSessionMarkdownMock.mockReset();
  exportSessionMarkdownMock.mockResolvedValue({
    status: "unavailable",
    message: "Session export bridge is unavailable.",
    export: null,
  });
  exportSessionRawJsonMock.mockReset();
  exportSessionRawJsonMock.mockResolvedValue({
    status: "unavailable",
    message: "Session export bridge is unavailable.",
    export: null,
  });
  openSessionFolderMock.mockReset();
  openSessionFolderMock.mockResolvedValue({
    status: "unavailable",
    message: "Session folder bridge is unavailable.",
    path: null,
  });
  getSidecarHealthMock.mockReset();
  startRecordingSessionMock.mockReset();
  startRecordingSessionMock.mockResolvedValue({
    status: "unavailable",
    message: "Recorder sidecar bridge is unavailable.",
    session: null,
  });
  pauseRecordingSessionMock.mockReset();
  pauseRecordingSessionMock.mockResolvedValue({
    status: "unavailable",
    message: "Recorder sidecar bridge is unavailable.",
    session: null,
  });
  resumeRecordingSessionMock.mockReset();
  resumeRecordingSessionMock.mockResolvedValue({
    status: "unavailable",
    message: "Recorder sidecar bridge is unavailable.",
    session: null,
  });
  stopRecordingSessionMock.mockReset();
  stopRecordingSessionMock.mockResolvedValue({
    status: "unavailable",
    message: "Recorder sidecar bridge is unavailable.",
    session: null,
  });
  startSidecarMock.mockReset();
  stopSidecarMock.mockReset();
});

function openWorkspace(name: "Home" | "History" | "Settings") {
  fireEvent.click(screen.getByRole("button", { name }));
}

async function openHomeProof() {
  openWorkspace("Home");
  const viewProofButton =
    screen.queryByRole("button", { name: "View Proof" }) ??
    (await screen.findByRole("button", { name: "View Moments" }));
  fireEvent.click(viewProofButton);
}

async function openHomeTechnicalDetails() {
  await openHomeProof();
  const review = await screen.findByRole("region", { name: "Session moments" });
  fireEvent.click(within(review).getByRole("button", { name: "Technical details" }));
}

test("renders the WorkTrace desktop shell status panels", () => {
  getSidecarHealthMock.mockResolvedValue(missingSidecar);

  render(<App />);

  expect(screen.getByRole("heading", { name: "WorkTrace AI" })).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: "Workspace" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Home" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "History" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Settings" })).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Start, finish and understand your work" }),
  ).toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "First-run privacy setup" })).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Start a focused session" })).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Privacy" })).not.toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "AI summary" })).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Proof access" })).not.toBeInTheDocument();
});

test("keeps Home focused on one-click recording before proof is requested", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);

  render(<App />);

  const recorderPanel = await screen.findByRole("article", { name: "Session controls" });
  expect(
    within(recorderPanel).getByRole("heading", { name: "Start a focused session" }),
  ).toBeInTheDocument();
  expect(within(recorderPanel).getByRole("button", { name: "Start Session" })).toBeEnabled();
  expect(within(recorderPanel).getByLabelText("Goal")).not.toBeVisible();
  expect(within(recorderPanel).getByLabelText("Session title")).not.toBeVisible();
  expect(within(recorderPanel).getByLabelText("Project")).not.toBeVisible();
  expect(within(recorderPanel).getByLabelText("Tags")).not.toBeVisible();
  expect(within(recorderPanel).getByLabelText("File watch roots")).not.toBeVisible();

  fireEvent.click(within(recorderPanel).getByText("Advanced options"));

  expect(within(recorderPanel).getByLabelText("Goal")).toBeInTheDocument();
  expect(within(recorderPanel).getByLabelText("Session title")).toBeInTheDocument();
  expect(within(recorderPanel).getByLabelText("Project")).toBeInTheDocument();
  expect(within(recorderPanel).getByLabelText("Tags")).toBeInTheDocument();
  expect(within(recorderPanel).getByLabelText("File watch roots")).toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Session summary and sharing" })).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Screenshot evidence" })).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Activity workspace" })).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Proof access" })).not.toBeInTheDocument();
});

test("shows a recap-first result after finish and keeps proof behind an explicit action", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  startRecordingSessionMock.mockResolvedValue(recordingControl);
  stopRecordingSessionMock.mockResolvedValue(stoppedControl);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_finish_001",
        timestamp: "2026-05-06T09:16:00+05:30",
        app: "VS Code",
        windowTitle: "workaudit-ai - App.tsx",
        source: "active_window",
        type: "active_window_changed",
      },
    ],
  });
  getSessionScreenshotsMock.mockResolvedValue(screenshotMetadata);

  render(<App />);

  const recorderPanel = await screen.findByRole("article", { name: "Session controls" });
  fireEvent.click(within(recorderPanel).getByRole("button", { name: "Start Session" }));
  expect(await within(recorderPanel).findByText("Recording session started.")).toBeInTheDocument();
  fireEvent.click(within(recorderPanel).getByRole("button", { name: "Finish Session" }));

  expect(await screen.findByRole("heading", { name: "Your session recap" })).toBeInTheDocument();
  const recap = screen.getByRole("region", { name: "Session recap" });
  const recorder = screen.getByRole("article", { name: "Session controls" });
  expect(
    Boolean(recap.compareDocumentPosition(recorder) & Node.DOCUMENT_POSITION_FOLLOWING),
  ).toBe(true);
  expect(screen.queryByRole("region", { name: "First-run privacy setup" })).not.toBeInTheDocument();
  expect(within(recap).queryByRole("button", { name: "Create Summary" })).not.toBeInTheDocument();
  expect(within(recap).queryByRole("button", { name: "Share Update" })).not.toBeInTheDocument();
  expect(within(recap).getByText("Smart recap is not set up")).toBeInTheDocument();
  expect(within(recap).getByRole("button", { name: "View Moments" })).toBeInTheDocument();
  expect(within(recap).getByRole("button", { name: "Review Activity" })).toBeInTheDocument();
  expect(within(recap).getByRole("button", { name: "Start New Session" })).toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Session summary and sharing" })).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Screenshot evidence" })).not.toBeInTheDocument();

  fireEvent.click(within(recap).getByRole("button", { name: "View Moments" }));

  const review = await screen.findByRole("region", { name: "Session moments" });
  expect(within(review).getByRole("heading", { name: "Captured moments" })).toBeInTheDocument();
  expect(within(review).getByText("1 visual moment captured locally.")).toBeInTheDocument();
  expect(within(review).getByRole("heading", { name: "Activity" })).toBeInTheDocument();
  expect(within(review).getByText("Used VS Code")).toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Session summary and sharing" })).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Screenshot evidence" })).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Activity workspace" })).not.toBeInTheDocument();
});

test("auto-creates the AI recap after finishing when summary generation is ready", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getAiReportStatusMock.mockResolvedValue(readyAiReportStatus);
  generateAiReportMock.mockResolvedValue(completeAiReport);
  startRecordingSessionMock.mockResolvedValue(recordingControl);
  stopRecordingSessionMock.mockResolvedValue(stoppedControl);

  render(<App />);

  const recorderPanel = await screen.findByRole("article", { name: "Session controls" });
  fireEvent.click(within(recorderPanel).getByRole("button", { name: "Start Session" }));
  expect(await within(recorderPanel).findByText("Recording session started.")).toBeInTheDocument();
  fireEvent.click(within(recorderPanel).getByRole("button", { name: "Finish Session" }));

  await waitFor(() => {
    expect(generateAiReportMock).toHaveBeenCalledWith("sess_desktop_001");
  });
  expect(await screen.findByText("Local AI report generated.")).toBeInTheDocument();
});

test("requires first-run privacy setup before recording", async () => {
  localStorage.removeItem(onboardingStorageKey);
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  startRecordingSessionMock.mockResolvedValue(recordingControl);

  render(<App />);

  const onboarding = screen.getByRole("region", { name: "First-run privacy setup" });
  expect(within(onboarding).getByText("Required before recording")).toBeInTheDocument();
  expect(within(onboarding).getByText(/active-window metadata/i)).toBeInTheDocument();
  expect(within(onboarding).getByText(/screenshot sampling/i)).toBeInTheDocument();
  expect(within(onboarding).getByText(/terminal ingestion only/)).toBeInTheDocument();
  expect(within(onboarding).getByText(/no cloud upload by default/i)).toBeInTheDocument();
  expect(within(onboarding).getByRole("button", { name: "Accept safe defaults" })).toBeEnabled();
  expect(within(onboarding).getByText("Private / Safe")).not.toBeVisible();

  const recorderPanel = screen.getByRole("article", { name: "Session controls" });
  const startButton = within(recorderPanel).getByRole("button", { name: "Start Session" });
  expect(startButton).toBeDisabled();
  expect(startRecordingSessionMock).not.toHaveBeenCalled();

  fireEvent.click(within(onboarding).getByRole("button", { name: "Accept safe defaults" }));

  expect(localStorage.getItem(onboardingStorageKey)).toContain("coding");
  expect(screen.queryByRole("region", { name: "First-run privacy setup" })).not.toBeInTheDocument();
  expect(startButton).not.toBeDisabled();

  fireEvent.click(startButton);
  expect(startRecordingSessionMock).toHaveBeenCalledWith(
    expect.objectContaining({
      fileWatchRoots: [],
      privacyMode: "standard",
    }),
  );
  expect(await screen.findByText("Recording session started.")).toBeInTheDocument();
});

test("keeps first-run privacy presets secondary but still usable", async () => {
  localStorage.removeItem(onboardingStorageKey);
  getSidecarHealthMock.mockResolvedValue(healthySidecar);

  render(<App />);

  const onboarding = screen.getByRole("region", { name: "First-run privacy setup" });
  fireEvent.click(within(onboarding).getByText("Review capture presets"));
  fireEvent.click(within(onboarding).getByRole("button", { name: /Private \/ Safe/ }));
  fireEvent.click(within(onboarding).getByRole("button", { name: "Accept selected preset" }));

  expect(localStorage.getItem(onboardingStorageKey)).toContain("private_safe");
  expect(screen.queryByRole("region", { name: "First-run privacy setup" })).not.toBeInTheDocument();

  const recorderPanel = await screen.findByRole("article", { name: "Session controls" });
  fireEvent.click(within(recorderPanel).getByRole("button", { name: "Start Session" }));
  expect(startRecordingSessionMock).toHaveBeenCalledWith(
    expect.objectContaining({
      privacyMode: "private",
    }),
  );
});

test("restores accepted first-run setup from local storage", async () => {
  localStorage.setItem(
    onboardingStorageKey,
    JSON.stringify({ accepted: true, selectedPreset: "study" }),
  );
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  startRecordingSessionMock.mockResolvedValue(recordingControl);

  render(<App />);

  expect(screen.queryByRole("region", { name: "First-run privacy setup" })).not.toBeInTheDocument();
  const recorderPanel = await screen.findByRole("article", { name: "Session controls" });
  expect(
    within(recorderPanel).getByRole("button", { name: "Start Session" }),
  ).not.toBeDisabled();
});

test("starts recordings with session goal project and tags", async () => {
  localStorage.setItem(
    onboardingStorageKey,
    JSON.stringify({ accepted: true, selectedPreset: "coding" }),
  );
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  startRecordingSessionMock.mockResolvedValue(recordingControl);

  render(<App />);

  const recorderPanel = await screen.findByRole("article", { name: "Session controls" });
  fireEvent.click(within(recorderPanel).getByText("Advanced options"));
  fireEvent.change(within(recorderPanel).getByLabelText("Session title"), {
    target: { value: "Auth API test session" },
  });
  fireEvent.change(within(recorderPanel).getByLabelText("Project"), {
    target: { value: "workaudit-ai" },
  });
  fireEvent.change(within(recorderPanel).getByLabelText("Goal"), {
    target: { value: "Finish authentication API tests" },
  });
  fireEvent.change(within(recorderPanel).getByLabelText("Tags"), {
    target: { value: "coding, tests, coding" },
  });

  fireEvent.click(within(recorderPanel).getByRole("button", { name: "Start Session" }));

  expect(startRecordingSessionMock).toHaveBeenCalledWith(
    expect.objectContaining({
      title: "Auth API test session",
      projectLabel: "workaudit-ai",
      goal: "Finish authentication API tests",
      tags: ["coding", "tests"],
    }),
  );
});

test("configures Privacy center and starts new recordings in private mode", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  startRecordingSessionMock.mockResolvedValue({
    status: "available",
    message: "Recording session started.",
    session: {
      id: "sess_private_001",
      startedAt: "2026-05-06T09:14:00+05:30",
      endedAt: null,
      status: "recording",
      title: "Desktop recording",
      goal: null,
      projectLabel: null,
      tags: [],
      storagePath: null,
      privacyMode: "private",
    },
  });

  render(<App />);

  openWorkspace("Settings");
  const privacyCenter = await screen.findByRole("region", { name: "Privacy center" });
  expect(within(privacyCenter).getByRole("checkbox", { name: /Private mode/ })).not.toBeChecked();
  expect(within(privacyCenter).queryByRole("textbox", { name: "Allowed apps" })).not.toBeInTheDocument();

  fireEvent.click(within(privacyCenter).getByText("Custom app lists"));
  expect(within(privacyCenter).getByRole("textbox", { name: "Allowed apps" })).toHaveValue(
    "Code.exe\nWindows Terminal",
  );
  expect(within(privacyCenter).getByRole("textbox", { name: "Blocked apps" })).toHaveValue(
    "chrome.exe\nmsedge.exe",
  );

  fireEvent.click(within(privacyCenter).getByRole("checkbox", { name: /Private mode/ }));
  fireEvent.change(within(privacyCenter).getByLabelText("Allowed apps"), {
    target: { value: "Code.exe\nWindows Terminal\nPowerShell.exe" },
  });
  fireEvent.change(within(privacyCenter).getByLabelText("Blocked apps"), {
    target: { value: "chrome.exe\nmsedge.exe\nslack.exe" },
  });

  expect(within(privacyCenter).getByText("Private")).toBeInTheDocument();
  expect(within(privacyCenter).getAllByText("3").length).toBeGreaterThanOrEqual(2);

  openWorkspace("Home");
  const recorderPanel = screen.getByRole("article", { name: "Session controls" });
  fireEvent.click(within(recorderPanel).getByRole("button", { name: "Start Session" }));

  expect(startRecordingSessionMock).toHaveBeenCalledWith(
    expect.objectContaining({
      fileWatchRoots: [],
      title: "Desktop recording",
      privacyMode: "private",
    }),
  );
  expect(await screen.findByText("Recording session started.")).toBeInTheDocument();
  expect(screen.getByText("private")).toBeInTheDocument();
});

test("loads and saves privacy policy through the sidecar bridge", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getPrivacyPolicyMock.mockResolvedValue({
    status: "available",
    message: "Privacy policy loaded.",
    policy: {
      allowlist: ["PowerShell.exe"],
      blocklist: ["Teams.exe"],
      clipboardSafeMode: true,
    },
  });
  updatePrivacyPolicyMock.mockResolvedValue({
    status: "available",
    message: "Privacy policy saved.",
    policy: {
      allowlist: ["PowerShell.exe", "Code.exe"],
      blocklist: ["Teams.exe"],
      clipboardSafeMode: false,
    },
  });

  render(<App />);

  openWorkspace("Settings");
  const privacyCenter = await screen.findByRole("region", { name: "Privacy center" });
  expect(within(privacyCenter).queryByLabelText("Allowed apps")).not.toBeInTheDocument();
  fireEvent.click(within(privacyCenter).getByText("Custom app lists"));
  expect(within(privacyCenter).getByLabelText("Allowed apps")).toHaveValue("PowerShell.exe");
  expect(within(privacyCenter).getByLabelText("Blocked apps")).toHaveValue("Teams.exe");

  fireEvent.change(within(privacyCenter).getByLabelText("Allowed apps"), {
    target: { value: "PowerShell.exe\nCode.exe" },
  });
  fireEvent.click(within(privacyCenter).getByRole("checkbox", { name: /Clipboard safe mode/ }));
  fireEvent.click(within(privacyCenter).getByRole("button", { name: "Save policy" }));

  expect(updatePrivacyPolicyMock).toHaveBeenCalledWith({
    allowlist: ["PowerShell.exe", "Code.exe"],
    blocklist: ["Teams.exe"],
    clipboardSafeMode: false,
  });
  expect(await within(privacyCenter).findByText("Privacy policy saved.")).toBeInTheDocument();
  expect(within(privacyCenter).getByLabelText("Allowed apps")).toHaveValue(
    "PowerShell.exe\nCode.exe",
  );
});

test("previews a privacy-safe diagnostics bundle without raw evidence or secrets", async () => {
  getSidecarHealthMock.mockResolvedValue({
    ...unhealthySidecar,
    message: "Startup failed near C:\\Users\\Admin\\.env with GEMINI_API_KEY=abc123.",
  });
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_sensitive_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "WindowsTerminal",
        windowTitle: "set GEMINI_API_KEY=abc123",
        source: "terminal_command_detector",
        type: "terminal_command",
      },
    ],
  });

  render(<App />);

  openWorkspace("Settings");
  expect(screen.queryByRole("region", { name: "Privacy-safe diagnostics" })).not.toBeInTheDocument();
  fireEvent.click(await screen.findByText("Advanced diagnostics"));
  const diagnostics = await screen.findByRole("region", {
    name: "Privacy-safe diagnostics",
  });
  fireEvent.click(within(diagnostics).getByRole("button", { name: "Preview diagnostics" }));

  expect(
    await within(diagnostics).findByText(
      "Diagnostics bundle preview generated locally. Review before sharing.",
    ),
  ).toBeInTheDocument();
  const preview = within(diagnostics).getByText((content, element) => {
    return (
      element?.tagName === "PRE" &&
      content.includes('"bundleType": "worktrace-safe-diagnostics"')
    );
  });
  expect(preview).toHaveTextContent('"rawEvidenceIncluded": false');
  expect(preview).toHaveTextContent('"screenshots"');
  expect(preview).toHaveTextContent("[redacted local path]");
  expect(preview).toHaveTextContent("GEMINI_API_KEY=[redacted]");
  expect(preview).not.toHaveTextContent("abc123");
  expect(preview).not.toHaveTextContent("set GEMINI_API_KEY");
  expect(preview).not.toHaveTextContent("C:\\Users\\Admin");
});

test("passes configured file watch roots when starting and resuming recordings", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  startRecordingSessionMock.mockResolvedValue(recordingControl);
  pauseRecordingSessionMock.mockResolvedValue(pausedControl);
  resumeRecordingSessionMock.mockResolvedValue(recordingControl);
  getSessionEventsMock.mockResolvedValue({ status: "available", events: [] });

  render(<App />);

  const recorderPanel = await screen.findByRole("article", { name: "Session controls" });
  fireEvent.change(within(recorderPanel).getByLabelText("File watch roots"), {
    target: {
      value: " C:\\repo \n\nC:\\repo\nD:\\client-work ",
    },
  });

  expect(
    within(recorderPanel).getByText(
      "2 metadata-only roots configured. Ignored folders and sensitive file names stay redacted.",
    ),
  ).toBeInTheDocument();

  fireEvent.click(within(recorderPanel).getByRole("button", { name: "Start Session" }));
  expect(await within(recorderPanel).findByText("Recording")).toBeInTheDocument();
  expect(startRecordingSessionMock).toHaveBeenCalledWith(
    expect.objectContaining({
      fileWatchRoots: ["C:\\repo", "D:\\client-work"],
      privacyMode: "standard",
    }),
  );

  fireEvent.click(within(recorderPanel).getByRole("button", { name: "Pause" }));
  expect(await within(recorderPanel).findByText("Paused")).toBeInTheDocument();

  fireEvent.click(within(recorderPanel).getByRole("button", { name: "Resume" }));
  expect(resumeRecordingSessionMock).toHaveBeenCalledWith({
    fileWatchRoots: ["C:\\repo", "D:\\client-work"],
    resumedAt: expect.any(String),
    sessionId: "sess_desktop_001",
  });
});

test("shows sidecar loading and missing states", async () => {
  getSidecarHealthMock.mockResolvedValue(missingSidecar);

  render(<App />);

  openWorkspace("Settings");
  fireEvent.click(await screen.findByText("Advanced diagnostics"));
  const agent = await screen.findByRole("article", { name: "Local agent status" });
  expect(await within(agent).findByText("Missing sidecar")).toBeInTheDocument();
  expect(within(agent).getByText("Local agent sidecar binary is not configured yet.")).toBeInTheDocument();
});

test("shows safe unhealthy state when the Tauri client cannot reach Rust", async () => {
  getSidecarHealthMock.mockResolvedValue(unhealthySidecar);

  render(<App />);

  openWorkspace("Settings");
  fireEvent.click(await screen.findByText("Advanced diagnostics"));
  const agent = await screen.findByRole("article", { name: "Local agent status" });
  expect(await within(agent).findByText("Sidecar unhealthy")).toBeInTheDocument();
  expect(within(agent).getByText("Could not reach the local sidecar command.")).toBeInTheDocument();
});

test("shows healthy sidecar version details", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);

  render(<App />);

  openWorkspace("Settings");
  fireEvent.click(await screen.findByText("Advanced diagnostics"));
  const agent = await screen.findByRole("article", { name: "Local agent status" });
  expect(await within(agent).findByText("Sidecar healthy")).toBeInTheDocument();
  expect(within(agent).getByText("Local agent sidecar is healthy.")).toBeInTheDocument();
  expect(within(agent).getByText("App 0.0.0 / schema 001_initial.sql")).toBeInTheDocument();
});

test("shows ordered raw active window timeline changes", async () => {
  getSidecarHealthMock.mockResolvedValue(missingSidecar);

  render(<App />);

  await openHomeTechnicalDetails();
  const timeline = screen.getByRole("region", { name: "Raw timeline" });
  const items = within(timeline).getAllByRole("listitem");

  expect(items).toHaveLength(5);
  expect(items.map((item) => item.textContent)).toEqual([
    expect.stringContaining("09:14VS Codeactive_windowworkaudit-ai - App.tsx"),
    expect.stringContaining("09:16Chromeactive_windowIssue #9 - GitHub"),
    expect.stringContaining("09:19Windows Terminalactive_windowuv run --python 3.13 pytest"),
    expect.stringContaining("09:22VS Codeactive_windowraw_events_repository.py"),
    expect.stringContaining("09:24File Exploreractive_windowworktrace session folder"),
  ]);
});

test("shows real sidecar active-window events when available", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  const sidecarEvents: SessionEventsResult = {
    status: "available",
    events: [
      {
        id: "evt_live_002",
        timestamp: "2026-05-06T09:16:00+05:30",
        app: "Chrome",
        windowTitle: "Issue #51",
        source: "active_window",
        type: "active_window_changed",
      },
      {
        id: "evt_live_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "VS Code",
        windowTitle: "workaudit-ai - App.tsx",
        source: "active_window",
        type: "active_window_changed",
      },
    ],
  };
  getSessionEventsMock.mockResolvedValue(sidecarEvents);

  render(<App />);

  await openHomeTechnicalDetails();
  const timeline = await screen.findByRole("region", { name: "Raw timeline" });
  const items = within(timeline).getAllByRole("listitem");

  expect(within(timeline).getByText("Live sidecar events")).toBeInTheDocument();
  expect(items).toHaveLength(2);
  expect(items.map((item) => item.textContent)).toEqual([
    expect.stringContaining("09:14VS Codeactive_windowworkaudit-ai - App.tsx"),
    expect.stringContaining("09:16Chromeactive_windowIssue #51"),
  ]);
});

test("shows real sidecar file watcher events when available", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  const sidecarEvents: SessionEventsResult = {
    status: "available",
    events: [
      {
        id: "evt_file_001",
        timestamp: "2026-05-06T09:15:00+05:30",
        app: "File change",
        windowTitle: "modified C:/repo/src/app.py",
        source: "file_watcher",
        type: "file_changed",
      },
      {
        id: "evt_live_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "VS Code",
        windowTitle: "workaudit-ai - App.tsx",
        source: "active_window",
        type: "active_window_changed",
      },
    ],
  };
  getSessionEventsMock.mockResolvedValue(sidecarEvents);

  render(<App />);

  await openHomeTechnicalDetails();
  const timeline = await screen.findByRole("region", { name: "Raw timeline" });
  const items = within(timeline).getAllByRole("listitem");

  expect(items).toHaveLength(2);
  expect(items.map((item) => item.textContent)).toEqual([
    expect.stringContaining("09:14VS Codeactive_windowworkaudit-ai - App.tsx"),
    expect.stringContaining("09:15File changefile_watchermodified C:/repo/src/app.py"),
  ]);
});

test("shows real sidecar terminal command events when available", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  const sidecarEvents: SessionEventsResult = {
    status: "available",
    events: [
      {
        id: "evt_terminal_001",
        timestamp: "2026-05-06T09:16:00+05:30",
        app: "Terminal command",
        windowTitle: "powershell exit 1: pnpm test --token [REDACTED]",
        source: "terminal_command_detector",
        type: "terminal_command",
      },
    ],
  };
  getSessionEventsMock.mockResolvedValue(sidecarEvents);

  render(<App />);

  await openHomeTechnicalDetails();
  const timeline = await screen.findByRole("region", { name: "Raw timeline" });
  const items = within(timeline).getAllByRole("listitem");

  expect(items).toHaveLength(1);
  expect(items[0].textContent).toContain(
    "09:16Terminal commandterminal_command_detectorpowershell exit 1: pnpm test --token [REDACTED]",
  );
});

test("renders session dashboard surfaces with honest unavailable actions", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);

  render(<App />);

  await openHomeTechnicalDetails();
  expect(await screen.findByRole("region", { name: "Activity workspace" })).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Screenshot evidence" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Delete screenshots" })).toBeDisabled();
  expect(screen.getByText("Connect to a live sidecar session before reviewing screenshots.")).toBeInTheDocument();

  openWorkspace("Home");
  expect(screen.getByRole("region", { name: "Session summary and sharing" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Export Detailed Notes" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Export raw JSON" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Open session folder" })).toBeDisabled();
  expect(screen.getByText("AI summary unavailable")).toBeInTheDocument();

  openWorkspace("Settings");
  expect(screen.getByRole("region", { name: "Privacy center" })).toBeInTheDocument();
});

test("loads screenshot metadata and shows a safe preview for a live sidecar session", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_live_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "VS Code",
        windowTitle: "workaudit-ai - App.tsx",
        source: "active_window",
        type: "active_window_changed",
      },
    ],
  });
  getSessionScreenshotsMock.mockResolvedValue(screenshotMetadata);
  getSessionScreenshotPreviewMock.mockResolvedValue(screenshotPreview);

  render(<App />);

  await openHomeTechnicalDetails();
  const screenshotPanel = await screen.findByRole("region", { name: "Screenshot evidence" });

  expect(await within(screenshotPanel).findByText("Screenshot metadata loaded.")).toBeInTheDocument();
  expect(getSessionScreenshotsMock).toHaveBeenCalledWith("latest");
  expect(within(screenshotPanel).getAllByText("shot_001").length).toBeGreaterThan(0);
  expect(within(screenshotPanel).getAllByText("evt_screen_001").length).toBeGreaterThan(0);
  expect(within(screenshotPanel).getByText("1920 x 1080 original")).toBeInTheDocument();
  expect(within(screenshotPanel).getByText("960 x 540 stored")).toBeInTheDocument();
  expect(within(screenshotPanel).getByText("screenshots/shot_001.png")).toBeInTheDocument();
  await waitFor(() => {
    expect(getSessionScreenshotPreviewMock).toHaveBeenCalledWith("latest", "shot_001");
  });
  expect(
    await within(screenshotPanel).findByAltText("Screenshot evidence shot_001"),
  ).toBeInTheDocument();
  expect(
    within(screenshotPanel).getByText("pytest failure near worktrace_agent/api/routes/sessions.py"),
  ).toBeInTheDocument();
});

test("deletes screenshots through the desktop bridge and shows deletion counts", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_live_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "VS Code",
        windowTitle: "workaudit-ai - App.tsx",
        source: "active_window",
        type: "active_window_changed",
      },
    ],
  });
  getSessionScreenshotsMock.mockResolvedValue(screenshotMetadata);
  deleteSessionScreenshotsMock.mockResolvedValue(screenshotDeletion);

  render(<App />);

  await openHomeTechnicalDetails();
  const screenshotPanel = await screen.findByRole("region", { name: "Screenshot evidence" });
  expect((await within(screenshotPanel).findAllByText("shot_001")).length).toBeGreaterThan(0);

  fireEvent.click(within(screenshotPanel).getByRole("button", { name: "Delete screenshots" }));

  expect(deleteSessionScreenshotsMock).toHaveBeenCalledWith("latest");
  expect(await within(screenshotPanel).findByText("Screenshots deleted.")).toBeInTheDocument();
  expect(within(screenshotPanel).getByText("1 row deleted")).toBeInTheDocument();
  expect(within(screenshotPanel).getByText("1 file deleted")).toBeInTheDocument();
  expect(within(screenshotPanel).getByText("No screenshot metadata for this session.")).toBeInTheDocument();
});

test("shows safe screenshot unavailable state for a live sidecar session", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_live_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "VS Code",
        windowTitle: "workaudit-ai - App.tsx",
        source: "active_window",
        type: "active_window_changed",
      },
    ],
  });
  getSessionScreenshotsMock.mockResolvedValue({
    status: "unavailable",
    message: "Screenshot metadata bridge is unavailable.",
    screenshots: [],
  });

  render(<App />);

  await openHomeTechnicalDetails();
  const screenshotPanel = await screen.findByRole("region", { name: "Screenshot evidence" });

  expect(await within(screenshotPanel).findByText("Screenshot metadata bridge is unavailable.")).toBeInTheDocument();
  expect(within(screenshotPanel).getByRole("button", { name: "Delete screenshots" })).toBeDisabled();
});

test("exports markdown and raw JSON previews for a live sidecar session", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_live_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "VS Code",
        windowTitle: "workaudit-ai - App.tsx",
        source: "active_window",
        type: "active_window_changed",
      },
    ],
  });
  exportSessionMarkdownMock.mockResolvedValue(markdownExport);
  exportSessionRawJsonMock.mockResolvedValue(rawJsonExport);
  openSessionFolderMock.mockResolvedValue({
    ...folderResult,
    message: "Session folder opened in File Explorer.",
  });

  render(<App />);

  await openHomeTechnicalDetails();
  const exportPanel = await screen.findByRole("region", { name: "Session summary and sharing" });
  fireEvent.click(within(exportPanel).getByRole("button", { name: "Export Detailed Notes" }));

  expect(exportSessionMarkdownMock).toHaveBeenCalledWith("latest");
  expect(await within(exportPanel).findByText("Markdown export generated.")).toBeInTheDocument();
  expect(within(exportPanel).getByText("evt_live_001")).toBeInTheDocument();
  expect(
    within(exportPanel).getByText(/Deterministic export generated from local session evidence/),
  ).toBeInTheDocument();

  fireEvent.click(within(exportPanel).getByRole("button", { name: "Export raw JSON" }));
  expect(exportSessionRawJsonMock).toHaveBeenCalledWith("latest");
  expect(await within(exportPanel).findByText("Raw JSON export generated.")).toBeInTheDocument();
  expect(within(exportPanel).getByText(/"events"/)).toBeInTheDocument();

  fireEvent.click(within(exportPanel).getByRole("button", { name: "Open session folder" }));
  expect(openSessionFolderMock).toHaveBeenCalledWith("latest");
  expect(
    await within(exportPanel).findByText("Session folder opened in File Explorer."),
  ).toBeInTheDocument();
  expect(within(exportPanel).getByText("C:/WorkTrace/sessions/sess_live_001")).toBeInTheDocument();
  expect(within(exportPanel).getByText("AI summary unavailable")).toBeInTheDocument();
});

test("shows safe export error state when the sidecar export bridge is unavailable", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_live_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "VS Code",
        windowTitle: "workaudit-ai - App.tsx",
        source: "active_window",
        type: "active_window_changed",
      },
    ],
  });
  exportSessionMarkdownMock.mockResolvedValue({
    status: "unavailable",
    message: "Session export bridge is unavailable.",
    export: null,
  });

  render(<App />);

  await openHomeTechnicalDetails();
  const exportPanel = await screen.findByRole("region", { name: "Session summary and sharing" });
  fireEvent.click(within(exportPanel).getByRole("button", { name: "Export Detailed Notes" }));

  expect(await within(exportPanel).findByText("Session export bridge is unavailable.")).toBeInTheDocument();
  expect(within(exportPanel).getByText("No export preview available yet.")).toBeInTheDocument();
});

test("shows model unavailable state and disables local AI report generation", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_live_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "VS Code",
        windowTitle: "workaudit-ai - App.tsx",
        source: "active_window",
        type: "active_window_changed",
      },
    ],
  });

  render(<App />);

  await openHomeProof();
  const review = await screen.findByRole("region", { name: "Session moments" });
  expect(within(review).getByText("Smart summary unavailable")).toBeInTheDocument();
  expect(
    within(review).getByText(
      "Set up local AI summaries in Settings to generate a private recap. Your screenshots and activity remain available locally.",
    ),
  ).toBeInTheDocument();
  await waitFor(() => expect(getAiReportStatusMock).toHaveBeenCalledWith("latest"));
  expect(screen.queryByRole("button", { name: "Create Summary" })).not.toBeInTheDocument();
  expect(screen.queryByText("GEMINI_API_KEY")).not.toBeInTheDocument();
  expect(screen.queryByText("gemini_gemma_dev")).not.toBeInTheDocument();
  expect(screen.queryByText("gemma-4-31b-it")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Create Development Summary" })).not.toBeInTheDocument();
});

test("keeps evidence IDs, paths, hashes and exports behind technical details", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_live_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "VS Code",
        windowTitle: "workaudit-ai - App.tsx",
        source: "active_window",
        type: "active_window_changed",
      },
    ],
  });
  getSessionScreenshotsMock.mockResolvedValue(screenshotMetadata);
  getSessionScreenshotPreviewMock.mockResolvedValue(screenshotPreview);

  render(<App />);

  await openHomeProof();
  const review = await screen.findByRole("region", { name: "Session moments" });
  expect(await within(review).findByText("Captured at 09:14")).toBeInTheDocument();
  expect(screen.queryByText("evt_live_001")).not.toBeInTheDocument();
  expect(screen.queryByText("shot_001")).not.toBeInTheDocument();
  expect(screen.queryByText("screenshots/shot_001.png")).not.toBeInTheDocument();
  expect(screen.queryByText("content_hash_001")).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Session summary and sharing" })).not.toBeInTheDocument();

  fireEvent.click(within(review).getByRole("button", { name: "Technical details" }));

  expect(await screen.findByRole("region", { name: "Session summary and sharing" })).toBeInTheDocument();
  expect(await screen.findByRole("region", { name: "Screenshot evidence" })).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Activity workspace" })).toBeInTheDocument();
  expect(screen.getByText("evt_live_001")).toBeInTheDocument();
  expect(screen.getByText("screenshots/shot_001.png")).toBeInTheDocument();
  expect(screen.getByText("content_hash_001")).toBeInTheDocument();
});

test("shows model settings with localhost endpoint and unavailable reason", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_live_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "VS Code",
        windowTitle: "workaudit-ai - App.tsx",
        source: "active_window",
        type: "active_window_changed",
      },
    ],
  });

  render(<App />);

  openWorkspace("Settings");
  const aiSummarySettings = await screen.findByRole("region", { name: "AI summary settings" });
  expect(within(aiSummarySettings).getByText("AI setup required")).toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Model settings" })).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Local model endpoint")).not.toBeInTheDocument();

  fireEvent.click(within(aiSummarySettings).getByText("Advanced AI setup"));
  const settingsPanel = await screen.findByRole("region", { name: "Model settings" });

  expect(within(settingsPanel).getByDisplayValue("http://127.0.0.1:11434")).toBeInTheDocument();
  expect(within(settingsPanel).getByText("Gemma E2B")).toBeInTheDocument();
  expect(within(settingsPanel).getByText("Default report model")).toBeInTheDocument();
  expect(within(settingsPanel).getByText("Gemma E4B")).toBeInTheDocument();
  expect(within(settingsPanel).getByText("Manual deep mode only")).toBeInTheDocument();
  expect(within(settingsPanel).getByText("Beta local AI setup")).toBeInTheDocument();
  expect(within(settingsPanel).getByText(/Install and start a user-managed Ollama-compatible runtime/)).toBeInTheDocument();
  expect(within(settingsPanel).getByText("gemma4:e2b")).toBeInTheDocument();
  expect(within(settingsPanel).getByText(/WorkTrace will not download it automatically/)).toBeInTheDocument();
  expect(within(settingsPanel).getByText("gemma4:e4b")).toBeInTheDocument();
  expect(
    within(settingsPanel).getByText(
      "Create Summary is unavailable because local AI is not ready.",
    ),
  ).toBeInTheDocument();
  expect(within(settingsPanel).queryByText(/full prompt/i)).not.toBeInTheDocument();
  expect(within(settingsPanel).queryByRole("button", { name: /download/i })).not.toBeInTheDocument();
});

test("model settings reject remote endpoints before report generation", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_live_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "VS Code",
        windowTitle: "workaudit-ai - App.tsx",
        source: "active_window",
        type: "active_window_changed",
      },
    ],
  });
  getAiReportStatusMock.mockResolvedValue(readyAiReportStatus);

  render(<App />);

  openWorkspace("Settings");
  const aiSummarySettings = await screen.findByRole("region", { name: "AI summary settings" });
  fireEvent.click(within(aiSummarySettings).getByText("Advanced AI setup"));
  const settingsPanel = await screen.findByRole("region", { name: "Model settings" });
  fireEvent.change(within(settingsPanel).getByLabelText("Local model endpoint"), {
    target: { value: "http://192.168.1.10:11434" },
  });

  expect(within(settingsPanel).getByText("Remote model endpoints are blocked.")).toBeInTheDocument();
  expect(
    within(settingsPanel).getByText(
      "Create Summary is unavailable because the endpoint is not localhost.",
    ),
  ).toBeInTheDocument();

  await openHomeTechnicalDetails();
  const exportPanel = screen.getByRole("region", { name: "Session summary and sharing" });
  expect(within(exportPanel).getByRole("button", { name: "Create Summary" })).toBeDisabled();
});

test("generates a local AI report with evidence IDs and model metadata", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_ai_ui_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "Terminal command",
        windowTitle: "powershell: pnpm test",
        source: "terminal_command_detector",
        type: "terminal_command",
      },
    ],
  });
  getAiReportStatusMock.mockResolvedValue(readyAiReportStatus);
  generateAiReportMock.mockResolvedValue(completeAiReport);

  render(<App />);

  await openHomeTechnicalDetails();
  const exportPanel = await screen.findByRole("region", { name: "Session summary and sharing" });
  await within(exportPanel).findByText("Local AI report runtime is ready.");
  fireEvent.click(await within(exportPanel).findByRole("button", { name: "Create Summary" }));

  expect(generateAiReportMock).toHaveBeenCalledWith("latest");
  expect(await within(exportPanel).findByText("Local AI report generated.")).toBeInTheDocument();
  expect(within(exportPanel).getByText("Tests ran successfully.")).toBeInTheDocument();
  expect(within(exportPanel).getByRole("heading", { name: "What I worked on" })).toBeInTheDocument();
  expect(within(exportPanel).getByText("Tested desktop report generation")).toBeInTheDocument();
  expect(within(exportPanel).getByRole("heading", { name: "Context switches" })).toBeInTheDocument();
  expect(within(exportPanel).getByText("Editor to terminal")).toBeInTheDocument();
  expect(within(exportPanel).getByRole("heading", { name: "Unfinished work" })).toBeInTheDocument();
  expect(within(exportPanel).getByText("Review report UX")).toBeInTheDocument();
  expect(within(exportPanel).getByRole("heading", { name: "Suggested continuation" })).toBeInTheDocument();
  expect(within(exportPanel).getByText("Suggested next step")).toBeInTheDocument();
  expect(within(exportPanel).getAllByText("evt_ai_ui_001").length).toBeGreaterThan(0);
  expect(within(exportPanel).getByText("fake-local-report-model")).toBeInTheDocument();
  expect(within(exportPanel).getByText("42 ms")).toBeInTheDocument();
  expect(within(exportPanel).getByText("sha256:fake-input-hash")).toBeInTheDocument();
  expect(within(exportPanel).getByRole("button", { name: "Regenerate Summary" })).toBeInTheDocument();
  expect(within(exportPanel).queryByText(/full prompt/i)).not.toBeInTheDocument();
});

test("creates a reviewed share-safe Markdown report without raw private evidence", async () => {
  const sensitiveReport: AiReportResult = {
    ...completeAiReport,
    report: {
      ...completeAiReport.report!,
      sessionTitle: "Client work at C:\\Users\\Admin\\secret\\plan.md",
      summary: {
        text: "Reviewed token=abc123 and C:\\Users\\Admin\\repo\\.env during testing.",
        evidenceEventIds: ["evt_ai_ui_001"],
      },
      commands: [
        {
          command: "set GEMINI_API_KEY=abc123 && pnpm test",
          evidenceEventIds: ["evt_ai_ui_001"],
        },
      ],
    },
  };
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_ai_ui_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "Terminal command",
        windowTitle: "powershell: pnpm test",
        source: "terminal_command_detector",
        type: "terminal_command",
      },
    ],
  });
  getAiReportStatusMock.mockResolvedValue(readyAiReportStatus);
  generateAiReportMock.mockResolvedValue(sensitiveReport);

  render(<App />);

  await openHomeTechnicalDetails();
  const exportPanel = await screen.findByRole("region", { name: "Session summary and sharing" });
  await within(exportPanel).findByText("Local AI report runtime is ready.");
  const generateButton = within(exportPanel).getByRole("button", {
    name: "Create Summary",
  });
  await waitFor(() => expect(generateButton).toBeEnabled());
  fireEvent.click(generateButton);
  expect(await within(exportPanel).findByText("Local AI report generated.")).toBeInTheDocument();
  fireEvent.click(
    within(exportPanel).getByRole("button", { name: "Preview Shareable Summary" }),
  );

  expect(
    await within(exportPanel).findByText(
      "Share-safe Markdown preview generated locally. Review it before sharing.",
    ),
  ).toBeInTheDocument();
  const shareSafePreview = within(exportPanel).getByText((content, element) => {
    return (
      element?.tagName === "PRE" &&
      content.includes("# WorkTrace AI Share-Safe Report")
    );
  });
  expect(shareSafePreview).toHaveTextContent("Screenshot images: omitted");
  expect(shareSafePreview).toHaveTextContent("[redacted local path]");
  expect(shareSafePreview).toHaveTextContent("GEMINI_API_KEY=[redacted]");
  expect(shareSafePreview).not.toHaveTextContent("abc123");
  expect(shareSafePreview).not.toHaveTextContent("C:\\Users\\Admin");
});

test("labels Development cloud reports with provider provenance and privacy disclosure", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_ai_ui_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "Terminal command",
        windowTitle: "powershell: pnpm test",
        source: "terminal_command_detector",
        type: "terminal_command",
      },
    ],
  });
  getAiReportStatusMock.mockResolvedValue({
    ...readyAiReportStatus,
    provider: "gemini_gemma_dev",
    requestedModel: "gemma-4-31b-it",
    modelName: "gemma-4-31b-it",
    message: "Gemini/Gemma development AI provider is ready.",
  });
  generateAiReportMock.mockResolvedValue(completeDevelopmentCloudAiReport);

  render(<App />);

  await openHomeProof();
  const review = await screen.findByRole("region", { name: "Session moments" });
  expect(screen.queryByText("Gemini/Gemma development AI provider is ready.")).not.toBeInTheDocument();
  expect(screen.queryByText("gemini_gemma_dev")).not.toBeInTheDocument();
  expect(screen.queryByText("gemma-4-31b-it")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Create Development Summary" })).not.toBeInTheDocument();

  fireEvent.click(within(review).getByRole("button", { name: "Technical details" }));
  const exportPanel = await screen.findByRole("region", { name: "Session summary and sharing" });
  await within(exportPanel).findByText("Gemini/Gemma development AI provider is ready.");
  expect(
    within(exportPanel).getByText(
      "Development cloud mode sends redacted text evidence to Google infrastructure. Screenshots and raw artifacts stay local by default.",
    ),
  ).toBeInTheDocument();

  fireEvent.click(
    await within(exportPanel).findByRole("button", {
      name: "Create Development Summary",
    }),
  );

  expect(generateAiReportMock).toHaveBeenCalledWith("latest");
  expect(
    await within(exportPanel).findByText("Gemini/Gemma development AI report generated."),
  ).toBeInTheDocument();
  expect(within(exportPanel).getAllByText("Gemini/Gemma development cloud").length).toBeGreaterThan(0);
  expect(within(exportPanel).getAllByText("gemma-4-31b-it").length).toBeGreaterThan(0);
  expect(within(exportPanel).getByText("gemma-4-26b-a4b-it")).toBeInTheDocument();
  expect(within(exportPanel).getByText("Fallback used")).toBeInTheDocument();
  expect(within(exportPanel).queryByText(/api key/i)).not.toBeInTheDocument();
  expect(within(exportPanel).queryByText(/full prompt/i)).not.toBeInTheDocument();
});

test("global status labels development cloud report mode without claiming no cloud upload", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_ai_ui_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "Terminal command",
        windowTitle: "powershell: pnpm test",
        source: "terminal_command_detector",
        type: "terminal_command",
      },
    ],
  });
  getAiReportStatusMock.mockResolvedValue({
    ...readyAiReportStatus,
    provider: "gemini_gemma_dev",
    requestedModel: "gemma-4-31b-it",
    modelName: "gemma-4-31b-it",
    message: "Gemini/Gemma development AI provider is ready.",
  });

  render(<App />);

  expect(await screen.findByText("Development AI enabled")).toBeInTheDocument();
  expect(
    screen.queryByText(
      "Development reports may send redacted text evidence to Google. Screenshots and raw artifacts stay local by default.",
    ),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByText("No cloud upload, keylogging, terminal spying, browser history, or file contents."),
  ).not.toBeInTheDocument();
});

test("settings keeps local report runtime separate from capture privacy", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_ai_ui_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "Terminal command",
        windowTitle: "powershell: pnpm test",
        source: "terminal_command_detector",
        type: "terminal_command",
      },
    ],
  });
  getAiReportStatusMock.mockResolvedValue({
    ...readyAiReportStatus,
    provider: "local_ollama",
    requestedModel: "gemma4:e2b",
    modelName: "gemma4:e2b",
  });

  render(<App />);

  expect(await screen.findByText("AI summary ready")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  const settings = await screen.findByRole("region", { name: "AI summary settings" });
  expect(within(settings).getByText("AI summary ready")).toBeInTheDocument();
  expect(
    within(settings).getByText(
      "The configured local report runtime is ready for a finished session.",
    ),
  ).toBeInTheDocument();
});

test("shows failed safely state when local AI report validation fails", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_ai_ui_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "Terminal command",
        windowTitle: "powershell: pnpm test",
        source: "terminal_command_detector",
        type: "terminal_command",
      },
    ],
  });
  getAiReportStatusMock.mockResolvedValue(readyAiReportStatus);
  generateAiReportMock.mockResolvedValue({
    status: "failed_safely",
    message: "Local report output could not be validated after one retry.",
    canGenerate: true,
    report: null,
    evidenceIds: [],
    modelName: "fake-local-report-model",
    modelVersion: "fake-v1",
    runtimeMs: null,
    inputHash: "sha256:fake-input-hash",
    generatedAt: null,
  });

  render(<App />);

  await openHomeTechnicalDetails();
  const exportPanel = await screen.findByRole("region", { name: "Session summary and sharing" });
  await within(exportPanel).findByText("Local AI report runtime is ready.");
  fireEvent.click(await within(exportPanel).findByRole("button", { name: "Create Summary" }));

  expect(
    await within(exportPanel).findByText("Local report output could not be validated after one retry."),
  ).toBeInTheDocument();
  expect(within(exportPanel).queryByText(/full prompt/i)).not.toBeInTheDocument();
});

test("cancels a running local AI report", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_ai_ui_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "Terminal command",
        windowTitle: "powershell: pnpm test",
        source: "terminal_command_detector",
        type: "terminal_command",
      },
    ],
  });
  getAiReportStatusMock.mockResolvedValue(readyAiReportStatus);
  generateAiReportMock.mockReturnValue(new Promise(() => undefined));

  render(<App />);

  await openHomeTechnicalDetails();
  const exportPanel = await screen.findByRole("region", { name: "Session summary and sharing" });
  await within(exportPanel).findByText("Local AI report runtime is ready.");
  fireEvent.click(await within(exportPanel).findByRole("button", { name: "Create Summary" }));
  fireEvent.click(await within(exportPanel).findByRole("button", { name: "Cancel Summary" }));

  expect(cancelAiReportMock).toHaveBeenCalledWith("latest");
  expect(await within(exportPanel).findByText("Local AI report generation cancelled.")).toBeInTheDocument();
});

test("does not generate a local AI report while recording is active", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  startRecordingSessionMock.mockResolvedValue(recordingControl);
  getAiReportStatusMock.mockResolvedValue(readyAiReportStatus);

  render(<App />);

  const recorderPanel = await screen.findByRole("article", { name: "Session controls" });
  fireEvent.click(within(recorderPanel).getByRole("button", { name: "Start Session" }));
  expect(await within(recorderPanel).findByText("Recording")).toBeInTheDocument();

  openWorkspace("Home");
  expect(screen.queryByRole("region", { name: "Session summary and sharing" })).not.toBeInTheDocument();
  expect(generateAiReportMock).not.toHaveBeenCalled();
});

test("starts pauses resumes and stops a recorder session from the desktop controls", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  startRecordingSessionMock.mockResolvedValue(recordingControl);
  pauseRecordingSessionMock.mockResolvedValue(pausedControl);
  resumeRecordingSessionMock.mockResolvedValue(recordingControl);
  stopRecordingSessionMock.mockResolvedValue(stoppedControl);
  getSessionEventsMock
    .mockResolvedValueOnce({ status: "available", events: [] })
    .mockResolvedValue({
      status: "available",
      events: [
        {
          id: "evt_live_001",
          timestamp: "2026-05-06T09:14:00+05:30",
          app: "VS Code",
          windowTitle: "workaudit-ai - App.tsx",
          source: "active_window",
          type: "active_window_changed",
        },
      ],
    });

  render(<App />);

  const recorderControls = screen.getByRole("article", { name: "Session controls" });
  expect(await within(recorderControls).findByText("Ready")).toBeInTheDocument();
  fireEvent.click(within(recorderControls).getByRole("button", { name: "Start Session" }));
  expect(await within(recorderControls).findByText("Recording")).toBeInTheDocument();
  expect(screen.queryByText("sess_desktop_001")).not.toBeInTheDocument();
  expect(screen.getByText("standard")).toBeInTheDocument();
  expect(screen.getByText("Recording session started.")).toBeInTheDocument();
  expect(startRecordingSessionMock).toHaveBeenCalledOnce();

  fireEvent.click(within(recorderControls).getByRole("button", { name: "Pause" }));
  expect(await within(recorderControls).findByText("Paused")).toBeInTheDocument();
  expect(screen.getByText("Recording session paused.")).toBeInTheDocument();
  expect(pauseRecordingSessionMock).toHaveBeenCalledWith({
    pausedAt: expect.any(String),
    sessionId: "sess_desktop_001",
  });

  fireEvent.click(within(recorderControls).getByRole("button", { name: "Resume" }));
  expect(await within(recorderControls).findByText("Recording")).toBeInTheDocument();
  expect(resumeRecordingSessionMock).toHaveBeenCalledWith({
    fileWatchRoots: [],
    resumedAt: expect.any(String),
    sessionId: "sess_desktop_001",
  });

  fireEvent.click(within(recorderControls).getByRole("button", { name: "Finish Session" }));
  const recap = await screen.findByRole("region", { name: "Session recap" });
  expect(within(recap).getByText("Your session recap")).toBeInTheDocument();
  expect(within(recap).getByText(/Captured 1 activity/)).toBeInTheDocument();
  expect(stopRecordingSessionMock).toHaveBeenCalledWith({
    stoppedAt: expect.any(String),
    sessionId: "sess_desktop_001",
  });
  const nextSessionControls = screen.getByRole("article", { name: "Session controls" });
  expect(within(nextSessionControls).getByRole("button", { name: "Start New Session" })).toBeInTheDocument();
});

test("recovers an active recorder session from the sidecar session list on load", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionsMock.mockResolvedValue(activeSessionListResult);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_recovered_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "VS Code",
        windowTitle: "workaudit-ai - App.tsx",
        source: "active_window",
        type: "active_window_changed",
      },
    ],
  });

  render(<App />);

  const recorderPanel = screen.getByRole("article", { name: "Session controls" });
  expect(await within(recorderPanel).findByText("Recording")).toBeInTheDocument();
  expect(screen.queryByText("sess_recovered_001")).not.toBeInTheDocument();
  expect(screen.queryByText("Session: none")).not.toBeInTheDocument();
  expect(screen.getByText("Active recording session recovered from the local agent.")).toBeInTheDocument();
});

test("recovers recorder state when start succeeds in the sidecar but command response is unavailable", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionsMock
    .mockResolvedValueOnce({
      status: "available",
      message: "Sessions loaded.",
      sessions: [],
    })
    .mockResolvedValue(activeSessionListResult);
  startRecordingSessionMock.mockResolvedValue({
    status: "unavailable",
    message: "Recorder response contract mismatch.",
    session: null,
  });
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [],
  });

  render(<App />);

  const recorderPanel = screen.getByRole("article", { name: "Session controls" });
  fireEvent.click(within(recorderPanel).getByRole("button", { name: "Start Session" }));

  expect(await within(recorderPanel).findByText("Recording")).toBeInTheDocument();
  expect(screen.queryByText("sess_recovered_001")).not.toBeInTheDocument();
  expect(
    screen.getByText("Active recording session recovered from the local agent."),
  ).toBeInTheDocument();
});

test("shows a safe Needs attention state when lifecycle bridge is missing", async () => {
  getSidecarHealthMock.mockResolvedValue(missingSidecar);
  startRecordingSessionMock.mockResolvedValue({
    status: "unavailable",
    message: "Recorder sidecar bridge is unavailable.",
    session: null,
  });

  render(<App />);

  const recorderPanel = screen.getByRole("article", { name: "Session controls" });
  fireEvent.click(within(recorderPanel).getByRole("button", { name: "Start Session" }));

  expect(await within(recorderPanel).findByText("Needs attention")).toBeInTheDocument();
  expect(screen.getByText("Recorder sidecar bridge is unavailable.")).toBeInTheDocument();
});

test("filters live raw timeline events by source", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_live_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "VS Code",
        windowTitle: "workaudit-ai - App.tsx",
        source: "active_window",
        type: "active_window_changed",
      },
      {
        id: "evt_file_001",
        timestamp: "2026-05-06T09:15:00+05:30",
        app: "File change",
        windowTitle: "modified C:/repo/src/app.py",
        source: "file_watcher",
        type: "file_changed",
      },
      {
        id: "evt_terminal_001",
        timestamp: "2026-05-06T09:16:00+05:30",
        app: "Terminal command",
        windowTitle: "powershell exit 1: pnpm test",
        source: "terminal_command_detector",
        type: "terminal_command",
      },
    ],
  });

  render(<App />);

  await openHomeTechnicalDetails();
  const timeline = await screen.findByRole("region", { name: "Raw timeline" });
  fireEvent.click(screen.getByRole("button", { name: "Terminal" }));

  const items = within(timeline).getAllByRole("listitem");
  expect(items).toHaveLength(1);
  expect(items[0].textContent).toContain("Terminal command");
  expect(within(timeline).queryByText("VS Code")).not.toBeInTheDocument();
  expect(within(timeline).queryByText("File change")).not.toBeInTheDocument();
});

test("filters live raw timeline events by local text search and date", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_code_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "VS Code",
        windowTitle: "workaudit-ai - App.tsx",
        source: "active_window",
        type: "active_window_changed",
      },
      {
        id: "evt_notes_001",
        timestamp: "2026-05-07T10:15:00+05:30",
        app: "Obsidian",
        windowTitle: "study notes",
        source: "active_window",
        type: "active_window_changed",
      },
    ],
  });

  render(<App />);

  await openHomeTechnicalDetails();
  const timeline = await screen.findByRole("region", { name: "Raw timeline" });
  fireEvent.change(screen.getByLabelText("Search local evidence"), {
    target: { value: "notes" },
  });

  expect(within(timeline).getAllByRole("listitem")).toHaveLength(1);
  expect(within(timeline).getByText("Obsidian")).toBeInTheDocument();
  expect(within(timeline).queryByText("VS Code")).not.toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("Event date"), {
    target: { value: "2026-05-06" },
  });

  expect(within(timeline).getByText("No raw events for this filter.")).toBeInTheDocument();
});

test("jumps from report evidence IDs to matching raw timeline events", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionEventsMock.mockResolvedValue({
    status: "available",
    events: [
      {
        id: "evt_ai_ui_001",
        timestamp: "2026-05-06T09:14:00+05:30",
        app: "Terminal command",
        windowTitle: "powershell: pnpm test",
        source: "terminal_command_detector",
        type: "terminal_command",
      },
      {
        id: "evt_other_001",
        timestamp: "2026-05-06T09:15:00+05:30",
        app: "VS Code",
        windowTitle: "App.tsx",
        source: "active_window",
        type: "active_window_changed",
      },
    ],
  });
  getAiReportStatusMock.mockResolvedValue(readyAiReportStatus);
  generateAiReportMock.mockResolvedValue(completeAiReport);

  render(<App />);

  await openHomeTechnicalDetails();
  const exportPanel = await screen.findByRole("region", { name: "Session summary and sharing" });
  await within(exportPanel).findByText("Local AI report runtime is ready.");
  fireEvent.click(await within(exportPanel).findByRole("button", { name: "Create Summary" }));
  expect(await within(exportPanel).findByText("Local AI report generated.")).toBeInTheDocument();
  fireEvent.click(
    (await within(exportPanel).findAllByRole("button", {
      name: "Show evidence evt_ai_ui_001",
    }))[0],
  );

  const timeline = await screen.findByRole("region", { name: "Raw timeline" });
  expect(screen.getByText("Selected evidence: evt_ai_ui_001")).toBeInTheDocument();
  expect(
    within(timeline).getByRole("listitem", { name: /Timeline event evt_ai_ui_001/ }),
  ).toHaveAttribute("aria-current", "true");
  expect(within(timeline).getByText("evt_ai_ui_001")).toBeInTheDocument();
});

test("shows empty raw timeline state when live sidecar has no events", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionEventsMock.mockResolvedValue({ status: "available", events: [] });

  render(<App />);

  await openHomeTechnicalDetails();
  const timeline = await screen.findByRole("region", { name: "Raw timeline" });

  expect(within(timeline).getByText("No raw events for this filter.")).toBeInTheDocument();
});

test("shows safe missing-sidecar timeline state before falling back to fixtures", async () => {
  getSidecarHealthMock.mockResolvedValue(missingSidecar);
  getSessionEventsMock.mockResolvedValue({ status: "unavailable", events: [] });

  render(<App />);

  await openHomeTechnicalDetails();
  const timeline = await screen.findByRole("region", { name: "Raw timeline" });

  expect(within(timeline).getByText("Fixture fallback")).toBeInTheDocument();
  expect(
    within(timeline).getByText(
      "The local sidecar event stream is unavailable, so this preview is using deterministic fixture events.",
    ),
  ).toBeInTheDocument();
});

test("does not show fake interrupted recovery on the default Home screen", async () => {
  getSidecarHealthMock.mockResolvedValue(missingSidecar);

  render(<App />);

  expect(screen.queryByRole("region", { name: "Interrupted session recovery" })).not.toBeInTheDocument();
  expect(screen.queryByText("Interrupted session found")).not.toBeInTheDocument();
});

test("shows interrupted session recovery actions for explicit recovery data", async () => {
  render(
    <RecoveryBanner
      sessions={[
        {
          id: "sess_banner_001",
          title: "Interrupted review",
          interruptedAt: "2026-05-06T09:24:00+05:30",
          eventCount: 1,
          availableActions: ["review", "export", "delete"],
        },
      ]}
    />,
  );

  const recovery = screen.getByRole("region", { name: "Interrupted session recovery" });

  expect(within(recovery).getByText("Interrupted session found")).toBeInTheDocument();
  expect(within(recovery).getByText("Interrupted review")).toBeInTheDocument();
  expect(within(recovery).getByText("1 event preserved")).toBeInTheDocument();
  expect(within(recovery).getByRole("button", { name: "Review" })).toBeInTheDocument();
  expect(within(recovery).getByRole("button", { name: "Export" })).toBeInTheDocument();
  expect(within(recovery).getByRole("button", { name: "Delete" })).toBeInTheDocument();
});

const sessionListResult: SessionListResult = {
  status: "available",
  message: "Sessions loaded.",
  sessions: [
    {
      id: "sess_browser_001",
      startedAt: "2026-05-06T09:14:00+05:30",
      endedAt: "2026-05-06T09:15:00+05:30",
      status: "Finished",
      title: "Test session",
      goal: "Review beta workflow",
      projectLabel: "workaudit-ai",
      tags: ["coding", "beta"],
      storagePath: null,
      privacyMode: "standard",
      eventCount: 2,
      screenshotCount: 1,
    },
    {
      id: "sess_browser_002",
      startedAt: "2026-05-05T10:00:00+05:30",
      endedAt: null,
      status: "interrupted",
      title: null,
      goal: null,
      projectLabel: null,
      tags: [],
      storagePath: null,
      privacyMode: "standard",
      eventCount: 0,
      screenshotCount: 0,
    },
  ],
};

const activeSessionListResult: SessionListResult = {
  status: "available",
  message: "Sessions loaded.",
  sessions: [
    {
      id: "sess_recovered_001",
      startedAt: "2026-05-06T09:14:00+05:30",
      endedAt: null,
      status: "recording",
      title: "Recovered active session",
      goal: "Continue recovered work",
      projectLabel: "workaudit-ai",
      tags: ["recovery"],
      storagePath: null,
      privacyMode: "standard",
      eventCount: 1,
      screenshotCount: 1,
    },
  ],
};

const sessionDeletion: SessionDeletionResult = {
  status: "available",
  message: "Session deleted.",
  deletedSessionRows: 1,
  deletedScreenshotFiles: 1,
  missingScreenshotFiles: 0,
  deletedScreenshotRows: 1,
  removedArtifactRoot: true,
};

test("session browser panel shows unavailable state when sidecar is missing", async () => {
  getSidecarHealthMock.mockResolvedValue(missingSidecar);

  render(<App />);

  openWorkspace("History");
  const panel = await screen.findByRole("region", { name: "Session history" });

  expect(within(panel).getByRole("button", { name: "Refresh sessions" })).toBeInTheDocument();
  expect(within(panel).getByText("Session list bridge is unavailable.")).toBeInTheDocument();
});

test("session browser loads session list from sidecar and shows session details", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionsMock.mockResolvedValue(sessionListResult);

  render(<App />);

  openWorkspace("History");
  const panel = await screen.findByRole("region", { name: "Session history" });

  expect(await within(panel).findByText("Test session")).toBeInTheDocument();
  expect(within(panel).queryByText("sess_browser_001")).not.toBeInTheDocument();
  expect(within(panel).getByRole("heading", { name: "Session history" })).toBeInTheDocument();
  expect(within(panel).queryByText("Session browser")).not.toBeInTheDocument();
  expect(within(panel).getByText("Test session")).toBeInTheDocument();
  expect(within(panel).getByText("2 activities")).toBeInTheDocument();
  expect(within(panel).getByText("1 visual moment")).toBeInTheDocument();
  expect(within(panel).getByText("Completed")).toBeInTheDocument();
  expect(within(panel).getByText("Untitled work session")).toBeInTheDocument();
  expect(within(panel).getByText("Interrupted")).toBeInTheDocument();
  const sessionCard = within(panel).getByText("Test session").closest("li");
  expect(sessionCard).not.toBeNull();
  expect(
    within(sessionCard as HTMLElement).getByRole("button", { name: "Delete session Test session" }),
  ).not.toBeVisible();
  expect(within(sessionCard as HTMLElement).getByText("Technical details")).not.toBeVisible();

  fireEvent.click(within(sessionCard as HTMLElement).getByText("Manage"));
  expect(within(sessionCard as HTMLElement).getByText("Technical details")).toBeVisible();
  expect(within(sessionCard as HTMLElement).getByText("Session ID: sess_browser_001")).toBeVisible();
  expect(
    within(sessionCard as HTMLElement).getByRole("button", { name: "Delete session Test session" }),
  ).toBeVisible();
});

test("session browser deletes a selected session through the bridge", async () => {
  getSidecarHealthMock.mockResolvedValue(healthySidecar);
  getSessionsMock.mockResolvedValue(sessionListResult);
  deleteSessionMock.mockResolvedValue(sessionDeletion);

  render(<App />);

  openWorkspace("History");
  const panel = await screen.findByRole("region", { name: "Session history" });
  expect(await within(panel).findByText("Test session")).toBeInTheDocument();

  fireEvent.click(within(panel).getAllByText("Manage")[0]);
  expect(
    within(panel).queryByRole("button", { name: "Delete session sess_browser_001" }),
  ).not.toBeInTheDocument();
  fireEvent.click(within(panel).getByRole("button", { name: "Delete session Test session" }));

  expect(deleteSessionMock).toHaveBeenCalledWith("sess_browser_001");
  expect(await within(panel).findByText("Session deleted.")).toBeInTheDocument();
  expect(within(panel).getByText("1 session row deleted")).toBeInTheDocument();
});
