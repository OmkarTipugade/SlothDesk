"""
SlothDesk SQLite database module.

Manages the operations history table.  The database file is kept outside the
scanned directory to avoid recursively indexing SlothDesk's own records.
"""
from __future__ import annotations

import os
import sqlite3
from typing import Optional

_DB_PATH: Optional[str] = None
_INITIALIZED = False

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS operations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id    TEXT    NOT NULL,
    timestamp       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    source          TEXT    NOT NULL,
    destination     TEXT    NOT NULL,
    category        TEXT    NOT NULL DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'pending',
    error           TEXT    DEFAULT NULL,
    source_fingerprint TEXT DEFAULT NULL
);
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_operations_operation_id ON operations (operation_id);
"""


def init_db(db_path: str) -> None:
    """Create the database file and tables if they don't exist."""
    global _DB_PATH, _INITIALIZED

    _DB_PATH = db_path
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(_CREATE_TABLE)
        conn.execute(_CREATE_INDEX)
        conn.commit()
    finally:
        conn.close()

    _INITIALIZED = True


def get_connection() -> sqlite3.Connection:
    """Return a new connection to the initialized database."""
    if not _INITIALIZED or _DB_PATH is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
