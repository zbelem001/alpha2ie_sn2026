import { currentAccessToken, decodeClaims, IdentityUnavailableError, isSecureRequest, spaceRole } from "@/lib/server/auth";

export async function GET(request: Request) {
  try {
    const token = await currentAccessToken(isSecureRequest(request));
    if (!token) return Response.json({ authenticated: false });
    const claims = decodeClaims(token);
    const role = spaceRole(claims);
    if (!role) return Response.json({ authenticated: false });
    return Response.json({
      authenticated: true,
      role,
      name: claims.name ?? claims.preferred_username ?? "",
      username: claims.preferred_username ?? "",
      administrationCode: claims.administration_code ?? null,
    });
  } catch (error) {
    if (error instanceof IdentityUnavailableError) {
      return Response.json({ detail: "Le service d’identité est indisponible." }, { status: 503 });
    }
    throw error;
  }
}
