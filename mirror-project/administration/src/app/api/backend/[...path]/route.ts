// Relais vers l'API démarches : ajoute le jeton de la session, que le navigateur ne voit jamais.
import { BACKEND_URL, currentAccessToken, decodeClaims, IdentityUnavailableError, isSecureRequest } from "@/lib/server/auth";
import { SPACE } from "@/lib/space";

type Context = { params: Promise<{ path: string[] }> };

async function forward(request: Request, { params }: Context) {
  const { path } = await params;
  const route = path.join("/");
  if (path.some((segment) => segment === "." || segment === "..") || !SPACE.backendRoutes.test(route)) {
    return Response.json({ detail: "Route non disponible dans cet espace." }, { status: 404 });
  }

  let token: string | null;
  try {
    token = await currentAccessToken(isSecureRequest(request));
  } catch (error) {
    if (error instanceof IdentityUnavailableError) {
      return Response.json({ detail: "Le service d’identité est indisponible." }, { status: 503 });
    }
    throw error;
  }
  if (!token) return Response.json({ detail: "Session expirée. Reconnectez-vous." }, { status: 401 });

  {
    const roles = decodeClaims(token).realm_access?.roles;
    if (!Array.isArray(roles) || !SPACE.roles.some((role) => roles.includes(role))) return Response.json({ detail: "Votre session ne permet pas d?acc?der ? cet espace. Reconnectez-vous avec un compte administrateur." }, { status: 403 });
  }

  const hasBody = !["GET", "HEAD"].includes(request.method);
  const target = `${BACKEND_URL}/v1/${path.map(encodeURIComponent).join("/")}${new URL(request.url).search}`;
  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/json",
        ...(hasBody ? { "Content-Type": "application/json" } : {}),
      },
      body: hasBody ? await request.text() : undefined,
      cache: "no-store",
    });
  } catch {
    return Response.json({ detail: "Le service des démarches est indisponible." }, { status: 503 });
  }
  if ([204, 205, 304].includes(upstream.status)) return new Response(null, { status: upstream.status });
  return new Response(await upstream.text(), {
    status: upstream.status,
    headers: { "Content-Type": upstream.headers.get("content-type") ?? "application/json" },
  });
}

export { forward as GET, forward as POST, forward as PUT, forward as PATCH, forward as DELETE };
