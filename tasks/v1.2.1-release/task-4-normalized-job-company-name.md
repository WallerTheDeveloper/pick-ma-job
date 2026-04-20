# Task 4 — Add company_name property to NormalizedJob

**Size:** S  
**Status:** done

## Goal

Make company name extraction platform-agnostic so the pipeline filter doesn't need per-platform logic.

## Changes

### `scrapers/base.py`

Add a `@property` on `NormalizedJob` (works on frozen dataclasses):

```python
@property
def company_name(self) -> str | None:
    value = self.extras.get("company_name") or self.extras.get("client_name")
    return str(value) if value else None
```

### `configs/platforms/upwork.json` (if applicable)

Add `"company_name"` mapping to the appropriate Apify field under `field_mappings.extras`. Check what field name Apify's Upwork actor exposes for the client/company name.

### `configs/platforms/linkedin.json` (verify only)

Confirm `company_name` is already present in `extras` mapping. No change expected.

## Notes

- Upwork jobs are often posted by individuals, not companies — `company_name` may frequently be `None` for Upwork. This is acceptable; the filter is a no-op when the field is absent.
- The fallback chain `extras.get("company_name") or extras.get("client_name")` ensures both keys are checked without platform-aware code in the pipeline.

## Success Criteria

- `job.company_name` returns the correct string for a LinkedIn job with `extras["company_name"]`.
- `job.company_name` returns the correct string for an Upwork job with `extras["client_name"]`.
- `job.company_name` returns `None` when neither key is present.
- `NormalizedJob` remains a `frozen=True` dataclass (no mutation).
