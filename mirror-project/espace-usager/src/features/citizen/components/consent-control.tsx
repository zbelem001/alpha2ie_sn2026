"use client";

import { useState } from "react";
import { consentIsActive } from "@/lib/journal";
import type { CitizenCase } from "@/features/citizen/hooks/use-citizen-space";
import styles from "@/features/citizen/styles/home.module.css";

const dateFormat = new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "long", year: "numeric", timeZone: "Africa/Ouagadougou" });
const format = (value?: string) => (value ? dateFormat.format(new Date(value)) : "");

// Consulter et retirer son accord : le retrait vaut pour la suite, aucune nouvelle
// vérification ne peut partir avec cet accord (DELETE /v1/cases/{id}/consent).
export function ConsentControl({ item, onRevoke }: { item: CitizenCase; onRevoke: (caseId: string) => Promise<void> }) {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const consent = item.consent;
  const where = item.channel === "assisted" ? "au guichet" : "depuis votre espace";

  async function revoke() {
    setBusy(true); setError("");
    try { await onRevoke(item.id); setConfirming(false); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Le retrait n’a pas abouti."); }
    finally { setBusy(false); }
  }

  let text: string;
  if (consent.status === "granted" && consentIsActive(consent)) text = `Accord donné ${where} le ${format(consent.decidedAt)}, valable jusqu’au ${format(consent.expiresAt)}, pour cette démarche seulement.`;
  else if (consent.status === "granted") text = `Votre accord a expiré le ${format(consent.expiresAt)}.`;
  else if (consent.status === "revoked") text = `Vous avez retiré votre accord le ${format(consent.decidedAt)}. Aucune nouvelle vérification ne peut être faite avec cet accord.`;
  else if (consent.status === "refused") text = `Vous avez refusé cette demande le ${format(consent.decidedAt)}.`;
  else text = item.channel === "assisted" ? "Votre accord sera recueilli au guichet." : "En attente de votre réponse (voir la demande ci-dessus).";

  return <div className={styles.consentBox}>
    <p><strong>Votre accord</strong> · {text}</p>
    {consent.status === "granted" && consentIsActive(consent) && (confirming ? <>
      <p>Après le retrait, plus aucune vérification ne pourra être faite pour cette démarche avec cet accord. Les vérifications déjà faites restent au journal.</p>
      <div className={styles.decisions}>
        <button className={styles.secondary} type="button" disabled={busy} onClick={revoke}>{busy ? "Retrait…" : "Confirmer le retrait"}</button>
        <button className={styles.reportButton} type="button" disabled={busy} onClick={() => setConfirming(false)}>Annuler</button>
      </div>
    </> : <button className={styles.reportButton} type="button" onClick={() => setConfirming(true)}>Retirer mon accord</button>)}
    {error && <p role="alert">{error}</p>}
  </div>;
}
