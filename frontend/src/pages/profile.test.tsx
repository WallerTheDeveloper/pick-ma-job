import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { handlers, makeProfile } from "@/test/handlers";
import { renderWithProviders } from "@/test/render";
import { ProfilePage } from "@/pages/profile";

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("ProfilePage", () => {
  it("loads and displays existing profile data in form fields", async () => {
    renderWithProviders(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByDisplayValue("Unity Developer")).toBeInTheDocument();
    });

    expect(screen.getByDisplayValue("Mid-level, 4 years")).toBeInTheDocument();
    expect(screen.getByDisplayValue("$30/hr")).toBeInTheDocument();

    // TagInput renders individual chips, not a single comma-joined value
    expect(screen.getByText("Unity")).toBeInTheDocument();
    expect(screen.getByText("C#")).toBeInTheDocument();
    expect(screen.getByText("AR/VR")).toBeInTheDocument();
    expect(screen.getByText("Rust")).toBeInTheDocument();
    expect(screen.getByText("C++")).toBeInTheDocument();
    expect(screen.getByText("Vue.js")).toBeInTheDocument();
    expect(screen.getByText("TypeScript")).toBeInTheDocument();
    expect(screen.getByText("Data science")).toBeInTheDocument();
    expect(screen.getByText("DevOps-only")).toBeInTheDocument();
    expect(screen.getByText("English")).toBeInTheDocument();
    expect(screen.getByText("Ukrainian")).toBeInTheDocument();
    expect(screen.getByText("German")).toBeInTheDocument();

    // Notable project
    expect(screen.getByDisplayValue("Rust Multiplayer Game")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Authoritative game server")).toBeInTheDocument();
  });

  it("shows empty state for new users with no profile", async () => {
    server.use(
      http.get("/api/profile", () =>
        HttpResponse.json({ profile: null }),
      ),
    );

    renderWithProviders(<ProfilePage />);

    await waitFor(() => {
      expect(
        screen.getByText(/Set up your profile/),
      ).toBeInTheDocument();
    });

    // Fields should be empty
    const roleInput = screen.getByPlaceholderText("e.g. Unity Developer");
    expect(roleInput).toHaveValue("");
  });

  it("saves a new profile and shows success toast", async () => {
    const user = userEvent.setup();

    server.use(
      http.get("/api/profile", () =>
        HttpResponse.json({ profile: null }),
      ),
      http.post("/api/profile", async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          profile: makeProfile({
            role: body.role,
            experience: body.experience,
            rate: body.rate,
            primary_skills: body.primary_skills,
          }),
        });
      }),
    );

    renderWithProviders(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("e.g. Unity Developer")).toBeInTheDocument();
    });

    await user.type(screen.getByPlaceholderText("e.g. Unity Developer"), "Game Dev");
    await user.type(screen.getByPlaceholderText("e.g. Mid-level, 4 years"), "Senior");
    await user.type(screen.getByPlaceholderText("e.g. $30/hr or $50k/year"), "$50/hr");

    // Click save
    const saveButtons = screen.getAllByText("Save Profile");
    await user.click(saveButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Profile saved successfully.")).toBeInTheDocument();
    });
  });

  it("edits existing profile fields and saves", async () => {
    const user = userEvent.setup();
    let savedBody: Record<string, unknown> | null = null;

    server.use(
      http.post("/api/profile", async ({ request }) => {
        savedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ profile: makeProfile(savedBody) });
      }),
    );

    renderWithProviders(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByDisplayValue("Unity Developer")).toBeInTheDocument();
    });

    // Change role
    const roleInput = screen.getByDisplayValue("Unity Developer");
    await user.clear(roleInput);
    await user.type(roleInput, "AR Engineer");

    // Save
    const saveButtons = screen.getAllByText("Save Profile");
    await user.click(saveButtons[0]);

    await waitFor(() => {
      expect(savedBody).not.toBeNull();
    });

    expect(savedBody!.role).toBe("AR Engineer");
    // Other fields should still be present
    expect(savedBody!.primary_skills).toEqual(["Unity", "C#", "AR/VR"]);
  });

  it("shows error toast on API failure", async () => {
    const user = userEvent.setup();

    server.use(
      http.post("/api/profile", () =>
        HttpResponse.json(
          { detail: "Validation failed: role is required" },
          { status: 422 },
        ),
      ),
    );

    renderWithProviders(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByDisplayValue("Unity Developer")).toBeInTheDocument();
    });

    const saveButtons = screen.getAllByText("Save Profile");
    await user.click(saveButtons[0]);

    await waitFor(() => {
      expect(
        screen.getByText("Validation failed: role is required"),
      ).toBeInTheDocument();
    });
  });

  it("shows error toast for invalid JSON in rubric field", async () => {
    const user = userEvent.setup();

    renderWithProviders(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByDisplayValue("Unity Developer")).toBeInTheDocument();
    });

    // Expand the Advanced rubric collapsible section
    await user.click(screen.getByText(/Advanced: raw JSON/));

    // Type invalid JSON in the rubric field
    const rubricInput = screen.getByPlaceholderText(
      '{"custom_field": "value"}',
    );
    await user.type(rubricInput, "not valid json");

    const saveButtons = screen.getAllByText("Save Profile");
    await user.click(saveButtons[0]);

    await waitFor(() => {
      expect(
        screen.getByText("Advanced rubric JSON is not valid. Fix or clear it before saving."),
      ).toBeInTheDocument();
    });
  });

  it("shows error state when profile fetch fails", async () => {
    server.use(
      http.get("/api/profile", () =>
        HttpResponse.json({ detail: "Internal error" }, { status: 500 }),
      ),
    );

    renderWithProviders(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load profile/)).toBeInTheDocument();
    });
  });

  it("adds and removes notable projects", async () => {
    const user = userEvent.setup();

    server.use(
      http.get("/api/profile", () =>
        HttpResponse.json({ profile: null }),
      ),
    );

    renderWithProviders(<ProfilePage />);

    await waitFor(() => {
      expect(
        screen.getByText("No projects yet. Add notable projects to strengthen your profile."),
      ).toBeInTheDocument();
    });

    // Add a project
    await user.click(screen.getByText("Add Project"));

    expect(screen.getByText("Project 1")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Project name")).toBeInTheDocument();

    await user.type(screen.getByPlaceholderText("Project name"), "Test Project");
    await user.type(
      screen.getByPlaceholderText("Brief description of the project"),
      "A test project",
    );

    expect(screen.getByDisplayValue("Test Project")).toBeInTheDocument();

    // Remove the project
    await user.click(screen.getByText("Remove"));

    expect(screen.queryByDisplayValue("Test Project")).not.toBeInTheDocument();
    expect(
      screen.getByText("No projects yet. Add notable projects to strengthen your profile."),
    ).toBeInTheDocument();
  });

  it("displays loading state while fetching profile", () => {
    renderWithProviders(<ProfilePage />);
    expect(screen.getByText("Loading profile...")).toBeInTheDocument();
  });
});
