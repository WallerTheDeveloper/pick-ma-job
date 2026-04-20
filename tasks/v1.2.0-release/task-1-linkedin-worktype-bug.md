# Task 1 — Bug: LinkedIn `workType` Validation Error

**Size:** S  
**Status:** done

## Problem

Pipeline errors with:
> Input is not valid: Field input.workType.1 must be equal to one of the allowed values: "on-site", "remote", "hybrid"

User sees red error text after pipeline finishes. Jobs are still scraped/evaluated but the error is confusing.

## Root Cause

- `frontend/src/components/search-config/linkedin-form.tsx:38-42` — `workTypeOptions` sends `"onsite"` (no hyphen).
- `scrapers/linkedin.py` — sanitizes `jobType`, `experienceLevel`, `maxItems`, `salaryBase` but has no sanitizer for `workType`. The invalid value is forwarded to Apify as-is.

## Files to Change

### Backend
- `scrapers/linkedin.py`
  - Add `_WORK_TYPE_MAP: dict[str, str]` mapping `"onsite"` → `"on-site"` and any other aliases.
  - Add `_VALID_WORK_TYPES: frozenset[str]` = `{"on-site", "remote", "hybrid"}`.
  - Before the Apify call, sanitize `actor_input["workType"]`: map known aliases, whitelist, log and drop unknowns. Mirror the existing `experienceLevel` sanitizer pattern.

### Frontend
- `frontend/src/components/search-config/linkedin-form.tsx:38-42`
  - Change option value `"onsite"` → `"on-site"` (label stays "On-site").
  - When hydrating a saved config, convert legacy `"onsite"` → `"on-site"` so old stored configs don't re-trigger the error next save.

## Success Criteria

- Running pipeline with existing saved LinkedIn configs no longer raises the validation error.
- Newly saved LinkedIn configs send `"on-site"`.
- Unknown `workType` values are logged and dropped gracefully rather than forwarded to Apify.
