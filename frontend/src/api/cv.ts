/** CV API functions — upload, fetch, delete, and customize CVs. */

import { api, ApiError, getCsrfToken } from "@/api/client";
import {
  cvGetResponseSchema,
  cvUploadResponseSchema,
  cvCustomizeResponseSchema,
  okResponseSchema,
} from "@/types/schemas";
import type {
  CVGetResponse,
  CVUploadResponse,
  CVCustomizeResponse,
  OkResponse,
} from "@/types/schemas";

export async function fetchCV(): Promise<CVGetResponse> {
  return api("/api/cv", {}, cvGetResponseSchema);
}

export async function uploadCV(file: File): Promise<CVUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const headers: Record<string, string> = {};
  const csrf = getCsrfToken();
  if (csrf) headers["X-CSRF-Token"] = csrf;

  const response = await fetch("/api/cv/upload", {
    method: "POST",
    headers,
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    const text = await response.text();
    let errorBody: unknown;
    try {
      errorBody = JSON.parse(text);
    } catch {
      errorBody = text;
    }
    throw new ApiError(response.status, errorBody);
  }

  const json: unknown = await response.json();
  return cvUploadResponseSchema.parse(json);
}

export async function deleteCV(): Promise<OkResponse> {
  return api("/api/cv", { method: "DELETE" }, okResponseSchema);
}

export async function customizeCV(
  jobResultId: string,
  forceRegenerate = false,
  adjustmentNotes?: string,
  humanize = true,
): Promise<CVCustomizeResponse> {
  return api(
    "/api/cv/customize",
    {
      method: "POST",
      body: {
        job_result_id: jobResultId,
        force_regenerate: forceRegenerate,
        adjustment_notes: adjustmentNotes || null,
        humanize,
      },
    },
    cvCustomizeResponseSchema,
  );
}
