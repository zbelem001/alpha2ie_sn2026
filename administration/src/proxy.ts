// Sans session, les pages de l'espace renvoient vers la connexion. L'API démarches
// vérifie de son côté chaque jeton : ce contrôle évite seulement d'afficher un écran vide.
import { NextResponse, type NextRequest } from "next/server";
import { REFRESH_COOKIE } from "@/lib/server/session-cookies";

export function proxy(request: NextRequest) {
  if (!request.cookies.has(REFRESH_COOKIE)) return NextResponse.redirect(new URL("/", request.url));
  return NextResponse.next();
}

export const config = { matcher: ["/administration/:path*"] };
