"""Push scored alerts to Attio CRM as company notes + tasks."""
from __future__ import annotations

import logging
import os
from typing import Any

from activation.hubspot import AlertPayload

logger = logging.getLogger(__name__)


def _build_note(alert: AlertPayload) -> str:
    return (
        f"Signal Engine Alert\n\n"
        f"Tier: {alert.tier.upper()}\n"
        f"Timing Score: {round(alert.timing_score, 1)}/100\n"
        f"ICP Fit: {alert.fit_score}/4\n\n"
        f"Why now: {alert.explanation}"
    )


class AttioClient:
    """Attio REST API v2 client for pushing signal alerts."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("ATTIO_API_KEY", "")
        self.base_url = "https://api.attio.com/v2"
        self.dry_run = not self.api_key

        if self.dry_run:
            logger.warning("No ATTIO_API_KEY set — running in dry-run mode")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _find_company(self, domain: str) -> str | None:
        import requests

        resp = requests.post(
            f"{self.base_url}/objects/companies/records/query",
            headers=self._headers(),
            json={
                "filter": {
                    "domains": domain,
                },
                "limit": 1,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return data[0]["id"]["record_id"] if data else None

    def _create_company(self, alert: AlertPayload) -> str:
        import requests

        resp = requests.post(
            f"{self.base_url}/objects/companies/records",
            headers=self._headers(),
            json={
                "data": {
                    "values": {
                        "name": [{"value": alert.company_name}],
                        "domains": [{"domain": alert.domain}],
                    }
                }
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["data"]["id"]["record_id"]

    def _create_note(self, record_id: str, alert: AlertPayload) -> None:
        import requests

        title = f"[{alert.tier.upper()}] Score {round(alert.timing_score, 1)} — {alert.company_name}"
        requests.post(
            f"{self.base_url}/notes",
            headers=self._headers(),
            json={
                "data": {
                    "title": title,
                    "format": "plaintext",
                    "content": _build_note(alert),
                    "parent_object": "companies",
                    "parent_record_id": record_id,
                }
            },
            timeout=10,
        ).raise_for_status()

    def push_alert(self, alert: AlertPayload) -> dict[str, Any]:
        if self.dry_run:
            logger.info(
                "[DRY RUN] Would push to Attio: %s (%s, score=%s)",
                alert.company_name, alert.tier, round(alert.timing_score, 1),
            )
            return {"status": "dry_run", "company": alert.company_name}

        record_id = self._find_company(alert.domain)
        if record_id is None:
            record_id = self._create_company(alert)

        self._create_note(record_id, alert)

        logger.info("Pushed alert to Attio for %s (record=%s)", alert.company_name, record_id)
        return {"status": "pushed", "record_id": record_id}


def push_alerts(alerts: list[AlertPayload], api_key: str | None = None) -> list[dict]:
    client = AttioClient(api_key)
    results = []
    for alert in alerts:
        try:
            result = client.push_alert(alert)
            results.append(result)
        except Exception:
            logger.exception("Failed to push alert to Attio for %s", alert.company_name)
            results.append({"status": "error", "company": alert.company_name})
    return results
