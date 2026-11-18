const KEY = "campusflow.session";
export const SIGNED_OUT_EVENT = "campusflow:signed-out";

export function getToken(): string {
  if (typeof window === "undefined") return "";
  return window.sessionStorage.getItem(KEY) ?? "";
}

export function setToken(token: string) {
  window.sessionStorage.setItem(KEY, token);
}

export function clearToken() {
  window.sessionStorage.removeItem(KEY);
}
