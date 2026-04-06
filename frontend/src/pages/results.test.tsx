import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { handlers, makeResultsList } from "@/test/handlers";
import { renderWithProviders } from "@/test/render";
import { ResultsPage } from "@/pages/results";

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("ResultsPage", () => {
  it("renders results list with score badges and titles", async () => {
    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Unity AR Developer Needed")).toBeInTheDocument();
    });

    expect(screen.getByText("React Frontend Developer")).toBeInTheDocument();
    expect(screen.getByText("Rust Game Server Engineer")).toBeInTheDocument();

    // Score badges
    expect(screen.getByText("9/10")).toBeInTheDocument();
    expect(screen.getByText("3/10")).toBeInTheDocument();
    expect(screen.getByText("8/10")).toBeInTheDocument();
  });

  it("shows empty state when no results", async () => {
    server.use(
      http.get("/api/results", () =>
        HttpResponse.json(makeResultsList([])),
      ),
    );

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/No results yet/),
      ).toBeInTheDocument();
    });
  });

  it("shows error state on API failure", async () => {
    server.use(
      http.get("/api/results", () =>
        HttpResponse.json({ detail: "Internal error" }, { status: 500 }),
      ),
    );

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load results/)).toBeInTheDocument();
    });
  });

  it("filters by status", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ResultsPage />);

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText("Unity AR Developer Needed")).toBeInTheDocument();
    });

    // All 3 results visible initially
    expect(screen.getByText("React Frontend Developer")).toBeInTheDocument();
    expect(screen.getByText("Rust Game Server Engineer")).toBeInTheDocument();

    // Open status dropdown and select "Dismissed"
    const statusTrigger = screen.getAllByText("All statuses")[0];
    await user.click(statusTrigger);
    await user.click(screen.getByText("Dismissed"));

    // Should now only show the dismissed result
    await waitFor(() => {
      expect(screen.getByText("React Frontend Developer")).toBeInTheDocument();
    });
    expect(screen.queryByText("Unity AR Developer Needed")).not.toBeInTheDocument();
    expect(screen.queryByText("Rust Game Server Engineer")).not.toBeInTheDocument();
  });

  it("filters by platform", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Unity AR Developer Needed")).toBeInTheDocument();
    });

    // Open platform dropdown and select "LinkedIn"
    const platformTrigger = screen.getAllByText("All platforms")[0];
    await user.click(platformTrigger);
    await user.click(screen.getByText("LinkedIn"));

    // Should only show linkedin result
    await waitFor(() => {
      expect(screen.getByText("React Frontend Developer")).toBeInTheDocument();
    });
    expect(screen.queryByText("Unity AR Developer Needed")).not.toBeInTheDocument();
    expect(screen.queryByText("Rust Game Server Engineer")).not.toBeInTheDocument();
  });

  it("filters by minimum score", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Unity AR Developer Needed")).toBeInTheDocument();
    });

    // Type min score of 7
    const minScoreInput = screen.getByPlaceholderText("Any");
    await user.type(minScoreInput, "7");

    // Should filter out the score=3 result
    await waitFor(() => {
      expect(screen.queryByText("React Frontend Developer")).not.toBeInTheDocument();
    });
    expect(screen.getByText("Unity AR Developer Needed")).toBeInTheDocument();
    expect(screen.getByText("Rust Game Server Engineer")).toBeInTheDocument();
  });

  it("clears filters with Clear filters button", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Unity AR Developer Needed")).toBeInTheDocument();
    });

    // Apply a filter
    const minScoreInput = screen.getByPlaceholderText("Any");
    await user.type(minScoreInput, "7");

    await waitFor(() => {
      expect(screen.queryByText("React Frontend Developer")).not.toBeInTheDocument();
    });

    // Clear filters button should appear
    const clearBtn = screen.getByText("Clear filters");
    await user.click(clearBtn);

    // All results should be back
    await waitFor(() => {
      expect(screen.getByText("React Frontend Developer")).toBeInTheDocument();
    });
    expect(screen.getByText("Unity AR Developer Needed")).toBeInTheDocument();
  });

  it("expands result row to show details", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Unity AR Developer Needed")).toBeInTheDocument();
    });

    // Details should not be visible yet
    expect(screen.queryByText("Perfect match for Unity AR developer")).not.toBeInTheDocument();

    // Click the row to expand
    await user.click(screen.getByText("Unity AR Developer Needed"));

    // Details should now be visible
    await waitFor(() => {
      expect(screen.getByText("Perfect match for Unity AR developer")).toBeInTheDocument();
    });
    expect(screen.getByText("Excellent fit for Unity AR work")).toBeInTheDocument();
    expect(screen.getByText("AR, Unity, Mobile")).toBeInTheDocument();
    expect(screen.getByText("Strong AR/VR match")).toBeInTheDocument();
    expect(screen.getByText("View job posting")).toBeInTheDocument();
  });

  it("updates result status via dropdown", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Unity AR Developer Needed")).toBeInTheDocument();
    });

    // Find the status select triggers inside result rows (combobox role).
    // The filter bar has 3 selects (status, platform, sort); result-row selects come after.
    const allComboboxes = screen.getAllByRole("combobox");
    // Filter bar has 3, then each result row has 1. First result's status = index 3.
    const firstStatusSelect = allComboboxes[3];
    await user.click(firstStatusSelect);

    // Select "Applied" from the opened popup
    await user.click(screen.getByText("Applied"));

    // The mutation should fire and refetch — verify no error appears
    await waitFor(() => {
      expect(screen.queryByText(/Failed to load/)).not.toBeInTheDocument();
    });
  });

  it("shows pagination controls when multiple pages", async () => {
    server.use(
      http.get("/api/results", ({ request }) => {
        const url = new URL(request.url);
        const page = parseInt(url.searchParams.get("page") ?? "1", 10);
        return HttpResponse.json(
          makeResultsList(undefined, {
            total: 120,
            page,
            limit: 50,
            total_pages: 3,
          }),
        );
      }),
    );

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Page 1 of 3/)).toBeInTheDocument();
    });

    expect(screen.getByText(/120/)).toBeInTheDocument();
    expect(screen.getByText("Previous")).toBeDisabled();
    expect(screen.getByText("Next")).toBeEnabled();
  });

  it("navigates to next page", async () => {
    const user = userEvent.setup();

    server.use(
      http.get("/api/results", ({ request }) => {
        const url = new URL(request.url);
        const page = parseInt(url.searchParams.get("page") ?? "1", 10);
        return HttpResponse.json(
          makeResultsList(undefined, {
            total: 120,
            page,
            limit: 50,
            total_pages: 3,
          }),
        );
      }),
    );

    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Page 1 of 3/)).toBeInTheDocument();
    });

    await user.click(screen.getByText("Next"));

    await waitFor(() => {
      expect(screen.getByText(/Page 2 of 3/)).toBeInTheDocument();
    });

    // Previous should now be enabled
    expect(screen.getByText("Previous")).toBeEnabled();
  });

  it("shows empty state with filter message when filters active", async () => {
    server.use(
      http.get("/api/results", () =>
        HttpResponse.json(makeResultsList([])),
      ),
    );

    const user = userEvent.setup();
    renderWithProviders(<ResultsPage />);

    // Type a min score to activate a filter
    await waitFor(() => {
      expect(screen.getByPlaceholderText("Any")).toBeInTheDocument();
    });

    await user.type(screen.getByPlaceholderText("Any"), "9");

    await waitFor(() => {
      expect(
        screen.getByText(/No results match your filters/),
      ).toBeInTheDocument();
    });
  });

  it("sorts results by changing sort control", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Unity AR Developer Needed")).toBeInTheDocument();
    });

    // Find the sort select — it's the 3rd combobox in the filter bar (status, platform, sort)
    const allComboboxes = screen.getAllByRole("combobox");
    const sortTrigger = allComboboxes[2];
    await user.click(sortTrigger);
    await user.click(screen.getByText("Newest first"));

    // Should re-fetch with new sort — results still render (same mock data)
    await waitFor(() => {
      expect(screen.getByText("Unity AR Developer Needed")).toBeInTheDocument();
    });
  });
});
