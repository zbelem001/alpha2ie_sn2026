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
    if (Array.isArray(detail)) {
      const fields: Record<string, string> = {
        code: "Code du service : 3 à 64 caractères, en minuscules, chiffres ou tirets, sans espace ni accent.",
        questionCode: "Vérification invalide ou inactive. Choisissez un service disponible.",
        question_code: "Vérification invalide ou inactive. Choisissez un service disponible.",
        title: "Nom : renseignez entre 3 et 200 caractères.",
        description: "Description : renseignez entre 5 et 1 000 caractères.",
        response_key: "La réponse du service est invalide.",
      };
      return [...new Set(detail.map((item: { loc?: unknown[] }) => {
        const field = String(item.loc?.at(-1) ?? "");
        return fields[field] ?? "Vérifiez le champ : " + (field || "formulaire") + ".";
      }))].join(" ");
    }
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
