# Task 3 — Create CompanyBlacklistService

**Size:** S  
**Status:** done

## Goal

Implement `services/company_blacklist.py`. Service owns validation and normalization; the repository owns DB access.

## Interface

```python
class CompanyBlacklistError(Exception): ...

class CompanyBlacklistService:
    async def list(self, user_id: UUID) -> list[CompanyBlacklistEntry]: ...
    async def add(self, user_id: UUID, name: str) -> CompanyBlacklistEntry: ...
    async def remove(self, user_id: UUID, entry_id: UUID) -> None: ...
```

## Validation Rules (in `add`)

1. Strip whitespace from `name`.
2. Reject empty string → `CompanyBlacklistError("Name cannot be empty")`
3. Reject length < 3 → `CompanyBlacklistError("Name must be at least 3 characters")`
4. Reject length > 200 → `CompanyBlacklistError("Name must be at most 200 characters")`
5. Normalize: `name_lower = name.strip().lower()`
6. Call `repo.insert`; if returns `None` → `CompanyBlacklistError("Company already blacklisted")`
7. Enforce soft cap of 500 entries/user before inserting → `CompanyBlacklistError("Blacklist limit reached (500)")`

## `remove`

- Call `repo.delete(user_id, entry_id)`; if returns `False` → `CompanyBlacklistError("Entry not found")`

## Success Criteria

- Validation fires before any DB call.
- Duplicate add raises `CompanyBlacklistError`, not a DB exception.
- Remove raises `CompanyBlacklistError` (not 500) for unknown or foreign entry_id.
- Soft cap of 500 enforced in service (not repo).
