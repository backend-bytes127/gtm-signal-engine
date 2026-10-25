"""Record and query alert feedback from sales reps."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import duckdb

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "signal_engine.duckdb"

FEEDBACK_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS gold.alert_feedback (
    feedback_id VARCHAR PRIMARY KEY,
    account_id VARCHAR NOT NULL,
    alert_date DATE NOT NULL,
    outcome VARCHAR NOT NULL,
    rep_id VARCHAR,
    notes VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


@dataclass(frozen=True)
class FeedbackEntry:
    account_id: str
    alert_date: str
    outcome: str
    rep_id: str | None = None
    notes: str | None = None


def ensure_feedback_table(db_path: str | Path = DB_PATH) -> None:
    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE SCHEMA IF NOT EXISTS gold")
    conn.execute(FEEDBACK_TABLE_DDL)
    conn.close()


def record_feedback(entry: FeedbackEntry, db_path: str | Path = DB_PATH) -> str:
    valid_outcomes = {"accepted", "dismissed", "converted", "stale"}
    if entry.outcome not in valid_outcomes:
        raise ValueError(f"outcome must be one of {valid_outcomes}, got '{entry.outcome}'")

    feedback_id = str(uuid4())
    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE SCHEMA IF NOT EXISTS gold")
    conn.execute(FEEDBACK_TABLE_DDL)
    conn.execute(
        """INSERT INTO gold.alert_feedback VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            feedback_id,
            entry.account_id,
            entry.alert_date,
            entry.outcome,
            entry.rep_id,
            entry.notes,
            datetime.now(),
        ],
    )
    conn.close()
    logger.info("Recorded feedback %s for account %s: %s", feedback_id, entry.account_id, entry.outcome)
    return feedback_id


def get_feedback_summary(db_path: str | Path = DB_PATH) -> list[tuple]:
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = conn.sql("""
            SELECT outcome, count(*) as cnt
            FROM gold.alert_feedback
            GROUP BY outcome
            ORDER BY cnt DESC
        """).fetchall()
    except duckdb.CatalogException:
        rows = []
    conn.close()
    return rows


def get_signal_effectiveness(db_path: str | Path = DB_PATH) -> list[tuple]:
    """Which signal types lead to accepted vs dismissed alerts."""
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = conn.sql("""
            WITH feedback_with_events AS (
                SELECT
                    f.account_id,
                    f.outcome,
                    ce.event_type,
                    ce.signal_category
                FROM gold.alert_feedback f
                INNER JOIN main.cleaned_events ce ON f.account_id = ce.account_id
                WHERE ce.occurred_at >= f.alert_date - INTERVAL '14 days'
                  AND ce.occurred_at <= f.alert_date
            )
            SELECT
                event_type,
                COUNT(*) FILTER (WHERE outcome = 'accepted') as accepted,
                COUNT(*) FILTER (WHERE outcome = 'dismissed') as dismissed,
                COUNT(*) FILTER (WHERE outcome = 'converted') as converted,
                ROUND(
                    COUNT(*) FILTER (WHERE outcome IN ('accepted', 'converted')) * 100.0
                    / NULLIF(COUNT(*), 0), 1
                ) as effectiveness_pct
            FROM feedback_with_events
            GROUP BY event_type
            ORDER BY effectiveness_pct DESC
        """).fetchall()
    except duckdb.CatalogException:
        rows = []
    conn.close()
    return rows
