/**
 * Tests for the AddToListMenu component.
 *
 * Covers:
 * - FE-17: Promise rejections from onAdd/onRemove are caught and shown
 *          as toast notifications (no more silent void discard)
 */

import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { handlers } from "@/test/handlers";
import { renderWithProviders } from "@/test/render";
import { AddToListMenu } from "@/components/add-to-list-menu";

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Helpers ───────────────────────────────────────────────────────────────────

const JOB_RESULT_ID = "00000000-0000-4000-8000-000000000010";

function renderMenu(
  onAdd: (id: string) => Promise<void> = () => Promise.resolve(),
  onRemove: (id: string) => Promise<void> = () => Promise.resolve(),
) {
  return renderWithProviders(
    <AddToListMenu
      jobResultId={JOB_RESULT_ID}
      onAdd={onAdd}
      onRemove={onRemove}
    />,
  );
}

// ── FE-17: Promise rejection toast ───────────────────────────────────────────

describe("AddToListMenu — promise rejection handling", () => {
  it("opens the dropdown when the bookmark button is clicked", async () => {
    const user = userEvent.setup();

    // Add a list so the dropdown has items
    server.use(
      http.get("/api/lists", () =>
        HttpResponse.json({
          lists: [{ id: "00000000-0000-4000-8000-000000000040", name: "Favorites", created_at: "2026-01-01T00:00:00Z" }],
        }),
      ),
    );

    renderMenu();

    const trigger = screen.getByRole("button", { name: /add to list/i });
    await user.click(trigger);

    await waitFor(() => {
      expect(screen.getByText("Add to list")).toBeInTheDocument();
    });
  });

  it("shows toast error when onAdd rejects", async () => {
    const user = userEvent.setup();
    const errorMessage = "Network error adding to list";

    server.use(
      http.get("/api/lists", () =>
        HttpResponse.json({
          lists: [{ id: "00000000-0000-4000-8000-000000000040", name: "Favorites", created_at: "2026-01-01T00:00:00Z" }],
        }),
      ),
    );

    const failingAdd = () => Promise.reject(new Error(errorMessage));
    renderMenu(failingAdd);

    // Open dropdown
    const trigger = screen.getByRole("button", { name: /add to list/i });
    await user.click(trigger);

    await waitFor(() => {
      expect(screen.getByText("Favorites")).toBeInTheDocument();
    });

    // Click the list item to trigger onAdd
    await user.click(screen.getByText("Favorites"));

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });

  it("shows a generic toast message when onAdd rejects with a non-Error", async () => {
    const user = userEvent.setup();

    server.use(
      http.get("/api/lists", () =>
        HttpResponse.json({
          lists: [{ id: "00000000-0000-4000-8000-000000000040", name: "Favorites", created_at: "2026-01-01T00:00:00Z" }],
        }),
      ),
    );

    const failingAdd = () => Promise.reject("string error");
    renderMenu(failingAdd);

    const trigger = screen.getByRole("button", { name: /add to list/i });
    await user.click(trigger);

    await waitFor(() => expect(screen.getByText("Favorites")).toBeInTheDocument());
    await user.click(screen.getByText("Favorites"));

    await waitFor(() => {
      expect(screen.getByText("Failed to update list")).toBeInTheDocument();
    });
  });

  it("shows 'No lists yet' message when there are no lists", async () => {
    const user = userEvent.setup();

    // Override to return empty list
    server.use(
      http.get("/api/lists", () => HttpResponse.json({ lists: [] })),
    );

    renderMenu();
    const trigger = screen.getByRole("button", { name: /add to list/i });
    await user.click(trigger);

    await waitFor(() => {
      expect(screen.getByText(/No lists yet/i)).toBeInTheDocument();
    });
  });
});
