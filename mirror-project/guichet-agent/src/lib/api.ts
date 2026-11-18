"use client";
// Appels du navigateur : uniquement vers cette application (/api/…), qui relaie vers
// Keycloak et l'API démarches avec le jeton gardé côté serveur.
import type { SpaceRole } from "@/lib/space";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

function messageFrom(body: unknown, status: number) {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return "Certaines informations sont invalides. Vérifiez votre saisie.";
  }
  if (status === 401) return "Votre session a expiré. Reconnectez-vous.";
  if (status === 403) return "Cette action ne vous est pas autorisée.";
  if (status >= 500) return "Le service est momentanément indisponible. Réessayez.";
  return "La demande n’a pas abouti.";
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, { ...init, headers: { "Content-Type": "application/json", ...init?.headers }, cache: "no-store" });
  } catch {
    throw new ApiError("Connexion impossible. Vérifiez votre réseau.", 0);
  }
  const text = await response.text();
  let body: unknown = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = text; }
  if (!response.ok) throw new ApiError(messageFrom(body, response.status), response.status);
  return body as T;
}

/** API démarches (/v1/…), par le relais de l'application. */
export function api<T>(path: string, init?: { method?: string; body?: unknown }): Promise<T> {
  return request<T>(`/api/backend/${path.replace(/^\//, "")}`, {
    method: init?.method ?? (init?.body === undefined ? "GET" : "POST"),
    body: init?.body === undefined ? undefined : JSON.stringify(init.body),
  });
}

export type Session =
  | { authenticated: false }
  | { authenticated: true; role: SpaceRole; name: string; username: string; administrationCode: string | null };

export const getSession = () => request<Session>("/api/auth/session");
export const login = (username: string, password: string) =>
  request<{ role: SpaceRole; home: string; name: string }>("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
export const logout = () => request<{ ok: true }>("/api/auth/logout", { method: "POST" });
