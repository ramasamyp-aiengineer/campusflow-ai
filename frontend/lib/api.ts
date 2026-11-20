import { SIGNED_OUT_EVENT, clearToken, getToken } from "./session";
import type { Persona } from "./types";

/** Browser-facing API origin. Defaults to the local FastAPI process. */
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/** Accept only http(s) links so story cards cannot open javascript: URLs. */
export function safeHref(url: string): string | undefined {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" || parsed.protocol === "http:" ? parsed.href : undefined;
  } catch {
    return undefined;
  }
}

/**
 * Authenticated JSON fetch against the CampusFlow API.
 * A 401 clears the session and notifies the shell to return to sign-in.
 */
export async function api<T>(path: string, _persona: Persona | null, init?: RequestInit): Promise<T> {
  const token = getToken();
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "The CampusFlow API is not reachable. Check that the server is running.");
  }
  if (response.status === 401 && token) {
    clearToken();
    window.dispatchEvent(new Event(SIGNED_OUT_EVENT));
  }
  const text = await response.text();
  let payload: unknown = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    payload = null;
  }
  if (!response.ok) {
    const detail = (payload as { detail?: unknown } | null)?.detail;
    const message = typeof detail === "string" ? detail : `Request failed (${response.status})`;
    throw new ApiError(response.status, message);
  }
  return payload as T;
}
