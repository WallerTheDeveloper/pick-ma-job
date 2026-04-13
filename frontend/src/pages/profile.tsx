/** Profile page — view and edit the user's professional profile. */

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { TagInput } from "@/components/tag-input";
import { useProfile } from "@/hooks/use-profile";
import {
  emptyForm,
  formToRequest,
  profileToForm,
  validateForm,
  type FormState,
  type ProjectEntry,
  type RubricState,
} from "@/pages/profile-helpers";

// ── Component ─────────────────────────────────────────────────────────────────

export function ProfilePage() {
  const { profile, isLoading, error, save, isSaving } = useProfile();
  const [form, setForm] = useState<FormState>(emptyForm);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    if (!initialized && !isLoading) {
      setForm(profile ? profileToForm(profile) : emptyForm());
      setInitialized(true);
    }
  }, [profile, isLoading, initialized]);

  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function updateRubric<K extends keyof RubricState>(key: K, value: RubricState[K]) {
    setForm((prev) => ({ ...prev, rubric: { ...prev.rubric, [key]: value } }));
  }

  function updateBackground(index: number, value: string) {
    setForm((prev) => ({
      ...prev,
      background: prev.background.map((entry, i) =>
        i === index ? { ...entry, value } : entry,
      ),
    }));
  }

  function addBackgroundEntry() {
    setForm((prev) => ({
      ...prev,
      background: [...prev.background, { id: crypto.randomUUID(), value: "" }],
    }));
  }

  function removeBackgroundEntry(index: number) {
    setForm((prev) => ({
      ...prev,
      background: prev.background.filter((_, i) => i !== index),
    }));
  }

  function updateProject(index: number, field: keyof ProjectEntry, value: string) {
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
      notableProjects: [
        ...prev.notableProjects,
        { id: crypto.randomUUID(), name: "", description: "" },
      ],
    }));
  }

  function removeProject(index: number) {
    setForm((prev) => ({
      ...prev,
      notableProjects: prev.notableProjects.filter((_, i) => i !== index),
    }));
  }

  async function handleClearAll() {
    const empty = emptyForm();
    setForm(empty);
    try {
      await save(formToRequest(empty));
      toast.success("Profile cleared.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to clear profile.");
    }
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
      toast.error(err instanceof Error ? err.message : "Failed to save profile.");
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
        <div className="flex items-center gap-2">
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button type="button" variant="destructive" disabled={isSaving}>
                Clear all
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Clear all profile fields?</AlertDialogTitle>
                <AlertDialogDescription>
                  This cannot be undone. All profile data will be permanently removed.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={handleClearAll}>
                  Clear all
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
          <Button type="submit" disabled={isSaving}>
            {isSaving ? "Saving..." : "Save Profile"}
          </Button>
        </div>
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
          <p className="text-sm text-muted-foreground">
            Used to score job relevance. Primary skills are weighted most heavily.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <label className="text-sm font-medium">Primary Skills</label>
            <p className="text-xs text-muted-foreground">
              Type a skill and press Enter or comma to add. These are weighted most heavily.
            </p>
            <TagInput
              value={form.primarySkills}
              onChange={(tags) => updateField("primarySkills", tags)}
              placeholder="Unity, C#, AR/VR…"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Secondary Skills</label>
            <p className="text-xs text-muted-foreground">Scored moderately.</p>
            <TagInput
              value={form.secondarySkills}
              onChange={(tags) => updateField("secondarySkills", tags)}
              placeholder="Rust, C++, Backend Architecture…"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Tertiary Skills</label>
            <p className="text-xs text-muted-foreground">Scored lightly.</p>
            <TagInput
              value={form.tertiarySkills}
              onChange={(tags) => updateField("tertiarySkills", tags)}
              placeholder="Vue.js, TypeScript, Blender…"
            />
          </div>
        </CardContent>
      </Card>

      {/* Background */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">Background</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                Each entry is a job, qualification, or relevant experience.
              </p>
            </div>
            <Button type="button" variant="outline" size="sm" onClick={addBackgroundEntry}>
              Add Entry
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {form.background.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No entries yet. Add your professional background.
            </p>
          )}
          {form.background.map((entry, i) => (
            <div key={entry.id} className="flex items-center gap-2">
              <Input
                placeholder="e.g. 2 years AR Developer at ZAUBAR"
                value={entry.value}
                onChange={(e) => updateBackground(i, e.target.value)}
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => removeBackgroundEntry(i)}
                className="shrink-0"
              >
                Remove
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Languages */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Languages</CardTitle>
        </CardHeader>
        <CardContent>
          <TagInput
            value={form.languages}
            onChange={(tags) => updateField("languages", tags)}
            placeholder="English, German, Ukrainian…"
          />
        </CardContent>
      </Card>

      {/* Notable Projects */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">Notable Projects</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                Highlighted in the AI evaluation for relevant job matches.
              </p>
            </div>
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
            <div key={project.id} className="space-y-2 rounded-md border p-3">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Project {i + 1}</label>
                <Button type="button" variant="ghost" size="sm" onClick={() => removeProject(i)}>
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
          <p className="mt-1 text-sm text-muted-foreground">
            Jobs matching these categories will score lower.
          </p>
        </CardHeader>
        <CardContent>
          <TagInput
            value={form.notAGoodFit}
            onChange={(tags) => updateField("notAGoodFit", tags)}
            placeholder="Pure frontend, Data science, DevOps-only…"
          />
        </CardContent>
      </Card>

      {/* Scoring Rubric */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Scoring Rubric</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">
            Fine-tune how the AI scores jobs. Leave fields empty to use defaults.
          </p>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="text-sm font-medium">Minimum Score Threshold</label>
              <p className="text-xs text-muted-foreground">
                Jobs below this score are flagged. Range: 1–10.
              </p>
              <Input
                type="number"
                min={1}
                max={10}
                placeholder="e.g. 5"
                value={form.rubric.minScore}
                onChange={(e) => updateRubric("minScore", e.target.value)}
                className="w-32"
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">Prefer Remote</label>
              <p className="text-xs text-muted-foreground">
                Score remote-friendly jobs higher.
              </p>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.rubric.preferRemote}
                  onChange={(e) => updateRubric("preferRemote", e.target.checked)}
                  className="h-4 w-4 rounded border-input accent-primary"
                />
                <span className="text-sm">Prefer remote positions</span>
              </label>
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium">Priority Keywords</label>
            <p className="text-xs text-muted-foreground">
              Jobs containing these keywords get a score boost.
            </p>
            <TagInput
              value={form.rubric.priorityKeywords}
              onChange={(tags) => updateRubric("priorityKeywords", tags)}
              placeholder="multiplayer, AR, game server…"
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium">Avoid Keywords</label>
            <p className="text-xs text-muted-foreground">
              Jobs containing these keywords score lower.
            </p>
            <TagInput
              value={form.rubric.avoidKeywords}
              onChange={(tags) => updateRubric("avoidKeywords", tags)}
              placeholder="Unreal, Godot, WordPress…"
            />
          </div>

          <Collapsible>
            <CollapsibleTrigger className="text-sm text-muted-foreground hover:text-foreground cursor-pointer">
              Advanced: raw JSON ▾
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2 space-y-1">
              <p className="text-xs text-muted-foreground">
                Extra rubric fields as JSON. These are merged with the structured fields above (structured fields take precedence on conflict).
              </p>
              <Textarea
                placeholder='{"custom_field": "value"}'
                value={form.rubric.advanced}
                onChange={(e) => updateRubric("advanced", e.target.value)}
                rows={4}
                className="font-mono text-sm"
              />
            </CollapsibleContent>
          </Collapsible>
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
