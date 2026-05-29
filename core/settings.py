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
class PassModelConfig:
    """Per-pass model configuration: provider, model name, and temperature.

    Each pipeline pass (optimize, humanize, keyword_audit) is configured
    independently so you can route different passes to different models
    or providers without code changes.
    """

    provider: str
    model: str
    temperature: float


@dataclass(frozen=True)
class CVModelConfig:
    """Per-pass model configuration for CV customization.

    Each field maps a pipeline pass name to a ``PassModelConfig`` that
    specifies which provider, model, and temperature to use for that pass.
    """

    optimize: PassModelConfig
    humanize: PassModelConfig
    keyword_audit: PassModelConfig


# Default configuration used when ``cv_models`` is absent from settings.json.
DEFAULT_CV_MODELS = CVModelConfig(
    optimize=PassModelConfig(
        provider="anthropic",
        model="claude-haiku-4-5-20251001",
        temperature=0,
    ),
    humanize=PassModelConfig(
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        temperature=0.85,
    ),
    keyword_audit=PassModelConfig(
        provider="anthropic",
        model="claude-haiku-4-5-20251001",
        temperature=0,
    ),
)


def _parse_pass_config(
    raw: Any,
    pass_name: str,
    default: PassModelConfig,
    fallback_model: str,
    fallback_temperature: float,
) -> PassModelConfig:
    """Parse a single pass config from raw JSON data.

    Priority:
    1. If *raw* is a dict with provider/model/temperature, use it directly.
    2. If *raw* is a string (legacy format), treat it as the model name
       with the default provider and fallback temperature.
    3. Fall back to *default* config.
    """
    if isinstance(raw, dict):
        return PassModelConfig(
            provider=raw.get("provider", default.provider),
            model=raw.get("model", default.model),
            temperature=raw.get("temperature", default.temperature),
        )
    if isinstance(raw, str):
        # Legacy format: just a model name string
        return PassModelConfig(
            provider=default.provider,
            model=raw,
            temperature=fallback_temperature,
        )
    return default


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
    cv_models: CVModelConfig = field(default_factory=lambda: CVModelConfig(
        optimize=PassModelConfig(
            provider="anthropic",
            model="claude-haiku-4-5-20251001",
            temperature=0,
        ),
        humanize=PassModelConfig(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            temperature=0.85,
        ),
        keyword_audit=PassModelConfig(
            provider="anthropic",
            model="claude-haiku-4-5-20251001",
            temperature=0,
        ),
    ))

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

        # Top-level fallback values
        fallback_model = raw.get("model", "claude-haiku-4-5-20251001")
        fallback_temperature = raw.get("temperature", 0)

        # Parse cv_models section — supports both new dict format and legacy
        # flat string format.  The section can appear at the top level as
        # ``cv_models`` or nested under ``models.cv_models`` (legacy).
        cv_models_raw = raw.pop("cv_models", None)
        if cv_models_raw is None:
            # Try legacy nested path: models.cv_models
            cv_models_raw = raw.pop("models", {}).pop("cv_models", None)

        if isinstance(cv_models_raw, dict):
            cv_models = CVModelConfig(
                optimize=_parse_pass_config(
                    cv_models_raw.get("optimize"), "optimize",
                    DEFAULT_CV_MODELS.optimize,
                    fallback_model, fallback_temperature,
                ),
                humanize=_parse_pass_config(
                    cv_models_raw.get("humanize"), "humanize",
                    DEFAULT_CV_MODELS.humanize,
                    fallback_model, fallback_temperature,
                ),
                keyword_audit=_parse_pass_config(
                    cv_models_raw.get("keyword_audit"), "keyword_audit",
                    DEFAULT_CV_MODELS.keyword_audit,
                    fallback_model, fallback_temperature,
                ),
            )
        else:
            cv_models = DEFAULT_CV_MODELS

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
