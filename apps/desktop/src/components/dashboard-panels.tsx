import type {
  AiReportClaim,
  AiReportResult,
  RecorderSession,
  ScreenshotDeletionResult,
  SessionDeletionResult,
  SessionExportPreview,
  SessionScreenshot,
  SessionScreenshotPreviewResult,
  SessionSummary,
} from "../lib/tauri-client";
import type { ModelEndpointValidation } from "./dashboard-utils";
import { useState } from "react";

export type RecorderUiStatus =
  | "idle"
  | "loading"
  | "unavailable"
  | RecorderSession["status"];

export type EventFilter = "all" | "active_window" | "file_watcher" | "terminal_command_detector";

export type ExportReviewState =
  | { status: "idle" | "loading" | "unavailable"; message: string; export: null }
  | { status: "success"; message: string; export: SessionExportPreview };

export type ShareSafeExportState =
  | { status: "idle" | "loading" | "unavailable"; message: string; markdown: null }
  | { status: "success"; message: string; markdown: string };

export type DiagnosticsBundleState =
  | { status: "idle" | "unavailable"; message: string; bundleJson: null }
  | { status: "success"; message: string; bundleJson: string };

export type FolderReviewState =
  | { status: "idle" | "loading" | "unavailable"; message: string; path: null }
  | { status: "success"; message: string; path: string };

export type ScreenshotReviewState =
  | { status: "idle" | "loading" | "unavailable"; message: string; screenshots: [] }
  | { status: "success"; message: string; screenshots: SessionScreenshot[] };

export type ScreenshotPreviewState =
  | { status: "idle" | "loading" | "unavailable"; message: string; preview: null }
  | { status: "success"; message: string; preview: SessionScreenshotPreviewResult["preview"] };

export type ScreenshotDeletionState =
  | { status: "idle" | "loading" | "unavailable"; message: string; result: null }
  | { status: "success"; message: string; result: ScreenshotDeletionResult };

export type SessionBrowserState =
  | { status: "idle" | "loading" | "unavailable"; message: string; sessions: [] }
  | { status: "success"; message: string; sessions: SessionSummary[] };

export type SessionDeletionState =
  | { status: "idle" | "loading" | "unavailable"; message: string; result: null }
  | { status: "success"; message: string; result: SessionDeletionResult };

export type AiReportReviewState = AiReportResult;

export type PrivacyCenterState = {
  privateMode: boolean;
  clipboardSafeMode: boolean;
  allowlistText: string;
  blocklistText: string;
};

export type FileWatchSettingsState = {
  rootsText: string;
};

export type SessionDraftState = {
  title: string;
  goal: string;
  projectLabel: string;
  tagsText: string;
};

export type OnboardingPreset = "private_safe" | "coding" | "study";

export type FirstRunOnboardingState = {
  accepted: boolean;
  selectedPreset: OnboardingPreset | null;
};

export function FirstRunOnboardingPanel({
  onAccept,
  onSelectPreset,
  state,
}: {
  onAccept: () => void;
  onSelectPreset: (preset: OnboardingPreset) => void;
  state: FirstRunOnboardingState;
}) {
  if (state.accepted) {
    return (
      <section
        aria-label="First-run privacy setup"
        className="rounded-md border border-emerald-300 bg-emerald-50 p-4 text-emerald-950 shadow-sm"
      >
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide">
              First-run privacy setup
            </p>
            <h2 className="mt-1 text-xl font-semibold tracking-normal">Setup accepted</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6">
              Capture settings are ready. Review Privacy center before recording if this
              session needs stricter exclusions.
            </p>
          </div>
          <div className="rounded-md border border-current bg-white/70 px-3 py-2 text-sm font-semibold">
            {presetLabel(state.selectedPreset)}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section
      aria-label="First-run privacy setup"
      className={`rounded-md border p-5 shadow-sm ${
        state.accepted
          ? "border-emerald-300 bg-emerald-50 text-emerald-950"
          : "border-amber-300 bg-amber-50 text-amber-950"
      }`}
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide">
            First-run privacy setup
          </p>
          <h2 className="mt-2 text-2xl font-semibold tracking-normal">
            Start safely with local capture
          </h2>
          <p className="mt-3 max-w-3xl text-sm leading-6">
            WorkTrace stores evidence locally. Active-window metadata and screenshot sampling
            can run during recording, watched folders are metadata-only, terminal ingestion only
            happens when explicitly configured, and there is no cloud upload by default.
          </p>
        </div>
        <div className="rounded-md border border-current bg-white/70 px-3 py-2 text-sm font-semibold">
          {state.accepted ? "Setup accepted" : "Required before recording"}
        </div>
      </div>

      <ul className="mt-4 grid gap-2 text-sm leading-6 md:grid-cols-2">
        <li>Active app/window changes are metadata evidence.</li>
        <li>Screenshots stay local and can be reviewed or deleted.</li>
        <li>Watched folders record file metadata only, never file contents.</li>
        <li>Cloud AI stays off unless a development provider is explicitly enabled.</li>
      </ul>

      <details className="mt-4 rounded-md border border-current/20 bg-white/50 p-3">
        <summary className="cursor-pointer text-sm font-semibold">
          Review capture presets
        </summary>
        <div className="mt-3 grid gap-3 md:grid-cols-3">
          <OnboardingPresetButton
            active={state.selectedPreset === "private_safe"}
            description="Private mode on. Screenshots, file watching, OCR and report evidence are suppressed for new recordings."
            label="Private / Safe"
            onClick={() => onSelectPreset("private_safe")}
          />
          <OnboardingPresetButton
            active={state.selectedPreset === "coding"}
            description="Standard metadata capture for coding work. Add project folders below when you want file-change metadata."
            label="Coding session"
            onClick={() => onSelectPreset("coding")}
          />
          <OnboardingPresetButton
            active={state.selectedPreset === "study"}
            description="Standard metadata capture with conservative blocked apps. No terminal capture unless you configure it."
            label="Study / Work"
            onClick={() => onSelectPreset("study")}
          />
        </div>
      </details>

      <button
        className="mt-4 rounded-md border border-current bg-white/80 px-4 py-2 text-sm font-semibold transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
        onClick={onAccept}
        type="button"
      >
        {state.selectedPreset ? "Accept selected preset" : "Accept safe defaults"}
      </button>
    </section>
  );
}

function OnboardingPresetButton({
  active,
  description,
  label,
  onClick,
}: {
  active: boolean;
  description: string;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      aria-pressed={active}
      className={`rounded-md border p-3 text-left text-sm ${
        active
          ? "border-zinc-950 bg-zinc-950 text-white"
          : "border-current bg-white/70 text-inherit"
      }`}
      onClick={onClick}
      type="button"
    >
      <span className="block font-semibold">{label}</span>
      <span className="mt-2 block leading-5">{description}</span>
    </button>
  );
}

export function PrivacyCenterPanel({
  onChange,
  onSave,
  policyMessage,
  policyStatus,
  state,
}: {
  onChange: (state: PrivacyCenterState) => void;
  onSave: () => void;
  policyMessage: string;
  policyStatus: "idle" | "loading" | "available" | "unavailable";
  state: PrivacyCenterState;
}) {
  const [customAppListsOpen, setCustomAppListsOpen] = useState(false);
  const allowlist = privacyListEntries(state.allowlistText);
  const blocklist = privacyListEntries(state.blocklistText);
  const isPolicyBusy = policyStatus === "loading";

  return (
    <section
      aria-label="Privacy center"
      className="rounded-md border border-emerald-300 bg-emerald-50 p-5 text-emerald-950 shadow-sm"
    >
      <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">
        Privacy
      </p>
      <h2 className="mt-2 text-xl font-semibold tracking-normal">Privacy center</h2>
      <div className="mt-4 grid gap-3">
        <label className="flex items-start gap-3 rounded-md border border-emerald-200 bg-white p-3 text-sm font-semibold text-zinc-900">
          <input
            checked={state.privateMode}
            className="mt-1 size-4 accent-emerald-700"
            onChange={(event) => onChange({ ...state, privateMode: event.target.checked })}
            type="checkbox"
          />
          <span>
            Private mode
            <span className="mt-1 block text-xs font-medium leading-5 text-zinc-600">
              New recordings start with active-window, screenshot, file, OCR, and report evidence
              suppressed by the sidecar privacy policy.
            </span>
          </span>
        </label>
        <label className="flex items-start gap-3 rounded-md border border-emerald-200 bg-white p-3 text-sm font-semibold text-zinc-900">
          <input
            checked={state.clipboardSafeMode}
            className="mt-1 size-4 accent-emerald-700"
            onChange={(event) =>
              onChange({ ...state, clipboardSafeMode: event.target.checked })
            }
            type="checkbox"
          />
          <span>
            Clipboard safe mode
            <span className="mt-1 block text-xs font-medium leading-5 text-zinc-600">
              Clipboard content stays disabled; only metadata-safe capture paths are eligible.
            </span>
          </span>
        </label>
      </div>

      <div className="mt-4 rounded-md border border-emerald-200 bg-white p-3">
        <button
          aria-expanded={customAppListsOpen}
          className="text-sm font-semibold text-zinc-900"
          onClick={() => setCustomAppListsOpen((current) => !current)}
          type="button"
        >
          Custom app lists
        </button>
        <p className="mt-1 text-xs leading-5 text-zinc-600">
          Optional power-user controls for executable allow/block lists.
        </p>
        {customAppListsOpen ? (
          <div className="mt-3 grid gap-3">
            <label className="grid gap-2 text-sm font-semibold text-zinc-900">
              Allowed apps
              <textarea
                aria-label="Allowed apps"
                className="min-h-20 rounded-md border border-emerald-200 bg-white px-3 py-2 text-sm font-normal text-zinc-950 outline-none focus:ring-2 focus:ring-emerald-200"
                onChange={(event) => onChange({ ...state, allowlistText: event.target.value })}
                spellCheck={false}
                value={state.allowlistText}
              />
            </label>
            <label className="grid gap-2 text-sm font-semibold text-zinc-900">
              Blocked apps
              <textarea
                aria-label="Blocked apps"
                className="min-h-20 rounded-md border border-emerald-200 bg-white px-3 py-2 text-sm font-normal text-zinc-950 outline-none focus:ring-2 focus:ring-emerald-200"
                onChange={(event) => onChange({ ...state, blocklistText: event.target.value })}
                spellCheck={false}
                value={state.blocklistText}
              />
            </label>
          </div>
        ) : null}
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-2 text-xs text-zinc-700">
        <MetadataRow
          label="Recording mode"
          value={state.privateMode ? "Private" : "Standard"}
        />
        <MetadataRow
          label="Clipboard"
          value={state.clipboardSafeMode ? "Metadata only" : "Disabled"}
        />
        <MetadataRow label="Allowed apps" value={`${allowlist.length}`} />
        <MetadataRow label="Blocked apps" value={`${blocklist.length}`} />
      </dl>
      <div className="mt-4 flex flex-col gap-3 rounded-md border border-emerald-200 bg-white p-3">
        <p className="text-xs font-semibold leading-5 text-zinc-700">{policyMessage}</p>
        <button
          className="w-fit rounded-md border border-emerald-700 px-3 py-1.5 text-sm font-semibold text-emerald-900 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isPolicyBusy}
          onClick={onSave}
          type="button"
        >
          {isPolicyBusy ? "Saving policy" : "Save policy"}
        </button>
      </div>
      <p className="mt-4 rounded-md border border-amber-300 bg-amber-50 p-3 text-xs font-semibold leading-5 text-amber-950">
        Private mode applies only to new recordings. Saved allow and block lists apply through
        the sidecar capture policy on future starts and resumes.
      </p>
    </section>
  );
}

export function DiagnosticsBundlePanel({
  onCopy,
  onDownload,
  onPreview,
  state,
}: {
  onCopy: () => void;
  onDownload: () => void;
  onPreview: () => void;
  state: DiagnosticsBundleState;
}) {
  const hasBundle = state.status === "success";

  return (
    <section
      aria-label="Privacy-safe diagnostics"
      className="rounded-md border border-zinc-300 bg-white p-5 shadow-sm"
    >
      <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">
        Support
      </p>
      <h2 className="mt-2 text-xl font-semibold tracking-normal">
        Privacy-safe diagnostics
      </h2>
      <p className="mt-3 text-sm leading-6 text-zinc-700">
        Build a local support bundle that includes app health, runtime status and safe counts,
        while excluding screenshots, OCR text, raw timeline events, terminal commands, prompts,
        reports, file paths and secrets by default.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-semibold text-zinc-800 transition hover:border-zinc-500"
          onClick={onPreview}
          type="button"
        >
          Preview diagnostics
        </button>
        <button
          className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-semibold text-zinc-800 transition hover:border-zinc-500 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={!hasBundle}
          onClick={onCopy}
          type="button"
        >
          Copy JSON
        </button>
        <button
          className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-semibold text-zinc-800 transition hover:border-zinc-500 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={!hasBundle}
          onClick={onDownload}
          type="button"
        >
          Download JSON
        </button>
      </div>
      <div
        aria-live="polite"
        className={`mt-4 rounded-md border p-3 text-sm ${
          state.status === "unavailable"
            ? "border-amber-300 bg-amber-50 text-amber-950"
            : "border-zinc-200 bg-zinc-50 text-zinc-800"
        }`}
      >
        <p className="font-semibold text-zinc-950">{state.message}</p>
        {state.bundleJson ? (
          <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap rounded-md border border-zinc-200 bg-white p-3 text-xs leading-5 text-zinc-800">
            {state.bundleJson}
          </pre>
        ) : (
          <p className="mt-2 text-sm leading-6">
            Preview the bundle before copying or downloading it for a bug report.
          </p>
        )}
      </div>
    </section>
  );
}

export function RecorderControlPanel({
  className = "",
  eventCount,
  fileWatchRoots,
  fileWatchRootsText,
  message,
  onFileWatchRootsChange,
  onPause,
  onResume,
  onSessionDraftChange,
  onStart,
  onStop,
  onboardingRequired,
  privateMode,
  session,
  sessionDraft,
  status,
}: {
  className?: string;
  eventCount: number;
  fileWatchRoots: string[];
  fileWatchRootsText: string;
  message: string;
  onFileWatchRootsChange: (rootsText: string) => void;
  onPause: () => void;
  onResume: () => void;
  onSessionDraftChange: (draft: SessionDraftState) => void;
  onStart: () => void;
  onStop: () => void;
  onboardingRequired: boolean;
  privateMode: boolean;
  session: RecorderSession | null;
  sessionDraft: SessionDraftState;
  status: RecorderUiStatus;
}) {
  const isBusy = status === "loading";
  const canPause = session?.status === "recording" && !isBusy;
  const canResume = session?.status === "paused" && !isBusy;
  const canStop =
    (session?.status === "recording" || session?.status === "paused") && !isBusy;
  const isActive = session?.status === "recording" || session?.status === "paused";
  const isFinished = session?.status === "stopped" || session?.status === "interrupted";
  const primaryTitle = isActive
    ? session.status === "paused"
      ? "Session paused"
      : "Recording your work session"
    : isFinished
      ? "Your session is ready"
      : "Start a focused session";
  const primaryMessage = isActive
    ? "WorkTrace is collecting local activity evidence on this PC."
    : isFinished
      ? "Review what happened, create a summary, or inspect the supporting proof."
      : "WorkTrace quietly captures allowed local activity and creates a useful summary afterwards.";

  return (
    <article
      aria-label="Session controls"
      className={`rounded-lg border p-5 shadow-[0_14px_34px_rgba(15,23,42,0.055)] transition duration-150 ease-out ${recorderTone(status)} ${className}`}
    >
      <div className="flex h-full flex-col gap-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide opacity-75">
              Home
            </p>
            <h2 className="mt-1 text-2xl font-semibold tracking-normal">{primaryTitle}</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6">{primaryMessage}</p>
          </div>
          <div className="rounded-md border border-current/20 bg-white/60 px-3 py-2 text-xs font-semibold uppercase tracking-wide">
            {recorderLabel(status)}
          </div>
        </div>
        <div className="space-y-3">
          <p className="text-sm leading-6" aria-live="polite">{message}</p>
          <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
            <Metric label="Activities" value={eventCount.toString()} />
            <Metric label="Privacy" value={session?.privacyMode ?? "standard"} />
            <Metric label="Screenshots" value="Local" />
            <Metric label="Note" value={(session?.goal ?? sessionDraft.goal) ? "Added" : "Optional"} />
          </div>
          <div className="flex flex-wrap gap-2 pt-1">
            <button
              className="rounded-md border border-zinc-950 bg-zinc-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:border-current disabled:bg-transparent disabled:text-current disabled:opacity-60"
              disabled={
                onboardingRequired ||
                isBusy ||
                session?.status === "recording" ||
                session?.status === "paused"
              }
              onClick={onStart}
              type="button"
            >
              Start Session
            </button>
            <button
              className="rounded-md border border-current px-3 py-1.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
              disabled={!canPause}
              onClick={onPause}
              type="button"
            >
              Pause
            </button>
            <button
              className="rounded-md border border-current px-3 py-1.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
              disabled={!canResume}
              onClick={onResume}
              type="button"
            >
              Resume
            </button>
            <button
              className="rounded-md border border-current px-3 py-1.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
              disabled={!canStop}
              onClick={onStop}
              type="button"
            >
              Finish Session
            </button>
          </div>
          <details className="rounded-md border border-current/15 bg-white/45 p-3">
            <summary className="cursor-pointer text-sm font-semibold">
              Advanced options
            </summary>
            <div className="mt-3 grid gap-3">
              <label className="grid gap-2 text-sm font-semibold">
                Goal
                <input
                  aria-label="Goal"
                  className="rounded-md border border-current bg-white/70 px-3 py-2 text-sm font-normal text-zinc-950 outline-none disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={isBusy || isActive}
                  onChange={(event) =>
                    onSessionDraftChange({ ...sessionDraft, goal: event.target.value })
                  }
                  placeholder="Optional note for this session"
                  value={sessionDraft.goal}
                />
              </label>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="grid gap-2 text-sm font-semibold">
                  Session title
                  <input
                    className="rounded-md border border-current bg-white/70 px-3 py-2 text-sm font-normal text-zinc-950 outline-none disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={isBusy || isActive}
                    onChange={(event) =>
                      onSessionDraftChange({ ...sessionDraft, title: event.target.value })
                    }
                    placeholder="Morning coding session"
                    value={sessionDraft.title}
                  />
                </label>
                <label className="grid gap-2 text-sm font-semibold">
                  Project
                  <input
                    className="rounded-md border border-current bg-white/70 px-3 py-2 text-sm font-normal text-zinc-950 outline-none disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={isBusy || isActive}
                    onChange={(event) =>
                      onSessionDraftChange({ ...sessionDraft, projectLabel: event.target.value })
                    }
                    placeholder="workaudit-ai"
                    value={sessionDraft.projectLabel}
                  />
                </label>
              </div>
              <label className="grid gap-2 text-sm font-semibold">
                Tags
                <input
                  className="rounded-md border border-current bg-white/70 px-3 py-2 text-sm font-normal text-zinc-950 outline-none disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={isBusy || isActive}
                  onChange={(event) =>
                    onSessionDraftChange({ ...sessionDraft, tagsText: event.target.value })
                  }
                  placeholder="coding, tests, client-a"
                  value={sessionDraft.tagsText}
                />
              </label>
              <label className="grid gap-2 text-sm font-semibold">
                Project folders to watch
                <textarea
                  aria-label="File watch roots"
                  className="min-h-16 rounded-md border border-current bg-white/70 px-3 py-2 text-sm font-normal text-zinc-950 outline-none disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={isBusy || privateMode || session?.status === "recording"}
                  onChange={(event) => onFileWatchRootsChange(event.target.value)}
                  placeholder="C:\\path\\to\\project"
                  spellCheck={false}
                  value={fileWatchRootsText}
                />
              </label>
              <p className="text-xs font-medium leading-5">
                {privateMode
                  ? "Private mode suppresses file watching for new starts and resumes."
                  : `${fileWatchRoots.length} metadata-only root${fileWatchRoots.length === 1 ? "" : "s"} configured. Ignored folders and sensitive file names stay redacted.`}
              </p>
              {session?.id ? (
                <p className="break-all rounded-md border border-current/10 bg-white/50 p-2 font-mono text-xs">
                  Diagnostic session ID: {session.id}
                </p>
              ) : null}
            </div>
          </details>
          {onboardingRequired ? (
            <p className="rounded-md border border-amber-300 bg-amber-50 p-3 text-xs font-semibold leading-5 text-amber-950">
              Complete first-run privacy setup before recording.
            </p>
          ) : null}
        </div>
      </div>
    </article>
  );
}

export function ScreenshotEvidencePanel({
  canReview,
  deletionState,
  onDelete,
  onSelect,
  previewState,
  selectedScreenshotId,
  state,
}: {
  canReview: boolean;
  deletionState: ScreenshotDeletionState;
  onDelete: () => void;
  onSelect: (screenshotId: string) => void;
  previewState: ScreenshotPreviewState;
  selectedScreenshotId: string | null;
  state: ScreenshotReviewState;
}) {
  const selectedScreenshot =
    state.status === "success"
      ? state.screenshots.find((screenshot) => screenshot.id === selectedScreenshotId) ??
        state.screenshots[0] ??
        null
      : null;
  const isScreenshotLoading = state.status === "loading";
  const hasScreenshots = state.status === "success" && state.screenshots.length > 0;
  const visibleScreenshots = hasScreenshots ? state.screenshots.slice(0, 6) : [];
  const hiddenScreenshotCount = hasScreenshots
    ? Math.max(state.screenshots.length - visibleScreenshots.length, 0)
    : 0;
  const deleteDisabled =
    !canReview ||
    isScreenshotLoading ||
    !hasScreenshots ||
    deletionState.status === "loading";

  return (
    <section
      aria-label="Screenshot evidence"
      className="rounded-md border border-zinc-300 bg-white p-5 shadow-sm"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">
            Screenshots
          </p>
          <h2 className="mt-2 text-xl font-semibold tracking-normal">Captured moments</h2>
          <p className="mt-3 text-sm leading-6 text-zinc-700">{state.message}</p>
        </div>
        <button
          className="w-fit shrink-0 rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-semibold text-zinc-800 transition hover:border-zinc-500 disabled:cursor-not-allowed disabled:text-zinc-500 disabled:opacity-70"
          disabled={deleteDisabled}
          onClick={onDelete}
          type="button"
        >
          Delete screenshots
        </button>
      </div>
      <p className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm leading-6 text-emerald-950">
        Preview images and OCR snippets stay local; hosted development AI does not upload
        screenshots by default.
      </p>

      {deletionState.status !== "idle" ? (
        <div
          aria-live="polite"
          className={`mt-3 rounded-md border p-3 text-sm ${
            deletionState.status === "unavailable"
              ? "border-amber-300 bg-amber-50 text-amber-950"
              : "border-zinc-200 bg-zinc-50 text-zinc-800"
          }`}
        >
          <p className="font-semibold text-zinc-950">{deletionState.message}</p>
          {deletionState.result ? (
            <div className="mt-2 grid gap-2 text-xs sm:grid-cols-3">
              <Metric
                label="Rows"
                value={`${deletionState.result.deletedRows} row deleted`}
              />
              <Metric
                label="Files"
                value={`${deletionState.result.deletedFiles} file deleted`}
              />
              <Metric
                label="Missing"
                value={`${deletionState.result.missingFiles} missing`}
              />
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="mt-4 space-y-3">
        {state.status === "loading" ? (
          <p className="rounded-md border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-700">
            Loading screenshot metadata.
          </p>
        ) : null}
        {state.status === "success" && state.screenshots.length === 0 ? (
          <p className="rounded-md border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-700">
            No screenshot metadata for this session.
          </p>
        ) : null}
        {hasScreenshots ? (
          <>
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-semibold text-zinc-900">Visual moments</p>
            {hiddenScreenshotCount > 0 ? (
              <span className="text-xs font-semibold text-zinc-500">
                Showing 6 of {state.screenshots.length}
              </span>
            ) : null}
          </div>
          <ul className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
            {visibleScreenshots.map((screenshot, index) => (
              <li key={screenshot.id}>
                <button
                  className={`w-full rounded-md border p-3 text-left text-sm transition ${
                    selectedScreenshot?.id === screenshot.id
                      ? "border-zinc-950 bg-zinc-50"
                      : "border-zinc-200 bg-white hover:border-zinc-400"
                  }`}
                  onClick={() => onSelect(screenshot.id)}
                  type="button"
                >
                  <span className="flex items-center justify-between gap-3">
                    <span className="font-semibold text-zinc-950">
                      Screenshot {String(index + 1).padStart(3, "0")}
                    </span>
                    <span className="rounded-full border border-zinc-200 bg-white px-2 py-0.5 text-xs font-semibold text-zinc-600">
                      {screenshot.storedWidth} x {screenshot.storedHeight}
                    </span>
                  </span>
                  <span className="mt-2 block text-xs text-zinc-600">Local only</span>
                </button>
              </li>
            ))}
          </ul>
          {hiddenScreenshotCount > 0 ? (
            <details className="mt-3 rounded-md border border-zinc-200 bg-zinc-50 p-3">
              <summary className="cursor-pointer text-sm font-semibold text-zinc-800">
                View all {state.screenshots.length} captured moments
              </summary>
              <ul className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
                {state.screenshots.slice(6).map((screenshot, index) => (
                  <li key={screenshot.id}>
                    <button
                      className={`w-full rounded-md border p-3 text-left text-sm transition ${
                        selectedScreenshot?.id === screenshot.id
                          ? "border-zinc-950 bg-white"
                          : "border-zinc-200 bg-white hover:border-zinc-400"
                      }`}
                      onClick={() => onSelect(screenshot.id)}
                      type="button"
                    >
                      <span className="font-semibold text-zinc-950">
                        Screenshot {String(index + 7).padStart(3, "0")}
                      </span>
                      <span className="mt-2 block text-xs text-zinc-600">Local only</span>
                    </button>
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
          </>
        ) : null}
      </div>

      {selectedScreenshot ? (
        <div className="mt-4 rounded-md border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-800">
          <h3 className="font-semibold tracking-normal text-zinc-950">Local preview</h3>
          {previewState.status === "loading" ? (
            <p className="mt-3 rounded-md border border-zinc-200 bg-white p-3 text-sm text-zinc-700">
              Loading local screenshot preview.
            </p>
          ) : null}
          {previewState.status === "success" && previewState.preview ? (
            <div className="mt-3 space-y-3">
              <img
                alt={`Screenshot evidence ${previewState.preview.screenshotId}`}
                className="max-h-72 w-full rounded-md border border-zinc-300 object-contain"
                src={previewState.preview.imageDataUrl}
              />
              {previewState.preview.ocrSnippets.length > 0 ? (
                <div className="rounded-md border border-zinc-200 bg-white p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
                    OCR snippets
                  </p>
                  <ul className="mt-2 space-y-2">
                    {previewState.preview.ocrSnippets.map((snippet) => (
                      <li className="break-words text-sm text-zinc-800" key={snippet}>
                        {snippet}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="rounded-md border border-zinc-200 bg-white p-3 text-sm text-zinc-700">
                  No OCR snippets are stored for this screenshot.
                </p>
              )}
            </div>
          ) : null}
          {previewState.status === "unavailable" ? (
            <p className="mt-3 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950">
              {previewState.message}
            </p>
          ) : null}
          <dl className="mt-3 space-y-2">
            <MetadataRow label="Evidence ID" value={selectedScreenshot.id} />
            <MetadataRow
              label="Source event"
              value={selectedScreenshot.sourceEventId ?? "none"}
            />
            <MetadataRow
              label="Original"
              value={`${selectedScreenshot.width} x ${selectedScreenshot.height} original`}
            />
            <MetadataRow
              label="Stored"
              value={`${selectedScreenshot.storedWidth} x ${selectedScreenshot.storedHeight} stored`}
            />
            <MetadataRow label="Bytes" value={selectedScreenshot.byteSize.toString()} />
            <MetadataRow label="Path" value={selectedScreenshot.storagePath} />
            <MetadataRow label="Content hash" value={selectedScreenshot.contentHash} />
            <MetadataRow label="Visual hash" value={selectedScreenshot.visualHash} />
          </dl>
        </div>
      ) : null}
    </section>
  );
}

export function MetadataRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1">
      <dt className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{label}</dt>
      <dd className="break-all text-sm text-zinc-800">{value}</dd>
    </div>
  );
}

function aiReportProviderLabel(provider: AiReportReviewState["provider"]): string {
  if (provider === "gemini_gemma_dev") {
    return "Gemini/Gemma development cloud";
  }
  if (provider === "local_ollama") {
    return "Local Ollama";
  }
  return "Not reported";
}

function isDevelopmentCloudAiReport(aiReportState: AiReportReviewState): boolean {
  return aiReportState.provider === "gemini_gemma_dev";
}

export function ExportReviewPanel({
  aiReportState,
  canReview,
  canRequestAiReport,
  exportState,
  folderState,
  onCancelAiReport,
  onExportMarkdown,
  onExportRawJson,
  onGenerateAiReport,
  onOpenSessionFolder,
  onCopyShareSafeMarkdown,
  onDownloadShareSafeMarkdown,
  onPreviewShareSafeMarkdown,
  onSelectEvidence,
  selectedEvidenceId,
  shareSafeState,
}: {
  aiReportState: AiReportReviewState;
  canReview: boolean;
  canRequestAiReport: boolean;
  exportState: ExportReviewState;
  folderState: FolderReviewState;
  onCancelAiReport: () => void;
  onExportMarkdown: () => void;
  onExportRawJson: () => void;
  onGenerateAiReport: () => void;
  onOpenSessionFolder: () => void;
  onCopyShareSafeMarkdown: () => void;
  onDownloadShareSafeMarkdown: () => void;
  onPreviewShareSafeMarkdown: () => void;
  onSelectEvidence: (evidenceId: string) => void;
  selectedEvidenceId: string | null;
  shareSafeState: ShareSafeExportState;
}) {
  const isExportBusy = exportState.status === "loading";
  const isFolderBusy = folderState.status === "loading";
  const isAiReportRunning = aiReportState.status === "running" || aiReportState.status === "loading";
  const isDevelopmentCloud = isDevelopmentCloudAiReport(aiReportState);
  const controlsDisabled = !canReview || isExportBusy;
  const folderDisabled = !canReview || isFolderBusy;
  const canPreviewShareSafe = canReview && aiReportState.report !== null;
  const canUseShareSafeMarkdown = shareSafeState.status === "success";
  const aiGenerateLabel =
    aiReportState.status === "complete"
      ? isDevelopmentCloud
        ? "Regenerate Development Summary"
        : "Regenerate Summary"
      : isDevelopmentCloud
        ? "Create Development Summary"
        : "Create Summary";
  const aiCancelLabel = isDevelopmentCloud ? "Cancel Development Summary" : "Cancel Summary";
  const aiGenerateDisabled =
    !canReview || !canRequestAiReport || !aiReportState.canGenerate || isAiReportRunning;
  const hasProviderProvenance =
    aiReportState.provider ||
    aiReportState.requestedModel ||
    aiReportState.actualModel ||
    aiReportState.fallbackUsed;
  const aiPanelTone =
    aiReportState.status === "complete" || aiReportState.status === "ready"
      ? "border-emerald-300 bg-emerald-50 text-emerald-950"
      : aiReportState.status === "running" || aiReportState.status === "loading"
        ? "border-sky-300 bg-sky-50 text-sky-950"
        : "border-amber-300 bg-amber-50 text-amber-950";

  return (
    <section
      aria-label="Session summary and sharing"
      className="rounded-md border border-zinc-300 bg-white p-5 shadow-sm"
    >
      <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">Summary</p>
      <h2 className="mt-2 text-xl font-semibold tracking-normal">Session summary</h2>
      <p className="mt-3 text-sm leading-6 text-zinc-700">
        Create a useful work summary first, then choose a private local export or a reviewed
        shareable version.
      </p>

      <div className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 p-4 text-emerald-950">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
              Recommended for sharing
            </p>
            <h3 className="mt-1 text-lg font-semibold tracking-normal">
              Shareable summary
            </h3>
            <p className="mt-2 text-sm leading-6">
              Builds a local preview from the current AI summary, redacts sensitive text, omits
              screenshots, OCR snippets, raw events and private artifact paths by default.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 lg:justify-end">
            <button
              className="rounded-md border border-current px-3 py-1.5 text-sm font-semibold transition hover:bg-white/50 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={!canPreviewShareSafe || shareSafeState.status === "loading"}
              onClick={onPreviewShareSafeMarkdown}
              type="button"
            >
              Preview Shareable Summary
            </button>
            <button
              className="rounded-md border border-current px-3 py-1.5 text-sm font-semibold transition hover:bg-white/50 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={!canUseShareSafeMarkdown}
              onClick={onCopyShareSafeMarkdown}
              type="button"
            >
              Copy Summary
            </button>
            <button
              className="rounded-md border border-current px-3 py-1.5 text-sm font-semibold transition hover:bg-white/50 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={!canUseShareSafeMarkdown}
              onClick={onDownloadShareSafeMarkdown}
              type="button"
            >
              Download Summary
            </button>
          </div>
        </div>
        <div
          aria-live="polite"
          className={`mt-3 rounded-md border p-3 text-sm ${
            shareSafeState.status === "unavailable"
              ? "border-amber-300 bg-amber-50 text-amber-950"
              : "border-emerald-200 bg-white/80 text-emerald-950"
          }`}
        >
          <p className="font-semibold">{shareSafeState.message}</p>
          {shareSafeState.markdown ? (
            <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap rounded-md border border-emerald-200 bg-white p-3 text-xs leading-5 text-zinc-800">
              {shareSafeState.markdown}
            </pre>
          ) : (
            <p className="mt-2 text-sm">
              Generate an evidence-linked summary first, then preview the shareable version before
              copying or downloading it.
            </p>
          )}
        </div>
      </div>

      <div className="mt-4 rounded-md border border-zinc-200 bg-zinc-50 p-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
            Private local files
          </p>
          <h3 className="mt-1 text-lg font-semibold tracking-normal text-zinc-950">
            Detailed notes for your machine
          </h3>
          <p className="mt-2 text-sm leading-6 text-zinc-700">
            These exports can include raw event structure, local paths, evidence IDs and private
            session detail. Keep them local unless you review the contents.
          </p>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
        <button
          className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-semibold text-zinc-800 disabled:cursor-not-allowed disabled:text-zinc-500 disabled:opacity-70"
          disabled={controlsDisabled}
          onClick={onExportMarkdown}
          type="button"
        >
          Export Detailed Notes
        </button>
        <button
          className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-semibold text-zinc-800 disabled:cursor-not-allowed disabled:text-zinc-500 disabled:opacity-70"
          disabled={folderDisabled}
          onClick={onOpenSessionFolder}
          type="button"
        >
          Open session folder
        </button>
        <details className="w-full rounded-md border border-zinc-200 bg-white p-3">
          <summary className="cursor-pointer text-sm font-semibold text-zinc-800">
            Advanced export
          </summary>
          <button
            className="mt-3 rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-semibold text-zinc-800 disabled:cursor-not-allowed disabled:text-zinc-500 disabled:opacity-70"
            disabled={controlsDisabled}
            onClick={onExportRawJson}
            type="button"
          >
            Export raw JSON
          </button>
        </details>
        </div>
      </div>
      <p className="mt-3 text-sm leading-6 text-zinc-700">
        {canReview
          ? "Exports are deterministic local files generated from the current session."
          : "Start or select a session before exporting."}
      </p>
      <div
        aria-live="polite"
        className={`mt-4 rounded-md border p-3 text-sm ${
          exportState.status === "unavailable"
            ? "border-amber-300 bg-amber-50 text-amber-950"
            : "border-zinc-200 bg-zinc-50 text-zinc-800"
        }`}
      >
        <p className="font-semibold text-zinc-950">{exportState.message}</p>
        {exportState.export ? (
          <div className="mt-3 space-y-3">
            <p className="break-all text-xs uppercase tracking-wide text-zinc-500">
              {exportState.export.path}
            </p>
            {exportState.export.evidenceIds.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {exportState.export.evidenceIds.map((evidenceId) => (
                  <span
                    className="rounded-md border border-zinc-300 bg-white px-2 py-1 text-xs font-semibold text-zinc-700"
                    key={evidenceId}
                  >
                    {evidenceId}
                  </span>
                ))}
              </div>
            ) : null}
            <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-md border border-zinc-200 bg-white p-3 text-xs leading-5 text-zinc-800">
              {exportState.export.preview}
            </pre>
          </div>
        ) : (
          <p className="mt-2 text-zinc-700">No export preview available yet.</p>
        )}
      </div>
      <div
        aria-live="polite"
        className="mt-3 rounded-md border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-800"
      >
        <p className="font-semibold text-zinc-950">{folderState.message}</p>
        {folderState.path ? <p className="mt-2 break-all text-zinc-700">{folderState.path}</p> : null}
      </div>
      <div className={`mt-3 rounded-md border p-3 text-sm ${aiPanelTone}`}>
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-semibold tracking-normal">
            {aiReportHeading(aiReportState.status)}
          </h3>
          <button
            className="rounded-md border border-current px-3 py-1.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-70"
            disabled={aiGenerateDisabled}
            onClick={onGenerateAiReport}
            type="button"
          >
            {aiGenerateLabel}
          </button>
          {aiReportState.status === "running" ? (
            <button
              className="rounded-md border border-current px-3 py-1.5 text-sm font-semibold"
              onClick={onCancelAiReport}
              type="button"
            >
              {aiCancelLabel}
            </button>
          ) : null}
        </div>
        <p className="mt-2 leading-6">{aiReportState.message}</p>
        {isDevelopmentCloud ? (
          <p className="mt-3 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm font-semibold leading-6 text-amber-950">
            Development cloud mode sends redacted text evidence to Google infrastructure. Screenshots and raw artifacts stay local by default.
          </p>
        ) : null}
        {aiReportState.modelName ||
        hasProviderProvenance ||
        aiReportState.runtimeMs !== null ||
        aiReportState.inputHash ? (
          <dl className="mt-3 grid gap-2 text-xs text-zinc-700">
            {hasProviderProvenance ? (
              <MetadataRow label="Provider" value={aiReportProviderLabel(aiReportState.provider)} />
            ) : null}
            {aiReportState.modelName ? (
              <MetadataRow label="Model" value={aiReportState.modelName} />
            ) : null}
            {aiReportState.requestedModel ? (
              <MetadataRow label="Requested model" value={aiReportState.requestedModel} />
            ) : null}
            {aiReportState.actualModel ? (
              <MetadataRow label="Actual model" value={aiReportState.actualModel} />
            ) : null}
            {aiReportState.fallbackUsed ? (
              <MetadataRow label="Fallback" value="Fallback used" />
            ) : null}
            {aiReportState.runtimeMs !== null ? (
              <MetadataRow label="Run time" value={`${aiReportState.runtimeMs} ms`} />
            ) : null}
            {aiReportState.inputHash ? (
              <MetadataRow label="Input hash" value={aiReportState.inputHash} />
            ) : null}
          </dl>
        ) : null}
        {aiReportState.evidenceIds.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {aiReportState.evidenceIds.map((evidenceId) => (
              <EvidenceIdButton
                evidenceId={evidenceId}
                key={evidenceId}
                onSelect={onSelectEvidence}
                selected={selectedEvidenceId === evidenceId}
              />
            ))}
          </div>
        ) : null}
        {aiReportState.report ? (
          <AiReportPreview
            onSelectEvidence={onSelectEvidence}
            report={aiReportState.report}
            selectedEvidenceId={selectedEvidenceId}
          />
        ) : null}
      </div>
    </section>
  );
}

function aiReportHeading(status: AiReportReviewState["status"]) {
  if (status === "complete") {
    return "AI summary complete";
  }
  if (status === "ready") {
    return "AI summary ready";
  }
  if (status === "running" || status === "loading") {
    return "AI summary running";
  }
  if (status === "cancelled") {
    return "AI summary cancelled";
  }
  return "AI summary unavailable";
}

export function AiReportPreview({
  onSelectEvidence,
  report,
  selectedEvidenceId,
}: {
  onSelectEvidence: (evidenceId: string) => void;
  report: AiReportResult["report"];
  selectedEvidenceId: string | null;
}) {
  if (!report) {
    return null;
  }

  const observedWork = report.observedWork ?? [];
  const contextSwitches = report.contextSwitches ?? [];
  const unfinishedWork = report.unfinishedWork ?? [];
  const continuationNotes = report.continuationNotes ?? [];

  return (
    <div className="mt-3 rounded-md border border-zinc-200 bg-white p-3 text-zinc-800">
      <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
        {report.sessionTitle}
      </p>
      <p className="mt-2 text-sm leading-6">{claimText(report.summary)}</p>
      <AiReportSection
        claims={observedWork}
        onSelectEvidence={onSelectEvidence}
        selectedEvidenceId={selectedEvidenceId}
        title="What I worked on"
      />
      <AiReportSection
        claims={report.timeline}
        onSelectEvidence={onSelectEvidence}
        selectedEvidenceId={selectedEvidenceId}
        title="Activity blocks"
      />
      <AiReportSection
        claims={report.blockers}
        onSelectEvidence={onSelectEvidence}
        selectedEvidenceId={selectedEvidenceId}
        title="Blockers and interruptions"
      />
      <AiReportSection
        claims={contextSwitches}
        onSelectEvidence={onSelectEvidence}
        selectedEvidenceId={selectedEvidenceId}
        title="Context switches"
      />
      <AiReportSection
        claims={report.importantFiles}
        onSelectEvidence={onSelectEvidence}
        selectedEvidenceId={selectedEvidenceId}
        title="Important files and context"
      />
      <AiReportSection
        claims={unfinishedWork}
        onSelectEvidence={onSelectEvidence}
        selectedEvidenceId={selectedEvidenceId}
        title="Unfinished work"
      />
      <AiReportSection
        claims={continuationNotes}
        onSelectEvidence={onSelectEvidence}
        selectedEvidenceId={selectedEvidenceId}
        title="Suggested continuation"
      />
      {report.commands.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {report.commands.map((command, index) => (
            <li className="rounded-md border border-zinc-200 bg-zinc-50 p-2" key={index}>
              <p className="break-all text-xs font-semibold text-zinc-800">
                {claimText(command)}
              </p>
              <EvidenceIdList
                evidenceIds={command.evidenceEventIds}
                onSelect={onSelectEvidence}
                selectedEvidenceId={selectedEvidenceId}
              />
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function AiReportSection({
  claims,
  onSelectEvidence,
  selectedEvidenceId,
  title,
}: {
  claims: AiReportClaim[];
  onSelectEvidence: (evidenceId: string) => void;
  selectedEvidenceId: string | null;
  title: string;
}) {
  if (claims.length === 0) {
    return null;
  }

  return (
    <section className="mt-4">
      <h4 className="text-sm font-semibold tracking-normal text-zinc-950">{title}</h4>
      <ul className="mt-2 space-y-2">
        {claims.map((claim, index) => (
          <li className="rounded-md border border-zinc-200 bg-zinc-50 p-2" key={index}>
            {claim.title ? (
              <p className="text-xs font-semibold text-zinc-900">{claim.title}</p>
            ) : null}
            {claimBodyText(claim) ? (
              <p className="mt-1 break-words text-sm leading-5 text-zinc-800">
                {claimBodyText(claim)}
              </p>
            ) : null}
            <EvidenceIdList
              evidenceIds={claim.evidenceEventIds}
              onSelect={onSelectEvidence}
              selectedEvidenceId={selectedEvidenceId}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}

function EvidenceIdList({
  evidenceIds,
  onSelect,
  selectedEvidenceId,
}: {
  evidenceIds: string[];
  onSelect: (evidenceId: string) => void;
  selectedEvidenceId: string | null;
}) {
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {evidenceIds.map((evidenceId) => (
        <EvidenceIdButton
          evidenceId={evidenceId}
          key={evidenceId}
          onSelect={onSelect}
          selected={selectedEvidenceId === evidenceId}
        />
      ))}
    </div>
  );
}

function EvidenceIdButton({
  evidenceId,
  onSelect,
  selected,
}: {
  evidenceId: string;
  onSelect: (evidenceId: string) => void;
  selected: boolean;
}) {
  return (
    <button
      aria-label={`Show evidence ${evidenceId}`}
      className={`max-w-full rounded-md border px-2 py-1 text-left font-mono text-xs font-semibold ${
        selected
          ? "border-amber-400 bg-amber-50 text-amber-950"
          : "border-zinc-300 bg-white text-zinc-700"
      }`}
      title={evidenceId}
      onClick={() => onSelect(evidenceId)}
      type="button"
    >
      <span className="block max-w-56 overflow-hidden text-ellipsis whitespace-nowrap">
        {evidenceId}
      </span>
    </button>
  );
}

function claimText(claim: AiReportClaim) {
  return claim.text ?? claim.command ?? claim.title ?? claim.path ?? "Evidence-cited claim";
}

function claimBodyText(claim: AiReportClaim) {
  return claim.text ?? claim.command ?? claim.path ?? null;
}

export function ModelSettingsPanel({
  aiReportState,
  endpoint,
  endpointValidation,
  onEndpointChange,
}: {
  aiReportState: AiReportReviewState;
  endpoint: string;
  endpointValidation: ModelEndpointValidation;
  onEndpointChange: (endpoint: string) => void;
}) {
  const runtimeReady = aiReportState.status === "ready" || aiReportState.status === "complete";
  const isDevelopmentCloud = isDevelopmentCloudAiReport(aiReportState);
  const unavailableReason = endpointValidation.reason
    ? "Create Summary is unavailable because the endpoint is not localhost."
    : aiReportState.canGenerate
      ? null
      : unavailableReportReason(aiReportState);

  return (
    <section
      aria-label="Model settings"
      className="rounded-md border border-zinc-300 bg-white p-5 shadow-sm"
    >
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">
            Models
          </p>
          <h2 className="mt-2 text-2xl font-semibold tracking-normal">Model settings</h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-zinc-700">
            Local runtime setup is explicit. The desktop never downloads models or starts a model
            server from this panel.
          </p>
        </div>
        <label
          className="grid w-full gap-2 text-sm font-semibold text-zinc-800 lg:max-w-md"
          htmlFor="model-endpoint"
        >
          Local model endpoint
          <input
            aria-label="Local model endpoint"
            className={`rounded-md border px-3 py-2 text-sm font-normal text-zinc-950 outline-none focus:ring-2 ${
              endpointValidation.isValid
                ? "border-zinc-300 focus:ring-emerald-200"
                : "border-rose-300 focus:ring-rose-200"
            }`}
            id="model-endpoint"
            onChange={(event) => onEndpointChange(event.target.value)}
            spellCheck={false}
            type="url"
            value={endpoint}
          />
          <span
            className={`text-xs font-medium ${
              endpointValidation.isValid ? "text-zinc-600" : "text-rose-700"
            }`}
          >
            {endpointValidation.message}
          </span>
        </label>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <ModelRuntimeCard
          detail="Ollama-compatible HTTP runtime"
          label="Local endpoint"
          state={endpointValidation.isValid ? "Localhost only" : "Blocked"}
          tone={endpointValidation.isValid ? "safe" : "blocked"}
        />
        <ModelRuntimeCard
          detail={
            isDevelopmentCloud
              ? "Gemini API Gemma is development-only and requires explicit environment consent."
              : "Default report model"
          }
          label={isDevelopmentCloud ? "Development cloud provider" : "Gemma E2B"}
          state={runtimeReady ? "Ready" : "Unavailable"}
          tone={runtimeReady ? "safe" : "pending"}
        />
        <ModelRuntimeCard
          detail="Manual deep mode only"
          label="Gemma E4B"
          state="Manual"
          tone="pending"
        />
      </div>

      {unavailableReason ? (
        <p
          aria-live="polite"
          className="mt-4 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm font-semibold text-amber-950"
        >
          {unavailableReason}
        </p>
      ) : null}

      <div className="mt-5 rounded-md border border-zinc-200 bg-zinc-50 p-4">
        <h3 className="text-base font-semibold tracking-normal text-zinc-950">
          Beta local AI setup
        </h3>
        <ol className="mt-3 grid gap-2 text-sm leading-6 text-zinc-700">
          <li>1. Install and start a user-managed Ollama-compatible runtime on this Windows PC.</li>
          <li>
            2. Keep the runtime bound to localhost, usually{" "}
            <code className="rounded bg-white px-1.5 py-0.5 text-xs font-semibold">
              http://127.0.0.1:11434
            </code>
            .
          </li>
          <li>
            3. Install the default report model tag{" "}
            <code className="rounded bg-white px-1.5 py-0.5 text-xs font-semibold">
              gemma4:e2b
            </code>
            . WorkTrace will not download it automatically.
          </li>
          <li>
            4. Use deep mode only after manually installing{" "}
            <code className="rounded bg-white px-1.5 py-0.5 text-xs font-semibold">
              gemma4:e4b
            </code>{" "}
            and confirming laptop memory is acceptable.
          </li>
        </ol>
        <p className="mt-3 text-sm leading-6 text-zinc-700">
          Development Gemini/Gemma stays separate and explicit-enable only. The beta product path is
          local Ollama with evidence-cited reports.
        </p>
      </div>
    </section>
  );
}

export function ModelRuntimeCard({
  detail,
  label,
  state,
  tone,
}: {
  detail: string;
  label: string;
  state: string;
  tone: "safe" | "pending" | "blocked";
}) {
  const toneClass =
    tone === "safe"
      ? "border-emerald-300 bg-emerald-50 text-emerald-950"
      : tone === "blocked"
        ? "border-rose-300 bg-rose-50 text-rose-950"
        : "border-zinc-200 bg-zinc-50 text-zinc-800";

  return (
    <article className={`rounded-md border p-4 ${toneClass}`}>
      <p className="text-sm font-semibold tracking-normal">{label}</p>
      <p className="mt-2 text-xl font-semibold tracking-normal">{state}</p>
      <p className="mt-2 text-sm leading-6">{detail}</p>
    </article>
  );
}


function unavailableReportReason(aiReportState: AiReportReviewState): string {
  if (aiReportState.status === "runtime_unavailable") {
    return "Create Summary is unavailable because local AI is not ready.";
  }
  const normalized = aiReportState.message.trim();
  if (!normalized) {
    return "Create Summary is unavailable because local AI is not ready.";
  }
  return `Create Summary is unavailable because ${normalized.charAt(0).toLowerCase()}${normalized.slice(1)}`;
}

export function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-md border border-zinc-200 bg-white/70 p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{label}</p>
      <p className="mt-1 break-words text-base font-semibold tracking-normal text-zinc-950">
        {value}
      </p>
    </div>
  );
}

function presetLabel(preset: OnboardingPreset | null): string {
  if (preset === "private_safe") {
    return "Private / Safe";
  }
  if (preset === "coding") {
    return "Coding session";
  }
  if (preset === "study") {
    return "Study / Work";
  }
  return "Preset not selected";
}

function privacyListEntries(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((entry) => entry.trim())
    .filter(Boolean);
}


function recorderLabel(status: RecorderUiStatus): string {
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

function recorderTone(status: RecorderUiStatus): string {
  if (status === "recording") {
    return "border-emerald-300 bg-emerald-50 text-emerald-950";
  }
  if (status === "idle") {
    return "border-emerald-300 bg-emerald-50 text-emerald-950";
  }
  if (status === "paused" || status === "loading") {
    return "border-amber-300 bg-amber-50 text-amber-950";
  }
  if (status === "unavailable" || status === "interrupted") {
    return "border-rose-300 bg-rose-50 text-rose-950";
  }
  return "border-zinc-300 bg-zinc-50 text-zinc-950";
}

export function SessionBrowserPanel({
  deletionState,
  onDelete,
  onRefresh,
  state,
}: {
  deletionState: SessionDeletionState;
  onDelete: (sessionId: string) => void;
  onRefresh: () => void;
  state: SessionBrowserState;
}) {
  return (
    <section
      aria-label="Session history"
      className="rounded-md border border-zinc-300 bg-white p-5 shadow-sm"
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">
            History
          </p>
          <h2 className="mt-2 text-xl font-semibold tracking-normal">Session history</h2>
        </div>
        <button
          className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-semibold text-zinc-800 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={state.status === "loading"}
          onClick={onRefresh}
          type="button"
        >
          Refresh sessions
        </button>
      </div>

      <p className="mt-3 text-sm leading-6 text-zinc-700">{state.message}</p>

      {state.status === "loading" ? (
        <p className="mt-3 rounded-md border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-700">
          Loading session list.
        </p>
      ) : null}

      {state.status === "success" && state.sessions.length === 0 ? (
        <p className="mt-3 rounded-md border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-700">
          No sessions found.
        </p>
      ) : null}

      {state.status === "success" && state.sessions.length > 0 ? (
        <ul className="mt-3 grid gap-3">
          {state.sessions.map((session) => {
            const displayTitle = sessionDisplayTitle(session);
            const durationLabel = sessionDurationLabel(session);
            return (
            <li
              className="rounded-md border border-zinc-200 bg-white p-4 shadow-[0_8px_24px_rgba(15,23,42,0.035)] transition duration-150 ease-out hover:-translate-y-0.5 hover:border-emerald-200 hover:bg-emerald-50/30"
              key={session.id}
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0 space-y-1">
                  <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
                    {formatSessionDateTime(session.startedAt)}
                    {durationLabel ? ` · ${durationLabel}` : ""}
                  </p>
                  <h3 className="break-words text-base font-semibold text-zinc-950">
                    {displayTitle}
                  </h3>
                  <p className="text-sm text-zinc-700">
                    {session.projectLabel
                      ? `Worked in ${session.projectLabel}`
                      : "Local work session"}
                  </p>
                {session.goal ? (
                  <p className="break-words text-sm text-zinc-700">Goal: {session.goal}</p>
                ) : null}
                {session.projectLabel || session.tags.length > 0 ? (
                <div className="flex flex-wrap gap-2 text-xs text-zinc-600">
                  {session.projectLabel ? (
                    <span className="rounded-full border border-zinc-200 bg-white px-2 py-0.5 font-semibold">
                      {session.projectLabel}
                    </span>
                  ) : null}
                  {session.tags.map((tag) => (
                    <span
                      className="rounded-full border border-zinc-200 bg-white px-2 py-0.5"
                      key={tag}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
                ) : null}
                <div className="flex flex-wrap gap-3 text-xs text-zinc-500">
                  <span className="rounded-full border border-zinc-200 bg-white px-2 py-0.5 font-semibold text-zinc-700">
                    {friendlySessionStatus(session.status)}
                  </span>
                  <span>
                    {session.eventCount} activit{session.eventCount === 1 ? "y" : "ies"}
                  </span>
                  <span>
                    {session.screenshotCount} visual moment
                    {session.screenshotCount !== 1 ? "s" : ""}
                  </span>
                </div>
              </div>
                <details className="shrink-0 text-sm">
                  <summary className="cursor-pointer rounded-md border border-zinc-300 bg-white px-3 py-1.5 font-semibold text-zinc-800">
                    Manage
                  </summary>
                  <div className="mt-2 grid gap-2 rounded-md border border-zinc-200 bg-white p-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
                      Technical details
                    </p>
                    <p className="max-w-72 break-all font-mono text-xs text-zinc-500">
                      Session ID: {session.id}
                    </p>
                    <button
                      aria-label={`Delete session ${displayTitle}`}
                      className="rounded-md border border-rose-300 px-3 py-1.5 text-left text-sm font-semibold text-rose-800 hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={deletionState.status === "loading"}
                      onClick={() => onDelete(session.id)}
                      type="button"
                    >
                      Delete session
                    </button>
                  </div>
                </details>
              </div>
            </li>
          );
          })}
        </ul>
      ) : null}

      {deletionState.status !== "idle" ? (
        <div
          aria-live="polite"
          className={`mt-3 rounded-md border p-3 text-sm ${
            deletionState.status === "unavailable"
              ? "border-amber-300 bg-amber-50 text-amber-950"
              : "border-zinc-200 bg-zinc-50 text-zinc-800"
          }`}
        >
          <p className="font-semibold text-zinc-950">{deletionState.message}</p>
          {deletionState.result ? (
            <div className="mt-2 grid gap-2 text-xs sm:grid-cols-3">
              <Metric
                label="Session rows"
                value={`${deletionState.result.deletedSessionRows} session row deleted`}
              />
              <Metric
                label="Screenshot files"
                value={`${deletionState.result.deletedScreenshotFiles} screenshot file deleted`}
              />
              <Metric
                label="Artifact root"
                value={deletionState.result.removedArtifactRoot ? "Removed" : "Kept"}
              />
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function friendlySessionStatus(status: string): string {
  const normalized = status.toLowerCase();
  const labels: Record<string, string> = {
    finished: "Completed",
    recording: "Recording",
    paused: "Paused",
    stopped: "Completed",
    interrupted: "Interrupted",
  };
  return labels[normalized] ?? status;
}

function sessionDisplayTitle(session: SessionSummary): string {
  return session.title || session.goal || session.projectLabel || "Untitled work session";
}

function formatSessionDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Saved session";
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function sessionDurationLabel(session: SessionSummary): string | null {
  if (!session.endedAt) {
    return null;
  }
  const start = new Date(session.startedAt).getTime();
  const end = new Date(session.endedAt).getTime();
  if (Number.isNaN(start) || Number.isNaN(end) || end <= start) {
    return null;
  }
  const minutes = Math.max(1, Math.round((end - start) / 60_000));
  if (minutes < 60) {
    return `${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return remainder ? `${hours} hr ${remainder} min` : `${hours} hr`;
}
