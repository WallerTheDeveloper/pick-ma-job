/** MSW request handlers for tests. */

import { http, HttpResponse } from "msw";

const TEST_USER = {
  id: "00000000-0000-0000-0000-000000000001",
  email: "test@example.com",
  is_admin: false,
};

const TEST_RUN_ID = "00000000-0000-0000-0000-000000000099";

export function makeDashboardResponse(overrides?: Record<string, unknown>) {
  return {
    user: TEST_USER,
    has_profile: true,
    config_count: 2,
    recent_runs: [],
    ...overrides,
  };
}

/** Tracks how many times status has been polled so we can simulate transitions. */
let statusPollCount = 0;

export function resetPollCount() {
  statusPollCount = 0;
}

export const handlers = [
  // Auth
  http.get("/auth/me", () =>
    HttpResponse.json({ user: TEST_USER }),
  ),

  // Dashboard
  http.get("/api/dashboard", () =>
    HttpResponse.json(makeDashboardResponse()),
  ),

  // Start run
  http.post("/api/run", () =>
    HttpResponse.json({ run_id: TEST_RUN_ID }, { status: 202 }),
  ),

  // Run status — transitions from running → completed after 2 polls
  http.get(`/api/run/:runId/status`, () => {
    statusPollCount++;
    if (statusPollCount >= 3) {
      return HttpResponse.json({
        run_id: TEST_RUN_ID,
        status: "completed",
        started_at: "2026-04-06T10:00:00Z",
        completed_at: "2026-04-06T10:01:00Z",
        result: {
          jobs_found: 25,
          jobs_skipped_dedup: 5,
          jobs_skipped_filter: 3,
          jobs_evaluated: 17,
          jobs_stored: 17,
          errors: [],
        },
        error: null,
      });
    }
    return HttpResponse.json({
      run_id: TEST_RUN_ID,
      status: "running",
      started_at: "2026-04-06T10:00:00Z",
      completed_at: null,
      result: null,
      error: null,
    });
  }),
];
