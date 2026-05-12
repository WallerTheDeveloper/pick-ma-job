/** Zod schemas matching backend Pydantic models (api/schemas.py). */

import { z } from "zod";

// ── Auth ─────────────────────────────────────────────────────────────────────

export const userInfoSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  is_admin: z.boolean(),
});

export type UserInfo = z.infer<typeof userInfoSchema>;

export const authMeResponseSchema = z.object({
  user: userInfoSchema,
});

export type AuthMeResponse = z.infer<typeof authMeResponseSchema>;

export const okResponseSchema = z.object({
  ok: z.boolean(),
});

export type OkResponse = z.infer<typeof okResponseSchema>;

// ── Pipeline ────────────────────────────────────────────────────────────────

export const runStartResponseSchema = z.object({
  run_id: z.string().uuid(),
});

export type RunStartResponse = z.infer<typeof runStartResponseSchema>;

export const runResultSchema = z.object({
  jobs_found: z.number(),
  jobs_skipped_dedup: z.number(),
  jobs_skipped_filter: z.number(),
  jobs_skipped_blacklist: z.number().optional(),
  jobs_skipped_language: z.number().optional(),
  jobs_skipped_closed: z.number().optional(),
  jobs_skipped_low_score: z.number().optional(),
  jobs_stored: z.number(),
  rate_limit_hits: z.number().default(0),
  rate_limit_wait_seconds: z.number().default(0),
  total_input_tokens: z.number().default(0),
  total_output_tokens: z.number().default(0),
  errors: z.array(z.string()),
});

export type RunResult = z.infer<typeof runResultSchema>;

export const runStatusResponseSchema = z.object({
  run_id: z.string().uuid(),
  status: z.string(),
  started_at: z.string(),
  completed_at: z.string().nullable(),
  result: runResultSchema.nullable(),
  error: z.string().nullable(),
});

export type RunStatusResponse = z.infer<typeof runStatusResponseSchema>;

// ── Results ────────────────────────────────────────────────────────────────

export const jobResultSchema = z.object({
  id: z.string().uuid(),
  platform: z.string(),
  job_id: z.string(),
  title: z.string(),
  url: z.string(),
  score: z.number().nullable(),
  evaluation: z
    .object({
      scratchpad: z.string().optional(),
      evaluation: z.string().optional(),
      relevancy_score: z.number().optional(),
      recommendation: z.string().optional(),
      flags: z.string().optional(),
      summary: z.string().optional(),
    })
    .nullable(),
  skip_reason: z.string().nullable().optional(),
  detected_language: z.string().nullable().optional(),
  is_closed: z.boolean().default(false),
  status: z.string(),
  created_at: z.string(),
});

export type JobResult = z.infer<typeof jobResultSchema>;

export const paginationMetaSchema = z.object({
  total: z.number(),
  limit: z.number(),
  page: z.number().optional(),
  total_pages: z.number().optional(),
});

export type PaginationMeta = z.infer<typeof paginationMetaSchema>;

export const resultsListResponseSchema = z.object({
  results: z.array(jobResultSchema),
  pagination: paginationMetaSchema,
  next_cursor: z.string().nullable().optional(),
});

export type ResultsListResponse = z.infer<typeof resultsListResponseSchema>;

export const resultStatusValues = ["new", "applied", "dismissed"] as const;
export type ResultStatus = (typeof resultStatusValues)[number];

// ── Profile ────────────────────────────────────────────────────────────────

export const notableProjectSchema = z.object({
  name: z.string(),
  description: z.string(),
});

export type NotableProject = z.infer<typeof notableProjectSchema>;

export const profileResponseSchema = z.object({
  id: z.string().uuid(),
  role: z.string().nullable(),
  experience: z.string().nullable(),
  rate: z.string().nullable(),
  primary_skills: z.array(z.string()),
  secondary_skills: z.array(z.string()),
  tertiary_skills: z.array(z.string()),
  not_a_good_fit: z.array(z.string()),
  background: z.array(z.string()),
  notable_projects: z.array(notableProjectSchema),
  languages: z.array(z.string()),
  rubric: z.record(z.string(), z.unknown()),
  cv_customize_threshold: z.number().int().min(1).max(10).default(7),
  exclude_keywords: z.array(z.string()).default([]),
  updated_at: z.string(),
});

export type ProfileResponse = z.infer<typeof profileResponseSchema>;

export const profileGetResponseSchema = z.object({
  profile: profileResponseSchema.nullable(),
});

export type ProfileGetResponse = z.infer<typeof profileGetResponseSchema>;

export const structuredRubricSchema = z.object({
  min_score: z.number().min(1).max(10).optional(),
  prefer_remote: z.boolean().optional(),
  priority_keywords: z.array(z.string()).optional(),
  avoid_keywords: z.array(z.string()).optional(),
});

export type StructuredRubric = z.infer<typeof structuredRubricSchema>;

export const profileSaveRequestSchema = z.object({
  role: z.string().nullable().default(null),
  experience: z.string().nullable().default(null),
  rate: z.string().nullable().default(null),
  primary_skills: z.array(z.string()).default([]),
  secondary_skills: z.array(z.string()).default([]),
  tertiary_skills: z.array(z.string()).default([]),
  not_a_good_fit: z.array(z.string()).default([]),
  background: z.array(z.string()).default([]),
  notable_projects: z.array(notableProjectSchema).default([]),
  languages: z.array(z.string()).default([]),
  rubric: z.record(z.string(), z.unknown()).default({}),
  cv_customize_threshold: z.number().int().min(1).max(10).default(7),
  exclude_keywords: z.array(z.string()).default([]),
});

// ── CV ─────────────────────────────────────────────────────────────────────

export const cvMetadataSchema = z.object({
  filename: z.string(),
  structured: z.record(z.string(), z.unknown()),
  updated_at: z.string(),
});

export type CVMetadata = z.infer<typeof cvMetadataSchema>;

export const cvGetResponseSchema = z.object({
  cv: cvMetadataSchema.nullable(),
});

export type CVGetResponse = z.infer<typeof cvGetResponseSchema>;

export const cvUploadResponseSchema = z.object({
  filename: z.string(),
  structured: z.record(z.string(), z.unknown()),
  updated_at: z.string(),
});

export type CVUploadResponse = z.infer<typeof cvUploadResponseSchema>;

export const cvSectionDiffSchema = z.object({
  title: z.string(),
  content: z.string(),
  changed: z.boolean(),
});

export type CVSectionDiff = z.infer<typeof cvSectionDiffSchema>;

export const cvCustomizeResponseSchema = z.object({
  customized_text: z.string(),
  from_cache: z.boolean(),
  warnings: z.array(z.string()).default([]),
  sections: z.array(cvSectionDiffSchema).nullable().optional(),
});

export type CVCustomizeResponse = z.infer<typeof cvCustomizeResponseSchema>;

export type ProfileSaveRequest = z.infer<typeof profileSaveRequestSchema>;

export const profileSaveResponseSchema = z.object({
  profile: profileResponseSchema,
});

export type ProfileSaveResponse = z.infer<typeof profileSaveResponseSchema>;

// ── Search Config ──────────────────────────────────────────────────────────

export const platformValues = ["upwork", "linkedin"] as const;
export type Platform = (typeof platformValues)[number];

export const searchConfigResponseSchema = z.object({
  id: z.string().uuid(),
  platform: z.enum(platformValues),
  query: z.string().nullable(),
  filters: z.record(z.string(), z.unknown()),
  updated_at: z.string(),
});

export type SearchConfigResponse = z.infer<typeof searchConfigResponseSchema>;

export const searchConfigsListResponseSchema = z.object({
  configs: z.array(searchConfigResponseSchema),
});

export type SearchConfigsListResponse = z.infer<typeof searchConfigsListResponseSchema>;

export const searchConfigCreateRequestSchema = z.object({
  platform: z.enum(platformValues),
  query: z.string().min(1, "Search query is required").nullable(),
  filters: z.record(z.string(), z.unknown()).default({}),
});

export type SearchConfigCreateRequest = z.infer<typeof searchConfigCreateRequestSchema>;

export const searchConfigCreateResponseSchema = z.object({
  config: searchConfigResponseSchema,
});

export type SearchConfigCreateResponse = z.infer<typeof searchConfigCreateResponseSchema>;

export const searchConfigUpdateRequestSchema = z.object({
  query: z.string().nullable(),
  filters: z.record(z.string(), z.unknown()).default({}),
});

export type SearchConfigUpdateRequest = z.infer<typeof searchConfigUpdateRequestSchema>;

// ── Job Lists ─────────────────────────────────────────────────────────────

export const jobListSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  created_at: z.string(),
});

export type JobList = z.infer<typeof jobListSchema>;

export const jobListsResponseSchema = z.object({
  lists: z.array(jobListSchema),
});

export type JobListsResponse = z.infer<typeof jobListsResponseSchema>;

export const jobListJobsResponseSchema = z.object({
  jobs: z.array(jobResultSchema),
});

export type JobListJobsResponse = z.infer<typeof jobListJobsResponseSchema>;

// ── Admin ──────────────────────────────────────────────────────────────────

export const userStatsSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  created_at: z.string(),
  last_login: z.string().nullable(),
  job_count: z.number(),
});

export type UserStats = z.infer<typeof userStatsSchema>;

export const adminUsersResponseSchema = z.object({
  users: z.array(userStatsSchema),
});

export type AdminUsersResponse = z.infer<typeof adminUsersResponseSchema>;

// ── Platforms ─────────────────────────────────────────────────────────────

export const platformInfoSchema = z.object({
  slug: z.string(),
  has_config: z.boolean(),
});

export type PlatformInfo = z.infer<typeof platformInfoSchema>;

export const platformsListResponseSchema = z.object({
  platforms: z.array(platformInfoSchema),
});

export type PlatformsListResponse = z.infer<typeof platformsListResponseSchema>;

// ── Evaluation ─────────────────────────────────────────────────────────────

export const bulkEvaluationRequestSchema = z.object({
  result_ids: z.array(z.string().uuid()).optional(),
  filter: z.object({
    platform: z.string().optional(),
    min_score: z.number().optional(),
    status: z.string().optional(),
  }).optional(),
});

export type BulkEvaluationRequest = z.infer<typeof bulkEvaluationRequestSchema>;

export const evaluationResponseSchema = z.object({
  result: jobResultSchema,
});

export type EvaluationResponse = z.infer<typeof evaluationResponseSchema>;

export const bulkEvaluationResponseSchema = z.object({
  total: z.number(),
  evaluated: z.number(),
  skipped_low_score: z.number(),
  failed: z.number(),
  updated_ids: z.array(z.string().uuid()),
});

export type BulkEvaluationResponse = z.infer<typeof bulkEvaluationResponseSchema>;

// ── Version ────────────────────────────────────────────────────────────────

export const versionResponseSchema = z.object({
  version: z.string(),
});

export type VersionResponse = z.infer<typeof versionResponseSchema>;

// ── Dashboard ───────────────────────────────────────────────────────────────

export const pipelineRunInfoSchema = z.object({
  id: z.string().uuid(),
  status: z.string(),
  started_at: z.string(),
  completed_at: z.string().nullable(),
  result: runResultSchema.nullable(),
  error: z.string().nullable(),
});

export type PipelineRunInfo = z.infer<typeof pipelineRunInfoSchema>;

export const dashboardResponseSchema = z.object({
  user: userInfoSchema,
  has_profile: z.boolean(),
  config_count: z.number(),
  recent_runs: z.array(pipelineRunInfoSchema),
});

export type DashboardResponse = z.infer<typeof dashboardResponseSchema>;

// ── Proposals ────────────────────────────────────────────────────────────────

export const proposalResponseSchema = z.object({
  proposal_text: z.string(),
  from_cache: z.boolean(),
});

export type ProposalResponse = z.infer<typeof proposalResponseSchema>;
