import type { RawTimelineEvent } from "../features/timeline/raw-timeline-simulation";
import type { SessionScreenshot } from "../lib/tauri-client";
import type { AiReportReviewState, ScreenshotReviewState } from "./dashboard-panels";

type ActivitySummaryItem = {
  id: string;
  time: string;
  title: string;
  detail: string;
};

type MomentSummaryItem = {
  id: string;
  label: string;
  time: string;
  app: string;
};

function formatClockTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value.slice(0, 5);
  }
  return new Intl.DateTimeFormat("en", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(parsed);
}

function summarizeActivity(event: RawTimelineEvent): ActivitySummaryItem {
  const sourceLabel =
    event.source === "active_window"
      ? `Used ${event.app}`
      : event.source === "file_watcher"
        ? "Updated a local file"
        : "Captured explicit terminal activity";
  const detail =
    event.windowTitle && event.windowTitle !== event.app
      ? event.windowTitle
      : "Local activity captured";

  return {
    id: event.id,
    time: formatClockTime(event.timestamp),
    title: sourceLabel,
    detail,
  };
}

function summarizeMoment(screenshot: SessionScreenshot, index: number): MomentSummaryItem {
  return {
    id: screenshot.id,
    label: `Moment ${String(index + 1).padStart(2, "0")}`,
    time: formatClockTime(screenshot.timestamp),
    app: "Captured screen moment",
  };
}

export function SessionReviewPanel({
  aiReportState,
  events,
  onOpenTechnicalDetails,
  onSelectScreenshot,
  screenshotState,
  selectedScreenshotId,
  technicalDetailsOpen,
}: {
  aiReportState: AiReportReviewState;
  events: RawTimelineEvent[];
  onOpenTechnicalDetails: () => void;
  onSelectScreenshot: (screenshotId: string) => void;
  screenshotState: ScreenshotReviewState;
  selectedScreenshotId: string | null;
  technicalDetailsOpen: boolean;
}) {
  const screenshots =
    screenshotState.status === "success" ? screenshotState.screenshots : [];
  const visibleMoments = screenshots.slice(0, 4).map(summarizeMoment);
  const visibleActivities = events.slice(0, 8).map(summarizeActivity);

  return (
    <section
      aria-label="Session moments"
      className="rounded-lg border border-zinc-200 bg-white p-5 shadow-[0_16px_38px_rgba(15,23,42,0.055)]"
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">
            Session review
          </p>
          <h2 className="mt-2 text-2xl font-semibold tracking-normal">What was captured</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-700">
            Review the local screen moments and app activity first. Technical proof, exports and
            provider diagnostics stay behind details.
          </p>
        </div>
        <button
          aria-expanded={technicalDetailsOpen}
          className="w-fit rounded-md border border-zinc-300 px-4 py-2 text-sm font-semibold text-zinc-800 transition hover:border-zinc-500"
          onClick={onOpenTechnicalDetails}
          type="button"
        >
          Technical details
        </button>
      </div>

      {aiReportState.status !== "complete" && !aiReportState.canGenerate ? (
        <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-950">
          <p className="font-semibold">Smart summary unavailable</p>
          <p>
            Set up local AI summaries in Settings to generate a private recap. Your screenshots and
            activity remain available locally.
          </p>
        </div>
      ) : null}

      <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,0.85fr)_minmax(0,1fr)]">
        <section aria-label="Captured moments" className="rounded-lg border border-zinc-200 p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold tracking-normal">Captured moments</h3>
              <p className="mt-1 text-sm text-zinc-600">
                {screenshots.length} visual {screenshots.length === 1 ? "moment" : "moments"} captured locally.
              </p>
            </div>
          </div>
          {screenshotState.status === "loading" ? (
            <p className="mt-3 rounded-md border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-700">
              Loading captured moments.
            </p>
          ) : null}
          {screenshots.length === 0 && screenshotState.status !== "loading" ? (
            <p className="mt-3 rounded-md border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-700">
              No visual moments were stored for this session.
            </p>
          ) : null}
          {visibleMoments.length > 0 ? (
            <ul className="mt-3 grid gap-2 sm:grid-cols-2">
              {visibleMoments.map((moment) => (
                <li key={moment.id}>
                  <button
                    className={`w-full rounded-md border p-3 text-left transition ${
                      selectedScreenshotId === moment.id
                        ? "border-zinc-950 bg-zinc-50"
                        : "border-zinc-200 bg-white hover:border-zinc-400"
                    }`}
                    onClick={() => onSelectScreenshot(moment.id)}
                    type="button"
                  >
                    <span className="block text-sm font-semibold text-zinc-950">
                      {moment.label}
                    </span>
                    <span className="mt-1 block text-sm text-zinc-700">
                      Captured at {moment.time}
                    </span>
                    <span className="mt-1 block text-xs font-semibold text-zinc-500">
                      {moment.app}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </section>

        <section aria-label="Activity" className="rounded-lg border border-zinc-200 p-4">
          <h3 className="text-lg font-semibold tracking-normal">Activity</h3>
          <p className="mt-1 text-sm text-zinc-600">
            {events.length} local {events.length === 1 ? "activity" : "activities"} captured.
          </p>
          {visibleActivities.length === 0 ? (
            <p className="mt-3 rounded-md border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-700">
              No activity entries are available for this session yet.
            </p>
          ) : (
            <ol className="mt-3 divide-y divide-zinc-100">
              {visibleActivities.map((activity) => (
                <li
                  className="grid gap-2 py-3 sm:grid-cols-[4.5rem_minmax(0,1fr)]"
                  key={activity.id}
                >
                  <time className="text-sm font-semibold text-zinc-500">{activity.time}</time>
                  <div>
                    <p className="text-sm font-semibold text-zinc-950">{activity.title}</p>
                    <p className="mt-1 truncate text-sm text-zinc-600">{activity.detail}</p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>
    </section>
  );
}
