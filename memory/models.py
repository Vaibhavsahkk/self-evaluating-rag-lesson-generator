"""
SQLite schema setup for the cross-run learning store.
"""

import os
import sqlite3


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    final_status TEXT NOT NULL,
    total_attempts INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS failures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    attempt_number INTEGER NOT NULL,
    checkpoint_name TEXT NOT NULL,
    reason TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learned_rules (
    checkpoint_name TEXT PRIMARY KEY,
    rule_text TEXT NOT NULL,
    source_run_ids TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_failures_run_id
    ON failures(run_id);
CREATE INDEX IF NOT EXISTS idx_failures_checkpoint
    ON failures(checkpoint_name);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    """
    Initialize the database and create tables if they don't exist.
    Returns an open connection with Row factory enabled.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn
