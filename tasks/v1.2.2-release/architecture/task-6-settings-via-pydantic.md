# Task 6 — Load Settings via Pydantic BaseSettings

**Size:** S  
**Status:** done  
**Priority:** MEDIUM

## Goal

Replace the ad-hoc `configs/settings.json` reads scattered at module import time with a single validated `Settings` object loaded once in the FastAPI lifespan and injected via `Depends()`.

## Problem

- `services/pipeline.py` and other modules parse `configs/settings.json` at import time
- Makes testing harder (can't override per test without monkey-patching the file)
- Import fails if the file is missing or malformed
- No schema — typos in keys are silent at startup

## Changes

**`core/settings.py`** — new file
```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        json_file="configs/settings.json",
        json_file_encoding="utf-8",
    )
    claude_model: str = "claude-sonnet-4-6"
    claude_temperature: float = 0.3
    score_threshold: int = Field(default=5, ge=1, le=10)
    alert_threshold: int = Field(default=7, ge=1, le=10)
    evaluation_concurrency: int = Field(default=8, ge=1, le=50)
    exclude_title_keywords: list[str] = []
```

**`main.py` lifespan**
```python
app.state.settings = Settings()
```

**`api/deps.py`**
```python
def get_settings(request: Request) -> Settings:
    return request.app.state.settings
```

**All callers** (`pipeline.py`, `evaluator.py`, etc.)
- Remove direct `json.load("configs/settings.json")` calls
- Accept `settings: Settings` via constructor or `Depends(get_settings)`

## Success Criteria

- Starting the app with a malformed `configs/settings.json` raises a clear `ValidationError` at startup, not mid-request
- Tests can override settings by constructing `Settings(score_threshold=3)` without touching the file
- `grep -r "settings.json"` in Python files returns only `core/settings.py`
