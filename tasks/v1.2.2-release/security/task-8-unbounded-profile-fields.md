# Task 8 — Constrain Unbounded Profile Dict/List Fields

**Size:** S  
**Status:** todo  
**Severity:** MEDIUM

## Goal

`notable_projects` and `rubric` in `ProfileSaveRequest` accept unbounded payloads that are stored in JSONB and embedded in Claude prompts. Add size validators to prevent storage exhaustion and prompt stuffing.

## Changes

**`api/schemas.py`**:
```python
from pydantic import Field, field_validator
from typing import Any

class ProfileSaveRequest(BaseModel):
    ...
    notable_projects: list[dict[str, Any]] = Field(default_factory=list)
    rubric: dict[str, Any] = Field(default_factory=dict)

    @field_validator("notable_projects")
    @classmethod
    def limit_notable_projects(cls, v: list) -> list:
        if len(v) > 20:
            raise ValueError("Maximum 20 notable projects allowed.")
        return v

    @field_validator("rubric")
    @classmethod
    def limit_rubric(cls, v: dict) -> dict:
        if len(v) > 30:
            raise ValueError("Maximum 30 rubric keys allowed.")
        return v
```

Also cap string fields inside `notable_projects` items if the schema allows free-form dicts, or define a typed `NotableProject` model to enforce structure.

## Success Criteria

- `POST /api/profile` with `notable_projects` containing 21 items returns `422`.
- `POST /api/profile` with a `rubric` containing 31 keys returns `422`.
- Normal profile saves (within limits) continue to work.
