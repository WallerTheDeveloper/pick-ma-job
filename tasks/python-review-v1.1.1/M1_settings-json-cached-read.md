# M1: Cache settings.json Read at Module Level in PipelineService

- **Phase:** Medium
- **Priority:** P2 — Performance
- **Status:** DONE
- **Depends on:** None

## Problem

`services/pipeline.py:84` reads and parses `settings.json` from disk inside `PipelineService.__init__`. This method is called inside `_execute` — a background task — meaning every pipeline run re-reads the file from disk. The file is static and never changes at runtime.

## Solution

**`services/pipeline.py`** — cache the parsed settings at module level:

```python
import json
from pathlib import Path

_SETTINGS_PATH = Path(__file__).parent.parent / "configs" / "settings.json"
_SETTINGS: dict = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
```

Then reference `_SETTINGS` in `__init__` instead of re-reading the file.

If the settings path may not exist in all environments, add a clear startup error:
```python
try:
    _SETTINGS: dict = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
except FileNotFoundError:
    raise RuntimeError(f"settings.json not found at {_SETTINGS_PATH}") from None
```

## Files

- `services/pipeline.py`

## Acceptance Criteria

- [x] `settings.json` is read from disk exactly once at module import time
- [x] Multiple pipeline runs do not re-read the file
- [x] A missing `settings.json` raises a clear `RuntimeError` at startup, not at runtime
