# P1-1: Audit configs/ for User-Agnostic Defaults

- **Phase:** 1 — Config Audit
- **Priority:** P1 — Foundation
- **Status:** DONE
- **Depends on:** None

## Problem

The `configs/` folder may contain user-specific strings (personal names, personal rates, personal keywords) that were carried over from the single-user prototype. In a multi-user SaaS context every config file must be neutral — no hardcoded profile data.

## Scope

Review all files under `configs/` and remove or replace any user-specific content:

- `configs/platforms/upwork.json`
- `configs/platforms/linkedin.json`
- `configs/prompts/upwork_context.json`
- `configs/prompts/linkedin_context.json`

### What to look for

- Personal names (e.g. "Danylo", "Golosov")
- Personal rates or salary figures (e.g. "€10–30/hour", "€50k")
- Personal skill lists or keywords (e.g. "unity", "AR/VR") hardcoded as default query values
- Location filters set to a personal city (e.g. "Berlin")
- Any rubric text that describes a specific individual

### Expected outcome

- Platform configs contain only structural/schema defaults (actor field names, pagination limits, sort order)
- Prompt context files contain evaluation guidelines, not personal profile content
- Personal profile data lives exclusively in the `profiles` DB table, injected at runtime by the evaluator

## Files

- `configs/platforms/upwork.json`
- `configs/platforms/linkedin.json`
- `configs/prompts/upwork_context.json`
- `configs/prompts/linkedin_context.json`

## Acceptance Criteria

- [x] No personal names, rates, or skill keywords appear in any file under `configs/`
- [x] Platform configs still work as valid Apify actor input templates
- [x] Prompt context files still produce valid evaluations when profile is injected at runtime
- [x] No runtime behaviour changes — existing tests still pass
