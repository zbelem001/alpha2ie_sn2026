"use client";

import Link from "next/link";
import { useState } from "react";
import { Bell, Check, ChevronDown, X } from "lucide-react";
import { useBrowserClock } from "@/lib/use-browser-clock";
import { requirementsFor } from "@/lib/document-references";
import type { CitizenCase } from "@/features/citizen/hooks/use-citizen-space";
import styles from "@/features/citizen/styles/home.module.css";

export function AuthorizationRequest({ request, onDecision }: { request: CitizenCase; onDecision: (decision: "granted" | "refused") => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const documents = requirementsFor(request.checks);
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
      <summary><span className={styles.requestCopy}><span className={styles.actionLabel}>Demande d’autorisation</span><strong id={`request-${request.id}`}>{request.requester}</strong><span className={styles.requestPurpose}>Vérification de vos informations pour votre démarche « {request.procedureTitle} ».</span></span><span className={styles.reviewAction}>Répondre <ChevronDown size={17} aria-hidden="true" /></span></summary>
      <div className={styles.requestBody}>
        <h3>Informations à vérifier</h3>
        <ul>{request.checks.map((check) => <li key={check.questionCode}><Check size={17} aria-hidden="true" />{check.label}</li>)}</ul>
        <p className={styles.requestLimit}>Cet accord concerne uniquement cette démarche, pour {request.consentDays} jours. Seule la réponse utile est transmise (par exemple « majeur : oui »), jamais le document lui-même.</p>
        {documents.length > 0 && <><h3>Documents concernés</h3><ul>{documents.map((doc) => <li key={doc.key}><Check size={17} aria-hidden="true" />{doc.label} · {doc.provider}</li>)}</ul><p>Vous n’avez rien à fournir. Les références enregistrées dans <Link href="/usager/profil">votre profil</Link> sont utilisées si l’administration en a besoin.</p></>}
        {error && <p role="alert">{error}</p>}
        <div className={styles.decisions}><button className={styles.primary} type="button" disabled={busy} onClick={() => decide("granted")}><Check size={18} aria-hidden="true" /> {busy ? "Envoi…" : "Je donne mon accord"}</button><button className={styles.secondary} type="button" disabled={busy} onClick={() => decide("refused")}><X size={18} aria-hidden="true" /> Je refuse</button></div>
      </div>
    </details>
  </section>;
}
