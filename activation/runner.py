"""CLI runner: load alerts from DuckDB and push to HubSpot + Slack."""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from activation.attio import push_alerts as push_attio_alerts
from activation.hubspot import AlertPayload, push_alerts as push_hubspot_alerts
from activation.slack import send_daily_digest, send_hot_alerts

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "signal_engine.duckdb"


def load_alerts(db_path: str | Path = DB_PATH) -> list[AlertPayload]:
    conn = duckdb.connect(str(db_path), read_only=True)
    rows = conn.sql("""
        select
            account_id, company_name, domain, tier,
            timing_score, fit_score, explanation
        from main.alerts
        order by score_rank
    """).fetchall()
    conn.close()

    return [
        AlertPayload(
            account_id=r[0],
            company_name=r[1],
            domain=r[2],
            tier=r[3],
            timing_score=r[4],
            fit_score=r[5],
            explanation=r[6],
        )
        for r in rows
    ]


def run() -> None:
    alerts = load_alerts()
    logger.info("Loaded %d alerts from DuckDB", len(alerts))

    if not alerts:
        logger.info("No alerts to push. Done.")
        return

    logger.info("Pushing to HubSpot...")
    hubspot_results = push_hubspot_alerts(alerts)
    pushed = sum(1 for r in hubspot_results if r["status"] in ("pushed", "dry_run"))
    logger.info("HubSpot: %d/%d pushed", pushed, len(alerts))

    logger.info("Pushing to Attio...")
    attio_results = push_attio_alerts(alerts)
    attio_pushed = sum(1 for r in attio_results if r["status"] in ("pushed", "dry_run"))
    logger.info("Attio: %d/%d pushed", attio_pushed, len(alerts))

    logger.info("Sending Slack digest...")
    digest_result = send_daily_digest(alerts)
    logger.info("Slack digest: %s", digest_result["status"])

    hot_alerts = [a for a in alerts if a.tier == "hot"]
    if hot_alerts:
        logger.info("Sending %d hot alerts to Slack...", len(hot_alerts))
        hot_results = send_hot_alerts(alerts)
        sent = sum(1 for r in hot_results if r["status"] != "error")
        logger.info("Slack hot alerts: %d/%d sent", sent, len(hot_alerts))

    logger.info("Activation complete.")


if __name__ == "__main__":
    run()
