/** Form state helpers and converters for the Profile page. */

import type { ProfileResponse, ProfileSaveRequest } from "@/types/schemas";

// ── Entry types ───────────────────────────────────────────────────────────────

export interface BackgroundEntry {
  id: string;
  value: string;
}

export interface ProjectEntry {
  id: string;
  name: string;
  description: string;
}

// ── Rubric helpers ────────────────────────────────────────────────────────────

const STRUCTURED_RUBRIC_KEYS = [
  "min_score",
  "prefer_remote",
  "priority_keywords",
  "avoid_keywords",
] as const;

export interface RubricState {
  minScore: string;
  preferRemote: boolean;
  priorityKeywords: string[];
  avoidKeywords: string[];
  advanced: string;
}

export function extractRubric(rubric: Record<string, unknown>): RubricState {
  const extra: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(rubric)) {
    if (!(STRUCTURED_RUBRIC_KEYS as readonly string[]).includes(k)) {
      extra[k] = v;
    }
  }
  return {
    minScore: typeof rubric.min_score === "number" ? String(rubric.min_score) : "",
    preferRemote: rubric.prefer_remote === true,
    priorityKeywords: Array.isArray(rubric.priority_keywords)
      ? rubric.priority_keywords.filter((x): x is string => typeof x === "string")
      : [],
    avoidKeywords: Array.isArray(rubric.avoid_keywords)
      ? rubric.avoid_keywords.filter((x): x is string => typeof x === "string")
      : [],
    advanced: Object.keys(extra).length > 0 ? JSON.stringify(extra, null, 2) : "",
  };
}

export function buildRubric(r: RubricState): Record<string, unknown> {
  const rubric: Record<string, unknown> = {};
  const minScore = Number(r.minScore);
  if (r.minScore !== "" && !isNaN(minScore) && minScore >= 1 && minScore <= 10) {
    rubric.min_score = minScore;
  }
  if (r.preferRemote) rubric.prefer_remote = true;
  if (r.priorityKeywords.length > 0) rubric.priority_keywords = r.priorityKeywords;
  if (r.avoidKeywords.length > 0) rubric.avoid_keywords = r.avoidKeywords;

  if (r.advanced.trim()) {
    let extra: Record<string, unknown>;
    try {
      extra = JSON.parse(r.advanced) as Record<string, unknown>;
    } catch {
      throw new Error(`Invalid JSON in advanced rubric field: ${r.advanced}`);
    }
    return { ...rubric, ...extra };
  }
  return rubric;
}

// ── Form state ────────────────────────────────────────────────────────────────

export interface FormState {
  role: string;
  experience: string;
  rate: string;
  primarySkills: string[];
  secondarySkills: string[];
  tertiarySkills: string[];
  notAGoodFit: string[];
  background: BackgroundEntry[];
  languages: string[];
  notableProjects: ProjectEntry[];
  rubric: RubricState;
}

export function emptyForm(): FormState {
  return {
    role: "",
    experience: "",
    rate: "",
    primarySkills: [],
    secondarySkills: [],
    tertiarySkills: [],
    notAGoodFit: [],
    background: [],
    languages: [],
    notableProjects: [],
    rubric: {
      minScore: "",
      preferRemote: false,
      priorityKeywords: [],
      avoidKeywords: [],
      advanced: "",
    },
  };
}

export function profileToForm(p: ProfileResponse): FormState {
  return {
    role: p.role ?? "",
    experience: p.experience ?? "",
    rate: p.rate ?? "",
    primarySkills: [...p.primary_skills],
    secondarySkills: [...p.secondary_skills],
    tertiarySkills: [...p.tertiary_skills],
    notAGoodFit: [...p.not_a_good_fit],
    background: p.background.map((value) => ({ id: crypto.randomUUID(), value })),
    languages: [...p.languages],
    notableProjects: p.notable_projects.map((proj) => ({
      id: crypto.randomUUID(),
      name: proj.name,
      description: proj.description,
    })),
    rubric: extractRubric(p.rubric),
  };
}

export function formToRequest(form: FormState): ProfileSaveRequest {
  return {
    role: form.role.trim() || null,
    experience: form.experience.trim() || null,
    rate: form.rate.trim() || null,
    primary_skills: form.primarySkills,
    secondary_skills: form.secondarySkills,
    tertiary_skills: form.tertiarySkills,
    not_a_good_fit: form.notAGoodFit,
    background: form.background.map((e) => e.value).filter(Boolean),
    languages: form.languages,
    notable_projects: form.notableProjects
      .filter((p) => p.name.trim() || p.description.trim())
      .map(({ name, description }) => ({ name, description })),
    rubric: buildRubric(form.rubric),
  };
}

export function validateForm(form: FormState): string | null {
  if (form.rubric.advanced.trim()) {
    try {
      JSON.parse(form.rubric.advanced);
    } catch {
      return "Advanced rubric JSON is not valid. Fix or clear it before saving.";
    }
  }
  const minScore = Number(form.rubric.minScore);
  if (form.rubric.minScore !== "" && (isNaN(minScore) || minScore < 1 || minScore > 10)) {
    return "Minimum score must be a number between 1 and 10.";
  }
  return null;
}
