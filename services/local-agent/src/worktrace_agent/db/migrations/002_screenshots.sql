CREATE TABLE screenshots (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  source_event_id TEXT NULL,
  timestamp TEXT NOT NULL,
  width INTEGER NOT NULL,
  height INTEGER NOT NULL,
  stored_width INTEGER NOT NULL,
  stored_height INTEGER NOT NULL,
  byte_size INTEGER NOT NULL,
  content_hash TEXT NOT NULL,
  visual_hash TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
  FOREIGN KEY (source_event_id) REFERENCES raw_events(id) ON DELETE SET NULL
);

CREATE INDEX idx_screenshots_session_timestamp ON screenshots (session_id, timestamp);
CREATE INDEX idx_screenshots_content_hash ON screenshots (content_hash);
