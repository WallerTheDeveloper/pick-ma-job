# P1-2: Fix AI Client Rating Scale (1–5 not 1–10)

- **Phase:** 1 — Critical Bugs
- **Priority:** P1 — High
- **Status:** DONE
- **Depends on:** None

## Problem

Upwork client ratings are on a **1–5 scale** (5 is the maximum). The AI evaluator appears to treat this as a 1–10 scale, causing a 5/5 perfect rating to be interpreted as mediocre (50%), which negatively skews the job evaluation score.

## Root Cause Investigation

1. **`configs/prompts/upwork_context.json`** — Check how `client_rating` is described in the platform context or message template. Look for any mention of scale/max value.
2. **`scrapers/upwork.py`** — Confirm what value the Apify actor returns for `client_rating` and how it's mapped into `NormalizedJob.extras`.
3. **`core/evaluator.py`** — Check how `extras` fields are interpolated into the prompt. Is the raw number passed with no context?
4. **System prompt / rubric** — Is there any implicit assumption about rating scale in the scoring rubric?

## Files

- `configs/prompts/upwork_context.json` — platform context injected into the prompt
- `scrapers/upwork.py` — field mapping into `NormalizedJob.extras`
- `core/evaluator.py` — prompt assembly

## Fix

In the prompt context, explicitly label `client_rating` with its scale. Either:

- Add a label in the prompt template: `"Client rating: {client_rating}/5"`
- Or add a note in the platform context explaining: `"client_rating is a value from 0 to 5 where 5 is the maximum possible rating"`

Do not convert the raw value — keep the original number but ensure the AI understands the scale.

## Acceptance Criteria

- [x] A job with `client_rating: 5` is evaluated as an excellent client signal, not a mediocre one
- [x] The prompt template or context clearly indicates the 1–5 scale
- [x] No changes needed to scraper output format — fix is prompt-side only
