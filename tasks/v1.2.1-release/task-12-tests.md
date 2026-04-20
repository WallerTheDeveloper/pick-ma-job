# Task 12 — Write backend tests for blacklist

**Size:** M  
**Status:** done

## Goal

Ensure ≥ 80% test coverage for all new backend code. Tests must prove the key guarantees: cost-saving (evaluator not called for blacklisted jobs) and cross-user isolation.

## Test Files

### `tests/services/test_company_blacklist.py`

- `add` with valid name → returns entry
- `add` with name < 3 chars → raises `CompanyBlacklistError`
- `add` with duplicate (same user) → raises `CompanyBlacklistError`
- `add` strips whitespace before validation
- `add` at 500-entry cap → raises `CompanyBlacklistError`
- `remove` with valid entry_id → succeeds
- `remove` with unknown entry_id → raises `CompanyBlacklistError`

### `tests/services/test_pipeline.py` (extend existing)

- Job whose `company_name` matches blacklist entry → evaluator mock NOT called, `jobs_skipped_blacklist` incremented
- Job with `company_name = None` → not blacklisted (passes through)
- Empty blacklist → no behaviour change vs baseline
- Substring match: blacklist `"google"` blocks `"Google DeepMind"` and `"Google LLC"`
- `jobs_skipped_blacklist` correctly summed across multiple platforms in `PipelineRunResult`

### `tests/repositories/test_company_blacklist.py`

- `insert` returns entry on success
- `insert` returns `None` on duplicate (`ON CONFLICT DO NOTHING`)
- `delete` returns `True` on success; `False` for non-existent id
- `delete` returns `False` when entry belongs to a different user (cross-user isolation)
- `find_names_by_user_id` returns only lowercase names for the given user

### `tests/api/test_api_company_blacklist.py`

- `GET /api/company-blacklist` — authenticated → 200 with entries list
- `GET /api/company-blacklist` — unauthenticated → 401
- `POST /api/company-blacklist` — valid name → 201 with entry
- `POST /api/company-blacklist` — duplicate → 409
- `POST /api/company-blacklist` — name < 3 chars → 422
- `DELETE /api/company-blacklist/{id}` — own entry → 204
- `DELETE /api/company-blacklist/{id}` — foreign entry (different user) → 404

## Success Criteria

- All listed test cases pass.
- Evaluator mock assertion confirms zero calls for blacklisted jobs.
- Cross-user isolation test proves DELETE returns 404 for foreign entries, not 204.
