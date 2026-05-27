"""Application settings — single validated source of truth.

Loaded once at startup via ``Settings.from_json_file()`` and stored on
``app.state.settings``.  All modules that previously called
``json.load("configs/settings.json")`` at import time now receive a
``Settings`` instance through constructor injection or FastAPI ``Depends()``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings

_DEFAULT_SETTINGS_PATH = Path(__file__).parent.parent / "configs" / "settings.json"


@dataclass(frozen=True)
class CVModelConfig:
    """Per-pass model configuration for CV customization.

    Each field can be either a simple model string (using the default provider)
    or a dict with 'provider' and 'model' keys for multi-provider routing.
    """

    optimize: str = "claude-haiku-4-5-20251001"
    humanize: str = "claude-sonnet-4-6-20250514"
    keyword_audit: str = "claude-haiku-4-5-20251001"


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration for a single LLM provider."""

    api_key_env: str
    default_max_retries: int = 6


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
    providers: dict[str, ProviderConfig] = {}
    cv_models: CVModelConfig = field(default_factory=CVModelConfig)

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

        # Parse providers section
        providers: dict[str, ProviderConfig] = {}
        for name, cfg in raw.pop("providers", {}).items():
            providers[name] = ProviderConfig(
                api_key_env=cfg.get("api_key_env", f"{name.upper()}_API_KEY"),
                default_max_retries=cfg.get("default_max_retries", 6),
            )

        # Parse cv_models section
        cv_models_raw = raw.pop("models", {}).pop("cv_models", {})
        if isinstance(cv_models_raw, dict):
            cv_models = CVModelConfig(
                optimize=cv_models_raw.get("optimize", "claude-haiku-4-5-20251001"),
                humanize=cv_models_raw.get("humanize", "claude-sonnet-4-6-20250514"),
                keyword_audit=cv_models_raw.get("keyword_audit", "claude-haiku-4-5-20251001"),
            )
        else:
            cv_models = CVModelConfig()

        data = {
            "claude_model": raw.get("model", "claude-haiku-4-5-20251001"),
            "claude_temperature": raw.get("temperature", 0),
            "score_threshold": raw.get("score_threshold", 5),
            "alert_threshold": raw.get("alert_threshold", 7),
            "evaluation_concurrency": raw.get("evaluation_concurrency", 8),
            "exclude_title_keywords": exclude_kw,
            "providers": providers,
            "cv_models": cv_models,
        }
        return cls(**data)
