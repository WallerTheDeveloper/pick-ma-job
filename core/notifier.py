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
        ...

    def notify(self, job: NormalizedJob, result: EvaluationResult) -> None:
        """Send a Telegram alert if the job meets the score threshold.

        Does nothing if ``result.relevancy_score < self.alert_threshold``.

        Args:
            job: The normalized job.
            result: The Claude evaluation result.
        """
        ...

    def _format_message(
        self,
        job: NormalizedJob,
        result: EvaluationResult,
    ) -> str:
        """Build the Markdown-formatted Telegram message string."""
        ...

    def _send(self, text: str) -> None:
        """POST the message to the Telegram Bot API.

        Raises:
            requests.HTTPError: If the API returns a non-2xx status.
        """
        ...
