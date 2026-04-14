/** Base API client with CSRF cookie reading and credentials. */

import type { ZodType } from "zod";

const CSRF_COOKIE = "csrf_token";

function getCsrfToken(): string | undefined {
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${CSRF_COOKIE}=`));
  return match ? decodeURIComponent(match.split("=").slice(1).join("=")) : undefined;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: unknown,
  ) {
    const message =
      typeof body === "object" && body !== null && "detail" in body
        ? String((body as { detail: string }).detail)
        : `Request failed with status ${status}`;
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
}

export async function api<T>(
  path: string,
  options: RequestOptions = {},
  schema?: ZodType<T>,
): Promise<T> {
  const { body, headers: extraHeaders, ...rest } = options;

  const headers: Record<string, string> = {
    ...(extraHeaders as Record<string, string>),
  };

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const method = (rest.method ?? "GET").toUpperCase();
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const csrf = getCsrfToken();
    if (csrf) {
      headers["X-CSRF-Token"] = csrf;
    } else if (import.meta.env.DEV) {
      console.warn(
        `[API] CSRF token missing for ${method} ${path}. Request will likely fail with 403.`,
      );
    }
  }

  const response = await fetch(path, {
    ...rest,
    method,
    headers,
    credentials: "include",
    body: body !== undefined ? JSON.stringify(body) : undefined,
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

  if (response.status === 204) {
    return undefined as T;
  }

  const json: unknown = await response.json();

  if (schema) {
    try {
      return schema.parse(json);
    } catch (err) {
      console.error(`[API] Response validation failed for ${method} ${path}:`, err, json);
      throw err;
    }
  }

  return json as T;
}
