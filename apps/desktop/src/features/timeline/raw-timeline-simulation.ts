export type RawTimelineEvent = {
  id: string;
  timestamp: string;
  app: string;
  windowTitle: string;
  source: "active_window" | "file_watcher" | "terminal_command_detector";
  type: "active_window_changed" | "file_changed" | "terminal_command";
};

export const rawTimelineSimulationEvents: RawTimelineEvent[] = [
  {
    id: "sess_active_window_001-active-window-000",
    timestamp: "2026-05-06T09:14:00+05:30",
    app: "VS Code",
    windowTitle: "workaudit-ai - App.tsx",
    source: "active_window",
    type: "active_window_changed",
  },
  {
    id: "sess_active_window_001-active-window-001",
    timestamp: "2026-05-06T09:16:00+05:30",
    app: "Chrome",
    windowTitle: "Issue #9 - GitHub",
    source: "active_window",
    type: "active_window_changed",
  },
  {
    id: "sess_active_window_001-active-window-002",
    timestamp: "2026-05-06T09:19:00+05:30",
    app: "Windows Terminal",
    windowTitle: "uv run --python 3.13 pytest",
    source: "active_window",
    type: "active_window_changed",
  },
  {
    id: "sess_active_window_001-active-window-003",
    timestamp: "2026-05-06T09:22:00+05:30",
    app: "VS Code",
    windowTitle: "raw_events_repository.py",
    source: "active_window",
    type: "active_window_changed",
  },
  {
    id: "sess_active_window_001-active-window-004",
    timestamp: "2026-05-06T09:24:00+05:30",
    app: "File Explorer",
    windowTitle: "worktrace session folder",
    source: "active_window",
    type: "active_window_changed",
  },
];
