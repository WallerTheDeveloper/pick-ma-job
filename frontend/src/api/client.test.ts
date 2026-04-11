/**
 * Tests for the base API client.
 *
 * Covers:
 * - FE-3: Zod schema passed to api() validates the response at runtime
 * - FE-4: CSRF token warning when missing on state-changing requests
 * - FE-5: getCsrfToken preserves full cookie value when it contains `=`
 */

import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { z } from "zod";
import { api, ApiError } from "@/api/client";

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  document.cookie = "csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/";
});
afterAll(() => server.close());

// ── FE-3: Zod runtime validation ─────────────────────────────────────────────

describe("api() — Zod schema validation", () => {
  it("returns parsed data when response matches the schema", async () => {
    server.use(
      http.get("/api/test", () => HttpResponse.json({ id: 1, name: "Alice" })),
    );

    const schema = z.object({ id: z.number(), name: z.string() });
    const result = await api("/api/test", {}, schema);
    expect(result).toEqual({ id: 1, name: "Alice" });
  });

  it("throws a ZodError when response does not match the schema", async () => {
    server.use(
      http.get("/api/test", () => HttpResponse.json({ wrong_field: true })),
    );

    const schema = z.object({ id: z.number(), name: z.string() });
    await expect(api("/api/test", {}, schema)).rejects.toThrow();
  });

  it("returns data as-is when no schema is provided", async () => {
    server.use(
      http.get("/api/test", () => HttpResponse.json({ anything: "goes" })),
    );

    const result = await api("/api/test");
    expect(result).toEqual({ anything: "goes" });
  });

  it("throws ApiError on non-ok HTTP status", async () => {
    server.use(
      http.get("/api/test", () =>
        HttpResponse.json({ detail: "Not found" }, { status: 404 }),
      ),
    );

    const error = await api("/api/test").catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(404);
    expect((error as ApiError).message).toBe("Not found");
  });

  it("returns undefined for 204 No Content", async () => {
    server.use(
      http.delete("/api/test", () => new HttpResponse(null, { status: 204 })),
    );

    const result = await api("/api/test", { method: "DELETE" });
    expect(result).toBeUndefined();
  });
});

// ── FE-5: CSRF cookie truncation fix ─────────────────────────────────────────

describe("CSRF cookie parsing", () => {
  it("sends the full CSRF token value even when it contains `=` characters", async () => {
    // base64-like token value that contains padding `=`
    const tokenWithEquals = "abc123==";
    document.cookie = `csrf_token=${tokenWithEquals}; path=/`;

    let receivedCsrfHeader: string | null = null;
    server.use(
      http.post("/api/test", ({ request }) => {
        receivedCsrfHeader = request.headers.get("X-CSRF-Token");
        return HttpResponse.json({ ok: true });
      }),
    );

    await api("/api/test", { method: "POST", body: {} });
    expect(receivedCsrfHeader).toBe(tokenWithEquals);
  });

  it("sends the full CSRF token when value contains multiple `=`", async () => {
    const token = "dGVzdA==base64==end";
    document.cookie = `csrf_token=${token}; path=/`;

    let receivedHeader: string | null = null;
    server.use(
      http.post("/api/test", ({ request }) => {
        receivedHeader = request.headers.get("X-CSRF-Token");
        return HttpResponse.json({ ok: true });
      }),
    );

    await api("/api/test", { method: "POST", body: {} });
    expect(receivedHeader).toBe(token);
  });

  it("sends the CSRF header when a valid token exists", async () => {
    document.cookie = "csrf_token=my-token; path=/";

    let headerSent: string | null = null;
    server.use(
      http.post("/api/test", ({ request }) => {
        headerSent = request.headers.get("X-CSRF-Token");
        return HttpResponse.json({ ok: true });
      }),
    );

    await api("/api/test", { method: "POST", body: {} });
    expect(headerSent).toBe("my-token");
  });

  it("omits the CSRF header when no csrf_token cookie is present", async () => {
    let headerSent: string | null = "sentinel";
    server.use(
      http.post("/api/test", ({ request }) => {
        headerSent = request.headers.get("X-CSRF-Token");
        return HttpResponse.json({ ok: true });
      }),
    );

    await api("/api/test", { method: "POST", body: {} });
    expect(headerSent).toBeNull();
  });
});

// ── FE-4: CSRF silent omission warning ───────────────────────────────────────

describe("CSRF missing warning (DEV mode)", () => {
  it("logs a console.warn when making a POST with no CSRF token", async () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    server.use(
      http.post("/api/test", () => HttpResponse.json({ ok: true })),
    );

    await api("/api/test", { method: "POST", body: {} });

    // In the test environment import.meta.env.DEV is true
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining("CSRF token missing"),
    );
    warnSpy.mockRestore();
  });

  it("does not warn when CSRF token is present", async () => {
    document.cookie = "csrf_token=valid; path=/";
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    server.use(
      http.post("/api/test", () => HttpResponse.json({ ok: true })),
    );

    await api("/api/test", { method: "POST", body: {} });
    expect(warnSpy).not.toHaveBeenCalled();
    warnSpy.mockRestore();
  });

  it("does not warn for GET requests with no CSRF token", async () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    server.use(
      http.get("/api/test", () => HttpResponse.json({ ok: true })),
    );

    await api("/api/test");
    expect(warnSpy).not.toHaveBeenCalled();
    warnSpy.mockRestore();
  });
});
