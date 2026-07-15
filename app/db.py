import sqlite3
from datetime import datetime, timezone
from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  card_id TEXT UNIQUE NOT NULL,
  token TEXT UNIQUE NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  pin TEXT NOT NULL,
  preferred_name TEXT NOT NULL,
  helpful_actions TEXT NOT NULL,
  general_note TEXT NOT NULL,
  trusted_contact TEXT NOT NULL,
  private_plan TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  event_type TEXT NOT NULL,
  card_id TEXT,
  source_ip TEXT,
  outcome TEXT NOT NULL,
  details TEXT
);
CREATE TABLE IF NOT EXISTS failed_attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_epoch INTEGER NOT NULL,
  token TEXT NOT NULL,
  source_ip TEXT NOT NULL
);
"""

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db

def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    exists = db.execute("SELECT 1 FROM cards WHERE token=?", ("demo-token-001",)).fetchone()
    if not exists:
        db.execute("""
          INSERT INTO cards (
            card_id, token, active, pin, preferred_name,
            helpful_actions, general_note, trusted_contact, private_plan
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
          "demo-card", "demo-token-001", 1, "2468", "Jessica",
          "Speak calmly, stay nearby, and ask before contacting anyone.",
          "Synthetic information for a local cybersecurity prototype.",
          "Synthetic Contact — (555) 010-2026",
          "Synthetic private plan: move to a quiet setting and contact the trusted person."
        ))
        db.commit()

def log_event(event_type, card_id, source_ip, outcome, details=""):
    db = get_db()
    db.execute("""
      INSERT INTO audit_events (ts,event_type,card_id,source_ip,outcome,details)
      VALUES (?,?,?,?,?,?)
    """, (
      datetime.now(timezone.utc).isoformat(),
      event_type, card_id, source_ip, outcome, details
    ))
    db.commit()
