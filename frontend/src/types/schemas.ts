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
