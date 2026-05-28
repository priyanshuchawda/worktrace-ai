CREATE TABLE ocr_results (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  screenshot_id TEXT NOT NULL,
  source_event_id TEXT NULL,
  timestamp TEXT NOT NULL,
  text TEXT NOT NULL,
  confidence REAL NOT NULL,
  engine_name TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
  FOREIGN KEY (screenshot_id) REFERENCES screenshots(id) ON DELETE CASCADE,
  FOREIGN KEY (source_event_id) REFERENCES raw_events(id) ON DELETE SET NULL
);

CREATE INDEX idx_ocr_results_session_timestamp ON ocr_results (session_id, timestamp);
CREATE INDEX idx_ocr_results_screenshot ON ocr_results (screenshot_id);
