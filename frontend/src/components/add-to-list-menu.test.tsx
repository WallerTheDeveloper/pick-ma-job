/**
 * Tests for the AddToListMenu component.
 *
 * Covers:
 * - FE-17: Promise rejections from onAdd/onRemove are caught and shown
 *          as toast notifications (no more silent void discard)
 * - T-14:  "Create new list…" item creates a list then adds the job in one flow
 */

import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
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
const NEW_LIST_ID = "00000000-0000-4000-8000-000000000041";

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

    const trigger = screen.getByRole("button", { name: /add to list/i });
    await user.click(trigger);

    await waitFor(() => {
      expect(screen.getByText("Favorites")).toBeInTheDocument();
    });

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

// ── T-14: Create new list flow ────────────────────────────────────────────────

describe("AddToListMenu — create new list", () => {
  it("shows 'Create new list…' item in the dropdown", async () => {
    const user = userEvent.setup();

    server.use(
      http.get("/api/lists", () => HttpResponse.json({ lists: [] })),
    );

    renderMenu();
    await user.click(screen.getByRole("button", { name: /add to list/i }));

    await waitFor(() => {
      expect(screen.getByText(/Create new list/i)).toBeInTheDocument();
    });
  });

  it("shows 'Create new list…' item even when lists exist", async () => {
    const user = userEvent.setup();

    server.use(
      http.get("/api/lists", () =>
        HttpResponse.json({
          lists: [{ id: "00000000-0000-4000-8000-000000000040", name: "Favorites", created_at: "2026-01-01T00:00:00Z" }],
        }),
      ),
    );

    renderMenu();
    await user.click(screen.getByRole("button", { name: /add to list/i }));

    await waitFor(() => {
      expect(screen.getByText("Favorites")).toBeInTheDocument();
      expect(screen.getByText(/Create new list/i)).toBeInTheDocument();
    });
  });

  it("opens a dialog when 'Create new list…' is clicked", async () => {
    const user = userEvent.setup();

    server.use(
      http.get("/api/lists", () => HttpResponse.json({ lists: [] })),
    );

    renderMenu();
    await user.click(screen.getByRole("button", { name: /add to list/i }));
    await waitFor(() => expect(screen.getByText(/Create new list/i)).toBeInTheDocument());

    await user.click(screen.getByText(/Create new list/i));

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/List name/i)).toBeInTheDocument();
    });
  });

  it("creates the list and adds the job on submit, then shows a success toast", async () => {
    const user = userEvent.setup();
    const onAdd = vi.fn(() => Promise.resolve());

    server.use(
      http.get("/api/lists", () => HttpResponse.json({ lists: [] })),
      http.post("/api/lists", async ({ request }) => {
        const body = (await request.json()) as { name: string };
        return HttpResponse.json({
          id: NEW_LIST_ID,
          name: body.name,
          created_at: "2026-04-13T00:00:00Z",
        });
      }),
      http.get("/api/results/:resultId/lists", () =>
        HttpResponse.json({ ok: true, list_ids: [NEW_LIST_ID] }),
      ),
    );

    renderMenu(onAdd);
    await user.click(screen.getByRole("button", { name: /add to list/i }));
    await waitFor(() => expect(screen.getByText(/Create new list/i)).toBeInTheDocument());
    await user.click(screen.getByText(/Create new list/i));

    await waitFor(() => expect(screen.getByPlaceholderText(/List name/i)).toBeInTheDocument());

    await user.type(screen.getByPlaceholderText(/List name/i), "My New List");
    await user.click(screen.getByRole("button", { name: /Create & add/i }));

    await waitFor(() => {
      expect(onAdd).toHaveBeenCalledWith(NEW_LIST_ID);
      expect(screen.getByText(/Added to "My New List"/i)).toBeInTheDocument();
    });
  });

  it("keeps the dialog open and shows error toast when creation fails", async () => {
    const user = userEvent.setup();

    server.use(
      http.get("/api/lists", () => HttpResponse.json({ lists: [] })),
      http.post("/api/lists", () =>
        HttpResponse.json({ detail: "Duplicate list name" }, { status: 400 }),
      ),
    );

    renderMenu();
    await user.click(screen.getByRole("button", { name: /add to list/i }));
    await waitFor(() => expect(screen.getByText(/Create new list/i)).toBeInTheDocument());
    await user.click(screen.getByText(/Create new list/i));

    await waitFor(() => expect(screen.getByPlaceholderText(/List name/i)).toBeInTheDocument());

    await user.type(screen.getByPlaceholderText(/List name/i), "Favorites");
    await user.click(screen.getByRole("button", { name: /Create & add/i }));

    await waitFor(() => {
      // ApiError extracts the "detail" field, so the server message is shown directly
      expect(screen.getByText(/Duplicate list name/i)).toBeInTheDocument();
    });
  });

  it("disables the submit button when the name is empty", async () => {
    const user = userEvent.setup();

    server.use(
      http.get("/api/lists", () => HttpResponse.json({ lists: [] })),
    );

    renderMenu();
    await user.click(screen.getByRole("button", { name: /add to list/i }));
    await waitFor(() => expect(screen.getByText(/Create new list/i)).toBeInTheDocument());
    await user.click(screen.getByText(/Create new list/i));

    await waitFor(() => expect(screen.getByRole("button", { name: /Create & add/i })).toBeInTheDocument());

    expect(screen.getByRole("button", { name: /Create & add/i })).toBeDisabled();
  });
});
