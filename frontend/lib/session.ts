const KEY = "campusflow.session";

/** Dispatched when the API rejects a bearer token so the shell can clear UI state. */
export const SIGNED_OUT_EVENT = "campusflow:signed-out";

/** Read the bearer token from sessionStorage (empty during SSR). */
export function getToken(): string {
  if (typeof window === "undefined") return "";
  return window.sessionStorage.getItem(KEY) ?? "";
}

/** Persist a bearer token for the current browser tab. */
export function setToken(token: string) {
  window.sessionStorage.setItem(KEY, token);
}

/** Drop the bearer token on sign-out or 401. */
export function clearToken() {
  window.sessionStorage.removeItem(KEY);
}
