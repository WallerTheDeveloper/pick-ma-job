# Task 05 — Per-Pass Model Configuration

**Size:** S  
**Status:** done  
**Priority:** MEDIUM  
**Depends on:** T01, T03

## Goal

Make the model and temperature for each pipeline pass configurable via `configs/settings.json`. This enables easy switching between models (e.g., Haiku → Sonnet, Anthropic → OpenAI) without code changes.

## Changes

### `configs/settings.json`

Add `cv_models` configuration:

```json
{
  "model": "claude-haiku-4-5-20251001",
  "temperature": 0,
  "alert_threshold": 7,
  "evaluation_concurrency": 3,
  "pre_filters": {
    "exclude_title_keywords": [...]
  },
  "cv_models": {
    "optimize": {
      "provider": "anthropic",
      "model": "claude-haiku-4-5-20251001",
      "temperature": 0
    },
    "humanize": {
      "provider": "anthropic",
      "model": "claude-sonnet-4-6-20250514",
      "temperature": 0.3
    },
    "keyword_audit": {
      "provider": "anthropic",
      "model": "claude-haiku-4-5-20251001",
      "temperature": 0
    }
  }
}
```

Each entry specifies:
- `provider` — which LLM provider to route to (currently only `"anthropic"`)
- `model` — the model identifier
- `temperature` — sampling temperature for that pass

### `core/settings.py`

Add `cv_models` field to `Settings`:

```python
@dataclass(frozen=True)
class CVModelConfig:
    provider: str
    model: str
    temperature: float

class Settings:
    # ... existing fields ...
    cv_models: dict[str, CVModelConfig]  # pass_name -> config
```

Update `load_settings()` to parse the new section with defaults:

```python
# Defaults if cv_models is absent from config
DEFAULT_CV_MODELS = {
    "optimize": CVModelConfig(provider="anthropic", model="claude-haiku-4-5-20251001", temperature=0),
    "humanize": CVModelConfig(provider="anthropic", model="claude-sonnet-4-6-20250514", temperature=0.3),
    "keyword_audit": CVModelConfig(provider="anthropic", model="claude-haiku-4-5-20251001", temperature=0),
}
```

### `core/llm_client.py` / MultiModelLLMClient

The `MultiModelLLMClient` built in T01 uses `for_pass("humanize")` etc. Those pass names correspond to the keys in `cv_models`. When `create_provider()` and `MultiModelLLMClient` are constructed in `api/deps.py`, they read from `Settings.cv_models` to build per-pass `LLMClient` instances.

### Prompt Files vs Settings

**Prompt files** (`cv_customize.json`, `cv_humanize.json`, `cv_keyword_audit.json`) specify their own `model` and `temperature` fields. These are used as overrides when the prompt file's values differ from `settings.json`.

Priority order:
1. If the prompt JSON file specifies `model` and `temperature`, those take precedence
2. Otherwise, fall back to `settings.json` `cv_models` config
3. Otherwise, fall back to `settings.json` top-level `model` and `temperature`

This allows prompt-level overrides without touching the global config.

## Files to Modify

| File | Change |
|------|--------|
| `configs/settings.json` | Add `cv_models` section |
| `core/settings.py` | Add `CVModelConfig` dataclass and `cv_models` field to `Settings` |
| `api/deps.py` | Build `MultiModelLLMClient` from `Settings.cv_models` |

## Success Criteria

- [x] `settings.json` has `cv_models` section with optimize, humanize, and keyword_audit entries
- [x] `Settings` class parses `cv_models` with defaults
- [x] Changing `cv_models.humanize.model` to a different model changes which model is used for Pass 3
- [x] Changing `cv_models.humanize.temperature` to 0.5 changes the sampling temperature for Pass 3
- [x] Prompt-level `model` and `temperature` override settings-level defaults
- [x] Missing `cv_models` in settings.json falls back to defaults (no crash)
