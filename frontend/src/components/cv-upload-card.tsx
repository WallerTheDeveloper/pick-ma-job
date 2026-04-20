/** CV upload card — file input, upload status, replace and delete actions. */

import { useRef } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { useCV, useUploadCV, useDeleteCV } from "@/hooks/use-cv";

export function CVUploadCard() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { data, isLoading } = useCV();
  const uploadMutation = useUploadCV();
  const deleteMutation = useDeleteCV();

  const cv = data?.cv ?? null;

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (fileInputRef.current) fileInputRef.current.value = "";

    try {
      await uploadMutation.mutateAsync(file);
      toast.success("CV uploaded and structured successfully.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to upload CV.");
    }
  }

  async function handleDelete() {
    try {
      await deleteMutation.mutateAsync();
      toast.success("CV deleted.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete CV.");
    }
  }

  const isUploading = uploadMutation.isPending;
  const isDeleting = deleteMutation.isPending;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">CV / Resume</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              Upload a PDF to enable AI-powered CV customization for qualifying jobs.
            </p>
          </div>
          {cv && (
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={isUploading || isDeleting}
                onClick={() => fileInputRef.current?.click()}
              >
                {isUploading ? "Uploading..." : "Replace"}
              </Button>
              <AlertDialog>
                <AlertDialogTrigger
                  render={
                    <Button
                      type="button"
                      variant="destructive"
                      size="sm"
                      disabled={isUploading || isDeleting}
                    />
                  }
                >
                  {isDeleting ? "Deleting..." : "Delete"}
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Delete CV?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will remove your CV and all cached customizations. This cannot be undone.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction onClick={handleDelete}>Delete</AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          className="hidden"
          onChange={handleFileChange}
        />
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading...</p>
        ) : cv ? (
          <div className="space-y-1">
            <p className="text-sm font-medium">{cv.filename}</p>
            <p className="text-xs text-muted-foreground">
              Uploaded {new Date(cv.updated_at).toLocaleDateString()}
            </p>
          </div>
        ) : (
          <Button
            type="button"
            variant="outline"
            disabled={isUploading}
            onClick={() => fileInputRef.current?.click()}
          >
            {isUploading ? "Uploading..." : "Upload PDF"}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
