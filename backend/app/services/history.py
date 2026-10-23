"""
SlothDesk history service.

Persists operation records in SQLite and provides paginated retrieval.
Uses parameterized SQL exclusively — never interpolates user input.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.database import get_connection
from app.schemas import ActionResult, HistoryRecord

logger = logging.getLogger(__name__)


def record_operations(
    operation_id: str,
    results: List[ActionResult],
    categories: Optional[Dict[str, str]] = None,
    fingerprints: Optional[Dict[str, str]] = None,
) -> None:
    """
    Persist a batch of operation results to SQLite.

    Parameters
    ----------
    operation_id : unique identifier for this batch
    results : per-action results from the organizer
    categories : optional mapping of source -> category
    fingerprints : optional mapping of source -> SHA-256 fingerprint
    """
    if not results:
        return

    cats = categories or {}
    fps = fingerprints or {}

    conn = get_connection()
    try:
        with conn:
            for r in results:
                conn.execute(
                    """
                    INSERT INTO operations (operation_id, source, destination, category, status, error, source_fingerprint)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        operation_id,
                        r.source,
                        r.destination,
                        cats.get(r.source, ""),
                        r.status.value if hasattr(r.status, "value") else str(r.status),
                        r.error,
                        fps.get(r.source),
                    ),
                )
    finally:
        conn.close()


def get_history(
    page: int = 1,
    page_size: int = 50,
) -> tuple:
    """
    Retrieve paginated operation history, newest first.

    Returns (records, total_count).
    """
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 200:
        page_size = 200

    offset = (page - 1) * page_size

    conn = get_connection()
    try:
        # Total count
        row = conn.execute("SELECT COUNT(*) FROM operations").fetchone()
        total = row[0] if row else 0

        # Paginated results, newest first
        rows = conn.execute(
            """
            SELECT id, operation_id, timestamp, source, destination,
                   category, status, error, source_fingerprint
            FROM operations
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        ).fetchall()

        records = [
            HistoryRecord(
                id=r["id"],
                operation_id=r["operation_id"],
                timestamp=r["timestamp"],
                source=r["source"],
                destination=r["destination"],
                category=r["category"],
                status=r["status"],
                error=r["error"],
                source_fingerprint=r["source_fingerprint"],
            )
            for r in rows
        ]

        return records, total
    finally:
        conn.close()


def get_stats() -> Dict[str, object]:
    """
    Compute aggregate stats from persisted operation history.

    Returns actual counts — never invents data or reports session-only state.
    """
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM operations").fetchone()[0]
        success = conn.execute(
            "SELECT COUNT(*) FROM operations WHERE status = ?", ("success",)
        ).fetchone()[0]
        failed = conn.execute(
            "SELECT COUNT(*) FROM operations WHERE status IN (?, ?)",
            ("failed", "skipped"),
        ).fetchone()[0]

        # Category breakdown (successes only)
        rows = conn.execute(
            "SELECT category, COUNT(*) as cnt FROM operations WHERE status = ? AND category != '' GROUP BY category",
            ("success",),
        ).fetchall()
        categories = {r["category"]: r["cnt"] for r in rows}

        return {
            "total_operations": total,
            "successful_moves": success,
            "failed_moves": failed,
            "categories": categories,
        }
    finally:
        conn.close()
