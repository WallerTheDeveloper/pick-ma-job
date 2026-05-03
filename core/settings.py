"""Application settings — single validated source of truth.

Loaded once at startup via ``Settings.from_json_file()`` and stored on
``app.state.settings``.  All modules that previously called
``json.load("configs/settings.json")`` at import time now receive a
``Settings`` instance through constructor injection or FastAPI ``Depends()``.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

_DEFAULT_SETTINGS_PATH = Path(__file__).parent.parent / "configs" / "settings.json"


class Settings(BaseSettings):
    """Validated application settings.

    Load from ``configs/settings.json`` via :meth:`from_json_file`.
    Tests can construct directly: ``Settings(score_threshold=3)``.
    """

    claude_model: str = "claude-haiku-4-5-20251001"
    claude_temperature: float = 0.0
    score_threshold: int = Field(default=5, ge=1, le=10)
    alert_threshold: int = Field(default=7, ge=1, le=10)
    evaluation_concurrency: int = Field(default=8, ge=1, le=50)
    exclude_title_keywords: list[str] = []

    @classmethod
    def from_json_file(cls, path: Path | str = _DEFAULT_SETTINGS_PATH) -> Settings:
        """Load settings from a JSON file and return a validated ``Settings``.

        Raises:
            FileNotFoundError: If the file does not exist.
            pydantic.ValidationError: If the JSON content is malformed.
        """
        path = Path(path)
        raw: dict = json.loads(path.read_text(encoding="utf-8"))

        pre_filters = raw.pop("pre_filters", {})
        exclude_kw = pre_filters.pop("exclude_title_keywords", [])

        data = {
            "claude_model": raw.get("model", "claude-haiku-4-5-20251001"),
            "claude_temperature": raw.get("temperature", 0),
            "score_threshold": raw.get("score_threshold", 5),
            "alert_threshold": raw.get("alert_threshold", 7),
            "evaluation_concurrency": raw.get("evaluation_concurrency", 8),
            "exclude_title_keywords": exclude_kw,
        }
        return cls(**data)
