# Task 8 — Create frontend types and API client

**Size:** S  
**Status:** done

## Goal

Add Zod schemas, TypeScript types, and the API client module for the blacklist feature.

## Types

File: `frontend/src/types/company-blacklist.ts`

```ts
import { z } from "zod";

export const CompanyBlacklistEntrySchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  created_at: z.string().datetime(),
});

export const CompanyBlacklistListResponseSchema = z.object({
  entries: z.array(CompanyBlacklistEntrySchema),
});

export type CompanyBlacklistEntry = z.infer<typeof CompanyBlacklistEntrySchema>;
export type CompanyBlacklistListResponse = z.infer<typeof CompanyBlacklistListResponseSchema>;
```

## API Client

File: `frontend/src/api/company-blacklist.ts`

```ts
export async function listBlacklist(): Promise<CompanyBlacklistListResponse>
export async function addBlacklist(name: string): Promise<CompanyBlacklistEntry>
export async function removeBlacklist(id: string): Promise<void>
```

- Use the existing `client.ts` base fetch wrapper.
- Validate responses with Zod schemas before returning.
- `removeBlacklist` is a DELETE request — handle 204 (no body).

## Success Criteria

- Invalid API responses (missing fields) throw a Zod validation error, not a runtime crash.
- All three functions type-check correctly.
