# Task 03: CV Strategic Enhancement (Anti-Fabrication)

## Goal

Fix the CV customization prompt to balance aggressive optimization with clear boundaries between strategic enhancement and outright fabrication. The AI should strategically enhance the candidate's CV — amplifying scope, connecting adjacent skills, and using stronger wording — while drawing a hard line on verifiable qualifications (languages, certifications, degrees) that cannot be plausibly learned quickly.

## Current Behavior

- `configs/prompts/cv_customize.json` system prompt says:
  > "You are an aggressive CV optimizer. Your goal is to maximize the candidate's chance of passing ATS filters — by any means necessary."
- It instructs:
  > "Exaggerate scope, scale, and impact of past work wherever plausible"
- The only guard is:
  > "Do NOT add experience that has zero basis in the original CV"
- This resulted in the AI claiming the user has "full professional French proficiency" when the user doesn't speak French at all
- `services/cv_service.py` `_call_customize()` passes the job description and original CV text to the LLM but does NOT include the user's structured data (skills, languages) as explicit boundary markers

## Root Cause

The prompt doesn't distinguish between **plausible strategic enhancement** and **outright fabrication**:
- "By any means necessary" gives the AI license to cross boundaries it shouldn't
- "Exaggerate... wherever plausible" doesn't define what "plausible" means
- "Inject relevant technologies and skills" without a learnability/verifiability check leads to claiming French fluency or PMP certifications
- The only guard ("zero basis") is too weak — a candidate with "beginner French" has a "basis" for claiming "fluent French", but learning French from beginner to professional fluency takes years

The AI needs a clear framework:
- **Learnability test**: Can someone with the candidate's background plausibly learn this in days to a few weeks? → Enhancement OK
- **Verifiability test**: Is this a hard credential (language, certification, degree) that's easily checked? → Must be accurate

## Required Changes

### 1. Rewrite `configs/prompts/cv_customize.json`

**File**: `configs/prompts/cv_customize.json`

Replace the current system prompt entirely. The new prompt must be profession-agnostic — it works for developers, nurses, HR specialists, accountants, or any other profession.

The complete JSON file should be:

```json
{
  "model": "claude-haiku-4-5-20251001",
  "system": "You are an aggressive CV customizer. Your goal is to maximize the candidate's chance of passing ATS filters through strategic enhancement — framing the candidate in the strongest possible light while respecting hard boundaries on verifiable claims.\n\nSTRATEGIC ENHANCEMENT (ENCOURAGED):\n- Connect adjacent skills: if the candidate has a skill, you may list adjacent skills in the same domain that they could plausibly learn quickly\n- Amplify scope and impact of REAL experience: 'worked on' → 'led', 'helped with' → 'drove', 'participated in' → 'contributed significantly to'\n- Reframe experience using the job description's exact keywords and terminology\n- Add skills or tools the candidate could plausibly learn in days to weeks based on their existing domain expertise\n- Reorder sections to put the most relevant content first\n- Strengthen bullet points with metrics and impact language consistent with what actually happened\n\nHARD BOUNDARIES (NEVER violate):\n- NEVER fabricate languages: do not claim fluency or proficiency in a language the candidate doesn't speak at a professional level. Learning a language takes years — this is off limits.\n- NEVER fabricate certifications, degrees, or professional licenses (e.g., PMP, certified public accountant, registered nurse license). These are verifiable credentials.\n- NEVER invent job titles, companies, dates, or employment history\n- NEVER claim experience on projects or in roles the candidate never held\n\nTHE LEARNABILITY TEST:\nBefore adding a skill not explicitly in the original CV, ask: 'Could someone with the candidate's background plausibly pick this up in days to a few weeks?'\n- A candidate experienced in a skill → listing an adjacent skill in the same domain: YES (learnable quickly)\n- A nurse experienced in ER → listing triage protocols: YES (same domain, learnable quickly)\n- An HR specialist experienced in recruitment → listing applicant tracking systems: YES (same domain, learnable quickly)\n- Any candidate → proficiency in a language they don't speak: NO (takes years to learn)\n- Any candidate → a verifiable certification they don't hold: NO (verifiable credential)\n- Any candidate → amplifying real scope of an actual project: YES (it happened, just frame it stronger)\n\nTHE VERIFIABILITY TEST:\nSome claims are easily checked by employers. These must be accurate:\n- Languages: claim only languages the candidate actually speaks at the stated level\n- Certifications and licenses: claim only those the candidate actually holds\n- Degrees and institutions: claim only those the candidate actually earned\n- Dates and job titles: claim only actual history\n\nOther claims — like scope of responsibility, skill breadth within a domain, or framing of achievements — are harder to verify and CAN be strategically enhanced.\n\nOutput plain text only — no JSON, no markdown fences, no commentary.\nFormat with clear section headers (ALL CAPS) and hyphen bullet points.",
  "user_template": "Job Title: {job_title}\n\nJob Description:\n{job_description}\n\n---\n\nCandidate's Verified Skills: {skills}\nCandidate's Verified Languages: {languages}\nCandidate's Verified Certifications: {certifications}\n\n---\n\nOriginal CV:\n{cv_text}\n\n---\n\nCustomize the CV for this role. Enhance strategically — connect adjacent skills, amplify real impact, use the job description's language — but do not fabricate languages, certifications, or credentials."
}
```

Key changes from current prompt:
| Current | New |
|---------|-----|
| "aggressive CV optimizer" + "by any means necessary" | "aggressive CV customizer" + "strategic enhancement... while respecting hard boundaries" |
| "Exaggerate scope, scale, and impact" | "Amplify scope and impact of REAL experience" with specific examples |
| "Inject relevant technologies and skills" (unrestricted) | "Add skills or tools the candidate could plausibly learn in days to weeks based on their existing domain expertise" |
| Single weak guard: "zero basis" | Two explicit frameworks: Learnability Test + Verifiability Test |
| No gap-handling guidance | Clear examples across professions (nurse, HR, general) of what's OK vs not OK |
| No structured data context | Candidate's verified skills, languages, and certifications included |
| Five generic NEVER rules | Four targeted NEVER rules focused on verifiable claims |
| Developer-centric examples ("Java dev", "React dev") | Profession-agnostic language applicable to any career |

### 2. Backend — Include Structured Data in CV Customization

**File**: `services/cv_service.py`

Update `_call_customize()` to pass the user's structured CV data as context. The `CVRow.structured` field (JSONB) contains parsed skills, languages, etc.

Modify the user template to include:
```
Candidate's Verified Skills: {skills}
Candidate's Verified Languages: {languages}
Candidate's Verified Certifications: {certifications}
```

Where these are extracted from the CV's `structured` data:
- Skills: from `structured.skills.primary + structured.skills.secondary + structured.skills.tertiary` (combine all levels)
- Languages: from `structured.languages` (list of {language, proficiency} objects, or plain strings)
- Certifications: from `structured.certifications` or `structured.other` (if available, otherwise empty string)

This gives the AI clear anchors for what's verified while leaving room for adjacent skill enhancement.

### 3. Backend — Post-Generation Verification

**File**: `services/cv_service.py`

After generating the customized CV, run a verification step that focuses on **verifiable claims only** — not all new skills:

```python
def _verify_customization(
    customized_text: str,
    original_structured: dict,
) -> list[str]:
    """Check for fabricated verifiable claims in customized CV.
    
    Only flags claims that are hard to learn quickly AND easily verifiable:
    - Languages not in the original or with upgraded proficiency
    - Certifications/licenses not in the original
    - Degrees or institutions not in the original
    
    Does NOT flag adjacent skills in the same domain (e.g., a nurse listing
    triage protocols, a marketer listing Google Analytics alongside Google Ads),
    reframed experience, or strengthened bullet points — those are strategic
    enhancement, not fabrication.
    """
```

Verification logic:
- **Languages**: Check if the customized text mentions languages not in `original_structured.languages` OR claims a higher proficiency than recorded. Flag these.
- **Certifications**: Check for certification keywords (PMP, CPA, RN, CISSP, etc.) not in `original_structured.certifications`. Flag these.
- **Degrees**: Check for degree references not in `original_structured.education`. Flag these.
- **Skills**: Do NOT flag new skills — the learnability test in the prompt handles this. Listing an adjacent skill within the candidate's domain is enhancement, not fabrication.

If warnings are found:
- Log them for debugging
- Include a `warnings` field in the CV customization response
- Do NOT block the customization — the user should still see it, but with a note to review verifiable claims

### 4. Frontend — Verification Warnings Display

**File**: `frontend/src/components/customize-cv-dialog.tsx`

If the backend returns verification warnings, show a subtle alert:
- A yellow warning banner at the top of the customized CV dialog
- Text: "This CV includes enhanced claims. Please verify the highlighted items match your actual qualifications."
- List of specific warnings (e.g., "French proficiency may not match your profile", "AWS Solutions Architect certification not in your records", "Project management certification not in your records")

## Files to Modify

| File | Change |
|------|--------|
| `configs/prompts/cv_customize.json` | Complete prompt rewrite — strategic enhancement with hard boundaries on verifiable claims, profession-agnostic |
| `services/cv_service.py` | Include structured skills/languages/certifications in prompt; add post-generation verification for verifiable claims only |
| `api/schemas.py` | Add optional `warnings` field to CVCustomizeResponse |
| `api/routes/api_cv.py` | Pass warnings to response |
| `frontend/src/components/customize-cv-dialog.tsx` | Show verification warnings |
| `frontend/src/types/schemas.ts` | Add `warnings` to CV customization type |

## Acceptance Criteria

- [ ] The CV customization prompt encourages strategic enhancement (adjacent skills, amplified impact, keyword matching)
- [ ] The prompt includes explicit hard boundaries on languages, certifications, and degrees
- [ ] The prompt includes the Learnability Test and Verifiability Test as decision frameworks
- [ ] The prompt is profession-agnostic — no developer-centric examples or language
- [ ] The prompt includes diverse examples across professions (healthcare, HR, general)
- [ ] The user template includes the candidate's verified skills, languages, and certifications as context
- [ ] Post-generation verification flags ONLY verifiable claims (languages, certs, degrees) — NOT adjacent skills
- [ ] A candidate's CV can list adjacent skills in their domain even if not explicitly in the original (adjacent skill enhancement)
- [ ] A candidate's CV does NOT claim language fluency if they don't speak that language (verifiable claim boundary)
- [ ] ATS keyword optimization works through strategic reframing, not fabrication
- [ ] The customized CV sounds stronger and more competitive than the original
- [ ] Warnings are displayed in the frontend when verifiable claims may be inaccurate

## Dependencies

- **Depends on**: Task 06 (Generic Profiles) — the prompt should use "candidate" terminology consistent with the work in Task 06
- **Blocks**: Task 04 (CV Diff-Style Generation) — changes the CV output format, should be done after the prompt is fixed
