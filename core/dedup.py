"""SQLite-based deduplication — tracks seen job IDs to avoid re-evaluation.

The database is created automatically on first run at the path configured in
``configs/settings.json`` (default: ``data/seen_jobs.db``).
"""

import logging
import os
import sqlite3

logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS seen_jobs (
    id       TEXT NOT NULL,
    platform TEXT NOT NULL,
    seen_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (id, platform)
)
"""


class DedupStore:
    """Persistent store for seen job IDs, backed by SQLite.

    Args:
        db_path: Path to the SQLite database file. Parent directories are
                 created automatically if they do not exist.
    """

    def __init__(self, db_path: str) -> None:
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(_CREATE_TABLE_SQL)
        self._conn.commit()
        logger.info("DedupStore initialised at %s", db_path)

    def is_seen(self, job_id: str, platform: str) -> bool:
        """Return True if this job ID has already been processed.

        Args:
            job_id: The platform-native job identifier.
            platform: The platform slug (e.g. ``"upwork"``).
        """
        row = self._conn.execute(
            "SELECT 1 FROM seen_jobs WHERE id = ? AND platform = ?",
            (job_id, platform),
        ).fetchone()
        return row is not None

    def mark_seen(self, job_id: str, platform: str) -> None:
        """Record a job ID as processed so it is skipped on future runs.

        Args:
            job_id: The platform-native job identifier.
            platform: The platform slug.
        """
        self._conn.execute(
            "INSERT OR IGNORE INTO seen_jobs (id, platform) VALUES (?, ?)",
            (job_id, platform),
        )
        self._conn.commit()
        logger.debug("Marked seen: %s [%s]", job_id, platform)

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()
        logger.debug("DedupStore connection closed")
