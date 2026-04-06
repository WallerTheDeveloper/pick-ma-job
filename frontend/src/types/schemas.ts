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

export const magicLinkErrorResponseSchema = z.object({
  ok: z.literal(false),
  error: z.string(),
});

export type MagicLinkErrorResponse = z.infer<typeof magicLinkErrorResponseSchema>;

// ── Pipeline ────────────────────────────────────────────────────────────────

export const runStartResponseSchema = z.object({
  run_id: z.string().uuid(),
});

export type RunStartResponse = z.infer<typeof runStartResponseSchema>;

export const runResultSchema = z.object({
  jobs_found: z.number(),
  jobs_skipped_dedup: z.number(),
  jobs_skipped_filter: z.number(),
  jobs_evaluated: z.number(),
  jobs_stored: z.number(),
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

// ── Dashboard ───────────────────────────────────────────────────────────────

export const pipelineRunInfoSchema = z.object({
  id: z.string().uuid(),
  status: z.string(),
  started_at: z.string(),
  completed_at: z.string().nullable(),
  result: z.record(z.string(), z.unknown()).nullable(),
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
