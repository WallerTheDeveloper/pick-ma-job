/** MSW request handlers for tests. */

import { http, HttpResponse } from "msw";

const TEST_USER = {
  id: "00000000-0000-0000-0000-000000000001",
  email: "test@example.com",
  is_admin: false,
};

const TEST_RUN_ID = "00000000-0000-0000-0000-000000000099";

function makeJobResult(overrides?: Record<string, unknown>) {
  return {
    id: "00000000-0000-0000-0000-000000000010",
    platform: "upwork",
    job_id: "job-001",
    title: "Unity AR Developer Needed",
    url: "https://upwork.com/jobs/1",
    score: 9,
    evaluation: {
      scratchpad: "Strong AR/VR match",
      evaluation: "Excellent fit for Unity AR work",
      relevancy_score: 9,
      recommendation: "Yes apply",
      flags: "AR, Unity, Mobile",
      summary: "Perfect match for Unity AR developer",
    },
    status: "new",
    created_at: "2026-04-06T10:00:00Z",
    ...overrides,
  };
}

function makeResultsList(
  results?: Record<string, unknown>[],
  pagination?: Record<string, unknown>,
) {
  const items = results ?? [
    makeJobResult(),
    makeJobResult({
      id: "00000000-0000-0000-0000-000000000011",
      job_id: "job-002",
      title: "React Frontend Developer",
      score: 3,
      status: "dismissed",
      platform: "linkedin",
      evaluation: {
        scratchpad: "Pure frontend role",
        evaluation: "Not a good fit — pure React role",
        relevancy_score: 3,
        recommendation: "Do not apply",
        flags: "React only, No Unity",
        summary: "Pure frontend web role, not relevant",
      },
    }),
    makeJobResult({
      id: "00000000-0000-0000-0000-000000000012",
      job_id: "job-003",
      title: "Rust Game Server Engineer",
      score: 8,
      status: "applied",
      evaluation: {
        scratchpad: "Rust multiplayer match",
        evaluation: "Good fit for Rust game server work",
        relevancy_score: 8,
        recommendation: "Yes apply",
        flags: "Rust, Multiplayer, Networking",
        summary: "Strong match for Rust game server role",
      },
    }),
  ];
  return {
    results: items,
    pagination: {
      total: items.length,
      page: 1,
      limit: 50,
      total_pages: 1,
      ...pagination,
    },
  };
}

function makeProfile(overrides?: Record<string, unknown>) {
  return {
    id: "00000000-0000-0000-0000-000000000020",
    role: "Unity Developer",
    experience: "Mid-level, 4 years",
    rate: "$30/hr",
    primary_skills: ["Unity", "C#", "AR/VR"],
    secondary_skills: ["Rust", "C++"],
    tertiary_skills: ["Vue.js", "TypeScript"],
    not_a_good_fit: ["Data science", "DevOps-only"],
    background: [
      "2 years AR & Web Developer at ZAUBAR",
      "2 years Backend Developer at Intelligent Project",
    ],
    notable_projects: [
      { name: "Rust Multiplayer Game", description: "Authoritative game server" },
    ],
    languages: ["English", "Ukrainian", "German"],
    rubric: {},
    updated_at: "2026-04-06T10:00:00Z",
    ...overrides,
  };
}

function makeSearchConfig(overrides?: Record<string, unknown>) {
  return {
    id: "00000000-0000-0000-0000-000000000030",
    platform: "upwork",
    query: "unity developer",
    filters: {
      experienceLevel: ["entry", "intermediate"],
      jobType: ["fixed", "hourly"],
      paymentVerified: true,
      perPage: 50,
      sort: "newest",
      maxJobAge: { value: 24, unit: "hours" },
    },
    updated_at: "2026-04-06T10:00:00Z",
    ...overrides,
  };
}

function makeAdminUser(overrides?: Record<string, unknown>) {
  return {
    id: "00000000-0000-0000-0000-000000000001",
    email: "admin@example.com",
    created_at: "2026-01-15T08:00:00Z",
    last_login: "2026-04-06T09:30:00Z",
    job_count: 42,
    ...overrides,
  };
}

export { makeJobResult, makeResultsList, makeProfile, makeSearchConfig, makeAdminUser };

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

  // Profile — GET returns existing profile
  http.get("/api/profile", () =>
    HttpResponse.json({ profile: makeProfile() }),
  ),

  // Profile — POST saves and returns updated profile
  http.post("/api/profile", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ profile: makeProfile(body) });
  }),

  // Results list
  http.get("/api/results", ({ request }) => {
    const url = new URL(request.url);
    const statusFilter = url.searchParams.get("status");
    const minScore = url.searchParams.get("min_score");
    const platform = url.searchParams.get("platform");
    const page = parseInt(url.searchParams.get("page") ?? "1", 10);

    let results = makeResultsList().results;

    if (statusFilter) {
      results = results.filter((r) => r.status === statusFilter);
    }
    if (minScore) {
      results = results.filter((r) => (r.score ?? 0) >= parseInt(minScore, 10));
    }
    if (platform) {
      results = results.filter((r) => r.platform === platform);
    }

    return HttpResponse.json({
      results,
      pagination: {
        total: results.length,
        page,
        limit: 50,
        total_pages: Math.max(1, Math.ceil(results.length / 50)),
      },
    });
  }),

  // Update result status
  http.patch("/api/results/:resultId", async ({ request, params }) => {
    const body = (await request.json()) as { status: string };
    const base = makeJobResult({ id: params.resultId });
    return HttpResponse.json({ ...base, status: body.status });
  }),

  // Search configs — list
  http.get("/api/search-configs", () =>
    HttpResponse.json({ configs: [makeSearchConfig()] }),
  ),

  // Search configs — create
  http.post("/api/search-configs", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      config: makeSearchConfig({
        id: "00000000-0000-0000-0000-000000000031",
        ...body,
      }),
    });
  }),

  // Search configs — delete
  http.delete("/api/search-configs/:configId", () =>
    HttpResponse.json({ ok: true }),
  ),

  // Admin — users list
  http.get("/api/admin/users", () =>
    HttpResponse.json({
      users: [
        makeAdminUser(),
        makeAdminUser({
          id: "00000000-0000-0000-0000-000000000002",
          email: "user@example.com",
          created_at: "2026-03-01T12:00:00Z",
          last_login: null,
          job_count: 0,
        }),
      ],
    }),
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
