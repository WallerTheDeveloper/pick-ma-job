# Task 5 — Feature: AI-Powered CV Customization

**Size:** L  
**Status:** done

## Goal

Help users get more interviews by tailoring their CV to each job posting. AI is explicitly allowed to exaggerate and embellish the user's experience to maximize ATS pass-through and interview rate. No guardrails.

## User Flow

1. User uploads their CV (PDF) on the Profile page.
2. Backend extracts text, AI structures it into sections, stores in DB.
3. On any result row where `score >= threshold` (configurable, default 7) and user has a CV uploaded, a **"Customize CV"** button appears.
4. User clicks → dialog opens with Original CV (read-only) and Customized CV (editable textarea).
5. AI rewrites the CV aggressively tailored to the job description.
6. User edits if desired, then copies to clipboard or downloads as `.txt`.
7. Result is cached per `(user_id, job_result_id)`. A **"Regenerate"** button forces a fresh AI call.

## Database

```sql
-- One CV per user; upload replaces existing
CREATE TABLE cvs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    structured JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id)
);

-- Cache customized output per job
CREATE TABLE cv_customizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_result_id UUID NOT NULL REFERENCES job_results(id) ON DELETE CASCADE,
    customized_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, job_result_id)
);
```

Also add `cv_customize_threshold INTEGER NOT NULL DEFAULT 7` to the `profiles` table.

## Backend Files

- `requirements.txt` — add `pypdf`
- DB migration — create `cvs`, `cv_customizations` tables; add `cv_customize_threshold` to `profiles`
- `repositories/cv.py` — `CVRepository`: `upsert`, `find_by_user`, `delete_by_user`
- `repositories/cv_customization.py` — `CVCustomizationRepository`: `upsert`, `find_by_user_and_job`, `delete_by_user_and_job`
- `services/cv_service.py` — PDF text extraction via `pypdf`, `structure_cv()` Claude call, `customize_cv()` Claude call
- `configs/prompts/cv_structure.json` — prompt for structuring raw CV text into sections JSON
- `configs/prompts/cv_customize.json` — prompt for customizing CV. **Must instruct Claude to:**
  - Aggressively optimize every bullet point for the job's keywords
  - Reframe existing experience using the job description's exact language
  - Exaggerate scope, scale, and impact of past work
  - Add relevant keywords and technologies from the job description wherever plausible
  - Restructure sections to front-load what the job cares about most
  - Goal: maximize the chance of passing ATS filters and getting an interview by any means
- `api/routes/api_cv.py`
  - `POST /api/cv/upload` — multipart, PDF only, 5 MB cap, rate-limit 5/hr. Extracts text, runs structure AI call, upserts to `cvs`.
  - `GET /api/cv` — returns metadata + structured preview (no raw text)
  - `DELETE /api/cv` — deletes CV and all cached customizations for user
  - `POST /api/cv/customize` — body `{job_result_id: UUID, force_regenerate?: bool}`. Validates: job owned by user, user has CV, score >= threshold. Returns `{customized_text, from_cache}`. Rate-limit 30/hr.
- `api/schemas.py` — `CVUploadResponse`, `CVMetadataResponse`, `CVCustomizeRequest`, `CVCustomizeResponse`
- `main.py` — register `api_cv` router

## Frontend Files

- `frontend/src/api/cv.ts` — `uploadCV`, `fetchCV`, `deleteCV`, `customizeCV`
- `frontend/src/hooks/use-cv.ts` — TanStack Query wrappers (`useCV`, `useUploadCV`, `useDeleteCV`, `useCustomizeCV`)
- `frontend/src/components/cv-upload-card.tsx`
  - File input (or drag-and-drop), accepts PDF only, shows filename + upload date after upload
  - "Replace" button re-triggers file input
  - "Delete" button removes CV with confirmation
- `frontend/src/pages/profile.tsx` — mount `<CVUploadCard />` and a "CV score threshold" number input (reads/writes `cv_customize_threshold` from profile)
- `frontend/src/components/customize-cv-dialog.tsx`
  - Two-pane dialog: Original CV (read-only scroll area) | Customized CV (editable `Textarea`)
  - "Regenerate" button calls `customizeCV` with `force_regenerate: true`
  - "Copy" button copies customized text to clipboard
  - "Download .txt" button triggers file download
  - Loading state while AI generates
- `frontend/src/components/result-row.tsx`
  - Show "Customize CV" button when `result.score >= threshold` AND `useCV().data` exists
  - Button opens `CustomizeCVDialog` for that result

## Profile API changes

- `api/routes/api_profile.py` — include `cv_customize_threshold` in GET/POST /api/profile
- `api/schemas.py` — add field to profile request/response models
- `repositories/profile.py` — include `cv_customize_threshold` in upsert
- `frontend/src/pages/profile.tsx` — add number input for threshold (label: "Show 'Customize CV' button for scores ≥")

## Design Decisions (confirmed by user)

- PDF only (no .docx / plain text) for v1.2.0
- One CV per user; upload replaces existing
- AI output displayed in editable textarea — user can modify before copying/downloading
- Results cached per `(user_id, job_result_id)`; "Regenerate" button bypasses cache
- Score threshold is configurable per user (stored in profile), default 7
- **No ethical guardrails** — AI should exaggerate freely to maximize interview chances
- Output is text sections only, not pixel-perfect PDF reproduction

## Success Criteria

- User uploads a PDF on Profile page; structured preview appears within ~10s.
- "Customize CV" button appears on qualifying result rows.
- Clicking produces a tailored CV text within ~10s.
- Re-opening the same result shows the cached version instantly.
- "Regenerate" forces a fresh AI call.
- User can edit, copy, and download the output.
