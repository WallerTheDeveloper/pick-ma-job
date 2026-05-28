"""Tests for core.settings — per-pass model configuration (T05)."""

import json
import tempfile
from pathlib import Path

import pytest

from core.settings import (
    CVModelConfig,
    DEFAULT_CV_MODELS,
    PassModelConfig,
    Settings,
)


# ---------------------------------------------------------------------------
# PassModelConfig
# ---------------------------------------------------------------------------


def test_pass_model_config_is_frozen():
    """PassModelConfig is immutable."""
    cfg = PassModelConfig(provider="anthropic", model="test", temperature=0)
    with pytest.raises(AttributeError):
        cfg.model = "other"  # type: ignore[misc]


def test_pass_model_config_fields():
    cfg = PassModelConfig(provider="anthropic", model="claude-haiku-4-5-20251001", temperature=0.3)
    assert cfg.provider == "anthropic"
    assert cfg.model == "claude-haiku-4-5-20251001"
    assert cfg.temperature == 0.3


# ---------------------------------------------------------------------------
# CVModelConfig
# ---------------------------------------------------------------------------


def test_cv_model_config_fields():
    cfg = CVModelConfig(
        optimize=PassModelConfig(provider="anthropic", model="haiku", temperature=0),
        humanize=PassModelConfig(provider="anthropic", model="sonnet", temperature=0.3),
        keyword_audit=PassModelConfig(provider="anthropic", model="haiku", temperature=0),
    )
    assert cfg.optimize.model == "haiku"
    assert cfg.humanize.model == "sonnet"
    assert cfg.humanize.temperature == 0.3
    assert cfg.keyword_audit.model == "haiku"


def test_default_cv_models():
    """DEFAULT_CV_MODELS has expected values."""
    assert DEFAULT_CV_MODELS.optimize.provider == "anthropic"
    assert DEFAULT_CV_MODELS.optimize.model == "claude-haiku-4-5-20251001"
    assert DEFAULT_CV_MODELS.optimize.temperature == 0
    assert DEFAULT_CV_MODELS.humanize.model == "claude-sonnet-4-6-20250514"
    assert DEFAULT_CV_MODELS.humanize.temperature == 0.3
    assert DEFAULT_CV_MODELS.keyword_audit.model == "claude-haiku-4-5-20251001"
    assert DEFAULT_CV_MODELS.keyword_audit.temperature == 0


# ---------------------------------------------------------------------------
# Settings.from_json_file — cv_models parsing
# ---------------------------------------------------------------------------


def _write_settings(data: dict) -> Path:
    """Write a settings dict to a temp file and return the path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(data, f)
    f.close()
    return Path(f.name)


def test_from_json_file_parses_cv_models_dict():
    """cv_models with per-pass dicts (provider/model/temperature) parses correctly."""
    data = {
        "model": "claude-haiku-4-5-20251001",
        "temperature": 0,
        "cv_models": {
            "optimize": {
                "provider": "anthropic",
                "model": "claude-haiku-4-5-20251001",
                "temperature": 0,
            },
            "humanize": {
                "provider": "anthropic",
                "model": "claude-sonnet-4-6-20250514",
                "temperature": 0.3,
            },
            "keyword_audit": {
                "provider": "anthropic",
                "model": "claude-haiku-4-5-20251001",
                "temperature": 0,
            },
        },
    }
    path = _write_settings(data)
    settings = Settings.from_json_file(path)

    assert settings.cv_models.optimize.provider == "anthropic"
    assert settings.cv_models.optimize.model == "claude-haiku-4-5-20251001"
    assert settings.cv_models.optimize.temperature == 0
    assert settings.cv_models.humanize.model == "claude-sonnet-4-6-20250514"
    assert settings.cv_models.humanize.temperature == 0.3
    assert settings.cv_models.keyword_audit.model == "claude-haiku-4-5-20251001"
    assert settings.cv_models.keyword_audit.temperature == 0


def test_from_json_file_cv_models_missing_uses_defaults():
    """Missing cv_models section falls back to DEFAULT_CV_MODELS."""
    data = {
        "model": "claude-haiku-4-5-20251001",
        "temperature": 0,
    }
    path = _write_settings(data)
    settings = Settings.from_json_file(path)

    assert settings.cv_models.optimize.model == DEFAULT_CV_MODELS.optimize.model
    assert settings.cv_models.humanize.model == DEFAULT_CV_MODELS.humanize.model
    assert settings.cv_models.humanize.temperature == DEFAULT_CV_MODELS.humanize.temperature
    assert settings.cv_models.keyword_audit.model == DEFAULT_CV_MODELS.keyword_audit.model


def test_from_json_file_partial_cv_models_uses_defaults_for_missing():
    """Partially specified cv_models uses defaults for missing pass entries."""
    data = {
        "model": "claude-haiku-4-5-20251001",
        "temperature": 0,
        "cv_models": {
            "humanize": {
                "provider": "anthropic",
                "model": "claude-sonnet-4-6-20250514",
                "temperature": 0.5,
            },
        },
    }
    path = _write_settings(data)
    settings = Settings.from_json_file(path)

    # optimize and keyword_audit fall back to defaults
    assert settings.cv_models.optimize.model == DEFAULT_CV_MODELS.optimize.model
    assert settings.cv_models.keyword_audit.model == DEFAULT_CV_MODELS.keyword_audit.model
    # humanize uses the specified values
    assert settings.cv_models.humanize.model == "claude-sonnet-4-6-20250514"
    assert settings.cv_models.humanize.temperature == 0.5


def test_from_json_file_partial_pass_config_inherits_defaults():
    """A pass config with only 'model' inherits provider and temperature from defaults."""
    data = {
        "model": "claude-haiku-4-5-20251001",
        "temperature": 0,
        "cv_models": {
            "humanize": {
                "model": "my-custom-model",
            },
        },
    }
    path = _write_settings(data)
    settings = Settings.from_json_file(path)

    assert settings.cv_models.humanize.model == "my-custom-model"
    # Provider and temperature inherit from defaults
    assert settings.cv_models.humanize.provider == "anthropic"
    assert settings.cv_models.humanize.temperature == DEFAULT_CV_MODELS.humanize.temperature


def test_from_json_file_legacy_string_format():
    """Legacy format where cv_models values are plain model name strings."""
    data = {
        "model": "claude-haiku-4-5-20251001",
        "temperature": 0,
        "cv_models": {
            "optimize": "custom-optimize-model",
            "humanize": "custom-humanize-model",
            "keyword_audit": "custom-audit-model",
        },
    }
    path = _write_settings(data)
    settings = Settings.from_json_file(path)

    # Legacy string format: model name with fallback temperature from top-level
    assert settings.cv_models.optimize.model == "custom-optimize-model"
    assert settings.cv_models.optimize.temperature == 0  # from top-level temperature
    assert settings.cv_models.humanize.model == "custom-humanize-model"
    assert settings.cv_models.humanize.temperature == 0  # from top-level temperature


def test_from_json_file_legacy_nested_path():
    """Legacy nested path: models.cv_models is still supported."""
    data = {
        "model": "claude-haiku-4-5-20251001",
        "temperature": 0,
        "models": {
            "cv_models": {
                "optimize": "legacy-opt-model",
                "humanize": "legacy-hum-model",
                "keyword_audit": "legacy-aud-model",
            },
        },
    }
    path = _write_settings(data)
    settings = Settings.from_json_file(path)

    assert settings.cv_models.optimize.model == "legacy-opt-model"
    assert settings.cv_models.humanize.model == "legacy-hum-model"
    assert settings.cv_models.keyword_audit.model == "legacy-aud-model"


def test_from_json_file_different_provider_per_pass():
    """Each pass can specify a different provider."""
    data = {
        "model": "claude-haiku-4-5-20251001",
        "temperature": 0,
        "cv_models": {
            "optimize": {
                "provider": "anthropic",
                "model": "claude-haiku-4-5-20251001",
                "temperature": 0,
            },
            "humanize": {
                "provider": "anthropic",
                "model": "claude-sonnet-4-6-20250514",
                "temperature": 0.3,
            },
            "keyword_audit": {
                "provider": "anthropic",
                "model": "claude-haiku-4-5-20251001",
                "temperature": 0,
            },
        },
    }
    path = _write_settings(data)
    settings = Settings.from_json_file(path)

    assert settings.cv_models.optimize.provider == "anthropic"
    assert settings.cv_models.humanize.provider == "anthropic"
    assert settings.cv_models.keyword_audit.provider == "anthropic"


def test_from_json_file_actual_settings():
    """Parse the actual configs/settings.json file to ensure it's valid."""
    settings_path = Path(__file__).parent.parent / "configs" / "settings.json"
    settings = Settings.from_json_file(settings_path)

    assert settings.cv_models.optimize.provider == "anthropic"
    assert settings.cv_models.optimize.model == "claude-haiku-4-5-20251001"
    assert settings.cv_models.optimize.temperature == 0
    assert settings.cv_models.humanize.provider == "anthropic"
    assert settings.cv_models.humanize.model == "claude-sonnet-4-6-20250514"
    assert settings.cv_models.humanize.temperature == 0.3
    assert settings.cv_models.keyword_audit.provider == "anthropic"
    assert settings.cv_models.keyword_audit.model == "claude-haiku-4-5-20251001"
    assert settings.cv_models.keyword_audit.temperature == 0