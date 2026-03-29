"""Telegram notifier — sends alerts for high-scoring job matches.

Uses the Telegram Bot API directly via ``requests`` (no third-party library).
Only sends a message if ``result.relevancy_score >= settings["alert_threshold"]``.

Message format uses Telegram Markdown (parse_mode=Markdown):

    🎯 *Score: 8/10* — Yes apply

    *Unity AR Developer — Indoor Navigation App*
    💰 $2,000 fixed
    📍 Client: United States

    Quick take: Strong AR Foundation match, clear scope.

    🔗 https://upwork.com/jobs/...
"""

import logging

import requests

from core.evaluator import EvaluationResult
from scrapers.base import NormalizedJob

logger = logging.getLogger(__name__)

_TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


class Notifier:
    """Sends Telegram alerts for jobs that meet the score threshold.

    Args:
        bot_token: Telegram Bot API token.
        chat_id: Destination chat or channel ID.
        alert_threshold: Minimum relevancy_score to trigger an alert.
    """

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        alert_threshold: int,
    ) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._alert_threshold = alert_threshold

    def notify(self, job: NormalizedJob, result: EvaluationResult) -> None:
        """Send a Telegram alert if the job meets the score threshold.

        Does nothing if ``result.relevancy_score < self.alert_threshold``.

        Args:
            job: The normalized job.
            result: The Claude evaluation result.
        """
        if result.relevancy_score < self._alert_threshold:
            logger.debug(
                "Job %s scored %d — below threshold %d, skipping alert",
                job.id,
                result.relevancy_score,
                self._alert_threshold,
            )
            return

        text = self._format_message(job, result)
        self._send(text)
        logger.info("Telegram alert sent for job %s (score=%d)", job.id, result.relevancy_score)

    def _format_message(
        self,
        job: NormalizedJob,
        result: EvaluationResult,
    ) -> str:
        """Build the Markdown-formatted Telegram message string."""
        # First line of recommendation (e.g. "Yes apply" before the dash)
        rec_short = result.recommendation.split("—")[0].strip()

        lines = [
            f"🎯 *Score: {result.relevancy_score}/10* — {rec_short}",
            "",
            f"*{_escape(job.title)}*",
        ]

        if job.budget:
            lines.append(f"💰 {_escape(job.budget)}")

        client_location = job.extras.get("client_location")
        if client_location:
            lines.append(f"📍 Client: {_escape(str(client_location))}")

        lines += [
            "",
            f"_{_escape(result.summary)}_",
            "",
            f"🔗 {job.url}",
        ]

        return "\n".join(lines)

    def _send(self, text: str) -> None:
        """POST the message to the Telegram Bot API.

        Raises:
            requests.HTTPError: If the API returns a non-2xx status.
        """
        url = _TELEGRAM_API_URL.format(token=self._bot_token)
        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()


def _escape(text: str) -> str:
    """Escape Telegram Markdown special characters in a string."""
    # In Telegram's legacy Markdown, only * _ ` [ need escaping
    for char in ("*", "_", "`", "["):
        text = text.replace(char, f"\\{char}")
    return text
