import type { InterruptedSessionPreview, RecoveryAction } from "./recovery-simulation";

type RecoveryBannerProps = {
  sessions: InterruptedSessionPreview[];
};

const actionLabels: Record<RecoveryAction, string> = {
  review: "Review",
  export: "Export",
  delete: "Delete",
};

export function RecoveryBanner({ sessions }: RecoveryBannerProps) {
  if (sessions.length === 0) {
    return null;
  }

  const heading = sessions.length === 1 ? "Interrupted session found" : "Interrupted sessions found";

  return (
    <section
      aria-label="Interrupted session recovery"
      className="rounded-md border border-amber-300 bg-amber-50 p-5 text-amber-950 shadow-sm"
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-amber-700">
            Recovery
          </p>
          <h2 className="mt-2 text-2xl font-semibold tracking-normal">{heading}</h2>
        </div>
        <p className="max-w-xl text-sm leading-6">
          Partial events remain available for review, export, or deletion.
        </p>
      </div>

      <ul className="mt-4 divide-y divide-amber-200">
        {sessions.map((session) => (
          <li
            className="flex flex-col gap-4 py-4 md:flex-row md:items-center md:justify-between"
            key={session.id}
          >
            <div>
              <p className="font-semibold">{session.title}</p>
              <p className="mt-1 text-sm">
                <span>{formatEventCount(session.eventCount)} preserved</span> at{" "}
                <time dateTime={session.interruptedAt}>{formatRecoveryTime(session.interruptedAt)}</time>
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {session.availableActions.map((action) => (
                <button
                  className="rounded-md border border-current px-3 py-1.5 text-sm font-semibold"
                  key={action}
                  type="button"
                >
                  {actionLabels[action]}
                </button>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function formatEventCount(eventCount: number): string {
  return eventCount === 1 ? "1 event" : `${eventCount} events`;
}

function formatRecoveryTime(timestamp: string): string {
  return timestamp.slice(11, 16);
}
