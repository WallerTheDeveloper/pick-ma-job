# CR-10: Platform Parameter Not Validated Before File Path Construction

- **Phase:** hardening
- **Priority:** P3 (Medium)
- **Status:** DONE
- **Depends on:** None

## Problem

In `api/routes/api_pipeline.py:50-56`, the `platform` query parameter is passed through to `services/pipeline.py:152-153` where it is used in `pathlib.Path / f"{platform}.json"` without allowlist validation. Although `pathlib` resolves paths safely and the file existence check prevents reading arbitrary files, a crafted `platform` value like `../../etc/passwd` could cause unexpected path resolution. Additionally, `load_platform_context(platform)` may have the same issue.

## Approach

1. In the route handler (`api/routes/api_pipeline.py`), validate `platform` against the existing `KNOWN_PLATFORMS` frozenset from `services/search_config.py` before any use.
2. Reject unknown values with HTTP 422: `"Unknown platform. Supported: upwork, linkedin"`.
3. Alternatively, use a Pydantic `Literal["upwork", "linkedin"]` type on the query parameter for automatic validation.

## Files

- `api/routes/api_pipeline.py:50-56` — validate `platform` against allowlist before passing to service
- `services/search_config.py:12` — reuse `KNOWN_PLATFORMS` (already exists as canonical source)

## Implementation Notes

- The `KNOWN_PLATFORMS` frozenset in `services/search_config.py:12` is built from `scrapers/registry.py:list_platforms()`. This is the canonical source of truth — don't hardcode the list.
- Using `Literal["upwork", "linkedin"]` in the Pydantic query param provides automatic OpenAPI docs but is less dynamic. The `KNOWN_PLATFORMS` approach adapts automatically when new platforms are added.
- Even though `pipeline.py:153` checks `platform_config_path.exists()`, validating early in the route is defense-in-depth and gives a clearer error message.
