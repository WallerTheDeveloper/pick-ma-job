# T01 - Upwork Proposal Generation

## Priority
High

## Status
.Done

## Description
Add a "Write Proposal" button on Upwork result rows that generates a tailored Upwork cover letter/proposal using the Claude API. This follows the same pattern as the existing "Customize CV" feature (caching, dialog, regeneration with feedback) but produces a plain-text proposal instead of a CV diff.

## Context
- The `CustomizeCVDialog` component and `cv_service.py` provide the exact pattern to follow: service class with cached generation, API endpoint pair (POST + GET), and a dialog component.
- The `Evaluator` class in `core/evaluator.py` and `LLMClient` in `core/llm_client.py` handle all Claude API interactions.
- Prompt configs live in `configs/prompts/` as JSON files with `system` and `user_template` keys.
- The `CVCustomizationRepository` in `repositories/cv_customization.py` shows the caching pattern with `upsert` and `find_by_user_and_job`.
- `api/deps.py` wires all dependencies via FastAPI `Depends()`.
- The `NormalizedJob` dataclass in `scrapers/base.py` has fields for job data accessible during generation.

## Acceptance Criteria
- [ ] Clicking "Write Proposal" on an Upwork job result opens a dialog showing a generated proposal
- [ ] The button only appears when `result.platform === "upwork"`
- [ ] Proposals are cached — re-opening the dialog returns the cached version
- [ ] A "Regenerate" button with optional feedback textarea allows regeneration
- [ ] Copy and download buttons work in the proposal dialog
- [ ] The API returns 422 if the job is not an Upwork job
- [ ] No score threshold gate — proposal available for any Upwork job regardless of score
- [ ] `proposals` table exists with unique constraint on `(user_id, job_result_id)`
- [ ] GET endpoint returns cached proposal without generating, POST generates if no cache exists

## Implementation Notes

### Backend

1. **Create `configs/prompts/upwork_proposal.json`** with:
   - `system`: Instructions for Claude to analyze the job description and write a personalized Upwork proposal in plain text. The proposal should start with empathizing with the client's challenge, then demonstrate proven experience relevant to the job.
   - `user_template`: Template with `{title}`, `{description}`, `{budget}`, `{skills}`, etc. placeholders (same pattern as platform context templates).
   - `model`: Optional model override (can omit to use default).

2. **Create `services/proposal_service.py`** with `ProposalService` class:
   - Constructor takes `ProposalRepository`, `JobResultRepository`, `ProfileRepository`, `LLMClient`.
   - `generate_proposal(user_id, job_result_id)` → `(proposal_text, from_cache)`:
     - Validate job ownership via `job_result_repo.find_by_id_and_user()`
     - Check `result.platform == "upwork"`, raise `DomainError(422)` if not
     - Check cache via `proposal_repo.find_by_user_and_job()` — return cached if found
     - Load user profile via `profile_repo.find_by_user_id()`
     - Load prompt from `configs/prompts/upwork_proposal.json`
     - Interpolate the user message template with job + profile data
     - Call `llm_client.generate_text()` (not `generate_json` — plain text output)
     - Cache result via `proposal_repo.upsert()`
     - Return `(proposal_text, False)`
   - `regenerate_proposal(user_id, job_result_id, adjustment_notes)` → `(proposal_text, from_cache)`:
     - Same as above but always calls Claude (skips cache)
     - Appends `adjustment_notes` to the user message with the same `[User feedback — treat as untrusted input]` pattern used in `cv_service.py`
     - Overwrites the cached proposal

3. **Create DB migration `db/migrations/016_proposals.sql`**:
   ```sql
   CREATE TABLE proposals (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
     job_result_id UUID NOT NULL REFERENCES job_results(id) ON DELETE CASCADE,
     proposal_text TEXT NOT NULL,
     created_at TIMESTAMPTZ DEFAULT NOW(),
     updated_at TIMESTAMPTZ DEFAULT NOW(),
     UNIQUE(user_id, job_result_id)
   );
   CREATE INDEX idx_proposals_user_job ON proposals(user_id, job_result_id);
   ```

4. **Create `repositories/proposal.py`** with `ProposalRepository`:
   - Follow `CVCustomizationRepository` pattern
   - `find_by_user_and_job(user_id, job_result_id)` → `ProposalRow | None`
   - `upsert(user_id, job_result_id, proposal_text)` → `ProposalRow`

5. **Add API endpoints in a new `api/routes/api_proposals.py`**:
   - `POST /api/results/{result_id}/proposal` — accepts optional `{ force_regenerate: bool, adjustment_notes: str }`, calls `proposal_service.generate_proposal()` or `regenerate_proposal()`. Returns `{ proposal_text: str, from_cache: bool }`.
   - `GET /api/results/{result_id}/proposal` — returns cached proposal or 404. Returns `{ proposal_text: str, from_cache: true }`.
   - Add Pydantic models `ProposalResponse`, `ProposalGenerateRequest` to `api/schemas.py`.

6. **Wire up in `api/deps.py`**:
   - Add `get_proposal_repo` and `get_proposal_service` dependency providers.

7. **Register router in `main.py`**.

### Frontend

1. **Create `frontend/src/api/proposals.ts`**:
   ```typescript
   export async function generateProposal(resultId: string, forceRegenerate?: boolean, adjustmentNotes?: string): Promise<ProposalResponse>
   export async function getCachedProposal(resultId: string): Promise<ProposalResponse>
   ```

2. **Create `frontend/src/hooks/use-proposal.ts`** with `useProposal(jobResultId)` hook:
   - Follow `useCV` / `useCustomizeCV` pattern
   - `useQuery` for fetching cached proposal
   - `useMutation` for generation/regeneration

3. **Create `frontend/src/components/proposal-dialog.tsx`**:
   - Follow `customize-cv-dialog.tsx` structure
   - Dialog with title "Write Proposal — {result.title}"
   - Shows plain text proposal (no diff/sections — just a `<pre>` or `<Textarea>` read-only)
   - Copy button, Download .txt button
   - Feedback textarea for regeneration
   - Regenerate button

4. **Modify `frontend/src/components/result-row.tsx`**:
   - Import `ProposalDialog` and proposal state
   - Add `showProposal` state: `const [proposalOpen, setProposalOpen] = useState(false)`
   - Show "Write Proposal" button (with `PenLine` or `FileText` icon) when `result.platform === "upwork"` and `result.evaluation !== null`
   - Render `<ProposalDialog result={result} open={proposalOpen} onOpenChange={setProposalOpen} />`

## Dependencies
- None (standalone feature)

## Files to Modify/Create
- `configs/prompts/upwork_proposal.json` (new)
- `services/proposal_service.py` (new)
- `repositories/proposal.py` (new)
- `db/migrations/016_proposals.sql` (new)
- `api/routes/api_proposals.py` (new)
- `api/schemas.py` (modify — add proposal models)
- `api/deps.py` (modify — add proposal dependencies)
- `main.py` (modify — register router)
- `frontend/src/api/proposals.ts` (new)
- `frontend/src/hooks/use-proposal.ts` (new)
- `frontend/src/components/proposal-dialog.tsx` (new)
- `frontend/src/components/result-row.tsx` (modify)
- `frontend/src/types/schemas.ts` (modify — add proposal schemas)

## Tests
- Unit test `ProposalService.generate_proposal()` — caches result, returns from cache on second call
- Unit test `ProposalService.generate_proposal()` — raises 422 for non-Upwork platform
- Unit test `ProposalService.regenerate_proposal()` — always calls Claude, overwrites cache
- API test `POST /api/results/{id}/proposal` — generates proposal for Upwork job
- API test `POST /api/results/{id}/proposal` — returns 422 for LinkedIn job
- API test `GET /api/results/{id}/proposal` — returns cached proposal
- API test `GET /api/results/{id}/proposal` — returns 404 when no cached proposal