import { useCallback, useEffect, useRef, useState } from "react";
import "./App.css";
import { RawTimeline } from "./features/timeline/RawTimeline";
import {
  rawTimelineSimulationEvents,
  type RawTimelineEvent,
} from "./features/timeline/raw-timeline-simulation";
import {
  DiagnosticsBundlePanel,
  ExportReviewPanel,
  FirstRunOnboardingPanel,
  Metric,
  ModelSettingsPanel,
  PrivacyCenterPanel,
  RecorderControlPanel,
  ScreenshotEvidencePanel,
  SessionBrowserPanel,
  type AiReportReviewState,
  type DiagnosticsBundleState,
  type EventFilter,
  type ExportReviewState,
  type FileWatchSettingsState,
  type FirstRunOnboardingState,
  type FolderReviewState,
  type OnboardingPreset,
  type PrivacyCenterState,
  type RecorderUiStatus,
  type ScreenshotDeletionState,
  type ScreenshotPreviewState,
  type ScreenshotReviewState,
  type SessionBrowserState,
  type SessionDeletionState,
  type SessionDraftState,
  type ShareSafeExportState,
} from "./components/dashboard-panels";
import {
  parseFileWatchRoots,
  validateLocalModelEndpoint,
} from "./components/dashboard-utils";
import { SessionReviewPanel } from "./components/session-review-panel";
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
  type AiReportClaim,
  type AiReportPayload,
  type RecorderControlResult,
  type RecorderSession,
  type RecorderSessionStatus,
  type SessionExportResult,
  type SessionEventsResult,
  type SessionFolderResult,
  type SessionListResult,
  type SessionSummary,
  type SessionScreenshotsResult,
  type SidecarHealth,
} from "./lib/tauri-client";

type WorkspaceView = "home" | "history" | "settings";

type WorkspaceNavItem = {
  id: WorkspaceView;
  label: string;
  description: string;
};

const initialSidecarHealth: SidecarHealth = {
  status: "loading",
  appVersion: null,
  schemaVersion: null,
  message: "Checking local agent sidecar status.",
};

const initialSessionEvents: SessionEventsResult = {
  status: "unavailable",
  events: [],
};

const initialRecorderMessage = "No active session. Start when ready.";

const eventFilters: { label: string; value: EventFilter }[] = [
  { label: "All", value: "all" },
  { label: "Active windows", value: "active_window" },
  { label: "Files", value: "file_watcher" },
  { label: "Terminal", value: "terminal_command_detector" },
];

const sidecarLabels: Record<SidecarHealth["status"], string> = {
  loading: "Checking sidecar",
  healthy: "Sidecar healthy",
  unhealthy: "Sidecar unhealthy",
  missing: "Missing sidecar",
};

const sidecarTone: Record<SidecarHealth["status"], string> = {
  loading: "border-sky-300 bg-sky-50 text-sky-950",
  healthy: "border-emerald-300 bg-emerald-50 text-emerald-950",
  unhealthy: "border-rose-300 bg-rose-50 text-rose-950",
  missing: "border-amber-300 bg-amber-50 text-amber-950",
};

const workspaceNavItems: WorkspaceNavItem[] = [
  {
    id: "home",
    label: "Home",
    description: "Start, finish and understand a session",
  },
  {
    id: "history",
    label: "History",
    description: "Review saved sessions",
  },
  {
    id: "settings",
    label: "Settings",
    description: "Privacy, AI and diagnostics",
  },
];

const initialExportReviewState: ExportReviewState = {
  status: "idle",
  message: "No export preview available yet.",
  export: null,
};

const initialShareSafeExportState: ShareSafeExportState = {
  status: "idle",
  message: "No share-safe report preview has been generated.",
  markdown: null,
};

const initialDiagnosticsBundleState: DiagnosticsBundleState = {
  status: "idle",
  message: "No diagnostics bundle has been generated.",
  bundleJson: null,
};

const initialFolderReviewState: FolderReviewState = {
  status: "idle",
  message: "Session folder lookup has not run yet.",
  path: null,
};

const initialScreenshotReviewState: ScreenshotReviewState = {
  status: "idle",
  message: "Connect to a live sidecar session before reviewing screenshots.",
  screenshots: [],
};

const initialScreenshotPreviewState: ScreenshotPreviewState = {
  status: "idle",
  message: "Select a screenshot to load a local preview.",
  preview: null,
};

const initialScreenshotDeletionState: ScreenshotDeletionState = {
  status: "idle",
  message: "No screenshot deletion has run yet.",
  result: null,
};

const initialSessionBrowserState: SessionBrowserState = {
  status: "unavailable",
  message: "Session list bridge is unavailable.",
  sessions: [],
};

const initialSessionDeletionState: SessionDeletionState = {
  status: "idle",
  message: "No session deletion has run yet.",
  result: null,
};

const initialAiReportReviewState: AiReportReviewState = {
  status: "runtime_unavailable",
  message: "Finish or select a session before creating a summary.",
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

const initialPrivacyCenterState: PrivacyCenterState = {
  privateMode: false,
  clipboardSafeMode: true,
  allowlistText: "Code.exe\nWindows Terminal",
  blocklistText: "chrome.exe\nmsedge.exe",
};

const initialPrivacyPolicyMessage = "Privacy policy is loaded from the local sidecar when available.";

const initialFileWatchSettingsState: FileWatchSettingsState = {
  rootsText: "",
};

const initialSessionDraftState: SessionDraftState = {
  title: "Desktop recording",
  goal: "",
  projectLabel: "",
  tagsText: "",
};

const defaultModelEndpoint = "http://127.0.0.1:11434";
const onboardingStorageKey = "worktrace.firstRunOnboarding.v1";

function activeRecorderSessionFromList(sessions: SessionSummary[]): RecorderSession | null {
  const activeSession = sessions.find(
    (session) => isRecorderSessionStatus(session.status) && isActiveRecorderStatus(session.status),
  );
  if (!activeSession) {
    return null;
  }
  return {
    id: activeSession.id,
    startedAt: activeSession.startedAt,
    endedAt: activeSession.endedAt,
    status: activeSession.status as RecorderSessionStatus,
    title: activeSession.title,
    goal: activeSession.goal,
    projectLabel: activeSession.projectLabel,
    tags: activeSession.tags,
    storagePath: activeSession.storagePath,
    privacyMode: activeSession.privacyMode,
  };
}

function isRecorderSessionStatus(status: string): status is RecorderSessionStatus {
  return (
    status === "recording" ||
    status === "paused" ||
    status === "stopped" ||
    status === "interrupted"
  );
}

function isActiveRecorderStatus(status: RecorderSessionStatus): boolean {
  return status === "recording" || status === "paused";
}

function recorderUiStatusFromSession(session: RecorderSession): RecorderUiStatus {
  return session.status;
}

type AiSummaryMode = {
  label: string;
  tone: "safe" | "pending" | "warning" | "blocked";
  details: string;
};

function aiSummaryMode(
  aiReportReview: AiReportReviewState,
  recorderStatus: RecorderUiStatus,
): AiSummaryMode {
  if (recorderStatus === "recording" || recorderStatus === "paused") {
    return {
      label: "Summary after finish",
      tone: "pending",
      details: "AI summaries become available after you finish the session.",
    };
  }
  if (aiReportReview.provider === "gemini_gemma_dev" && aiReportReview.canGenerate) {
    return {
      label: "Development AI enabled",
      tone: "warning",
      details:
        "Development reports may send redacted text evidence to Google. Screenshots and raw artifacts stay local by default.",
    };
  }
  if (aiReportReview.canGenerate || aiReportReview.status === "complete") {
    return {
      label: "AI summary ready",
      tone: "safe",
      details: "The configured local report runtime is ready for a finished session.",
    };
  }
  return {
    label: "AI setup required",
    tone: "pending",
    details: "Set up local AI, or explicitly enable the development report shortcut.",
  };
}

function SessionResultPanel({
  activityCount,
  aiReportState,
  canCreateSummary,
  onReviewActivity,
  onCreateSummary,
  onShareUpdate,
  onSetupSummaries,
  onStartNewSession,
  onViewProof,
  session,
  shareDisabled,
  visualMomentCount,
}: {
  activityCount: number;
  aiReportState: AiReportReviewState;
  canCreateSummary: boolean;
  onReviewActivity: () => void;
  onCreateSummary: () => void;
  onShareUpdate: () => void;
  onSetupSummaries: () => void;
  onStartNewSession: () => void;
  onViewProof: () => void;
  session: RecorderSession | null;
  shareDisabled: boolean;
  visualMomentCount: number;
}) {
  const isRunning = aiReportState.status === "running" || aiReportState.status === "loading";
  const title = aiReportState.report?.sessionTitle || session?.title || "Work session";
  const summaryText =
    aiReportState.report?.summary.text ??
    (isRunning
      ? "WorkTrace is creating your private recap from local session evidence."
      : `Captured ${activityCount} ${activityCount === 1 ? "activity" : "activities"} and ${visualMomentCount} visual ${visualMomentCount === 1 ? "moment" : "moments"} locally.`);
  const actionLabel = aiReportState.status === "complete" ? "Regenerate Summary" : "Create Summary";
  const canShare = !shareDisabled && aiReportState.status === "complete";

  return (
    <section
      aria-label="Session recap"
      className="rounded-lg border border-emerald-200 bg-white p-6 shadow-[0_16px_38px_rgba(15,23,42,0.06)]"
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl">
          <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">
            Session result
          </p>
          <h2 className="mt-2 text-2xl font-semibold tracking-normal">Your session recap</h2>
          <p className="mt-1 text-sm font-semibold text-zinc-700">{title}</p>
          <p className="mt-3 text-sm leading-6 text-zinc-700">{summaryText}</p>
          {aiReportState.status === "complete" ? (
            <p className="mt-3 text-sm font-semibold text-emerald-700">{aiReportState.message}</p>
          ) : null}
          {aiReportState.status !== "complete" && !aiReportState.canGenerate ? (
            <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-950">
              <span className="block font-semibold">Smart recap is not set up</span>
              Your captured session is ready to review. Set up private AI summaries later from
              Settings.
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2 lg:justify-end">
          {canCreateSummary || aiReportState.status === "complete" || isRunning ? (
            <button
              className="rounded-md border border-zinc-950 bg-zinc-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:border-zinc-300 disabled:bg-zinc-100 disabled:text-zinc-500"
              disabled={!canCreateSummary || isRunning}
              onClick={onCreateSummary}
              type="button"
            >
              {isRunning ? "Creating Summary" : actionLabel}
            </button>
          ) : null}
          {canShare ? (
            <button
              className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-semibold text-zinc-800 transition hover:border-zinc-500"
              onClick={onShareUpdate}
              type="button"
            >
              Share Update
            </button>
          ) : null}
          <button
            className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-semibold text-zinc-800 transition hover:border-zinc-500"
            onClick={onViewProof}
            type="button"
          >
            View Moments
          </button>
          <button
            className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-semibold text-zinc-800 transition hover:border-zinc-500"
            onClick={onReviewActivity}
            type="button"
          >
            Review Activity
          </button>
          <button
            className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-semibold text-zinc-800 transition hover:border-zinc-500"
            onClick={onStartNewSession}
            type="button"
          >
            Start New Session
          </button>
          {aiReportState.status !== "complete" && !aiReportState.canGenerate ? (
            <button
              className="rounded-md border border-transparent px-4 py-2 text-sm font-semibold text-zinc-600 transition hover:text-zinc-950"
              onClick={onSetupSummaries}
              type="button"
            >
              Set up smart summaries
            </button>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function StartNewSessionPanel({
  onStart,
  status,
}: {
  onStart: () => void;
  status: RecorderUiStatus;
}) {
  return (
    <article
      aria-label="Session controls"
      className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-zinc-500">
            Next session
          </p>
          <h2 className="mt-1 text-lg font-semibold tracking-normal">Ready when you are</h2>
          <p className="mt-1 text-sm leading-6 text-zinc-700">
            Start a fresh local work session without opening advanced recorder settings.
          </p>
        </div>
        <button
          className="w-fit rounded-md border border-zinc-950 bg-zinc-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:border-zinc-300 disabled:bg-zinc-100 disabled:text-zinc-500"
          disabled={status === "loading" || status === "recording" || status === "paused"}
          onClick={onStart}
          type="button"
        >
          Start New Session
        </button>
      </div>
    </article>
  );
}

function App() {
  const [activeWorkspace, setActiveWorkspace] = useState<WorkspaceView>("home");
  const [sidecarHealth, setSidecarHealth] = useState<SidecarHealth>(initialSidecarHealth);
  const [sessionEvents, setSessionEvents] = useState<SessionEventsResult>(initialSessionEvents);
  const [recorderSession, setRecorderSession] = useState<RecorderSession | null>(null);
  const [recorderStatus, setRecorderStatus] = useState<RecorderUiStatus>("idle");
  const [recorderMessage, setRecorderMessage] = useState(initialRecorderMessage);
  const [eventFilter, setEventFilter] = useState<EventFilter>("all");
  const [eventSearch, setEventSearch] = useState("");
  const [eventDate, setEventDate] = useState("");
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  const [exportReview, setExportReview] =
    useState<ExportReviewState>(initialExportReviewState);
  const [shareSafeExport, setShareSafeExport] =
    useState<ShareSafeExportState>(initialShareSafeExportState);
  const [diagnosticsBundle, setDiagnosticsBundle] =
    useState<DiagnosticsBundleState>(initialDiagnosticsBundleState);
  const [folderReview, setFolderReview] =
    useState<FolderReviewState>(initialFolderReviewState);
  const [aiReportReview, setAiReportReview] =
    useState<AiReportReviewState>(initialAiReportReviewState);
  const [screenshotReview, setScreenshotReview] =
    useState<ScreenshotReviewState>(initialScreenshotReviewState);
  const [screenshotPreview, setScreenshotPreview] =
    useState<ScreenshotPreviewState>(initialScreenshotPreviewState);
  const [screenshotDeletion, setScreenshotDeletion] =
    useState<ScreenshotDeletionState>(initialScreenshotDeletionState);
  const [selectedScreenshotId, setSelectedScreenshotId] = useState<string | null>(null);
  const [sessionBrowser, setSessionBrowser] =
    useState<SessionBrowserState>(initialSessionBrowserState);
  const [sessionDeletion, setSessionDeletion] =
    useState<SessionDeletionState>(initialSessionDeletionState);
  const [privacyCenter, setPrivacyCenter] =
    useState<PrivacyCenterState>(initialPrivacyCenterState);
  const [privacyPolicyStatus, setPrivacyPolicyStatus] =
    useState<"idle" | "loading" | "available" | "unavailable">("idle");
  const [privacyPolicyMessage, setPrivacyPolicyMessage] =
    useState(initialPrivacyPolicyMessage);
  const [fileWatchSettings, setFileWatchSettings] =
    useState<FileWatchSettingsState>(initialFileWatchSettingsState);
  const [sessionDraft, setSessionDraft] =
    useState<SessionDraftState>(initialSessionDraftState);
  const [modelEndpoint, setModelEndpoint] = useState(defaultModelEndpoint);
  const [firstRunOnboarding, setFirstRunOnboarding] =
    useState<FirstRunOnboardingState>(readFirstRunOnboarding);
  const [homeProofVisible, setHomeProofVisible] = useState(false);
  const [technicalProofVisible, setTechnicalProofVisible] = useState(false);
  const [advancedAiSetupOpen, setAdvancedAiSetupOpen] = useState(false);
  const [advancedDiagnosticsOpen, setAdvancedDiagnosticsOpen] = useState(false);
  const autoAiReportSessionIdRef = useRef<string | null>(null);
  const sourceEvents: RawTimelineEvent[] =
    sessionEvents.status === "available" ? sessionEvents.events : rawTimelineSimulationEvents;
  const timelineEvents = filterTimelineEvents(sourceEvents, {
    date: eventDate,
    query: eventSearch,
    source: eventFilter,
  });
  const sessionEventCount = sourceEvents.length;
  const visibleEventCount = timelineEvents.length;
  const sourceStatusLabel =
    sessionEvents.status === "available" ? "Latest sidecar session" : "Fixture preview session";
  const reviewSessionId =
    recorderSession?.id ?? (sessionEvents.status === "available" ? "latest" : null);
  const endpointValidation = validateLocalModelEndpoint(modelEndpoint);
  const canRequestAiReport =
    Boolean(reviewSessionId) &&
    recorderStatus !== "recording" &&
    recorderStatus !== "paused" &&
    endpointValidation.isValid;
  const hasFinishedSession =
    recorderSession?.status === "stopped" || recorderSession?.status === "interrupted";
  const hasSessionResult = hasFinishedSession || aiReportReview.status === "complete";
  const canOpenHomeProof = recorderStatus !== "recording" && recorderStatus !== "paused";
  const showHomeProof = homeProofVisible;
  const fileWatchRoots = parseFileWatchRoots(fileWatchSettings.rootsText);
  const activeFileWatchRoots = privacyCenter.privateMode ? [] : fileWatchRoots;
  const summaryMode = aiSummaryMode(aiReportReview, recorderStatus);

  const handleSelectEvidence = useCallback((evidenceId: string) => {
    setSelectedEvidenceId(evidenceId);
    setEventFilter("all");
    setEventSearch("");
    setEventDate("");
    setActiveWorkspace("home");
  }, []);

  const requestAiReport = useCallback(async (sessionId: string) => {
    setAiReportReview((current) => ({
      ...current,
      status: "running",
      message: "Local AI summary generation is running.",
      report: null,
    }));
    setAiReportReview(await generateAiReport(sessionId));
  }, []);

  useEffect(() => {
    if (!selectedEvidenceId) {
      return;
    }
    document
      .getElementById(`timeline-event-${selectedEvidenceId}`)
      ?.scrollIntoView?.({ block: "center", behavior: "smooth" });
  }, [selectedEvidenceId]);

  const applyOnboardingPreset = (preset: OnboardingPreset) => {
    setFirstRunOnboarding((current) => ({
      ...current,
      selectedPreset: preset,
      accepted: false,
    }));
    if (preset === "private_safe") {
      setPrivacyCenter((current) => ({
        ...current,
        privateMode: true,
        clipboardSafeMode: true,
        blocklistText: "chrome.exe\nmsedge.exe\nslack.exe\nTeams.exe",
      }));
      setFileWatchSettings({ rootsText: "" });
      return;
    }
    if (preset === "coding") {
      setPrivacyCenter((current) => ({
        ...current,
        privateMode: false,
        clipboardSafeMode: true,
        allowlistText: "Code.exe\nWindows Terminal\nPowerShell.exe",
        blocklistText: "chrome.exe\nmsedge.exe",
      }));
      return;
    }
    setPrivacyCenter((current) => ({
      ...current,
      privateMode: false,
      clipboardSafeMode: true,
      allowlistText: "Code.exe\nWindows Terminal",
      blocklistText: "chrome.exe\nmsedge.exe\nslack.exe",
    }));
  };

  const acceptFirstRunOnboarding = () => {
    const selectedPreset = firstRunOnboarding.selectedPreset ?? "coding";
    const nextState: FirstRunOnboardingState = {
      accepted: true,
      selectedPreset,
    };
    setFirstRunOnboarding(nextState);
    writeFirstRunOnboarding(nextState);
  };

  const refreshSidecarHealth = useCallback(async () => {
    setSidecarHealth(initialSidecarHealth);
    setSidecarHealth(await getSidecarHealth());
  }, []);

  const handleStartSidecar = async () => {
    setSidecarHealth({
      ...initialSidecarHealth,
      message: "Starting local agent sidecar.",
    });
    setSidecarHealth(await startSidecar());
  };

  const handleStopSidecar = async () => {
    setSidecarHealth({
      ...initialSidecarHealth,
      message: "Stopping local agent sidecar.",
    });
    setSidecarHealth(await stopSidecar());
  };

  const applySessionBrowserResult = useCallback((sessions: SessionListResult) => {
    if (sessions.status === "unavailable") {
      setSessionBrowser({
        status: "unavailable",
        message: sessions.message,
        sessions: [],
      });
      return;
    }
    setSessionBrowser({
      status: "success",
      message: sessions.message,
      sessions: sessions.sessions,
    });
  }, []);

  const recoverActiveRecorderSession = useCallback(async (
    sessions: SessionListResult,
    message: string,
  ): Promise<boolean> => {
    if (sessions.status === "unavailable") {
      return false;
    }
    const activeSession = activeRecorderSessionFromList(sessions.sessions);
    if (!activeSession) {
      return false;
    }
    setRecorderSession(activeSession);
    setRecorderStatus(recorderUiStatusFromSession(activeSession));
    setRecorderMessage(message);
    setSessionEvents(await getSessionEvents(activeSession.id));
    return true;
  }, []);

  const applyRecorderResult = async (result: RecorderControlResult) => {
    setRecorderMessage(result.message);
    if (result.status === "unavailable") {
      const sessions = await getSessions();
      applySessionBrowserResult(sessions);
      const recovered = await recoverActiveRecorderSession(
        sessions,
        "Active recording session recovered from the local agent.",
      );
      if (recovered) {
        return;
      }
      setRecorderStatus("unavailable");
      return;
    }

    setRecorderSession(result.session);
    setRecorderStatus(recorderUiStatusFromSession(result.session));
    setSessionEvents(await getSessionEvents(result.session.id));
    if (
      (result.session.status === "stopped" || result.session.status === "interrupted") &&
      autoAiReportSessionIdRef.current !== result.session.id &&
      endpointValidation.isValid
    ) {
      const latestAiReportState =
        aiReportReview.status === "ready" && aiReportReview.canGenerate
          ? aiReportReview
          : await getAiReportStatus(result.session.id);
      if (latestAiReportState !== aiReportReview) {
        setAiReportReview(latestAiReportState);
      }
      if (latestAiReportState.canGenerate && latestAiReportState.status === "ready") {
        autoAiReportSessionIdRef.current = result.session.id;
        void requestAiReport(result.session.id);
      }
    }
  };

  const handleStartRecording = async () => {
    if (!firstRunOnboarding.accepted) {
      setRecorderMessage("Complete first-run privacy setup before recording.");
      return;
    }
    setHomeProofVisible(false);
    setTechnicalProofVisible(false);
    setRecorderStatus("loading");
    setRecorderMessage("Starting recording session.");
    await applyRecorderResult(
      await startRecordingSession({
        sessionId: createSessionId(),
        startedAt: nowWithOffset(),
        title: optionalTrimmed(sessionDraft.title) ?? "Desktop recording",
        goal: optionalTrimmed(sessionDraft.goal),
        projectLabel: optionalTrimmed(sessionDraft.projectLabel),
        tags: parseSessionTags(sessionDraft.tagsText),
        privacyMode: privacyCenter.privateMode ? "private" : "standard",
        fileWatchRoots: activeFileWatchRoots,
      }),
    );
  };

  const handlePauseRecording = async () => {
    if (!recorderSession) {
      return;
    }
    setRecorderStatus("loading");
    setRecorderMessage("Pausing recording session.");
    await applyRecorderResult(
      await pauseRecordingSession({
        sessionId: recorderSession.id,
        pausedAt: nowWithOffset(),
      }),
    );
  };

  const handleResumeRecording = async () => {
    if (!recorderSession) {
      return;
    }
    setRecorderStatus("loading");
    setRecorderMessage("Resuming recording session.");
    await applyRecorderResult(
      await resumeRecordingSession({
        sessionId: recorderSession.id,
        resumedAt: nowWithOffset(),
        fileWatchRoots: activeFileWatchRoots,
      }),
    );
  };

  const handleStopRecording = async () => {
    if (!recorderSession) {
      return;
    }
    setHomeProofVisible(false);
    setTechnicalProofVisible(false);
    setRecorderStatus("loading");
    setRecorderMessage("Stopping recording session.");
    await applyRecorderResult(
      await stopRecordingSession({
        sessionId: recorderSession.id,
        stoppedAt: nowWithOffset(),
      }),
    );
  };

  const applyExportResult = (result: SessionExportResult) => {
    if (result.status === "unavailable") {
      setExportReview({
        status: "unavailable",
        message: result.message,
        export: null,
      });
      return;
    }

    setExportReview({
      status: "success",
      message: result.message,
      export: result.export,
    });
  };

  const applyFolderResult = (result: SessionFolderResult) => {
    if (result.status === "unavailable") {
      setFolderReview({
        status: "unavailable",
        message: result.message,
        path: null,
      });
      return;
    }

    setFolderReview({
      status: "success",
      message: result.message,
      path: result.path,
    });
  };

  const handleExportMarkdown = async () => {
    if (!reviewSessionId) {
      return;
    }
    setExportReview({
      status: "loading",
      message: "Generating Markdown export preview.",
      export: null,
    });
    applyExportResult(await exportSessionMarkdown(reviewSessionId));
  };

  const handleExportRawJson = async () => {
    if (!reviewSessionId) {
      return;
    }
    setExportReview({
      status: "loading",
      message: "Generating raw JSON export preview.",
      export: null,
    });
    applyExportResult(await exportSessionRawJson(reviewSessionId));
  };

  const handleOpenSessionFolder = async () => {
    if (!reviewSessionId) {
      return;
    }
    setFolderReview({
      status: "loading",
      message: "Opening session folder in Windows Explorer.",
      path: null,
    });
    applyFolderResult(await openSessionFolder(reviewSessionId));
  };

  const handlePreviewShareSafeMarkdown = () => {
    if (!aiReportReview.report) {
      setShareSafeExport({
        status: "unavailable",
        message: "Create a summary before preparing a shareable export.",
        markdown: null,
      });
      return;
    }
    setShareSafeExport({
      status: "success",
      message: "Share-safe Markdown preview generated locally. Review it before sharing.",
      markdown: buildShareSafeReportMarkdown(aiReportReview.report),
    });
  };

  const handleCopyShareSafeMarkdown = async () => {
    if (shareSafeExport.status !== "success") {
      return;
    }
    try {
      await navigator.clipboard.writeText(shareSafeExport.markdown);
      setShareSafeExport({
        ...shareSafeExport,
        message: "Share-safe Markdown copied to clipboard.",
      });
    } catch {
      setShareSafeExport({
        ...shareSafeExport,
        message: "Share-safe Markdown is ready. Clipboard copy is unavailable in this runtime.",
      });
    }
  };

  const handleDownloadShareSafeMarkdown = () => {
    if (shareSafeExport.status !== "success") {
      return;
    }
    const blob = new Blob([shareSafeExport.markdown], {
      type: "text/markdown;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "worktrace-share-safe-report.md";
    link.rel = "noopener";
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setShareSafeExport({
      ...shareSafeExport,
      message: "Share-safe Markdown download started.",
    });
  };

  const handlePreviewDiagnosticsBundle = () => {
    setDiagnosticsBundle({
      status: "success",
      message: "Diagnostics bundle preview generated locally. Review before sharing.",
      bundleJson: buildDiagnosticsBundleJson({
        aiReportReview,
        endpointIsLocalhost: endpointValidation.isValid,
        eventCount: sessionEventCount,
        fileWatchRootsCount: fileWatchRoots.length,
        firstRunOnboarding,
        privacyCenter,
        privacyPolicyMessage,
        privacyPolicyStatus,
        recorderSession,
        recorderStatus,
        screenshotCount:
          screenshotReview.status === "success" ? screenshotReview.screenshots.length : 0,
        sessionBrowser,
        sidecarHealth,
        visibleEventCount,
      }),
    });
  };

  const handleCopyDiagnosticsBundle = async () => {
    if (diagnosticsBundle.status !== "success") {
      return;
    }
    try {
      await navigator.clipboard.writeText(diagnosticsBundle.bundleJson);
      setDiagnosticsBundle({
        ...diagnosticsBundle,
        message: "Diagnostics JSON copied to clipboard.",
      });
    } catch {
      setDiagnosticsBundle({
        ...diagnosticsBundle,
        message: "Diagnostics JSON is ready. Clipboard copy is unavailable in this runtime.",
      });
    }
  };

  const handleDownloadDiagnosticsBundle = () => {
    if (diagnosticsBundle.status !== "success") {
      return;
    }
    const blob = new Blob([diagnosticsBundle.bundleJson], {
      type: "application/json;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "worktrace-diagnostics.safe.json";
    link.rel = "noopener";
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setDiagnosticsBundle({
      ...diagnosticsBundle,
      message: "Diagnostics JSON download started.",
    });
  };

  const handleGenerateAiReport = async () => {
    if (!reviewSessionId || !canRequestAiReport || !aiReportReview.canGenerate) {
      return;
    }
    await requestAiReport(reviewSessionId);
  };

  const handleCancelAiReport = async () => {
    if (!reviewSessionId) {
      return;
    }
    setAiReportReview(await cancelAiReport(reviewSessionId));
  };

  const applyScreenshotResult = (result: SessionScreenshotsResult) => {
    if (result.status === "unavailable") {
      setScreenshotReview({
        status: "unavailable",
        message: result.message,
        screenshots: [],
      });
      setSelectedScreenshotId(null);
      return;
    }

    setScreenshotReview({
      status: "success",
      message: result.message,
      screenshots: result.screenshots,
    });
    setSelectedScreenshotId(result.screenshots[0]?.id ?? null);
  };

  const handleDeleteScreenshots = async () => {
    if (!reviewSessionId) {
      return;
    }
    setScreenshotDeletion({
      status: "loading",
      message: "Deleting screenshot artifacts.",
      result: null,
    });
    const result = await deleteSessionScreenshots(reviewSessionId);
    if (result.status === "unavailable") {
      setScreenshotDeletion({
        status: "unavailable",
        message: result.message,
        result: null,
      });
      return;
    }
    setScreenshotDeletion({
      status: "success",
      message: result.message,
      result,
    });
    setScreenshotReview({
      status: "success",
      message: "Screenshot metadata loaded.",
      screenshots: [],
    });
    setSelectedScreenshotId(null);
  };

  const handleRefreshSessions = useCallback(async () => {
    setSessionBrowser({
      status: "loading",
      message: "Loading session list.",
      sessions: [],
    });
    const result = await getSessions();
    if (result.status === "unavailable") {
      setSessionBrowser({
        status: "unavailable",
        message: result.message,
        sessions: [],
      });
      return;
    }
    setSessionBrowser({
      status: "success",
      message: result.message,
      sessions: result.sessions,
    });
  }, []);

  const handleDeleteSession = async (sessionId: string) => {
    setSessionDeletion({
      status: "loading",
      message: "Deleting session.",
      result: null,
    });
    const result = await deleteSession(sessionId);
    if (result.status === "unavailable") {
      setSessionDeletion({
        status: "unavailable",
        message: result.message,
        result: null,
      });
      return;
    }
    setSessionDeletion({
      status: "success",
      message: result.message,
      result,
    });
    // Refresh the session list after deletion
    void handleRefreshSessions();
  };

  const handleSavePrivacyPolicy = async () => {
    setPrivacyPolicyStatus("loading");
    setPrivacyPolicyMessage("Saving privacy policy to the local sidecar.");
    const result = await updatePrivacyPolicy({
      allowlist: privacyTextEntries(privacyCenter.allowlistText),
      blocklist: privacyTextEntries(privacyCenter.blocklistText),
      clipboardSafeMode: privacyCenter.clipboardSafeMode,
    });
    if (result.status === "unavailable") {
      setPrivacyPolicyStatus("unavailable");
      setPrivacyPolicyMessage(result.message);
      return;
    }
    setPrivacyCenter({
      ...privacyCenter,
      allowlistText: result.policy.allowlist.join("\n"),
      blocklistText: result.policy.blocklist.join("\n"),
      clipboardSafeMode: result.policy.clipboardSafeMode,
    });
    setPrivacyPolicyStatus("available");
    setPrivacyPolicyMessage(result.message);
  };

  useEffect(() => {
    let isMounted = true;

    void Promise.all([
      getSidecarHealth(),
      getSessionEvents(),
      getSessions(),
      getPrivacyPolicy(),
    ]).then(async ([health, events, sessions, privacyPolicy]) => {
      if (!isMounted) {
        return;
      }

      setSidecarHealth(health);
      setSessionEvents(events);
      applySessionBrowserResult(sessions);

      if (sessions.status === "available") {
        const activeSession = activeRecorderSessionFromList(sessions.sessions);
        if (activeSession) {
          setRecorderSession(activeSession);
          setRecorderStatus(recorderUiStatusFromSession(activeSession));
          setRecorderMessage("Active recording session recovered from the local agent.");
          const activeEvents = await getSessionEvents(activeSession.id);
          if (isMounted) {
            setSessionEvents(activeEvents);
          }
        } else {
          setRecorderStatus("idle");
          setRecorderMessage(initialRecorderMessage);
        }
      }

      if (privacyPolicy.status === "unavailable") {
        setPrivacyPolicyStatus("unavailable");
        setPrivacyPolicyMessage(privacyPolicy.message);
      } else {
        setPrivacyPolicyStatus("available");
        setPrivacyPolicyMessage(privacyPolicy.message);
        setPrivacyCenter((current) => ({
          ...current,
          allowlistText: privacyPolicy.policy.allowlist.join("\n"),
          blocklistText: privacyPolicy.policy.blocklist.join("\n"),
          clipboardSafeMode: privacyPolicy.policy.clipboardSafeMode,
        }));
      }
    });

    return () => {
      isMounted = false;
    };
  }, [applySessionBrowserResult]);

  useEffect(() => {
    let isMounted = true;

    void Promise.resolve().then(async () => {
      if (!isMounted) {
        return;
      }

      if (!reviewSessionId) {
        setScreenshotReview(initialScreenshotReviewState);
        setScreenshotPreview(initialScreenshotPreviewState);
        setScreenshotDeletion(initialScreenshotDeletionState);
        setSelectedScreenshotId(null);
        return;
      }

      setScreenshotReview({
        status: "loading",
        message: "Loading screenshot metadata.",
        screenshots: [],
      });
      setScreenshotDeletion(initialScreenshotDeletionState);
      const result = await getSessionScreenshots(reviewSessionId);
      if (isMounted) {
        applyScreenshotResult(result);
      }
    });

    return () => {
      isMounted = false;
    };
  }, [reviewSessionId]);

  useEffect(() => {
    let isMounted = true;

    void Promise.resolve().then(async () => {
      if (!isMounted) {
        return;
      }

      if (!reviewSessionId || !selectedScreenshotId) {
        setScreenshotPreview(initialScreenshotPreviewState);
        return;
      }

      setScreenshotPreview({
        status: "loading",
        message: "Loading local screenshot preview.",
        preview: null,
      });
      const result = await getSessionScreenshotPreview(reviewSessionId, selectedScreenshotId);
      if (!isMounted) {
        return;
      }
      if (result.status === "unavailable") {
        setScreenshotPreview({
          status: "unavailable",
          message: result.message,
          preview: null,
        });
        return;
      }
      setScreenshotPreview({
        status: "success",
        message: result.message,
        preview: result.preview,
      });
    });

    return () => {
      isMounted = false;
    };
  }, [reviewSessionId, selectedScreenshotId]);

  useEffect(() => {
    let isMounted = true;

    void Promise.resolve().then(async () => {
      if (!isMounted) {
        return;
      }

      if (!reviewSessionId) {
        setAiReportReview(initialAiReportReviewState);
        return;
      }

      setAiReportReview({
        ...initialAiReportReviewState,
        status: "loading",
        message: "Checking local AI summary runtime.",
      });
      const result = await getAiReportStatus(reviewSessionId);
      if (isMounted) {
        setAiReportReview(result);
      }
    });

    return () => {
      isMounted = false;
    };
  }, [reviewSessionId]);

  const activeWorkspaceItem =
    workspaceNavItems.find((item) => item.id === activeWorkspace) ?? workspaceNavItems[0];
  return (
    <main className="min-h-screen bg-[#f4f5f7] text-zinc-950">
      <div className="mx-auto grid min-h-screen w-full max-w-[96rem] grid-cols-1 lg:grid-cols-[15.5rem_minmax(0,1fr)]">
        <aside className="border-b border-zinc-200 bg-[#09090b] px-4 py-4 text-white shadow-[0_18px_50px_rgba(9,9,11,0.16)] lg:sticky lg:top-0 lg:flex lg:h-screen lg:flex-col lg:border-b-0 lg:border-r lg:px-4 lg:py-5">
          <div className="flex items-center justify-between gap-4 lg:block">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-emerald-300">
                Private beta
              </p>
              <h1 className="mt-1 text-2xl font-semibold tracking-normal">WorkTrace AI</h1>
            </div>
            <div className="rounded-md border border-white/15 bg-white/10 px-3 py-2 text-xs font-semibold text-zinc-200 lg:mt-4 lg:w-full">
              Local-first
            </div>
          </div>
          <nav
            aria-label="Workspace"
            className="mt-4 flex gap-2 overflow-x-auto pb-1 lg:block lg:space-y-1.5 lg:overflow-visible lg:pb-0"
          >
            {workspaceNavItems.map((item, index) => {
              const active = activeWorkspace === item.id;
              return (
                <button
                  aria-label={item.label}
                  aria-current={active ? "page" : undefined}
                    className={`group min-w-36 rounded-md border px-3 py-2 text-left transition duration-150 ease-out hover:-translate-y-0.5 lg:w-full ${
                    active
                      ? "border-emerald-300 bg-emerald-300 text-zinc-950 shadow-sm"
                      : "border-white/10 bg-white/5 text-zinc-200 hover:border-white/25 hover:bg-white/10"
                  }`}
                  key={item.id}
                  onClick={() => setActiveWorkspace(item.id)}
                  type="button"
                >
                  <span className="flex items-center gap-2">
                    <span
                      className={`rounded border px-1.5 py-0.5 text-[0.65rem] font-semibold ${
                        active
                          ? "border-zinc-950/20 bg-zinc-950/10"
                          : "border-white/10 bg-white/5 text-zinc-400 group-hover:text-zinc-200"
                      }`}
                    >
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <span className="text-sm font-semibold">{item.label}</span>
                  </span>
                  <span className="mt-1 hidden text-xs leading-5 opacity-80 lg:block">
                    {item.description}
                  </span>
                </button>
              );
            })}
          </nav>
          <div className="mt-4 hidden rounded-md border border-white/10 bg-white/5 p-3 text-xs leading-5 text-zinc-300 lg:block">
            Capture stays local. Hosted development reports are labelled when enabled.
          </div>
          <div className="mt-auto hidden pt-4 text-xs leading-5 text-zinc-500 lg:block">
            Built for private work sessions, evidence review and local-first reports.
          </div>
        </aside>

        <section className="min-w-0 px-4 py-4 sm:px-6 lg:px-7">
          <header className="rounded-lg border border-zinc-200 bg-white/95 p-5 shadow-[0_14px_36px_rgba(15,23,42,0.055)]">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
              <div className="min-w-0">
                <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">
                  {activeWorkspaceItem.label} workspace
                </p>
                <h2 className="mt-1 text-2xl font-semibold tracking-normal text-zinc-950 sm:text-3xl">
                  {workspaceHeading(activeWorkspace)}
                </h2>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-700">
                  {workspaceDescription(activeWorkspace)}
                </p>
              </div>
              <div className="grid gap-2 sm:grid-cols-3 xl:min-w-[30rem]">
                <ShellStatusChip
                  label="Capture"
                  value={sidecarHealth.status === "healthy" ? "Ready" : "Needs attention"}
                  tone={sidecarHealth.status === "healthy" ? "safe" : "pending"}
                />
                <ShellStatusChip
                  label="Session"
                  value={recorderStatusLabel(recorderStatus)}
                  tone={recorderStatus === "unavailable" ? "blocked" : "safe"}
                />
                <ShellStatusChip
                  label="AI Summary"
                  value={summaryMode.label}
                  tone={summaryMode.tone}
                />
              </div>
            </div>
          </header>

          <div className="mt-4 animate-workspace space-y-4" key={activeWorkspace}>
            {activeWorkspace === "home" ? (
              <>
                {!firstRunOnboarding.accepted && !hasSessionResult ? (
                  <FirstRunOnboardingPanel
                    onAccept={acceptFirstRunOnboarding}
                    onSelectPreset={applyOnboardingPreset}
                    state={firstRunOnboarding}
                  />
                ) : null}
                {hasSessionResult ? (
                  <SessionResultPanel
                    activityCount={sessionEventCount}
                    aiReportState={aiReportReview}
                    canCreateSummary={
                      canRequestAiReport && aiReportReview.canGenerate && aiReportReview.status !== "running"
                    }
                    onCreateSummary={handleGenerateAiReport}
                    onReviewActivity={() => {
                      setHomeProofVisible(true);
                      setTechnicalProofVisible(false);
                    }}
                    onShareUpdate={handlePreviewShareSafeMarkdown}
                    onSetupSummaries={() => setActiveWorkspace("settings")}
                    onStartNewSession={handleStartRecording}
                    onViewProof={() => {
                      setHomeProofVisible(true);
                      setTechnicalProofVisible(false);
                    }}
                    session={recorderSession}
                    shareDisabled={!aiReportReview.report}
                    visualMomentCount={
                      screenshotReview.status === "success" ? screenshotReview.screenshots.length : 0
                    }
                  />
                ) : null}
                <section
                  aria-label="Home session flow"
                  className={
                    hasSessionResult
                      ? "grid grid-cols-1 gap-4"
                      : "grid grid-cols-1 gap-4"
                  }
                >
                  {hasSessionResult ? (
                    <StartNewSessionPanel
                      onStart={handleStartRecording}
                      status={recorderStatus}
                    />
                  ) : (
                    <RecorderControlPanel
                      eventCount={
                        sessionEvents.status === "available" ? sessionEvents.events.length : 0
                      }
                      fileWatchRoots={fileWatchRoots}
                      fileWatchRootsText={fileWatchSettings.rootsText}
                      message={recorderMessage}
                      onFileWatchRootsChange={(rootsText) => setFileWatchSettings({ rootsText })}
                      onPause={handlePauseRecording}
                      onResume={handleResumeRecording}
                      onSessionDraftChange={setSessionDraft}
                      onStart={handleStartRecording}
                      onStop={handleStopRecording}
                      onboardingRequired={!firstRunOnboarding.accepted}
                      privateMode={privacyCenter.privateMode}
                      session={recorderSession}
                      sessionDraft={sessionDraft}
                      status={recorderStatus}
                    />
                  )}
                </section>
                {canOpenHomeProof && !hasSessionResult && !homeProofVisible ? (
                  <details className="rounded-lg border border-zinc-200 bg-white/70 p-3 text-sm text-zinc-700 shadow-sm">
                    <summary className="cursor-pointer font-semibold text-zinc-800">
                      Advanced review
                    </summary>
                    <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <p className="max-w-2xl leading-6">
                        Open local proof tools for manual testing, raw timeline review, exports,
                        and evidence diagnostics.
                      </p>
                      <button
                        className="w-fit rounded-md border border-zinc-300 px-4 py-2 text-sm font-semibold text-zinc-800 transition hover:border-zinc-500"
                        onClick={() => {
                          setHomeProofVisible(true);
                          setTechnicalProofVisible(false);
                        }}
                        type="button"
                      >
                        View Proof
                      </button>
                    </div>
                  </details>
                ) : null}
                {showHomeProof ? (
                  <>
                    <SessionReviewPanel
                      aiReportState={aiReportReview}
                      events={timelineEvents}
                      onOpenTechnicalDetails={() =>
                        setTechnicalProofVisible((current) => !current)
                      }
                      onSelectScreenshot={setSelectedScreenshotId}
                      screenshotState={screenshotReview}
                      selectedScreenshotId={selectedScreenshotId}
                      technicalDetailsOpen={technicalProofVisible}
                    />
                    {technicalProofVisible ? (
                      <>
                        <section className="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(20rem,0.8fr)]">
                          <ExportReviewPanel
                            aiReportState={aiReportReview}
                            canReview={Boolean(reviewSessionId)}
                            canRequestAiReport={canRequestAiReport}
                            exportState={exportReview}
                            folderState={folderReview}
                            onCancelAiReport={handleCancelAiReport}
                            onExportMarkdown={handleExportMarkdown}
                            onExportRawJson={handleExportRawJson}
                            onGenerateAiReport={handleGenerateAiReport}
                            onOpenSessionFolder={handleOpenSessionFolder}
                            onCopyShareSafeMarkdown={handleCopyShareSafeMarkdown}
                            onDownloadShareSafeMarkdown={handleDownloadShareSafeMarkdown}
                            onPreviewShareSafeMarkdown={handlePreviewShareSafeMarkdown}
                            onSelectEvidence={handleSelectEvidence}
                            selectedEvidenceId={selectedEvidenceId}
                            shareSafeState={shareSafeExport}
                          />
                          <ScreenshotEvidencePanel
                            canReview={Boolean(reviewSessionId)}
                            deletionState={screenshotDeletion}
                            onDelete={handleDeleteScreenshots}
                            onSelect={setSelectedScreenshotId}
                            previewState={screenshotPreview}
                            selectedScreenshotId={selectedScreenshotId}
                            state={screenshotReview}
                          />
                        </section>
                        <section
                          aria-label="Activity workspace"
                          className="rounded-md border border-zinc-200 bg-white p-4 shadow-sm"
                        >
                          <details open>
                            <summary className="cursor-pointer text-sm font-semibold text-zinc-900">
                              Detailed activity and proof
                            </summary>
                            <div className="mt-4 space-y-4">
                              <div className="grid gap-3 md:grid-cols-4">
                                <Metric label="Activities" value={sessionEventCount.toString()} />
                                <Metric label="Visible" value={visibleEventCount.toString()} />
                                <Metric label="Source" value={sourceStatusLabel} />
                                <Metric label="Filter" value={filterLabel(eventFilter)} />
                              </div>
                              <TimelineFilterPanel
                                eventDate={eventDate}
                                eventFilter={eventFilter}
                                eventSearch={eventSearch}
                                onClear={() => {
                                  setEventSearch("");
                                  setEventDate("");
                                  setSelectedEvidenceId(null);
                                }}
                                onDateChange={setEventDate}
                                onFilterChange={setEventFilter}
                                onSearchChange={setEventSearch}
                                selectedEvidenceId={selectedEvidenceId}
                              />
                              <RawTimeline
                                events={timelineEvents}
                                selectedEvidenceId={selectedEvidenceId}
                                sourceStatus={sessionEvents.status}
                              />
                            </div>
                          </details>
                        </section>
                      </>
                    ) : null}
                  </>
                ) : null}
              </>
            ) : null}

            {activeWorkspace === "history" ? (
              <SessionBrowserPanel
                deletionState={sessionDeletion}
                onDelete={handleDeleteSession}
                onRefresh={handleRefreshSessions}
                state={sessionBrowser}
              />
            ) : null}

            {activeWorkspace === "settings" ? (
              <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(20rem,0.9fr)]">
                <PrivacyCenterPanel
                  onChange={setPrivacyCenter}
                  onSave={handleSavePrivacyPolicy}
                  policyMessage={privacyPolicyMessage}
                  policyStatus={privacyPolicyStatus}
                  state={privacyCenter}
                />
                <div className="space-y-4">
                  <section
                    aria-label="AI summary settings"
                    className="rounded-md border border-zinc-200 bg-white p-5 shadow-sm"
                  >
                    <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">
                      AI Summary
                    </p>
                    <h2 className="mt-2 text-xl font-semibold tracking-normal">
                      {summaryMode.label}
                    </h2>
                    <p className="mt-3 text-sm leading-6 text-zinc-700">
                      {summaryMode.details}
                    </p>
                    <div
                      className={`mt-4 rounded-md border p-3 text-sm font-semibold ${
                        summaryMode.tone === "warning"
                          ? "border-amber-300 bg-amber-50 text-amber-950"
                          : summaryMode.tone === "safe"
                            ? "border-emerald-300 bg-emerald-50 text-emerald-950"
                            : "border-zinc-200 bg-zinc-50 text-zinc-800"
                      }`}
                    >
                      {aiReportReview.canGenerate || aiReportReview.status === "complete"
                        ? "Summary generation is available for finished sessions."
                        : "Captured sessions remain reviewable even when smart summaries need setup."}
                    </div>
                    <details
                      className="mt-4 rounded-md border border-zinc-200 bg-zinc-50 p-3"
                      onToggle={(event) =>
                        setAdvancedAiSetupOpen(event.currentTarget.open)
                      }
                      open={advancedAiSetupOpen}
                    >
                      <summary className="cursor-pointer text-sm font-semibold text-zinc-900">
                        Advanced AI setup
                      </summary>
                      {advancedAiSetupOpen ? (
                        <div className="mt-4">
                          <ModelSettingsPanel
                            aiReportState={aiReportReview}
                            endpoint={modelEndpoint}
                            endpointValidation={endpointValidation}
                            onEndpointChange={setModelEndpoint}
                          />
                        </div>
                      ) : null}
                    </details>
                  </section>
                  <details
                    className="rounded-md border border-zinc-200 bg-white p-4 shadow-sm"
                    onToggle={(event) =>
                      setAdvancedDiagnosticsOpen(event.currentTarget.open)
                    }
                    open={advancedDiagnosticsOpen}
                  >
                    <summary className="cursor-pointer text-sm font-semibold text-zinc-900">
                      Advanced diagnostics
                    </summary>
                    {advancedDiagnosticsOpen ? (
                      <div className="mt-4 space-y-4">
                        <LocalAgentCard
                          health={sidecarHealth}
                          onCheck={refreshSidecarHealth}
                          onStart={handleStartSidecar}
                          onStop={handleStopSidecar}
                        />
                        <DiagnosticsBundlePanel
                          onCopy={handleCopyDiagnosticsBundle}
                          onDownload={handleDownloadDiagnosticsBundle}
                          onPreview={handlePreviewDiagnosticsBundle}
                          state={diagnosticsBundle}
                        />
                      </div>
                    ) : null}
                  </details>
                </div>
              </section>
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}

function LocalAgentCard({
  health,
  onCheck,
  onStart,
  onStop,
}: {
  health: SidecarHealth;
  onCheck: () => void;
  onStart: () => void;
  onStop: () => void;
}) {
  return (
    <article
      aria-label="Local agent status"
      className={`rounded-md border p-3 shadow-sm ${sidecarTone[health.status]}`}
    >
      <div className="flex h-full flex-col justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold tracking-normal">Local agent</h2>
          <p className="mt-1 text-lg font-semibold tracking-normal">
            {sidecarLabels[health.status]}
          </p>
        </div>
        <div className="space-y-2">
          <p className="text-sm leading-6">{health.message}</p>
          {health.appVersion && health.schemaVersion ? (
            <p className="text-xs font-medium">
              App {health.appVersion} / schema {health.schemaVersion}
            </p>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <button
              className="rounded-md border border-current px-3 py-1.5 text-sm font-semibold transition hover:bg-white/60 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={health.status === "loading"}
              onClick={onCheck}
              type="button"
            >
              Check
            </button>
            <button
              className="rounded-md border border-current px-3 py-1.5 text-sm font-semibold transition hover:bg-white/60 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={health.status === "loading"}
              onClick={onStart}
              type="button"
            >
              Start
            </button>
            <button
              className="rounded-md border border-current px-3 py-1.5 text-sm font-semibold transition hover:bg-white/60 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={health.status === "loading"}
              onClick={onStop}
              type="button"
            >
              Stop
            </button>
          </div>
        </div>
      </div>
    </article>
  );
}

function ShellStatusChip({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "safe" | "pending" | "warning" | "blocked";
}) {
  const toneClass =
    tone === "safe"
      ? "border-emerald-200 bg-emerald-50 text-emerald-950"
      : tone === "warning"
        ? "border-amber-200 bg-amber-50 text-amber-950"
        : tone === "blocked"
          ? "border-rose-200 bg-rose-50 text-rose-950"
          : "border-zinc-200 bg-zinc-50 text-zinc-800";
  return (
    <div className={`min-w-0 rounded-md border px-3 py-2 shadow-sm ${toneClass}`}>
      <p className="text-[0.7rem] font-semibold uppercase tracking-wide opacity-75">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold">{value}</p>
    </div>
  );
}

function TimelineFilterPanel({
  eventDate,
  eventFilter,
  eventSearch,
  onClear,
  onDateChange,
  onFilterChange,
  onSearchChange,
  selectedEvidenceId,
}: {
  eventDate: string;
  eventFilter: EventFilter;
  eventSearch: string;
  onClear: () => void;
  onDateChange: (date: string) => void;
  onFilterChange: (filter: EventFilter) => void;
  onSearchChange: (query: string) => void;
  selectedEvidenceId: string | null;
}) {
  return (
    <div className="rounded-md border border-zinc-300 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">
            Find evidence
          </p>
          <h2 className="mt-2 text-xl font-semibold tracking-normal">
            Search the local timeline
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-700">
            Filter by source, date, app, window title or evidence ID. Search runs locally over
            the current session view.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 lg:justify-end" aria-label="Event filters">
          {eventFilters.map((filter) => (
            <button
              className={`rounded-md border px-3 py-1.5 text-sm font-semibold transition ${
                eventFilter === filter.value
                  ? "border-zinc-950 bg-zinc-950 text-white"
                  : "border-zinc-300 bg-white text-zinc-800 hover:border-zinc-500"
              }`}
              key={filter.value}
              onClick={() => onFilterChange(filter.value)}
              type="button"
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_12rem_auto] md:items-end">
        <label className="grid gap-2 text-sm font-semibold text-zinc-800">
          Search local evidence
          <input
            className="rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-900 outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="App, title, source, type, evidence ID"
            type="search"
            value={eventSearch}
          />
        </label>
        <label className="grid gap-2 text-sm font-semibold text-zinc-800">
          Event date
          <input
            className="rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-900 outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
            onChange={(event) => onDateChange(event.target.value)}
            type="date"
            value={eventDate}
          />
        </label>
        <button
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm font-semibold text-zinc-800 transition hover:border-zinc-500 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={!eventSearch && !eventDate && !selectedEvidenceId}
          onClick={onClear}
          type="button"
        >
          Clear evidence filters
        </button>
      </div>
      {selectedEvidenceId ? (
        <div
          aria-live="polite"
          className="mt-3 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950"
        >
          <span className="sr-only">Selected evidence: {selectedEvidenceId}</span>
          <p className="font-semibold">Selected evidence</p>
          <p className="mt-1 break-all font-mono text-xs">{selectedEvidenceId}</p>
        </div>
      ) : null}
    </div>
  );
}

function workspaceHeading(workspace: WorkspaceView): string {
  const headings: Record<WorkspaceView, string> = {
    home: "Start, finish and understand your work",
    history: "Your work history",
    settings: "Capture protection and AI setup",
  };
  return headings[workspace];
}

function workspaceDescription(workspace: WorkspaceView): string {
  const descriptions: Record<WorkspaceView, string> = {
    home:
      "Press Start Session, work normally, finish, then review the summary and supporting proof.",
    history:
      "Find past sessions by human title, status, duration and captured activity.",
    settings:
      "Manage privacy, local AI setup, storage-safe diagnostics and advanced local-agent controls.",
  };
  return descriptions[workspace];
}

function recorderStatusLabel(status: RecorderUiStatus): string {
  const labels: Record<RecorderUiStatus, string> = {
    idle: "Ready",
    loading: "Working",
    unavailable: "Needs attention",
    recording: "Recording",
    paused: "Paused",
    stopped: "Finished",
    interrupted: "Interrupted",
  };
  return labels[status];
}

function createSessionId(): string {
  const randomId = globalThis.crypto?.randomUUID?.() ?? Math.random().toString(36).slice(2);
  return `sess_desktop_${randomId.replace(/-/g, "_")}`;
}

function nowWithOffset(): string {
  return new Date().toISOString().replace("Z", "+00:00");
}

function filterLabel(filter: EventFilter): string {
  return eventFilters.find((entry) => entry.value === filter)?.label ?? "All";
}

function optionalTrimmed(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function parseSessionTags(value: string): string[] {
  const tags: string[] = [];
  const seen = new Set<string>();
  for (const rawTag of value.split(",")) {
    const tag = rawTag.trim();
    const key = tag.toLocaleLowerCase();
    if (!tag || seen.has(key)) {
      continue;
    }
    seen.add(key);
    tags.push(tag);
    if (tags.length >= 12) {
      break;
    }
  }
  return tags;
}

function buildDiagnosticsBundleJson({
  aiReportReview,
  endpointIsLocalhost,
  eventCount,
  fileWatchRootsCount,
  firstRunOnboarding,
  privacyCenter,
  privacyPolicyMessage,
  privacyPolicyStatus,
  recorderSession,
  recorderStatus,
  screenshotCount,
  sessionBrowser,
  sidecarHealth,
  visibleEventCount,
}: {
  aiReportReview: AiReportReviewState;
  endpointIsLocalhost: boolean;
  eventCount: number;
  fileWatchRootsCount: number;
  firstRunOnboarding: FirstRunOnboardingState;
  privacyCenter: PrivacyCenterState;
  privacyPolicyMessage: string;
  privacyPolicyStatus: "idle" | "loading" | "available" | "unavailable";
  recorderSession: RecorderSession | null;
  recorderStatus: RecorderUiStatus;
  screenshotCount: number;
  sessionBrowser: SessionBrowserState;
  sidecarHealth: SidecarHealth;
  visibleEventCount: number;
}): string {
  const bundle = {
    bundleType: "worktrace-safe-diagnostics",
    generatedAt: new Date().toISOString(),
    privacy: {
      excludes: [
        "screenshots",
        "ocr_text",
        "raw_timeline_events",
        "terminal_commands",
        "window_titles",
        "file_paths",
        "prompts",
        "reports",
        "api_keys",
        "tokens",
        "environment_values",
      ],
      privateMode: privacyCenter.privateMode,
      clipboardSafeMode: privacyCenter.clipboardSafeMode,
      allowlistCount: countDiagnosticsListEntries(privacyCenter.allowlistText),
      blocklistCount: countDiagnosticsListEntries(privacyCenter.blocklistText),
      firstRunAccepted: firstRunOnboarding.accepted,
      firstRunPreset: firstRunOnboarding.selectedPreset,
      policyStatus: privacyPolicyStatus,
      policyMessage: sanitizeDiagnosticsText(privacyPolicyMessage),
    },
    sidecar: {
      status: sidecarHealth.status,
      appVersion: sidecarHealth.appVersion,
      schemaVersion: sidecarHealth.schemaVersion,
      message: sanitizeDiagnosticsText(sidecarHealth.message),
    },
    recorder: {
      status: recorderStatus,
      activeSessionPresent: recorderSession !== null,
      activeSessionStatus: recorderSession?.status ?? null,
      storagePathPresent: Boolean(recorderSession?.storagePath),
      fileWatchRootsCount,
    },
    evidence: {
      loadedEventCount: eventCount,
      visibleEventCount,
      screenshotMetadataCount: screenshotCount,
      rawEvidenceIncluded: false,
    },
    reports: {
      status: aiReportReview.status,
      provider: aiReportReview.provider,
      modelName: aiReportReview.modelName,
      requestedModel: aiReportReview.requestedModel,
      actualModel: aiReportReview.actualModel,
      fallbackUsed: aiReportReview.fallbackUsed,
      runtimeMs: aiReportReview.runtimeMs,
      inputHashPresent: Boolean(aiReportReview.inputHash),
      reportBodyIncluded: false,
      message: sanitizeDiagnosticsText(aiReportReview.message),
      endpointIsLocalhost,
    },
    sessions: {
      listStatus: sessionBrowser.status,
      count: sessionBrowser.sessions.length,
      message: sanitizeDiagnosticsText(sessionBrowser.message),
    },
  };
  return `${JSON.stringify(bundle, null, 2)}\n`;
}

function countDiagnosticsListEntries(value: string): number {
  return value
    .split(/[\n,]/)
    .map((entry) => entry.trim())
    .filter(Boolean).length;
}

function sanitizeDiagnosticsText(value: string): string {
  return value
    .replace(/[A-Za-z]:\\[^\s`"'<>]+/g, "[redacted local path]")
    .replace(/\/(?:Users|home)\/[^\s`"'<>]+/gi, "[redacted local path]")
    .replace(/\b([A-Z0-9_]*(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD))\s*[:=]\s*[^\s,;`"'<>]+/gi, "$1=[redacted]")
    .replace(/\b(password|passwd|pwd|token|api[_-]?key|secret)\s*[:=]\s*[^\s,;`"'<>]+/gi, "$1=[redacted]")
    .replace(/\bBearer\s+[A-Za-z0-9._~+/=-]+/g, "Bearer [redacted]")
    .replace(/\b(?:sk|ghp|github_pat)_[A-Za-z0-9_=-]{8,}\b/g, "[redacted token]")
    .replace(/-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+PRIVATE KEY-----/g, "[redacted private key]")
    .trim();
}

function buildShareSafeReportMarkdown(report: AiReportPayload): string {
  const lines = [
    "# WorkTrace AI Share-Safe Report",
    "",
    "This report was generated locally from evidence-cited session summary data. Screenshot pixels, OCR snippets, raw event payloads, terminal transcripts and private artifact paths are omitted by default.",
    "",
    `Session: ${redactShareSafeText(report.sessionTitle)}`,
    `Confidence: ${Math.round(report.confidence * 100)}%`,
    "",
    "## Summary",
    "",
    `- ${shareSafeClaimText(report.summary)}`,
  ];

  appendShareSafeSection(lines, "What I worked on", report.observedWork ?? []);
  appendShareSafeSection(lines, "Activity blocks", report.timeline);
  appendShareSafeSection(lines, "Blockers and interruptions", report.blockers);
  appendShareSafeSection(lines, "Context switches", report.contextSwitches ?? []);
  appendShareSafeSection(lines, "Unfinished work", report.unfinishedWork ?? []);
  appendShareSafeSection(lines, "Suggested continuation", report.continuationNotes ?? []);
  appendShareSafeSection(lines, "Important context", report.importantFiles);
  appendShareSafeSection(lines, "Commands", report.commands);

  lines.push(
    "",
    "## Sharing Safety",
    "",
    "- Screenshot images: omitted",
    "- OCR snippets: omitted",
    "- Raw events: omitted",
    "- Local paths and obvious secrets: redacted",
    "- Evidence references: IDs only",
  );

  return `${lines.join("\n")}\n`;
}

function appendShareSafeSection(
  lines: string[],
  title: string,
  claims: AiReportClaim[],
): void {
  if (claims.length === 0) {
    return;
  }
  lines.push("", `## ${title}`, "");
  for (const claim of claims) {
    lines.push(`- ${shareSafeClaimText(claim)}`);
    if (claim.evidenceEventIds.length > 0) {
      lines.push(`  - Evidence: ${claim.evidenceEventIds.map(redactEvidenceId).join(", ")}`);
    }
  }
}

function shareSafeClaimText(claim: AiReportClaim): string {
  const parts = [claim.title, claim.text, claim.command, claim.path]
    .filter((value): value is string => Boolean(value?.trim()))
    .map(redactShareSafeText);
  return parts.join(" - ") || "Evidence-cited claim";
}

function redactShareSafeText(value: string): string {
  return value
    .replace(/[A-Za-z]:\\[^\s`"'<>]+/g, "[redacted local path]")
    .replace(/\/(?:Users|home)\/[^\s`"'<>]+/gi, "[redacted local path]")
    .replace(/\b([A-Z0-9_]*(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD))\s*[:=]\s*[^\s,;`"'<>]+/gi, "$1=[redacted]")
    .replace(/\b(password|passwd|pwd|token|api[_-]?key|secret)\s*[:=]\s*[^\s,;`"'<>]+/gi, "$1=[redacted]")
    .replace(/\bBearer\s+[A-Za-z0-9._~+/=-]+/g, "Bearer [redacted]")
    .replace(/\b(?:sk|ghp|github_pat)_[A-Za-z0-9_=-]{8,}\b/g, "[redacted token]")
    .replace(/-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+PRIVATE KEY-----/g, "[redacted private key]")
    .trim();
}

function redactEvidenceId(value: string): string {
  return value.replace(/[^\w:.-]/g, "");
}

function filterTimelineEvents(
  events: RawTimelineEvent[],
  filters: { date: string; query: string; source: EventFilter },
): RawTimelineEvent[] {
  const query = filters.query.trim().toLowerCase();
  return events.filter((event) => {
    if (filters.source !== "all" && event.source !== filters.source) {
      return false;
    }
    if (filters.date && event.timestamp.slice(0, 10) !== filters.date) {
      return false;
    }
    if (!query) {
      return true;
    }
    return searchableEventText(event).includes(query);
  });
}

function searchableEventText(event: RawTimelineEvent): string {
  return [
    event.id,
    event.timestamp,
    event.app,
    event.windowTitle,
    event.source,
    event.type,
  ]
    .join(" ")
    .toLowerCase();
}

function privacyTextEntries(value: string): string[] {
  const entries: string[] = [];
  for (const line of value.split(/\r?\n/)) {
    const entry = line.trim();
    if (!entry || entries.includes(entry)) {
      continue;
    }
    entries.push(entry);
  }
  return entries;
}

function readFirstRunOnboarding(): FirstRunOnboardingState {
  try {
    const rawValue = globalThis.localStorage?.getItem(onboardingStorageKey);
    if (!rawValue) {
      return { accepted: false, selectedPreset: null };
    }
    const parsed = JSON.parse(rawValue) as Partial<FirstRunOnboardingState>;
    if (
      parsed.accepted === true &&
      (parsed.selectedPreset === "private_safe" ||
        parsed.selectedPreset === "coding" ||
        parsed.selectedPreset === "study")
    ) {
      return {
        accepted: true,
        selectedPreset: parsed.selectedPreset,
      };
    }
  } catch {
    return { accepted: false, selectedPreset: null };
  }
  return { accepted: false, selectedPreset: null };
}

function writeFirstRunOnboarding(state: FirstRunOnboardingState) {
  try {
    globalThis.localStorage?.setItem(onboardingStorageKey, JSON.stringify(state));
  } catch {
    // Recording remains gated in memory when local storage is unavailable.
  }
}

export default App;
