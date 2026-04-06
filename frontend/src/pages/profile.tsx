/** Profile page — view and edit the user's professional profile. */

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { useProfile } from "@/hooks/use-profile";
import type { NotableProject, ProfileSaveRequest } from "@/types/schemas";

/** Split a comma-separated string into a trimmed, non-empty array. */
function splitList(value: string): string[] {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

/** Join an array back to a comma-separated display string. */
function joinList(arr: readonly string[]): string {
  return arr.join(", ");
}

interface FormState {
  role: string;
  experience: string;
  rate: string;
  primarySkills: string;
  secondarySkills: string;
  tertiarySkills: string;
  notAGoodFit: string;
  background: string;
  languages: string;
  notableProjects: NotableProject[];
  rubricText: string;
}

function emptyForm(): FormState {
  return {
    role: "",
    experience: "",
    rate: "",
    primarySkills: "",
    secondarySkills: "",
    tertiarySkills: "",
    notAGoodFit: "",
    background: "",
    languages: "",
    notableProjects: [],
    rubricText: "",
  };
}

function profileToForm(
  p: NonNullable<ReturnType<typeof useProfile>["profile"]>,
): FormState {
  return {
    role: p.role ?? "",
    experience: p.experience ?? "",
    rate: p.rate ?? "",
    primarySkills: joinList(p.primary_skills),
    secondarySkills: joinList(p.secondary_skills),
    tertiarySkills: joinList(p.tertiary_skills),
    notAGoodFit: joinList(p.not_a_good_fit),
    background: p.background.join("\n"),
    languages: joinList(p.languages),
    notableProjects: p.notable_projects.length > 0 ? p.notable_projects : [],
    rubricText: Object.keys(p.rubric).length > 0
      ? JSON.stringify(p.rubric, null, 2)
      : "",
  };
}

function formToRequest(form: FormState): ProfileSaveRequest {
  let rubric: Record<string, unknown> = {};
  if (form.rubricText.trim()) {
    try {
      rubric = JSON.parse(form.rubricText);
    } catch {
      // validation will catch this
    }
  }

  return {
    role: form.role.trim() || null,
    experience: form.experience.trim() || null,
    rate: form.rate.trim() || null,
    primary_skills: splitList(form.primarySkills),
    secondary_skills: splitList(form.secondarySkills),
    tertiary_skills: splitList(form.tertiarySkills),
    not_a_good_fit: splitList(form.notAGoodFit),
    background: form.background
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean),
    languages: splitList(form.languages),
    notable_projects: form.notableProjects.filter(
      (p) => p.name.trim() || p.description.trim(),
    ),
    rubric,
  };
}

function validateForm(form: FormState): string | null {
  if (form.rubricText.trim()) {
    try {
      JSON.parse(form.rubricText);
    } catch {
      return "Custom rubric must be valid JSON.";
    }
  }
  return null;
}

export function ProfilePage() {
  const { profile, isLoading, error, save, isSaving } = useProfile();
  const [form, setForm] = useState<FormState>(emptyForm);
  const [initialized, setInitialized] = useState(false);

  // Populate form when profile loads
  useEffect(() => {
    if (!initialized && !isLoading) {
      setForm(profile ? profileToForm(profile) : emptyForm());
      setInitialized(true);
    }
  }, [profile, isLoading, initialized]);

  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function updateProject(index: number, field: keyof NotableProject, value: string) {
    setForm((prev) => ({
      ...prev,
      notableProjects: prev.notableProjects.map((p, i) =>
        i === index ? { ...p, [field]: value } : p,
      ),
    }));
  }

  function addProject() {
    setForm((prev) => ({
      ...prev,
      notableProjects: [...prev.notableProjects, { name: "", description: "" }],
    }));
  }

  function removeProject(index: number) {
    setForm((prev) => ({
      ...prev,
      notableProjects: prev.notableProjects.filter((_, i) => i !== index),
    }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const validationError = validateForm(form);
    if (validationError) {
      toast.error(validationError);
      return;
    }

    try {
      const result = await save(formToRequest(form));
      setForm(profileToForm(result.profile));
      toast.success("Profile saved successfully.");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to save profile.",
      );
    }
  }

  if (isLoading) {
    return <p className="text-muted-foreground">Loading profile...</p>;
  }

  if (error) {
    return (
      <p className="text-destructive">
        Failed to load profile:{" "}
        {error instanceof Error ? error.message : "Unknown error"}
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Profile</h2>
          <p className="mt-1 text-muted-foreground">
            {profile
              ? "Edit your professional profile used for job evaluation."
              : "Set up your profile so the pipeline can evaluate jobs against your skills."}
          </p>
        </div>
        <Button type="submit" disabled={isSaving}>
          {isSaving ? "Saving..." : "Save Profile"}
        </Button>
      </div>

      {/* Basic info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Basic Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-1">
              <label className="text-sm font-medium">Role</label>
              <Input
                placeholder="e.g. Unity Developer"
                value={form.role}
                onChange={(e) => updateField("role", e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">Experience Level</label>
              <Input
                placeholder="e.g. Mid-level, 4 years"
                value={form.experience}
                onChange={(e) => updateField("experience", e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">Rate</label>
              <Input
                placeholder="e.g. $30/hr or $50k/year"
                value={form.rate}
                onChange={(e) => updateField("rate", e.target.value)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Skills */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Skills</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <label className="text-sm font-medium">Primary Skills</label>
            <p className="text-xs text-muted-foreground">
              Comma-separated. These are weighted most heavily in scoring.
            </p>
            <Textarea
              placeholder="Unity, C#, AR/VR, Mobile Development"
              value={form.primarySkills}
              onChange={(e) => updateField("primarySkills", e.target.value)}
              rows={2}
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Secondary Skills</label>
            <p className="text-xs text-muted-foreground">
              Comma-separated. Scored moderately.
            </p>
            <Textarea
              placeholder="Rust, C++, Backend Architecture"
              value={form.secondarySkills}
              onChange={(e) => updateField("secondarySkills", e.target.value)}
              rows={2}
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Tertiary Skills</label>
            <p className="text-xs text-muted-foreground">
              Comma-separated. Scored lightly.
            </p>
            <Textarea
              placeholder="Vue.js, TypeScript, Blender"
              value={form.tertiarySkills}
              onChange={(e) => updateField("tertiarySkills", e.target.value)}
              rows={2}
            />
          </div>
        </CardContent>
      </Card>

      {/* Background & Languages */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Background</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <label className="text-sm font-medium">Professional Background</label>
            <p className="text-xs text-muted-foreground">
              One entry per line (e.g. each job or qualification).
            </p>
            <Textarea
              placeholder={"2 years AR & Web Developer at ZAUBAR\n2 years Backend Developer at Intelligent Project\nBSc Computer Science"}
              value={form.background}
              onChange={(e) => updateField("background", e.target.value)}
              rows={4}
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Languages</label>
            <p className="text-xs text-muted-foreground">Comma-separated.</p>
            <Input
              placeholder="English, German, Ukrainian"
              value={form.languages}
              onChange={(e) => updateField("languages", e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {/* Notable Projects */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Notable Projects</CardTitle>
            <Button type="button" variant="outline" size="sm" onClick={addProject}>
              Add Project
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {form.notableProjects.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No projects yet. Add notable projects to strengthen your profile.
            </p>
          )}
          {form.notableProjects.map((project, i) => (
            <div key={i} className="space-y-2 rounded-md border p-3">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Project {i + 1}</label>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeProject(i)}
                >
                  Remove
                </Button>
              </div>
              <Input
                placeholder="Project name"
                value={project.name}
                onChange={(e) => updateProject(i, "name", e.target.value)}
              />
              <Textarea
                placeholder="Brief description of the project"
                value={project.description}
                onChange={(e) => updateProject(i, "description", e.target.value)}
                rows={2}
              />
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Not a good fit */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Not a Good Fit For</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">
              Comma-separated. Jobs matching these will score lower.
            </p>
            <Textarea
              placeholder="Pure frontend, Data science, DevOps-only"
              value={form.notAGoodFit}
              onChange={(e) => updateField("notAGoodFit", e.target.value)}
              rows={2}
            />
          </div>
        </CardContent>
      </Card>

      {/* Custom Rubric */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Custom Rubric</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">
              Optional JSON object with custom scoring criteria. Leave empty to
              use the default rubric.
            </p>
            <Textarea
              placeholder='{"min_score": 5, "prefer_remote": true}'
              value={form.rubricText}
              onChange={(e) => updateField("rubricText", e.target.value)}
              rows={4}
              className="font-mono text-sm"
            />
          </div>
        </CardContent>
      </Card>

      <Separator />

      <div className="flex justify-end">
        <Button type="submit" disabled={isSaving}>
          {isSaving ? "Saving..." : "Save Profile"}
        </Button>
      </div>
    </form>
  );
}
