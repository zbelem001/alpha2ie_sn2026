"use client";

import { useState } from "react";
import type { Consultation, Report, ReportKind } from "@/lib/journal";
import styles from "@/features/citizen/styles/home.module.css";

const dateFormat = new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "long", year: "numeric", timeZone: "Africa/Ouagadougou" });

const ACTIONS: Record<ReportKind, { button: string; confirm: string; done: (entry: Consultation, date: string) => string }> = {
  not_me: {
    button: "Je ne reconnais pas cette consultation",
    confirm: "Votre signalement sera inscrit au journal de la démarche et visible par l’administration qui a consulté vos informations.",
    done: (entry, date) => `Consultation signalée le ${date} : ${entry.organization} voit votre signalement dans votre dossier.`,
  },
  wrong_result: {
    button: "Une information est fausse : demander une correction",
    confirm: "Votre demande sera inscrite au journal de la démarche, pour que l’administration la transmette au registre concerné.",
    done: (entry, date) => `Correction demandée le ${date} : ${entry.organization} la voit dans votre dossier, pour transmission à ${entry.source}.`,
  },
};

// Signaler une consultation du journal (POST /v1/cases/{id}/journal/{événement}/report) :
// contestation (« ce n'est pas moi ») ou demande de correction auprès de la source.
export function ReportActions({ entry, reports, onReport }: { entry: Consultation; reports: Report[]; onReport: (kind: ReportKind) => Promise<void> }) {
  const [confirming, setConfirming] = useState<ReportKind | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (entry.kind !== "consultation") return null;

  async function send(kind: ReportKind) {
    setBusy(true); setError("");
    try { await onReport(kind); setConfirming(null); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Le signalement n’a pas abouti."); }
    finally { setBusy(false); }
  }

  return <div className={styles.consentBox}>
    {(Object.keys(ACTIONS) as ReportKind[]).map((kind) => {
      const sent = reports.find((report) => report.kind === kind);
      if (sent) return <p key={kind} role="status">{ACTIONS[kind].done(entry, dateFormat.format(new Date(sent.occurredAt)))}</p>;
      if (confirming === kind) return <div key={kind}>
        <p>{ACTIONS[kind].confirm}</p>
        <div className={styles.decisions}>
          <button className={styles.secondary} type="button" disabled={busy} onClick={() => send(kind)}>{busy ? "Envoi…" : "Confirmer"}</button>
          <button className={styles.reportButton} type="button" disabled={busy} onClick={() => setConfirming(null)}>Annuler</button>
        </div>
      </div>;
      return <p key={kind}><button className={styles.reportButton} type="button" disabled={busy || confirming !== null} onClick={() => setConfirming(kind)}>{ACTIONS[kind].button}</button></p>;
    })}
    {error && <p role="alert">{error}</p>}
  </div>;
}
