# Task 6 — Add Pydantic schemas for blacklist API

**Size:** S  
**Status:** done

## Goal

Add request/response models to `api/schemas.py`.

## Schemas

```python
class CompanyBlacklistEntryResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime

class CompanyBlacklistListResponse(BaseModel):
    entries: list[CompanyBlacklistEntryResponse]

class CompanyBlacklistAddRequest(BaseModel):
    name: str = Field(min_length=3, max_length=200)

class CompanyBlacklistAddResponse(BaseModel):
    entry: CompanyBlacklistEntryResponse
```

## Notes

- `name_lower` is an internal field — do not expose it in response schemas.
- `CompanyBlacklistAddRequest` mirrors service-layer validation but provides a first line of defence at the HTTP layer (FastAPI auto-422).

## Success Criteria

- POST with `name` shorter than 3 chars returns 422 (FastAPI validation, before the service layer).
- Response schemas do not leak `name_lower` or `user_id`.
