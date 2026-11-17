"use client";

import Image from "next/image";
import { useId, type ReactNode } from "react";

/**
 * Motif turquoise : capsules à 45° avec bouts arrondis en escalier,
 * dégradé, bandes claires et petites décorations.
 * Utilisé en haut sur mobile et en grand dans le panneau de droite sur desktop.
 */
function PaintCapsules({ className }: { className?: string }) {
  const uid = useId().replace(/:/g, "");
  const mint = `mint-${uid}`;
  const mintLight = `mint-light-${uid}`;

  return (
    <svg
      className={className}
      viewBox="0 0 305 215"
      preserveAspectRatio="xMinYMin slice"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <linearGradient
          id={mint}
          gradientUnits="userSpaceOnUse"
          x1="0"
          y1="60"
          x2="300"
          y2="10"
        >
          <stop offset="0%" stopColor="#8ED6C6" />
          <stop offset="55%" stopColor="#B4E6DA" />
          <stop offset="100%" stopColor="#D8F3EC" />
        </linearGradient>
        <linearGradient
          id={mintLight}
          gradientUnits="userSpaceOnUse"
          x1="0"
          y1="0"
          x2="300"
          y2="40"
        >
          <stop offset="0%" stopColor="#BFEADF" />
          <stop offset="100%" stopColor="#E6F8F3" />
        </linearGradient>
      </defs>

      {/* Capsules principales */}
      <g stroke={`url(#${mint})`} strokeWidth="44" strokeLinecap="round">
        <line x1="-62" y1="80" x2="28" y2="170" />
        <line x1="-52" y1="18" x2="68" y2="138" />
        <line x1="-42" y1="-44" x2="108" y2="106" />
        <line x1="-2" y1="-76" x2="148" y2="74" />
        <line x1="58" y1="-88" x2="188" y2="42" />
        <line x1="118" y1="-100" x2="228" y2="10" />
      </g>

      {/* Petite capsule claire en haut à droite */}
      <line
        x1="235"
        y1="-12"
        x2="278"
        y2="31"
        stroke={`url(#${mintLight})`}
        strokeWidth="26"
        strokeLinecap="round"
      />

      {/* Bandes claires à l'intérieur */}
      <g
        stroke="#FFFFFF"
        strokeOpacity="0.5"
        strokeWidth="6"
        strokeLinecap="round"
      >
        <line x1="-10" y1="60" x2="40" y2="110" />
        <line x1="20" y1="18" x2="80" y2="78" />
        <line x1="100" y1="26" x2="132" y2="58" />
        <line x1="150" y1="-10" x2="176" y2="16" />
      </g>

    </svg>
  );
}

export function AuthShell({ children }: { children: ReactNode }) {
  return (
    <main className="login-page access-page">
      <PaintCapsules className="paint paint--mobile" />
      <PaintCapsules className="paint paint--visual" />
      <header className="login-brand">
        <div className="login-logo">
          <Image
            src="/Coat_of_arms_of_Burkina_Faso_(2025-present)%20(1).svg"
            alt="Armoiries du Burkina Faso"
            fill
            sizes="(max-width: 720px) 46px, 64px"
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
