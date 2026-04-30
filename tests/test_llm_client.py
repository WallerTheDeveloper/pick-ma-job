"""Tests for core.llm_client — Anthropic client is mocked throughout."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.llm_client import LLMClient, LLMError, _strip_json_fences

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_JSON = {"result": "ok", "score": 8}


def _make_client_mock(response_text: str) -> MagicMock:
    """Return a mock AsyncAnthropic whose messages.create() returns response_text."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=response_text)]
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)
    return mock_client


def _make_sequential_mock(texts: list[str]) -> MagicMock:
    """Return a mock whose messages.create() returns texts in sequence."""
    messages = []
    for t in texts:
        msg = MagicMock()
        msg.content = [MagicMock(text=t)]
        messages.append(msg)
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=messages)
    return mock_client


def _make_llm(response_text: str) -> LLMClient:
    return LLMClient(
        client=_make_client_mock(response_text),
        default_model="test-model",
    )


# ---------------------------------------------------------------------------
# _strip_json_fences
# ---------------------------------------------------------------------------


def test_strip_clean_json():
    assert _strip_json_fences(json.dumps(VALID_JSON)) == json.dumps(VALID_JSON)


def test_strip_json_fences():
    fenced = f"```json\n{json.dumps(VALID_JSON)}\n```"
    assert _strip_json_fences(fenced) == json.dumps(VALID_JSON)


def test_strip_plain_fences():
    fenced = f"```\n{json.dumps(VALID_JSON)}\n```"
    assert _strip_json_fences(fenced) == json.dumps(VALID_JSON)


def test_strip_fences_with_whitespace():
    fenced = f"  ```json\n{json.dumps(VALID_JSON)}\n```  "
    assert _strip_json_fences(fenced) == json.dumps(VALID_JSON)


# ---------------------------------------------------------------------------
# generate_json
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_json_clean():
    llm = _make_llm(json.dumps(VALID_JSON))
    result = await llm.generate_json(system="sys", user="usr")
    assert result == VALID_JSON


@pytest.mark.asyncio
async def test_generate_json_with_fences():
    fenced = f"```json\n{json.dumps(VALID_JSON)}\n```"
    llm = _make_llm(fenced)
    result = await llm.generate_json(system="sys", user="usr")
    assert result == VALID_JSON


@pytest.mark.asyncio
async def test_generate_json_invalid_raises_llm_error():
    llm = _make_llm("not json at all")
    with pytest.raises(LLMError, match="invalid JSON"):
        await llm.generate_json(system="sys", user="usr")


@pytest.mark.asyncio
async def test_generate_json_passes_model_and_max_tokens():
    mock_client = _make_client_mock(json.dumps(VALID_JSON))
    llm = LLMClient(client=mock_client, default_model="default-model")
    await llm.generate_json(system="sys", user="usr", model="override-model", max_tokens=2048)
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "override-model"
    assert call_kwargs["max_tokens"] == 2048
    assert call_kwargs["system"] == "sys"


@pytest.mark.asyncio
async def test_generate_json_uses_default_model():
    mock_client = _make_client_mock(json.dumps(VALID_JSON))
    llm = LLMClient(client=mock_client, default_model="default-model")
    await llm.generate_json(system="sys", user="usr")
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "default-model"


# ---------------------------------------------------------------------------
# generate_text
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_text_returns_raw():
    llm = _make_llm("hello world")
    result = await llm.generate_text(system="sys", user="usr")
    assert result == "hello world"


@pytest.mark.asyncio
async def test_generate_text_passes_params():
    mock_client = _make_client_mock("response")
    llm = LLMClient(client=mock_client, default_model="dm")
    await llm.generate_text(system="s", user="u", model="m", max_tokens=16)
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "m"
    assert call_kwargs["max_tokens"] == 16


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_text_retries_on_529_then_succeeds():
    """529 → retry → success (simulates CV service scenario from task spec)."""
    import anthropic

    error_529 = anthropic.APIStatusError(
        message="overloaded",
        response=MagicMock(status_code=529),
        body=None,
    )
    success_msg = MagicMock()
    success_msg.content = [MagicMock(text="ok")]

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=[error_529, success_msg])

    llm = LLMClient(client=mock_client, default_model="test")
    result = await llm.generate_text(system="sys", user="usr")
    assert result == "ok"
    assert mock_client.messages.create.call_count == 2


@pytest.mark.asyncio
async def test_generate_json_retries_on_429_then_succeeds():
    """429 → retry → success."""
    import anthropic

    error_429 = anthropic.APIStatusError(
        message="rate limited",
        response=MagicMock(status_code=429),
        body=None,
    )
    success_msg = MagicMock()
    success_msg.content = [MagicMock(text=json.dumps(VALID_JSON))]

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=[error_429, success_msg])

    llm = LLMClient(client=mock_client, default_model="test")
    result = await llm.generate_json(system="sys", user="usr")
    assert result == VALID_JSON
    assert mock_client.messages.create.call_count == 2


@pytest.mark.asyncio
async def test_generate_text_retries_on_503_then_succeeds():
    """503 → retry → success."""
    import anthropic

    error_503 = anthropic.APIStatusError(
        message="service unavailable",
        response=MagicMock(status_code=503),
        body=None,
    )
    success_msg = MagicMock()
    success_msg.content = [MagicMock(text="ok")]

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=[error_503, success_msg])

    llm = LLMClient(client=mock_client, default_model="test")
    result = await llm.generate_text(system="sys", user="usr")
    assert result == "ok"
    assert mock_client.messages.create.call_count == 2


@pytest.mark.asyncio
async def test_generate_text_exhausts_retries_raises_llm_error():
    """All 3 attempts fail with 529 → LLMError(retryable=True)."""
    import anthropic

    error_529 = anthropic.APIStatusError(
        message="overloaded",
        response=MagicMock(status_code=529),
        body=None,
    )

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=[error_529, error_529, error_529])

    llm = LLMClient(client=mock_client, default_model="test", default_max_retries=3)
    with pytest.raises(LLMError, match="529") as exc_info:
        await llm.generate_text(system="sys", user="usr")
    assert exc_info.value.retryable is True
    assert mock_client.messages.create.call_count == 3


@pytest.mark.asyncio
async def test_generate_text_non_retryable_error_raises_immediately():
    """400 (bad request) is not retryable — raises LLMError on first attempt."""
    import anthropic

    error_400 = anthropic.APIStatusError(
        message="bad request",
        response=MagicMock(status_code=400),
        body=None,
    )

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=error_400)

    llm = LLMClient(client=mock_client, default_model="test")
    with pytest.raises(LLMError, match="400") as exc_info:
        await llm.generate_text(system="sys", user="usr")
    assert exc_info.value.retryable is False
    assert mock_client.messages.create.call_count == 1


# ---------------------------------------------------------------------------
# LLMClient is frozen
# ---------------------------------------------------------------------------


def test_llm_client_is_immutable():
    llm = _make_llm("")
    with pytest.raises(Exception):
        llm.default_model = "other"  # type: ignore[misc]
