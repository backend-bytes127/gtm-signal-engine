"""Push scored alerts to HubSpot as company properties + tasks."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AlertPayload:
    account_id: str
    company_name: str
    domain: str
    tier: str
    timing_score: float
    fit_score: int
    explanation: str


def _build_company_properties(alert: AlertPayload) -> dict[str, Any]:
    return {
        "properties": {
            "signal_tier": alert.tier,
            "signal_score": str(round(alert.timing_score, 1)),
            "signal_fit_score": str(alert.fit_score),
            "signal_explanation": alert.explanation[:500],
            "signal_last_scored": "today",
        }
    }


def _build_task_properties(alert: AlertPayload) -> dict[str, Any]:
    subject = f"[{alert.tier.upper()}] {alert.company_name} — Score {round(alert.timing_score, 1)}"
    body = (
        f"Signal Engine Alert\n\n"
        f"Company: {alert.company_name}\n"
        f"Domain: {alert.domain}\n"
        f"Tier: {alert.tier}\n"
        f"Score: {round(alert.timing_score, 1)}/100\n"
        f"ICP Fit: {alert.fit_score}/4\n\n"
        f"Why now: {alert.explanation}"
    )
    return {
        "properties": {
            "hs_task_subject": subject,
            "hs_task_body": body,
            "hs_task_status": "NOT_STARTED",
            "hs_task_priority": "HIGH" if alert.tier == "hot" else "MEDIUM",
        }
    }


class HubSpotClient:
    """HubSpot API client for pushing signal alerts."""

    def __init__(self, access_token: str | None = None):
        self.access_token = access_token or os.environ.get("HUBSPOT_ACCESS_TOKEN", "")
        self.base_url = "https://api.hubapi.com"
        self.dry_run = not self.access_token

        if self.dry_run:
            logger.warning("No HUBSPOT_ACCESS_TOKEN set — running in dry-run mode")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def push_alert(self, alert: AlertPayload) -> dict[str, Any]:
        company_props = _build_company_properties(alert)
        task_props = _build_task_properties(alert)

        if self.dry_run:
            logger.info(
                "[DRY RUN] Would push to HubSpot: %s (%s, score=%s)",
                alert.company_name, alert.tier, round(alert.timing_score, 1),
            )
            return {"status": "dry_run", "company": company_props, "task": task_props}

        import requests

        search_resp = requests.post(
            f"{self.base_url}/crm/v3/objects/companies/search",
            headers=self._headers(),
            json={
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "domain",
                        "operator": "EQ",
                        "value": alert.domain,
                    }]
                }],
                "limit": 1,
            },
            timeout=10,
        )
        search_resp.raise_for_status()
        results = search_resp.json().get("results", [])

        if results:
            company_id = results[0]["id"]
            update_resp = requests.patch(
                f"{self.base_url}/crm/v3/objects/companies/{company_id}",
                headers=self._headers(),
                json=company_props,
                timeout=10,
            )
            update_resp.raise_for_status()
        else:
            company_props["properties"]["domain"] = alert.domain
            company_props["properties"]["name"] = alert.company_name
            create_resp = requests.post(
                f"{self.base_url}/crm/v3/objects/companies",
                headers=self._headers(),
                json=company_props,
                timeout=10,
            )
            create_resp.raise_for_status()
            company_id = create_resp.json()["id"]

        task_resp = requests.post(
            f"{self.base_url}/crm/v3/objects/tasks",
            headers=self._headers(),
            json=task_props,
            timeout=10,
        )
        task_resp.raise_for_status()

        logger.info("Pushed alert for %s (company_id=%s)", alert.company_name, company_id)
        return {"status": "pushed", "company_id": company_id}


def push_alerts(alerts: list[AlertPayload], access_token: str | None = None) -> list[dict]:
    client = HubSpotClient(access_token)
    results = []
    for alert in alerts:
        try:
            result = client.push_alert(alert)
            results.append(result)
        except Exception:
            logger.exception("Failed to push alert for %s", alert.company_name)
            results.append({"status": "error", "company": alert.company_name})
    return results
