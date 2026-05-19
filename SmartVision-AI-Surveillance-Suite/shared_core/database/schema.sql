CREATE TABLE IF NOT EXISTS cameras (
  camera_id TEXT PRIMARY KEY,
  module TEXT,
  name TEXT,
  source TEXT NOT NULL,
  enabled BOOLEAN DEFAULT TRUE,
  metadata_json JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT UNIQUE NOT NULL,
  module TEXT NOT NULL,
  camera_id TEXT NOT NULL,
  clip_path TEXT,
  snapshot_path TEXT,
  start_ts REAL NOT NULL,
  end_ts REAL,
  duration_seconds REAL,
  score REAL DEFAULT 0,
  tags JSON,
  metadata_json JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(camera_id) REFERENCES cameras(camera_id)
);

CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  alert_id TEXT UNIQUE NOT NULL,
  event_id TEXT,
  module TEXT NOT NULL,
  camera_id TEXT NOT NULL,
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  priority INTEGER DEFAULT 2,
  metadata_json JSON,
  created_ts REAL NOT NULL,
  acknowledged BOOLEAN DEFAULT FALSE,
  FOREIGN KEY(event_id) REFERENCES events(event_id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor TEXT DEFAULT 'system',
  action TEXT NOT NULL,
  target TEXT,
  metadata_json JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS module_health (
  module TEXT PRIMARY KEY,
  status TEXT DEFAULT 'unknown',
  last_heartbeat_ts REAL,
  metadata_json JSON
);
