"use client";

import Image from "next/image";
import type { ReactNode } from "react";

/** Étoile à cinq branches de l'écu, en jaune-or (couleur du texte courant). */
function FasoStar({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false">
      <path d="M12 1.5l3.09 7.26 7.86.68-5.96 5.17 1.79 7.69L12 18.27l-6.78 4.03 1.79-7.69L1.05 9.44l7.86-.68z" />
    </svg>
  );
}

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
      <section className="visual-panel" aria-label="Bienvenue">
        <FasoStar className="visual-star" />
        <div className="visual-copy">
          <span className="visual-eyebrow">Moins de papiers. Plus de simplicité.</span>
          <h2>Vos démarches,<br />en toute confiance.</h2>
          <p>
            Un seul espace pour suivre vos démarches, autoriser les échanges
            et garder le contrôle sur vos données.
          </p>
        </div>
      </section>
    </main>
  );
}
