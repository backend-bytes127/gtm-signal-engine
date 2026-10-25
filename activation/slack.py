"""Send scored alert digests to Slack."""
from __future__ import annotations

import logging
import os
from typing import Any

from activation.hubspot import AlertPayload

logger = logging.getLogger(__name__)


def _build_digest_blocks(alerts: list[AlertPayload]) -> list[dict[str, Any]]:
    hot = [a for a in alerts if a.tier == "hot"]
    warm = [a for a in alerts if a.tier == "warm"]

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Signal Engine — Daily Digest"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{len(hot)} hot* and *{len(warm)} warm* accounts today.",
            },
        },
        {"type": "divider"},
    ]

    for alert in hot[:5]:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":fire: *{alert.company_name}* — "
                    f"Score {round(alert.timing_score, 1)} | Fit {alert.fit_score}/4\n"
                    f"_{alert.explanation}_"
                ),
            },
        })

    if len(hot) > 5:
        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"_+ {len(hot) - 5} more hot accounts_",
            }],
        })

    if warm:
        blocks.append({"type": "divider"})
        warm_names = ", ".join(a.company_name for a in warm[:10])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Warm accounts:* {warm_names}"
                + (f" _+ {len(warm) - 10} more_" if len(warm) > 10 else ""),
            },
        })

    return blocks


def _build_hot_alert_blocks(alert: AlertPayload) -> list[dict[str, Any]]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":rotating_light: *New Hot Account*\n\n"
                    f"*{alert.company_name}* ({alert.domain})\n"
                    f"Score: *{round(alert.timing_score, 1)}* | Fit: *{alert.fit_score}/4* | Tier: *{alert.tier}*\n\n"
                    f">{alert.explanation}"
                ),
            },
        },
    ]


class SlackClient:
    """Slack client for sending signal alert notifications."""

    def __init__(self, webhook_url: str | None = None, bot_token: str | None = None):
        self.webhook_url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL", "")
        self.bot_token = bot_token or os.environ.get("SLACK_BOT_TOKEN", "")
        self.dry_run = not self.webhook_url and not self.bot_token

        if self.dry_run:
            logger.warning("No Slack credentials set — running in dry-run mode")

    def send_digest(self, alerts: list[AlertPayload], channel: str = "#signal-alerts") -> dict:
        blocks = _build_digest_blocks(alerts)

        if self.dry_run:
            logger.info("[DRY RUN] Would send digest with %d alerts to %s", len(alerts), channel)
            return {"status": "dry_run", "blocks": blocks}

        return self._post(channel, blocks)

    def send_hot_alert(self, alert: AlertPayload, channel: str = "#signal-alerts") -> dict:
        blocks = _build_hot_alert_blocks(alert)

        if self.dry_run:
            logger.info(
                "[DRY RUN] Would send hot alert for %s to %s",
                alert.company_name, channel,
            )
            return {"status": "dry_run", "blocks": blocks}

        return self._post(channel, blocks)

    def _post(self, channel: str, blocks: list[dict]) -> dict:
        if self.webhook_url:
            import requests

            resp = requests.post(
                self.webhook_url,
                json={"blocks": blocks},
                timeout=10,
            )
            resp.raise_for_status()
            return {"status": "sent_via_webhook"}

        from slack_sdk import WebClient

        client = WebClient(token=self.bot_token)
        resp = client.chat_postMessage(channel=channel, blocks=blocks, text="Signal Engine Alert")
        return {"status": "sent_via_bot", "ts": resp["ts"]}


def _default_channel() -> str:
    return os.environ.get("SLACK_CHANNEL_ID", "#signal-alerts")


def send_daily_digest(alerts: list[AlertPayload], channel: str | None = None) -> dict:
    client = SlackClient()
    return client.send_digest(alerts, channel or _default_channel())


def send_hot_alerts(alerts: list[AlertPayload], channel: str | None = None) -> list[dict]:
    client = SlackClient()
    ch = channel or _default_channel()
    results = []
    hot = [a for a in alerts if a.tier == "hot"]
    for alert in hot:
        try:
            result = client.send_hot_alert(alert, ch)
            results.append(result)
        except Exception:
            logger.exception("Failed to send hot alert for %s", alert.company_name)
            results.append({"status": "error", "company": alert.company_name})
    return results
