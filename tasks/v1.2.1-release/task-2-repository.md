# Task 2 — Create CompanyBlacklistRepository

**Size:** S  
**Status:** done

## Goal

Implement `repositories/company_blacklist.py` following the pattern in `repositories/profile.py`.

## Data Model

```python
@dataclass(frozen=True)
class CompanyBlacklistEntry:
    id: UUID
    user_id: UUID
    name: str
    name_lower: str
    created_at: datetime
```

## Methods

| Method | Signature | Notes |
|--------|-----------|-------|
| `find_by_user_id` | `(user_id: UUID) -> list[CompanyBlacklistEntry]` | ORDER BY name |
| `find_names_by_user_id` | `(user_id: UUID) -> tuple[str, ...]` | Returns lowercase names only; used by pipeline (immutable tuple) |
| `insert` | `(user_id: UUID, name: str) -> CompanyBlacklistEntry \| None` | `ON CONFLICT DO NOTHING RETURNING *`; None on conflict |
| `delete` | `(user_id: UUID, entry_id: UUID) -> bool` | WHERE scoped by user_id; returns False if not found |
| `exists` | `(user_id: UUID, name_lower: str) -> bool` | Cheap existence check |

## Success Criteria

- All methods scope queries by `user_id` — no cross-user data access possible.
- `find_names_by_user_id` returns an immutable `tuple[str, ...]` (not a list).
- `insert` returns `None` on duplicate (not an exception).
- `delete` returns `False` (not an exception) when entry not found or belongs to another user.
