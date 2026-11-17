"use client";

import { Bell, Check, ChevronDown, X } from "lucide-react";
import type { CitizenHomeData } from "@/features/citizen/mocks/home";
import { useBrowserClock } from "@/lib/use-browser-clock";
import styles from "@/features/citizen/styles/home.module.css";

type Request = NonNullable<CitizenHomeData["pendingRequest"]> & { requestedAt?: string };

export function AuthorizationRequest({ request, onDecision }: { request: Request; onDecision: (decision: "granted" | "refused") => void }) {
  const now = useBrowserClock();
  const minutes = request.requestedAt ? Math.max(0, Math.floor(((now || new Date(request.requestedAt).getTime()) - new Date(request.requestedAt).getTime()) / 60_000)) : 30;
  return <section className={styles.attention} aria-labelledby={`request-${request.id}`}>
    <div className={styles.requestNotification}><span>{minutes === 0 ? "À l’instant" : `Il y a ${minutes} minute${minutes === 1 ? "" : "s"}`}</span><Bell size={18} aria-label="Nouvelle demande" /></div>
    <details className={styles.requestDetails}>
      <summary><span className={styles.requestCopy}><span className={styles.actionLabel}>Demande d’autorisation</span><strong id={`request-${request.id}`}>{request.organization}</strong><span className={styles.requestPurpose}>Vérification de vos informations pour {request.purpose}.</span></span><span className={styles.reviewAction}>Répondre <ChevronDown size={17} aria-hidden="true" /></span></summary>
      <div className={styles.requestBody}><h3>Informations à vérifier</h3><ul>{request.checks.map((check) => <li key={check}><Check size={17} aria-hidden="true" />{check}</li>)}</ul><p className={styles.requestLimit}>Cet accord concerne uniquement cette démarche, pour {request.duration}.</p><div className={styles.decisions}><button className={styles.primary} type="button" onClick={() => onDecision("granted")}><Check size={18} aria-hidden="true" /> Je donne mon accord</button><button className={styles.secondary} type="button" onClick={() => onDecision("refused")}><X size={18} aria-hidden="true" /> Je refuse</button></div></div>
    </details>
  </section>;
}
