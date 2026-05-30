# Task 06 — Frontend: Humanization UI

**Size:** M  
**Status:** done  
**Priority:** MEDIUM  
**Depends on:** T03

## Goal

Add UI indicators in the CV customization dialog that show the user when humanization has been applied, and allow them to toggle it on/off.

## Design Decisions (to confirm with user)

Before implementation, confirm:
1. Should humanization be the default for all CV customizations? → **Yes**, proposed default is ON
2. Should the user be able to disable humanization? → **Yes**, add a toggle
3. Should there be a "raw" vs "humanized" view comparison? → Not in v1.4.1. Just show the humanized version with a badge

## Changes

### Backend API — `POST /api/cv/customize`

Add optional `humanize` parameter (default `true`):

```python
class CVCustomizeRequest(BaseModel):
    job_result_id: UUID
    force_regenerate: bool = False
    adjustment_notes: str | None = Field(default=None, max_length=2000)
    humanize: bool = True  # NEW
```

When `humanize=False`, skip Passes 2-5 and return only Pass 1 output (current behavior).

### Frontend — `customize-cv-dialog.tsx`

Add a small toggle/switch at the top of the dialog:

```tsx
<div className="flex items-center gap-2 mb-3">
  <Label htmlFor="humanize-toggle" className="text-xs text-muted-foreground">
    AI-tell protection
  </Label>
  <Switch
    id="humanize-toggle"
    checked={humanize}
    onCheckedChange={setHumanize}
  />
  <TooltipProvider>
    <Tooltip>
      <TooltipTrigger asChild>
        <InfoCircledIcon className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
      </TooltipTrigger>
      <TooltipContent>
        Rewrites the CV to sound more natural and reduce AI detection markers.
        Turn off for raw AI output.
      </TooltipContent>
    </Tooltip>
  </TooltipProvider>
</div>
```

When humanize is ON (default), the response includes all 5 passes. When OFF, only Pass 1 runs.

### Frontend — Badge/Indicator

When the humanized text is displayed, add a small, subtle badge:

```tsx
<div className="flex items-center gap-1.5 mb-2">
  <Badge variant="secondary" className="text-xs">
    Humanized
  </Badge>
  {warnings.length > 0 && (
    <Badge variant="outline" className="text-xs text-yellow-600">
      {warnings.length} warning{warnings.length > 1 ? 's' : ''}
    </Badge>
  )}
</div>
```

### Frontend — API Client Update

Update `frontend/src/api/cv.ts`:

```typescript
export async function customizeCV(
  jobResultId: string,
  forceRegenerate: boolean = false,
  adjustmentNotes?: string,
  humanize: boolean = true,  // NEW
): Promise<CVCustomizeResponse> {
  const response = await apiClient.post('/api/cv/customize', {
    job_result_id: jobResultId,
    force_regenerate: forceRegenerate,
    adjustment_notes: adjustmentNotes,
    humanize,
  });
  return response.data;
}
```

## Files to Modify

| File | Change |
|------|--------|
| `api/schemas.py` | Add `humanize: bool = True` to `CVCustomizeRequest` |
| `api/routes/api_cv.py` | Pass `humanize` parameter to `cv_service.customize_cv()` |
| `services/cv_service.py` | Accept `humanize: bool = True` in `customize_cv()`; skip Passes 2-5 when False |
| `frontend/src/api/cv.ts` | Add `humanize` parameter to `customizeCV()` |
| `frontend/src/hooks/use-cv.ts` | Pass `humanize` through to `customizeCV()` |
| `frontend/src/components/customize-cv-dialog.tsx` | Add toggle, badge, tooltip |

## Success Criteria

- [x] Humanization is ON by default — all new CV customizations run the 5-pass pipeline
- [x] User can toggle humanization OFF to get raw Pass 1 output
- [x] Toggle persists during the dialog session (not stored in DB)
- [x] "Humanized" badge appears when humanization was applied
- [x] Warning badge shows count of verification warnings
- [x] `humanize=False` skips Passes 2-5 and returns Pass 1 output directly
- [x] Cached results bypass the pipeline regardless of toggle (use `force_regenerate` to re-run)
