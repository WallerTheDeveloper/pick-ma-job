# Task 7 — Create blacklist API route and wire deps

**Size:** M  
**Status:** done

## Goal

Expose CRUD endpoints for the company blacklist and wire all dependencies.

## Endpoints

File: `api/routes/api_company_blacklist.py`

| Method | Path | Auth | CSRF | Rate limit | Response |
|--------|------|------|------|------------|----------|
| GET | `/api/company-blacklist` | required | no | no | `CompanyBlacklistListResponse` |
| POST | `/api/company-blacklist` | required | yes | yes | `CompanyBlacklistAddResponse` (201); 409 on dup; 422 on validation |
| DELETE | `/api/company-blacklist/{entry_id}` | required | yes | no | 204 No Content; 404 if not owned |

### Error mapping

- `CompanyBlacklistError("Company already blacklisted")` → 409
- `CompanyBlacklistError("Entry not found")` → 404
- All other `CompanyBlacklistError` → 422

### Pattern reference

Mirror `api/routes/api_profile.py` for auth dependency usage and CSRF handling.

## `api/deps.py`

Add:
```python
def get_company_blacklist_repo(db=Depends(get_db)) -> CompanyBlacklistRepository: ...
def get_company_blacklist_service(repo=Depends(get_company_blacklist_repo)) -> CompanyBlacklistService: ...
```

Update `get_pipeline_service` to accept and pass `company_blacklist_repo`.

## `main.py`

Mount the new router alongside the existing ones.

## Success Criteria

- GET returns empty list for a new user (not 500).
- POST returns 201 with entry on success; 409 on duplicate; 422 on short name.
- DELETE returns 204 on success; 404 when entry_id belongs to another user.
- Unauthenticated requests return 401.
