# Pick MA Job

## Bugs & Adjustments

1. AI evaluates client’s rating out of 10. So if client’s rating is 5 (which is max) then AI evaluates job as bad because it thinks that 10/10 is max when in reality 5/5 is max
2. Tab title is Vite+React+TS but must be Pick Most Appropriate Job
3. Icon of the tab must be custom instead of the Vite’s default
4. CRITICAL: pipeline works for my account - [golo7ov.danil@gmail.com](mailto:golo7ov.danil@gmail.com) but doesn’t work for other clients. When user clicks run pipeline button - object of type 'NoneType' has no len() and also following payload:

{
    "run_id": "fd74fc93-fcb4-4966-93da-2f67fd2dc92c",
    "status": "failed",
    "started_at": "2026-04-10T13:41:53.964434Z",
    "completed_at": "2026-04-10T13:41:54.020593Z",
    "result": null,
    "error": "object of type 'NoneType' has no len()"
}

## Features:

1. User must be able to add lists of jobs. Each job can be added to created list
2. User must be able to delete any row
3. If job is <5 then don’t even evaluate it. AI must first evaluate score before generating anything else. If score is too low - there is no point in generating anything else for this job - it must be just skipped. This way we can save tokens and make pipeline cheaper.
4. Explain that Pick MA Job means Pick Most Appropriate Job on the landing page
5. Add Dark mode theme