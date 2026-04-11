import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { handlers } from "@/test/handlers";
import { renderWithProviders } from "@/test/render";
import { AdminPage } from "@/pages/admin";

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("AdminPage", () => {
  it("redirects non-admin users to dashboard", async () => {
    // Default test user has is_admin: false
    renderWithProviders(<AdminPage />, { initialEntries: ["/admin"] });

    await waitFor(() => {
      expect(screen.queryByText("Admin — Users")).not.toBeInTheDocument();
    });
  });

  it("renders users table for admin users", async () => {
    server.use(
      http.get("/auth/me", () =>
        HttpResponse.json({
          user: {
            id: "00000000-0000-4000-8000-000000000001",
            email: "admin@example.com",
            is_admin: true,
          },
        }),
      ),
    );

    renderWithProviders(<AdminPage />);

    await waitFor(() => {
      expect(screen.getByText("Admin — Users")).toBeInTheDocument();
    });

    expect(screen.getByText("2 registered users")).toBeInTheDocument();

    // Table headers
    expect(screen.getByText("Email")).toBeInTheDocument();
    expect(screen.getByText("Registered")).toBeInTheDocument();
    expect(screen.getByText("Last Login")).toBeInTheDocument();
    expect(screen.getByText("Jobs")).toBeInTheDocument();

    // User rows
    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
    expect(screen.getByText("user@example.com")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();

    // user with null last_login shows "Never"
    expect(screen.getByText("Never")).toBeInTheDocument();
  });

  it("shows error state when API fails", async () => {
    server.use(
      http.get("/auth/me", () =>
        HttpResponse.json({
          user: {
            id: "00000000-0000-4000-8000-000000000001",
            email: "admin@example.com",
            is_admin: true,
          },
        }),
      ),
      http.get("/api/admin/users", () =>
        HttpResponse.json({ detail: "Forbidden" }, { status: 403 }),
      ),
    );

    renderWithProviders(<AdminPage />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load users/)).toBeInTheDocument();
    });
  });

  it("shows empty state when no users exist", async () => {
    server.use(
      http.get("/auth/me", () =>
        HttpResponse.json({
          user: {
            id: "00000000-0000-4000-8000-000000000001",
            email: "admin@example.com",
            is_admin: true,
          },
        }),
      ),
      http.get("/api/admin/users", () =>
        HttpResponse.json({ users: [] }),
      ),
    );

    renderWithProviders(<AdminPage />);

    await waitFor(() => {
      expect(screen.getByText("No users found.")).toBeInTheDocument();
    });
  });

  it("shows loading state while fetching", async () => {
    server.use(
      http.get("/auth/me", () =>
        HttpResponse.json({
          user: {
            id: "00000000-0000-4000-8000-000000000001",
            email: "admin@example.com",
            is_admin: true,
          },
        }),
      ),
      http.get("/api/admin/users", async () => {
        // Delay response so loading state is visible
        await new Promise((resolve) => setTimeout(resolve, 200));
        return HttpResponse.json({ users: [] });
      }),
    );

    renderWithProviders(<AdminPage />);

    // First shows auth loading, then users loading
    await waitFor(() => {
      expect(screen.getByText("Loading users...")).toBeInTheDocument();
    });
  });
});
