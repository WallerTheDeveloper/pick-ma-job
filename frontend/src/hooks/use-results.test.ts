/**
 * Tests for the useResults hook.
 *
 * Covers:
 * - FE-13: minScore NaN guard — non-numeric strings must not send NaN to the API
 */

import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import React from "react";
import { useResults } from "@/hooks/use-results";
import { makeResultsList } from "@/test/handlers";

// ── MSW server ───────────────────────────────────────────────────────────────

const capturedUrls: string[] = [];

const server = setupServer(
  http.get("/api/results", ({ request }) => {
    capturedUrls.push(request.url);
    return HttpResponse.json(makeResultsList());
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  capturedUrls.length = 0;
});
afterAll(() => server.close());

// ── Wrapper ───────────────────────────────────────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      React.createElement(MemoryRouter, null, children),
    );
  };
}

// ── FE-13: NaN guard on minScore ─────────────────────────────────────────────

describe("useResults — minScore NaN guard", () => {
  it("does NOT include min_score in the query when minScore is empty", async () => {
    const { result } = renderHook(() => useResults({ minScore: "" }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    const url = capturedUrls.at(-1)!;
    expect(url).not.toContain("min_score");
  });

  it("does NOT include min_score when minScore is a non-numeric string", async () => {
    const { result } = renderHook(() => useResults({ minScore: "abc" }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    const url = capturedUrls.at(-1)!;
    expect(url).not.toContain("min_score=NaN");
    expect(url).not.toContain("min_score=");
  });

  it("does NOT include min_score when minScore is 'NaN' string", async () => {
    const { result } = renderHook(() => useResults({ minScore: "NaN" }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    const url = capturedUrls.at(-1)!;
    expect(url).not.toContain("min_score");
  });

  it("includes a numeric min_score when minScore is a valid number string", async () => {
    const { result } = renderHook(() => useResults({ minScore: "7" }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    const url = capturedUrls.at(-1)!;
    expect(url).toContain("min_score=7");
  });

  it("includes min_score=1 for the boundary value '1'", async () => {
    const { result } = renderHook(() => useResults({ minScore: "1" }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    const url = capturedUrls.at(-1)!;
    expect(url).toContain("min_score=1");
  });
});

// ── updateFilter resets pagination ───────────────────────────────────────────

describe("useResults — updateFilter", () => {
  it("returns results from the hook", async () => {
    const { result } = renderHook(() => useResults(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.results.length).toBeGreaterThan(0);
  });

  it("starts with default empty filters", () => {
    const { result } = renderHook(() => useResults(), { wrapper: createWrapper() });
    expect(result.current.filters.status).toBe("");
    expect(result.current.filters.minScore).toBe("");
    expect(result.current.filters.platform).toBe("");
  });
});
