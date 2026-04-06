import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { handlers } from "@/test/handlers";
import { renderWithProviders } from "@/test/render";
import { SearchConfigPage } from "@/pages/search-config";

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("SearchConfigPage", () => {
  it("displays loading state initially", () => {
    renderWithProviders(<SearchConfigPage />);
    expect(screen.getByText("Loading search configs...")).toBeInTheDocument();
  });

  it("loads and displays existing configs", async () => {
    renderWithProviders(<SearchConfigPage />);

    await waitFor(() => {
      expect(screen.getByText("Upwork")).toBeInTheDocument();
    });

    expect(screen.getByText("unity developer")).toBeInTheDocument();
    expect(screen.getByText("entry, intermediate")).toBeInTheDocument();
    expect(screen.getByText("fixed, hourly")).toBeInTheDocument();
  });

  it("shows empty state when no configs exist", async () => {
    server.use(
      http.get("/api/search-configs", () =>
        HttpResponse.json({ configs: [] }),
      ),
    );

    renderWithProviders(<SearchConfigPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/No search configs yet/),
      ).toBeInTheDocument();
    });
  });

  it("opens inline form when Add Config is clicked", async () => {
    const user = userEvent.setup();

    renderWithProviders(<SearchConfigPage />);

    await waitFor(() => {
      expect(screen.getByText("Add Config")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Add Config"));

    expect(screen.getByText("New Search Config")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("e.g. unity developer")).toBeInTheDocument();
  });

  it("creates a new config and shows success toast", async () => {
    const user = userEvent.setup();

    renderWithProviders(<SearchConfigPage />);

    await waitFor(() => {
      expect(screen.getByText("Add Config")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Add Config"));

    // Fill in query
    await user.type(
      screen.getByPlaceholderText("e.g. unity developer"),
      "rust game server",
    );

    // Submit
    await user.click(screen.getByText("Create Config"));

    await waitFor(() => {
      expect(screen.getByText("Search config created.")).toBeInTheDocument();
    });
  });

  it("shows validation error when query is empty", async () => {
    const user = userEvent.setup();

    renderWithProviders(<SearchConfigPage />);

    await waitFor(() => {
      expect(screen.getByText("Add Config")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Add Config"));

    // Submit without filling query
    await user.click(screen.getByText("Create Config"));

    await waitFor(() => {
      expect(
        screen.getByText("Search query is required."),
      ).toBeInTheDocument();
    });
  });

  it("cancels form and hides it", async () => {
    const user = userEvent.setup();

    renderWithProviders(<SearchConfigPage />);

    await waitFor(() => {
      expect(screen.getByText("Add Config")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Add Config"));
    expect(screen.getByText("New Search Config")).toBeInTheDocument();

    await user.click(screen.getByText("Cancel"));
    expect(screen.queryByText("New Search Config")).not.toBeInTheDocument();
  });

  it("opens delete confirmation dialog and deletes config", async () => {
    const user = userEvent.setup();

    renderWithProviders(<SearchConfigPage />);

    await waitFor(() => {
      expect(screen.getByText("Upwork")).toBeInTheDocument();
    });

    // Click delete on the card
    await user.click(screen.getByText("Delete"));

    // Confirmation dialog should appear
    await waitFor(() => {
      expect(
        screen.getByText("Delete Search Config"),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByText(/Are you sure you want to delete/),
    ).toBeInTheDocument();

    // Confirm deletion — find the destructive Delete button in the dialog
    const deleteButtons = screen.getAllByText("Delete");
    const confirmButton = deleteButtons.find(
      (btn) => btn.closest("[data-slot='dialog-content']") !== null,
    );
    expect(confirmButton).toBeDefined();
    await user.click(confirmButton!);

    await waitFor(() => {
      expect(screen.getByText("Search config deleted.")).toBeInTheDocument();
    });
  });

  it("shows error when create API fails", async () => {
    const user = userEvent.setup();

    server.use(
      http.post("/api/search-configs", () =>
        HttpResponse.json(
          { detail: "Platform config already exists" },
          { status: 422 },
        ),
      ),
    );

    renderWithProviders(<SearchConfigPage />);

    await waitFor(() => {
      expect(screen.getByText("Add Config")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Add Config"));
    await user.type(
      screen.getByPlaceholderText("e.g. unity developer"),
      "test query",
    );
    await user.click(screen.getByText("Create Config"));

    await waitFor(() => {
      expect(
        screen.getByText("Platform config already exists"),
      ).toBeInTheDocument();
    });
  });

  it("shows error state when fetch fails", async () => {
    server.use(
      http.get("/api/search-configs", () =>
        HttpResponse.json({ detail: "Internal error" }, { status: 500 }),
      ),
    );

    renderWithProviders(<SearchConfigPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/Failed to load search configs/),
      ).toBeInTheDocument();
    });
  });

  it("toggles Upwork filter buttons", async () => {
    const user = userEvent.setup();

    renderWithProviders(<SearchConfigPage />);

    await waitFor(() => {
      expect(screen.getByText("Add Config")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Add Config"));

    // Toggle experience level
    const entryButton = screen.getByText("Entry");
    await user.click(entryButton);
    expect(entryButton.className).toContain("bg-primary");

    // Toggle off
    await user.click(entryButton);
    expect(entryButton.className).not.toContain("bg-primary");
  });
});
