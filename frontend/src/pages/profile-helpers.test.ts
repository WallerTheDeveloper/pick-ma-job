/**
 * Unit tests for profile form helpers.
 *
 * Covers:
 * - FE-9:  profileToForm assigns stable unique IDs (not array indices)
 * - FE-11: buildRubric returns a new object (immutability) and propagates JSON
 *          parse errors instead of swallowing them
 */

import { describe, expect, it } from "vitest";
import {
  buildRubric,
  extractRubric,
  formToRequest,
  profileToForm,
  validateForm,
  type FormState,
  type RubricState,
} from "@/pages/profile-helpers";
import type { ProfileResponse } from "@/types/schemas";

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeApiProfile(overrides: Partial<ProfileResponse> = {}): ProfileResponse {
  return {
    id: "p-1",
    role: "Unity Developer",
    experience: "4 years",
    rate: "$30/hr",
    primary_skills: ["Unity", "C#"],
    secondary_skills: ["Rust"],
    tertiary_skills: ["Vue.js"],
    not_a_good_fit: ["DevOps-only"],
    background: ["2 years at ZAUBAR", "2 years at Intelligent Project"],
    notable_projects: [
      { name: "Rust Server", description: "Multiplayer game" },
      { name: "VR Defense", description: "Tower defense in VR" },
    ],
    languages: ["English", "Ukrainian"],
    rubric: {},
    cv_customize_threshold: 7,
    updated_at: "2026-04-06T10:00:00Z",
    ...overrides,
  };
}

function makeRubricState(overrides: Partial<RubricState> = {}): RubricState {
  return {
    minScore: "",
    preferRemote: false,
    priorityKeywords: [],
    avoidKeywords: [],
    advanced: "",
    ...overrides,
  };
}

function makeFormState(overrides: Partial<FormState> = {}): FormState {
  return {
    role: "Developer",
    experience: "Mid",
    rate: "$30",
    primarySkills: [],
    secondarySkills: [],
    tertiarySkills: [],
    notAGoodFit: [],
    background: [],
    languages: [],
    notableProjects: [],
    rubric: makeRubricState(),
    cvCustomizeThreshold: 7,
    ...overrides,
  };
}

// ── FE-9: stable unique IDs on form state ─────────────────────────────────────

describe("profileToForm", () => {
  it("assigns unique string IDs to background entries", () => {
    const profile = makeApiProfile({ background: ["Entry A", "Entry B", "Entry C"] });
    const form = profileToForm(profile);

    const ids = form.background.map((e) => e.id);
    const unique = new Set(ids);
    expect(unique.size).toBe(3);
    ids.forEach((id) => expect(typeof id).toBe("string"));
  });

  it("assigns unique string IDs to notable projects", () => {
    const profile = makeApiProfile();
    const form = profileToForm(profile);

    const ids = form.notableProjects.map((p) => p.id);
    const unique = new Set(ids);
    expect(unique.size).toBe(2);
    ids.forEach((id) => expect(typeof id).toBe("string"));
  });

  it("preserves background entry values", () => {
    const profile = makeApiProfile({ background: ["ZAUBAR", "Intelligent Project"] });
    const form = profileToForm(profile);

    expect(form.background[0].value).toBe("ZAUBAR");
    expect(form.background[1].value).toBe("Intelligent Project");
  });

  it("preserves notable project name and description", () => {
    const profile = makeApiProfile();
    const form = profileToForm(profile);

    expect(form.notableProjects[0].name).toBe("Rust Server");
    expect(form.notableProjects[0].description).toBe("Multiplayer game");
  });

  it("copies skill arrays (not same reference)", () => {
    const profile = makeApiProfile();
    const form = profileToForm(profile);

    expect(form.primarySkills).toEqual(["Unity", "C#"]);
    // Must be a copy, not the same array object
    expect(form.primarySkills).not.toBe(profile.primary_skills);
  });

  it("each call produces different IDs for background entries", () => {
    const profile = makeApiProfile({ background: ["X"] });
    const form1 = profileToForm(profile);
    const form2 = profileToForm(profile);
    expect(form1.background[0].id).not.toBe(form2.background[0].id);
  });
});

// ── FE-11: buildRubric — immutability + error propagation ────────────────────

describe("buildRubric", () => {
  it("returns a new object and does not mutate the input", () => {
    const state = makeRubricState({ minScore: "7", preferRemote: true });
    const result = buildRubric(state);

    // Result has the expected fields
    expect(result.min_score).toBe(7);
    expect(result.prefer_remote).toBe(true);

    // The RubricState itself is unchanged
    expect(state.minScore).toBe("7");
  });

  it("merges advanced JSON without mutating the base rubric", () => {
    const state = makeRubricState({ advanced: '{"extra_field": "hello"}' });
    const result = buildRubric(state);

    expect(result).toMatchObject({ extra_field: "hello" });
    // Returned object is fresh — verify it's not the same reference as anything we passed
    expect(result).not.toBe(state);
  });

  it("throws a SyntaxError when advanced JSON is invalid", () => {
    const state = makeRubricState({ advanced: "not valid json {{" });
    expect(() => buildRubric(state)).toThrow(SyntaxError);
  });

  it("omits min_score when minScore is empty string", () => {
    const result = buildRubric(makeRubricState({ minScore: "" }));
    expect(result).not.toHaveProperty("min_score");
  });

  it("omits min_score when minScore is non-numeric", () => {
    const result = buildRubric(makeRubricState({ minScore: "abc" }));
    expect(result).not.toHaveProperty("min_score");
  });

  it("omits min_score when minScore is out of 1-10 range", () => {
    expect(buildRubric(makeRubricState({ minScore: "0" }))).not.toHaveProperty("min_score");
    expect(buildRubric(makeRubricState({ minScore: "11" }))).not.toHaveProperty("min_score");
  });

  it("includes priority_keywords and avoid_keywords when non-empty", () => {
    const state = makeRubricState({
      priorityKeywords: ["Unity", "AR"],
      avoidKeywords: ["Unreal"],
    });
    const result = buildRubric(state);
    expect(result.priority_keywords).toEqual(["Unity", "AR"]);
    expect(result.avoid_keywords).toEqual(["Unreal"]);
  });

  it("omits prefer_remote when false", () => {
    const result = buildRubric(makeRubricState({ preferRemote: false }));
    expect(result).not.toHaveProperty("prefer_remote");
  });

  it("does not include advanced keys when advanced is empty string", () => {
    const result = buildRubric(makeRubricState({ advanced: "" }));
    // Only structured keys may be present
    const keys = Object.keys(result);
    keys.forEach((k) => {
      expect(["min_score", "prefer_remote", "priority_keywords", "avoid_keywords"]).toContain(k);
    });
  });
});

// ── extractRubric ─────────────────────────────────────────────────────────────

describe("extractRubric", () => {
  it("extracts known fields correctly", () => {
    const rubric = {
      min_score: 7,
      prefer_remote: true,
      priority_keywords: ["Unity"],
      avoid_keywords: ["Unreal"],
    };
    const state = extractRubric(rubric);
    expect(state.minScore).toBe("7");
    expect(state.preferRemote).toBe(true);
    expect(state.priorityKeywords).toEqual(["Unity"]);
    expect(state.avoidKeywords).toEqual(["Unreal"]);
    expect(state.advanced).toBe("");
  });

  it("puts unknown keys into the advanced JSON field", () => {
    const rubric = { custom_field: "hello", another: 42 };
    const state = extractRubric(rubric);
    const parsed = JSON.parse(state.advanced) as Record<string, unknown>;
    expect(parsed.custom_field).toBe("hello");
    expect(parsed.another).toBe(42);
  });

  it("returns empty state for an empty rubric", () => {
    const state = extractRubric({});
    expect(state.minScore).toBe("");
    expect(state.preferRemote).toBe(false);
    expect(state.priorityKeywords).toEqual([]);
    expect(state.avoidKeywords).toEqual([]);
    expect(state.advanced).toBe("");
  });
});

// ── validateForm ──────────────────────────────────────────────────────────────

describe("validateForm", () => {
  it("returns null for a valid form", () => {
    const form = makeFormState();
    expect(validateForm(form)).toBeNull();
  });

  it("returns an error string when advanced rubric JSON is invalid", () => {
    const form = makeFormState({
      rubric: makeRubricState({ advanced: "{ bad json" }),
    });
    const err = validateForm(form);
    expect(typeof err).toBe("string");
    expect(err).toMatch(/JSON/i);
  });

  it("returns an error string when minScore is non-numeric", () => {
    const form = makeFormState({
      rubric: makeRubricState({ minScore: "abc" }),
    });
    const err = validateForm(form);
    expect(typeof err).toBe("string");
  });

  it("returns an error string when minScore is out of range", () => {
    const form = makeFormState({
      rubric: makeRubricState({ minScore: "11" }),
    });
    expect(validateForm(form)).not.toBeNull();
  });

  it("returns null when minScore is a valid number in range", () => {
    const form = makeFormState({
      rubric: makeRubricState({ minScore: "7" }),
    });
    expect(validateForm(form)).toBeNull();
  });
});

// ── formToRequest ─────────────────────────────────────────────────────────────

describe("formToRequest", () => {
  it("converts background entries to string array, filtering empty values", () => {
    const form = makeFormState({
      background: [
        { id: "1", value: "ZAUBAR" },
        { id: "2", value: "" },
        { id: "3", value: "Intelligent Project" },
      ],
    });
    const req = formToRequest(form);
    expect(req.background).toEqual(["ZAUBAR", "Intelligent Project"]);
  });

  it("excludes notable projects with empty name and description", () => {
    const form = makeFormState({
      notableProjects: [
        { id: "1", name: "Rust Server", description: "Multiplayer" },
        { id: "2", name: "", description: "" },
      ],
    });
    const req = formToRequest(form);
    expect(req.notable_projects).toHaveLength(1);
    expect(req.notable_projects[0].name).toBe("Rust Server");
  });

  it("trims role, experience, and rate — nullifies empty strings", () => {
    const form = makeFormState({ role: "  ", experience: " Dev ", rate: "" });
    const req = formToRequest(form);
    expect(req.role).toBeNull();
    expect(req.experience).toBe("Dev");
    expect(req.rate).toBeNull();
  });
});
