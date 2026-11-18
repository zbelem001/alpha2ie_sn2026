// Session côté serveur : jetons Keycloak dans des cookies httpOnly, jamais exposés au navigateur.
//
// Démonstration : la connexion utilise l'échange identifiant / mot de passe du client
// dlnuf-api (Direct Access Grant), pour garder le formulaire de l'application. En production,
// passer au flux Authorization Code avec PKCE (redirection vers la page de connexion Keycloak).
import { cookies } from "next/headers";
import { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/server/session-cookies";
import { SPACE, type SpaceRole } from "@/lib/space";

const KEYCLOAK_URL = (process.env.KEYCLOAK_URL ?? "http://localhost:8180").replace(/\/$/, "");
const REALM = process.env.KEYCLOAK_REALM ?? "dlnuf";
const CLIENT_ID = process.env.KEYCLOAK_CLIENT_ID ?? "dlnuf-api";
const OIDC = `${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect`;
export const BACKEND_URL = (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/$/, "");

type TokenSet = { access_token: string; refresh_token: string; expires_in: number; refresh_expires_in: number };
export type Claims = {
  sub?: string; preferred_username?: string; name?: string; exp?: number;
  realm_access?: { roles?: unknown }; administration_code?: string;
};

export class IdentityUnavailableError extends Error {}

export function decodeClaims(token: string): Claims {
  try {
    return JSON.parse(Buffer.from(token.split(".")[1] ?? "", "base64url").toString("utf8")) as Claims;
  } catch {
    return {};
  }
}

export function spaceRole(claims: Claims): SpaceRole | null {
  const roles = Array.isArray(claims.realm_access?.roles) ? claims.realm_access.roles : [];
  return SPACE.roles.find((role) => roles.includes(role)) ?? null;
}

async function tokenRequest(form: Record<string, string>): Promise<TokenSet | null> {
  let response: Response;
  try {
    response = await fetch(`${OIDC}/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ client_id: CLIENT_ID, ...form }),
      cache: "no-store",
    });
  } catch {
    throw new IdentityUnavailableError("Keycloak injoignable");
  }
  if (response.status >= 500) throw new IdentityUnavailableError(`Keycloak : HTTP ${response.status}`);
  return response.ok ? ((await response.json()) as TokenSet) : null;
}

export function passwordGrant(username: string, password: string) {
  return tokenRequest({ grant_type: "password", username, password, scope: "openid" });
}

export async function storeTokens(tokens: TokenSet, secure: boolean) {
  const store = await cookies();
  const options = { httpOnly: true, sameSite: "lax" as const, path: "/", secure };
  store.set(ACCESS_COOKIE, tokens.access_token, { ...options, maxAge: tokens.expires_in });
  store.set(REFRESH_COOKIE, tokens.refresh_token, { ...options, maxAge: tokens.refresh_expires_in });
}

export async function clearTokens() {
  const store = await cookies();
  store.delete(ACCESS_COOKIE);
  store.delete(REFRESH_COOKIE);
}

/** Jeton d'accès valide, renouvelé si nécessaire. À appeler depuis un gestionnaire de route. */
export async function currentAccessToken(secure: boolean): Promise<string | null> {
  const store = await cookies();
  const access = store.get(ACCESS_COOKIE)?.value;
  if (access) {
    const { exp } = decodeClaims(access);
    if (exp && exp * 1000 > Date.now() + 15_000) return access;
  }
  const refresh = store.get(REFRESH_COOKIE)?.value;
  if (!refresh) return null;
  const tokens = await tokenRequest({ grant_type: "refresh_token", refresh_token: refresh });
  if (!tokens) {
    await clearTokens();
    return null;
  }
  await storeTokens(tokens, secure);
  return tokens.access_token;
}

/** Ferme la session Keycloak (si possible) et efface les cookies. */
export async function endSession() {
  const refresh = (await cookies()).get(REFRESH_COOKIE)?.value;
  if (refresh) {
    await fetch(`${OIDC}/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ client_id: CLIENT_ID, refresh_token: refresh }),
      cache: "no-store",
    }).catch(() => undefined);
  }
  await clearTokens();
}

export function isSecureRequest(request: Request) {
  return new URL(request.url).protocol === "https:" || request.headers.get("x-forwarded-proto") === "https";
}
