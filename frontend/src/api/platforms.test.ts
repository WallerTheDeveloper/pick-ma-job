/**
 * Tests for Zod schema validation of platform-related API responses.
 *
 * Covers:
 * - T-09: platformInfoSchema and platformsListResponseSchema accept valid data
 * - T-09: platformsListResponseSchema rejects invalid data
 * - T-09: startRun sends a JSON body with platforms
 */

import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { platformInfoSchema, platformsListResponseSchema } from "@/types/schemas";
import { fetchPlatforms } from "@/api/platforms";
import { startRun } from "@/api/pipeline";

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Zod schema unit tests ────────────────────────────────────────────────────

describe("platformInfoSchema", () => {
  it("accepts a valid platform info object", () => {
    const result = platformInfoSchema.safeParse({ slug: "upwork", has_config: true });
    expect(result.success).toBe(true);
  });

  it("accepts has_config = false", () => {
    const result = platformInfoSchema.safeParse({ slug: "linkedin", has_config: false });
    expect(result.success).toBe(true);
  });

  it("rejects missing slug", () => {
    const result = platformInfoSchema.safeParse({ has_config: true });
    expect(result.success).toBe(false);
  });

  it("rejects non-boolean has_config", () => {
    const result = platformInfoSchema.safeParse({ slug: "upwork", has_config: "yes" });
    expect(result.success).toBe(false);
  });
});

describe("platformsListResponseSchema", () => {
  it("accepts a valid platforms list response", () => {
    const result = platformsListResponseSchema.safeParse({
      platforms: [
        { slug: "upwork", has_config: true },
        { slug: "linkedin", has_config: false },
      ],
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.platforms).toHaveLength(2);
    }
  });

  it("accepts an empty platforms array", () => {
    const result = platformsListResponseSchema.safeParse({ platforms: [] });
    expect(result.success).toBe(true);
  });

  it("rejects a response missing the platforms key", () => {
    const result = platformsListResponseSchema.safeParse({ items: [] });
    expect(result.success).toBe(false);
  });

  it("rejects a platform entry with an invalid shape", () => {
    const result = platformsListResponseSchema.safeParse({
      platforms: [{ slug: 42, has_config: true }],
    });
    expect(result.success).toBe(false);
  });
});

// ── Integration: fetchPlatforms hits /api/platforms ──────────────────────────

describe("fetchPlatforms", () => {
  it("returns parsed platforms list from the API", async () => {
    server.use(
      http.get("/api/platforms", () =>
        HttpResponse.json({
          platforms: [
            { slug: "upwork", has_config: true },
            { slug: "linkedin", has_config: false },
          ],
        }),
      ),
    );

    const data = await fetchPlatforms();
    expect(data.platforms).toHaveLength(2);
    expect(data.platforms[0].slug).toBe("upwork");
    expect(data.platforms[1].has_config).toBe(false);
  });

  it("throws when the API response does not match the schema", async () => {
    server.use(
      http.get("/api/platforms", () =>
        HttpResponse.json({ wrong: "shape" }),
      ),
    );

    await expect(fetchPlatforms()).rejects.toThrow();
  });
});

// ── Integration: startRun sends JSON body ────────────────────────────────────

describe("startRun", () => {
  it("sends a JSON body with platforms when provided", async () => {
    let receivedBody: unknown;
    server.use(
      http.post("/api/run", async ({ request }) => {
        receivedBody = await request.json();
        return HttpResponse.json({ run_id: "a1b2c3d4-e5f6-4a7b-8c9d-000000000001" });
      }),
    );

    await startRun({ platforms: ["upwork", "linkedin"] });
    expect(receivedBody).toEqual({ platforms: ["upwork", "linkedin"] });
  });

  it("sends an empty body when no args provided", async () => {
    let receivedBody: unknown;
    server.use(
      http.post("/api/run", async ({ request }) => {
        receivedBody = await request.json();
        return HttpResponse.json({ run_id: "a1b2c3d4-e5f6-4a7b-8c9d-000000000002" });
      }),
    );

    await startRun();
    expect(receivedBody).toEqual({});
  });

  it("sends an empty body when platforms is undefined", async () => {
    let receivedBody: unknown;
    server.use(
      http.post("/api/run", async ({ request }) => {
        receivedBody = await request.json();
        return HttpResponse.json({ run_id: "a1b2c3d4-e5f6-4a7b-8c9d-000000000003" });
      }),
    );

    await startRun({});
    expect(receivedBody).toEqual({});
  });
});
