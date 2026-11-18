import { BACKEND_URL } from "@/lib/server/auth";
import { SPACE } from "@/lib/space";

export async function POST(request: Request) {
  const origin = request.headers.get("origin");
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host") ?? new URL(request.url).host;
  try { if (origin && new URL(origin).host !== host) return Response.json({ detail: "Origine refusée." }, { status: 403 }); } catch { return Response.json({ detail: "Origine invalide." }, { status: 403 }); }
  let body;
  try { body = await request.json(); } catch { return Response.json({ detail: "Requête invalide." }, { status: 400 }); }
  if (!body || typeof body !== "object" || Array.isArray(body)) return Response.json({ detail: "Requete invalide." }, { status: 400 });
  const { action, ...payload } = body;
  if (!["continue", "verify", "register"].includes(action)) return Response.json({ detail: "Action invalide." }, { status: 400 });
  if (!SPACE.roles.includes("citizen") && action !== "continue") return Response.json({ detail: "Les comptes agents sont créés par l’administration." }, { status: 403 });
  if (action === "continue") payload.agent = !SPACE.roles.includes("citizen");
  try {
    const response = await fetch(`${BACKEND_URL}/v1/auth/phone/${action}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload), cache: "no-store", signal: AbortSignal.timeout(20000) });
    if (response.status === 404) return Response.json({ detail: "Ce numero n’a pas de compte administrateur. Contactez votre responsable." }, { status: 404 });
    return new Response(await response.text(), { status: response.status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });
  } catch { return Response.json({ detail: "Le service d’accès est indisponible. Réessayez." }, { status: 503 }); }
}
