export type RecoveryAction = "review" | "export" | "delete";

export type InterruptedSessionPreview = {
  id: string;
  title: string;
  interruptedAt: string;
  eventCount: number;
  availableActions: RecoveryAction[];
};

export const recoverySimulationSessions: InterruptedSessionPreview[] = [
  {
    id: "sess_banner_001",
    title: "Interrupted review",
    interruptedAt: "2026-05-06T09:24:00+05:30",
    eventCount: 1,
    availableActions: ["review", "export", "delete"],
  },
];
