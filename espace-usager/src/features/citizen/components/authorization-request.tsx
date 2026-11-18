"use client";

import { useState } from "react";
import { Bell, Check, ChevronDown, X } from "lucide-react";
import { useBrowserClock } from "@/lib/use-browser-clock";
import type { CitizenCase } from "@/features/citizen/hooks/use-citizen-space";
import styles from "@/features/citizen/styles/home.module.css";

export function AuthorizationRequest({ request, onDecision }: { request: CitizenCase; onDecision: (decision: "granted" | "refused") => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const now = useBrowserClock();
  const minutes = Math.max(0, Math.floor(((now || new Date(request.createdAt).getTime()) - new Date(request.createdAt).getTime()) / 60_000));
  async function decide(decision: "granted" | "refused") {
    if (busy) return;
    setBusy(true); setError("");
    try { await onDecision(decision); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Votre réponse n’a pas été enregistrée."); }
    finally { setBusy(false); }
  }
  return <section className={styles.attention} aria-labelledby={`request-${request.id}`}>
    <div className={styles.requestNotification}><span>{minutes === 0 ? "À l’instant" : minutes < 60 ? `Il y a ${minutes} minute${minutes === 1 ? "" : "s"}` : `Dossier ${request.reference}`}</span><Bell size={18} aria-label="Nouvelle demande" /></div>
    <details className={styles.requestDetails}>
      <summary>
        <span className={styles.requestCopy}>
          <span className={styles.actionLabel}>Demande d’autorisation</span>
          <strong id={`request-${request.id}`}>{request.requester}</strong>
          <span className={styles.requestPurpose}><strong>{request.procedureTitle}</strong></span>
        </span>
        <span className={styles.reviewAction}>Répondre <ChevronDown size={17} aria-hidden="true" /></span>
      </summary>
      <div className={styles.requestBody}>
        <p className={styles.requestLimit}><strong>Votre accord est limité à cette démarche pendant {request.consentDays} jours.</strong></p>
        {request.checks.length > 0 && <>
          <h3>Informations concernées</h3>
          <ul>{request.checks.map((check) => <li key={check.questionCode}><Check size={17} aria-hidden="true" /><strong>{check.registry}</strong><span>{check.label.replace(/ : .*$/, "")}</span></li>)}</ul>
        </>}
        {error && <p role="alert">{error}</p>}
        {request.channel === "assisted"
          ? <p>Pour donner votre accord au guichet, communiquez à l’agent le code reçu uniquement si vous acceptez.</p>
          : <div className={styles.decisions}><button className={styles.primary} type="button" disabled={busy} onClick={() => decide("granted")}><Check size={18} aria-hidden="true" /> {busy ? "Envoi…" : "Je donne mon accord"}</button><button className={styles.secondary} type="button" disabled={busy} onClick={() => decide("refused")}><X size={18} aria-hidden="true" /> Je refuse</button></div>}
      </div>
    </details>
  </section>;
}
