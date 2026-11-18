import { decodeClaims, IdentityUnavailableError, isSecureRequest, passwordGrant, spaceRole, storeTokens } from "@/lib/server/auth";
import { SPACE } from "@/lib/space";

export async function POST(request: Request) {
  let body: { username?: unknown; password?: unknown };
  try {
    body = await request.json();
  } catch {
    return Response.json({ detail: "Requête invalide." }, { status: 400 });
  }
  const username = typeof body.username === "string" ? body.username.trim() : "";
  const password = typeof body.password === "string" ? body.password : "";
  if (!username || !password) return Response.json({ detail: "Identifiant et mot de passe requis." }, { status: 400 });

  if (!/^[0-9]{8}$/.test(username) || !/^[0-9]{4,6}$/.test(password)) return Response.json({ detail: "Numero ou code PIN invalide." }, { status: 400 });

  try {
    const tokens = await passwordGrant(username, password);
    if (!tokens) return Response.json({ detail: "Identifiant ou mot de passe incorrect." }, { status: 401 });
    const claims = decodeClaims(tokens.access_token);
    const role = spaceRole(claims);
    if (!role) return Response.json({ detail: "Ce compte n’a pas accès à cet espace." }, { status: 403 });
    await storeTokens(tokens, isSecureRequest(request));
    return Response.json({ role, home: SPACE.home[role] ?? "/", name: claims.name ?? claims.preferred_username ?? username });
  } catch (error) {
    if (error instanceof IdentityUnavailableError) {
      return Response.json({ detail: "Le service d’identité est indisponible. Réessayez dans un instant." }, { status: 503 });
    }
    throw error;
  }
}
