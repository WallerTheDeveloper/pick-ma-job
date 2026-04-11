/**
 * Tests for the ProtectedRoute component.
 *
 * Covers:
 * - FE-14: Redirects to /login (not /) when user is not authenticated or auth fails
 */

import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { handlers } from "@/test/handlers";
import { renderWithProviders } from "@/test/render";
import { ProtectedRoute } from "@/components/protected-route";
import { Routes, Route } from "react-router";

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Test helpers ──────────────────────────────────────────────────────────────

/**
 * Renders a minimal router tree:
 *   /protected — protected by ProtectedRoute, renders "Protected Content"
 *   /login     — renders "Login Page"
 *   /          — renders "Landing Page"
 */
function renderProtectedRoute(initialPath = "/protected") {
  return renderWithProviders(
    <Routes>
      <Route element={<ProtectedRoute />}>
        <Route path="/protected" element={<div>Protected Content</div>} />
      </Route>
      <Route path="/login" element={<div>Login Page</div>} />
      <Route path="/" element={<div>Landing Page</div>} />
    </Routes>,
    { initialEntries: [initialPath] },
  );
}

// ── FE-14: Redirect to /login ─────────────────────────────────────────────────

describe("ProtectedRoute", () => {
  it("renders protected content when the user is authenticated", async () => {
    // Default handler returns a valid user
    renderProtectedRoute();

    await waitFor(() => {
      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });
  });

  it("shows a loading state while auth is in flight", () => {
    // Artificially delay /auth/me so the loading branch is visible
    server.use(
      http.get("/auth/me", async () => {
        await new Promise(() => {}); // never resolves in this test
        return HttpResponse.json({});
      }),
    );

    renderProtectedRoute();
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("redirects to /login when the user is not authenticated (401)", async () => {
    server.use(
      http.get("/auth/me", () =>
        HttpResponse.json({ detail: "Unauthorized" }, { status: 401 }),
      ),
    );

    renderProtectedRoute();

    await waitFor(() => {
      expect(screen.getByText("Login Page")).toBeInTheDocument();
    });

    // Must NOT redirect to the root landing page
    expect(screen.queryByText("Landing Page")).not.toBeInTheDocument();
  });

  it("redirects to /login on a 403 Forbidden response", async () => {
    server.use(
      http.get("/auth/me", () =>
        HttpResponse.json({ detail: "Forbidden" }, { status: 403 }),
      ),
    );

    renderProtectedRoute();

    await waitFor(() => {
      expect(screen.getByText("Login Page")).toBeInTheDocument();
    });
  });

  it("redirects to /login on a 500 server error", async () => {
    server.use(
      http.get("/auth/me", () =>
        HttpResponse.json({ detail: "Internal error" }, { status: 500 }),
      ),
    );

    renderProtectedRoute();

    await waitFor(() => {
      expect(screen.getByText("Login Page")).toBeInTheDocument();
    });
  });

  it("does NOT redirect to / when auth fails", async () => {
    server.use(
      http.get("/auth/me", () =>
        HttpResponse.json({ detail: "Unauthorized" }, { status: 401 }),
      ),
    );

    renderProtectedRoute();

    await waitFor(() => {
      // The destination must be /login, not /
      expect(screen.getByText("Login Page")).toBeInTheDocument();
    });

    expect(screen.queryByText("Landing Page")).not.toBeInTheDocument();
  });
});
