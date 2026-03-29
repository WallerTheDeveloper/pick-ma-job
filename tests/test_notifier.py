"""Unit tests for core.notifier.Notifier.

requests is mocked throughout — no network calls made.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from core.evaluator import EvaluationResult
from core.notifier import Notifier, _escape
from scrapers.base import NormalizedJob

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BOT_TOKEN = "123456:ABC-test-token"
CHAT_ID = "-100123456789"
THRESHOLD = 7

FULL_JOB = NormalizedJob(
    id="job-001",
    platform="upwork",
    title="Unity AR Developer",
    description="Build an AR app.",
    url="https://upwork.com/jobs/job-001",
    budget="$2,000 fixed",
    extras={"client_location": "United States"},
)

HIGH_SCORE_RESULT = EvaluationResult({
    "relevancy_score": 8,
    "recommendation": "Yes apply — strong AR match",
    "summary": "Great AR Foundation fit with clear scope.",
    "evaluation": "Strong match.",
    "flags": "Verified client",
    "scratchpad": "",
})

LOW_SCORE_RESULT = EvaluationResult({
    "relevancy_score": 4,
    "recommendation": "Do not apply — poor fit",
    "summary": "Not relevant.",
    "evaluation": "Weak match.",
    "flags": "No budget",
    "scratchpad": "",
})


def _make_notifier() -> Notifier:
    return Notifier(BOT_TOKEN, CHAT_ID, THRESHOLD)


def _mock_post(status_code: int = 200) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = requests.HTTPError(response=mock_resp)
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp


# ---------------------------------------------------------------------------
# notify — threshold logic
# ---------------------------------------------------------------------------


def test_notify_sends_when_score_meets_threshold():
    notifier = _make_notifier()
    with patch("core.notifier.requests.post", return_value=_mock_post()) as mock_post:
        notifier.notify(FULL_JOB, HIGH_SCORE_RESULT)

    mock_post.assert_called_once()


def test_notify_sends_when_score_equals_threshold():
    result = EvaluationResult({**HIGH_SCORE_RESULT.raw, "relevancy_score": THRESHOLD})
    notifier = _make_notifier()
    with patch("core.notifier.requests.post", return_value=_mock_post()) as mock_post:
        notifier.notify(FULL_JOB, result)

    mock_post.assert_called_once()


def test_notify_skips_when_score_below_threshold():
    notifier = _make_notifier()
    with patch("core.notifier.requests.post") as mock_post:
        notifier.notify(FULL_JOB, LOW_SCORE_RESULT)

    mock_post.assert_not_called()


def test_notify_skips_when_score_one_below_threshold():
    result = EvaluationResult({**HIGH_SCORE_RESULT.raw, "relevancy_score": THRESHOLD - 1})
    notifier = _make_notifier()
    with patch("core.notifier.requests.post") as mock_post:
        notifier.notify(FULL_JOB, result)

    mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# _send — HTTP call details
# ---------------------------------------------------------------------------


def test_send_posts_to_correct_telegram_url():
    notifier = _make_notifier()
    with patch("core.notifier.requests.post", return_value=_mock_post()) as mock_post:
        notifier._send("hello")

    url = mock_post.call_args[0][0]
    assert BOT_TOKEN in url
    assert "sendMessage" in url


def test_send_payload_contains_chat_id_and_text():
    notifier = _make_notifier()
    with patch("core.notifier.requests.post", return_value=_mock_post()) as mock_post:
        notifier._send("test message")

    payload = mock_post.call_args.kwargs["json"]
    assert payload["chat_id"] == CHAT_ID
    assert payload["text"] == "test message"


def test_send_uses_markdown_parse_mode():
    notifier = _make_notifier()
    with patch("core.notifier.requests.post", return_value=_mock_post()) as mock_post:
        notifier._send("text")

    payload = mock_post.call_args.kwargs["json"]
    assert payload["parse_mode"] == "Markdown"


def test_send_disables_web_preview():
    notifier = _make_notifier()
    with patch("core.notifier.requests.post", return_value=_mock_post()) as mock_post:
        notifier._send("text")

    payload = mock_post.call_args.kwargs["json"]
    assert payload["disable_web_page_preview"] is True


def test_send_raises_on_http_error():
    notifier = _make_notifier()
    with patch("core.notifier.requests.post", return_value=_mock_post(status_code=400)):
        with pytest.raises(requests.HTTPError):
            notifier._send("text")


# ---------------------------------------------------------------------------
# _format_message — content
# ---------------------------------------------------------------------------


def test_format_message_contains_score():
    notifier = _make_notifier()
    msg = notifier._format_message(FULL_JOB, HIGH_SCORE_RESULT)
    assert "8/10" in msg


def test_format_message_contains_title():
    notifier = _make_notifier()
    msg = notifier._format_message(FULL_JOB, HIGH_SCORE_RESULT)
    assert "Unity AR Developer" in msg


def test_format_message_contains_budget():
    notifier = _make_notifier()
    msg = notifier._format_message(FULL_JOB, HIGH_SCORE_RESULT)
    assert "$2,000 fixed" in msg


def test_format_message_contains_client_location():
    notifier = _make_notifier()
    msg = notifier._format_message(FULL_JOB, HIGH_SCORE_RESULT)
    assert "United States" in msg


def test_format_message_contains_summary():
    notifier = _make_notifier()
    msg = notifier._format_message(FULL_JOB, HIGH_SCORE_RESULT)
    assert "Great AR Foundation fit with clear scope." in msg


def test_format_message_contains_url():
    notifier = _make_notifier()
    msg = notifier._format_message(FULL_JOB, HIGH_SCORE_RESULT)
    assert "https://upwork.com/jobs/job-001" in msg


def test_format_message_recommendation_before_dash_shown():
    notifier = _make_notifier()
    msg = notifier._format_message(FULL_JOB, HIGH_SCORE_RESULT)
    assert "Yes apply" in msg
    # The part after the dash is the detail — only short form shown in header
    assert "strong AR match" not in msg.splitlines()[0]


def test_format_message_omits_budget_line_when_none():
    job = NormalizedJob(
        id="j", platform="upwork", title="T", description="D",
        url="https://upwork.com/jobs/j", budget=None, extras={},
    )
    notifier = _make_notifier()
    msg = notifier._format_message(job, HIGH_SCORE_RESULT)
    assert "💰" not in msg


def test_format_message_omits_location_line_when_absent():
    job = NormalizedJob(
        id="j", platform="upwork", title="T", description="D",
        url="https://upwork.com/jobs/j", extras={},
    )
    notifier = _make_notifier()
    msg = notifier._format_message(job, HIGH_SCORE_RESULT)
    assert "📍" not in msg


# ---------------------------------------------------------------------------
# _escape
# ---------------------------------------------------------------------------


def test_escape_asterisk():
    assert _escape("bold*text") == "bold\\*text"


def test_escape_underscore():
    assert _escape("italic_text") == "italic\\_text"


def test_escape_backtick():
    assert _escape("code`snippet") == "code\\`snippet"


def test_escape_bracket():
    assert _escape("[link]") == "\\[link]"


def test_escape_plain_text_unchanged():
    assert _escape("hello world") == "hello world"


def test_escape_multiple_special_chars():
    result = _escape("*bold* and _italic_")
    assert result == "\\*bold\\* and \\_italic\\_"
