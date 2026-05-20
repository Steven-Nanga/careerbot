"""SQLite persistence for deduplicating seen jobs."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from config import DATABASE_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_jobs (
    job_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    organisation TEXT,
    url TEXT,
    source TEXT,
    score INTEGER,
    match_reason TEXT,
    matched_at TEXT,
    first_seen_at TEXT NOT NULL
);
"""

EXTRA_COLUMNS = {
    "score": "INTEGER",
    "match_reason": "TEXT",
    "matched_at": "TEXT",
}


@contextmanager
def connect(db_path: str = DATABASE_PATH) -> Iterator[sqlite3.Connection]:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(SCHEMA)
        ensure_columns(conn)
        conn.commit()
        yield conn
    finally:
        conn.close()


def ensure_columns(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(seen_jobs)").fetchall()}
    for column, definition in EXTRA_COLUMNS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE seen_jobs ADD COLUMN {column} {definition}")


def has_seen(conn: sqlite3.Connection, job_id: str) -> bool:
    row = conn.execute("SELECT 1 FROM seen_jobs WHERE job_id = ?", (job_id,)).fetchone()
    return row is not None


def mark_seen(conn: sqlite3.Connection, job: dict) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO seen_jobs
            (job_id, title, organisation, url, source, score, match_reason, matched_at, first_seen_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job["id"],
            job.get("title", ""),
            job.get("organisation", ""),
            job.get("url", ""),
            job.get("source", ""),
            job.get("match_score"),
            job.get("match_reason", ""),
            job.get("matched_at", ""),
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
