import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { handlers, makeDashboardResponse, resetPollCount } from "@/test/handlers";
import { renderWithProviders } from "@/test/render";
import { DashboardPage } from "@/pages/dashboard";

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  resetPollCount();
});
afterAll(() => server.close());

describe("DashboardPage", () => {
  it("renders welcome message and stats cards", async () => {
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Dashboard")).toBeInTheDocument();
    });

    expect(screen.getByText(/test@example\.com/)).toBeInTheDocument();
    expect(screen.getByText("Configured")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("disables Run Pipeline button when profile is missing", async () => {
    server.use(
      http.get("/api/dashboard", () =>
        HttpResponse.json(makeDashboardResponse({ has_profile: false })),
      ),
    );

    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Run Pipeline")).toBeInTheDocument();
    });

    expect(screen.getByText("Run Pipeline")).toBeDisabled();
    expect(screen.getByText("Set up your profile first.")).toBeInTheDocument();
  });

  it("disables Run Pipeline button when no search configs", async () => {
    server.use(
      http.get("/api/dashboard", () =>
        HttpResponse.json(makeDashboardResponse({ config_count: 0 })),
      ),
    );

    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Run Pipeline")).toBeInTheDocument();
    });

    expect(screen.getByText("Run Pipeline")).toBeDisabled();
    expect(
      screen.getByText("Add at least one search config."),
    ).toBeInTheDocument();
  });

  it("triggers pipeline run and polls status until completed", async () => {
    const user = userEvent.setup();

    renderWithProviders(<DashboardPage />);

    // Wait for dashboard to load
    await waitFor(() => {
      expect(screen.getByText("Run Pipeline")).toBeEnabled();
    });

    // Click run
    await user.click(screen.getByText("Run Pipeline"));

    // Should show running state
    await waitFor(() => {
      expect(screen.getByText("Running")).toBeInTheDocument();
    });

    // Should eventually poll to completed and show result summary
    await waitFor(
      () => {
        expect(screen.getByText("Completed")).toBeInTheDocument();
      },
      { timeout: 10000 },
    );

    // Verify result summary is displayed
    expect(screen.getByText("Jobs found")).toBeInTheDocument();
    expect(screen.getByText("25")).toBeInTheDocument();
    expect(screen.getByText("Evaluated")).toBeInTheDocument();
    expect(screen.getAllByText("17")).toHaveLength(2); // Evaluated + Stored
  });

  it("displays error when run start fails", async () => {
    const user = userEvent.setup();

    server.use(
      http.post("/api/run", () =>
        HttpResponse.json(
          { detail: "Profile not configured." },
          { status: 400 },
        ),
      ),
    );

    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Run Pipeline")).toBeEnabled();
    });

    // The mutation rejects — catch it so it doesn't become an unhandled rejection
    await user.click(screen.getByText("Run Pipeline"));

    await waitFor(() => {
      expect(screen.getByText(/Profile not configured/)).toBeInTheDocument();
    });
  });

  it("shows failed run status with error message", async () => {
    const user = userEvent.setup();

    server.use(
      http.get("/api/run/:runId/status", () =>
        HttpResponse.json({
          run_id: "00000000-0000-0000-0000-000000000099",
          status: "failed",
          started_at: "2026-04-06T10:00:00Z",
          completed_at: "2026-04-06T10:00:30Z",
          result: null,
          error: "Apify actor timed out",
        }),
      ),
    );

    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Run Pipeline")).toBeEnabled();
    });

    await user.click(screen.getByText("Run Pipeline"));

    await waitFor(() => {
      expect(screen.getByText("Failed")).toBeInTheDocument();
    });

    expect(screen.getByText("Apify actor timed out")).toBeInTheDocument();
  });
});
