import type { RawTimelineEvent } from "./raw-timeline-simulation";

type RawTimelineProps = {
  events: RawTimelineEvent[];
  selectedEvidenceId: string | null;
  sourceStatus: "available" | "unavailable";
};

export function RawTimeline({ events, selectedEvidenceId, sourceStatus }: RawTimelineProps) {
  const orderedEvents = [...events].sort((first, second) =>
    first.timestamp.localeCompare(second.timestamp),
  );
  const isLive = sourceStatus === "available";
  const selectedEvent = selectedEvidenceId
    ? orderedEvents.find((event) => event.id === selectedEvidenceId)
    : null;

  return (
    <section
      aria-label="Raw timeline"
      className="overflow-hidden rounded-md border border-zinc-300 bg-white shadow-sm"
    >
      <div className="border-b border-zinc-200 bg-zinc-50/70 p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">
              {isLive ? "Live sidecar events" : "Fixture fallback"}
            </p>
            <h2 className="mt-2 text-2xl font-semibold tracking-normal">Evidence timeline</h2>
          </div>
          <span
            className={`w-fit rounded-full border px-3 py-1 text-xs font-semibold ${
              isLive
                ? "border-emerald-200 bg-emerald-50 text-emerald-900"
                : "border-amber-200 bg-amber-50 text-amber-900"
            }`}
          >
            {isLive ? "Local sidecar" : "Preview fixture"}
          </span>
        </div>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-zinc-700">
          {isLive
            ? "Active-window, file-change, and explicit terminal command events loaded from the local sidecar event stream."
            : "The local sidecar event stream is unavailable, so this preview is using deterministic fixture events."}
        </p>
      </div>

      <div className="grid gap-3 border-b border-zinc-200 p-5 sm:grid-cols-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Events</p>
          <p className="mt-1 text-2xl font-semibold text-zinc-950">{orderedEvents.length}</p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Selected</p>
          <p className="mt-1 truncate text-sm font-semibold text-zinc-950">
            {selectedEvent ? selectedEvent.app : "None"}
          </p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Stream</p>
          <p className="mt-1 text-sm font-semibold text-zinc-950">
            {isLive ? "Local evidence" : "Demo evidence"}
          </p>
        </div>
      </div>

      {orderedEvents.length === 0 ? (
        <p className="m-5 rounded-md border border-dashed border-zinc-300 bg-zinc-50 p-4 text-sm text-zinc-700">
          No raw events for this filter.
        </p>
      ) : (
        <ol className="divide-y divide-zinc-100">
          {orderedEvents.map((event) => {
            const isSelected = event.id === selectedEvidenceId;
            return (
              <li
                aria-current={isSelected ? "true" : undefined}
                aria-label={`Timeline event ${event.id}`}
                className={`grid gap-3 border-l-4 px-5 py-4 transition md:grid-cols-[5rem_minmax(10rem,13rem)_minmax(0,1fr)] ${
                  isSelected
                    ? "border-amber-400 bg-amber-50"
                    : "border-transparent hover:bg-zinc-50"
                }`}
                id={`timeline-event-${event.id}`}
                key={event.id}
              >
                <span className="sr-only">
                  {formatTimelineTime(event.timestamp)}
                  {event.app}
                  {event.source}
                  {event.windowTitle}
                </span>
                <time
                  className="text-sm font-semibold text-zinc-700"
                  dateTime={event.timestamp}
                  title={event.timestamp}
                >
                  {formatTimelineTime(event.timestamp)}
                </time>
                <div className="min-w-0">
                  <p className="truncate font-semibold text-zinc-950" title={event.app}>
                    {event.app}
                  </p>
                  <p className="mt-1 w-fit rounded-full border border-zinc-200 bg-white px-2 py-0.5 text-[0.7rem] font-semibold uppercase tracking-wide text-zinc-600">
                    {eventSourceLabel(event.source)}
                  </p>
                </div>
                <div className="min-w-0">
                  <p className="break-words text-sm leading-6 text-zinc-800">
                    {event.windowTitle}
                  </p>
                  <p
                    className="mt-2 max-w-full overflow-hidden text-ellipsis whitespace-nowrap rounded-md border border-zinc-200 bg-white px-2 py-1 font-mono text-xs text-zinc-500"
                    title={event.id}
                  >
                    {event.id}
                  </p>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

function formatTimelineTime(timestamp: string): string {
  return timestamp.slice(11, 16);
}

function eventSourceLabel(source: RawTimelineEvent["source"]): string {
  const labels: Record<RawTimelineEvent["source"], string> = {
    active_window: "Active window",
    file_watcher: "File",
    terminal_command_detector: "Terminal",
  };
  return labels[source];
}
