/**
 * Tests for the ListManager component.
 *
 * Covers:
 * - FE-16: Async mutation errors are caught and shown as toast notifications
 *          (handleCreate and commitRename both have try/catch)
 */

import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { handlers } from "@/test/handlers";
import { renderWithProviders } from "@/test/render";
import { ListManager } from "@/components/list-manager";

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderListManager() {
  return renderWithProviders(
    <ListManager selectedListId={null} onSelectList={() => {}} />,
  );
}

// ── FE-16: error handling in create / rename ──────────────────────────────────

describe("ListManager — error handling", () => {
  it("shows a toast when createList fails", async () => {
    const user = userEvent.setup();

    server.use(
      http.post("/api/lists", () =>
        HttpResponse.json({ detail: "Failed to create list" }, { status: 500 }),
      ),
    );

    renderListManager();

    // Wait for the component to mount (lists query resolves)
    await waitFor(() => expect(screen.getByPlaceholderText("New list name…")).toBeInTheDocument());

    const input = screen.getByPlaceholderText("New list name…");
    await user.type(input, "My List");
    await user.keyboard("{Enter}");

    await waitFor(() => {
      expect(screen.getByText(/Failed to create list/i)).toBeInTheDocument();
    });
  });

  it("shows 'All results' option and renders list items", async () => {
    // Add a list to the mock response
    server.use(
      http.get("/api/lists", () =>
        HttpResponse.json({
          lists: [{ id: "00000000-0000-4000-8000-000000000040", name: "Favorites", created_at: "2026-01-01T00:00:00Z" }],
        }),
      ),
    );

    renderListManager();

    await waitFor(() => {
      expect(screen.getByText("All results")).toBeInTheDocument();
      expect(screen.getByText("Favorites")).toBeInTheDocument();
    });
  });

  it("shows toast when renameList fails — clicking the pencil button enters edit mode", async () => {
    const user = userEvent.setup();

    server.use(
      http.get("/api/lists", () =>
        HttpResponse.json({
          lists: [{ id: "00000000-0000-4000-8000-000000000040", name: "Favorites", created_at: "2026-01-01T00:00:00Z" }],
        }),
      ),
      http.patch("/api/lists/:listId", () =>
        HttpResponse.json({ detail: "Rename failed" }, { status: 500 }),
      ),
    );

    renderListManager();

    await waitFor(() => expect(screen.getByText("Favorites")).toBeInTheDocument());

    // The pencil (edit) and trash buttons are icon-only buttons with no accessible name.
    // They appear in DOM order: [All results button, pencil, trash, create (+)].
    // Use getAllByRole and pick the pencil button by identifying it via SVG class name.
    const allButtons = screen.getAllByRole("button");
    const pencilButton = allButtons.find((btn) =>
      btn.querySelector(".lucide-pencil") !== null,
    );

    expect(pencilButton).toBeDefined();
    await user.click(pencilButton!);

    // Entering edit mode shows a text input pre-filled with the list name.
    await waitFor(() => {
      expect(screen.getByDisplayValue("Favorites")).toBeInTheDocument();
    });

    // Click the ✓ check button to commit the rename (PATCH request will fail)
    const allButtons2 = screen.getAllByRole("button");
    const checkButton = allButtons2.find((btn) =>
      btn.querySelector(".lucide-check") !== null,
    );
    expect(checkButton).toBeDefined();
    await user.click(checkButton!);

    // The ApiError.message comes from the `detail` field in the 500 response body.
    // The toast shows err.message since ApiError extends Error.
    await waitFor(() => {
      expect(screen.getByText("Rename failed")).toBeInTheDocument();
    });
  });

  it("creates a list successfully and clears the input", async () => {
    const user = userEvent.setup();

    server.use(
      http.post("/api/lists", () =>
        HttpResponse.json({
          id: "00000000-0000-4000-8000-000000000041",
          name: "New List",
          created_at: "2026-01-01T00:00:00Z",
        }),
      ),
    );

    renderListManager();
    await waitFor(() => expect(screen.getByPlaceholderText("New list name…")).toBeInTheDocument());

    const input = screen.getByPlaceholderText("New list name…") as HTMLInputElement;
    await user.type(input, "New List");
    await user.keyboard("{Enter}");

    // Input should be cleared after successful creation
    await waitFor(() => {
      expect(input.value).toBe("");
    });
  });

  it("does not call createList when input is empty", async () => {
    const user = userEvent.setup();
    let createCalled = false;

    server.use(
      http.post("/api/lists", () => {
        createCalled = true;
        return HttpResponse.json({ id: "x", name: "X", created_at: "" });
      }),
    );

    renderListManager();
    await waitFor(() => expect(screen.getByPlaceholderText("New list name…")).toBeInTheDocument());

    await user.keyboard("{Enter}");

    // Give time for any async calls
    await new Promise((r) => setTimeout(r, 50));
    expect(createCalled).toBe(false);
  });
});
