"use client";

import Image from "next/image";
import type { ReactNode } from "react";

export function AuthShell({ children }: { children: ReactNode }) {
  return (
    <main className="login-page access-page" id="contenu">
      <header className="login-brand">
        <div className="login-logo">
          <Image
            src="/Coat_of_arms_of_Burkina_Faso_(2025-present)%20(1).svg"
            alt="Armoiries du Burkina Faso"
            fill
            sizes="34px"
            preload
          />
        </div>
        <div className="login-brand-copy">
          <span className="login-country">Burkina Faso</span>
          <span className="login-service">Dites-le-nous une fois</span>
        </div>
      </header>
      <section className="login-panel" aria-labelledby="login-title">
        <div className="login-block">{children}</div>
      </section>
      {/* Armoiries tirées de docs/armoiries-1.png (fond rendu transparent, 83 Ko) ; décoratives :
          la pilule du logo les annonce déjà aux lecteurs d'écran. Masquées sur téléphone. */}
      <div className="visual-panel">
        <Image className="login-arms" src="/armoiries.webp" alt="" width={936} height={1100} unoptimized />
      </div>
    </main>
  );
}
