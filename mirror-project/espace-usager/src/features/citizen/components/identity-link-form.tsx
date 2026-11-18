"use client";

import { useState, type FormEvent } from "react";
import styles from "@/features/citizen/styles/home.module.css";

// Rattachement du compte à la référence de l'acte de naissance : c'est elle qui permet
// aux administrations de retrouver le citoyen dans les registres.
export function IdentityLinkForm({ onLink }: { onLink: (subjectRef: string) => Promise<void> }) {
  const [value, setValue] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    if (!value.trim()) { setError("Saisissez la référence de votre acte de naissance."); return; }
    if (!confirmed) { setError("Confirmez qu’il s’agit bien de votre acte de naissance."); return; }
    setBusy(true); setError("");
    try { await onLink(value); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Le rattachement n’a pas abouti."); }
    finally { setBusy(false); }
  }
  return <section className={styles.profilePanel} aria-labelledby="identity-link-title">
    <h2 id="identity-link-title">Rattacher mon compte</h2>
    <p>Pour voir vos démarches et les consultations de vos informations, indiquez une fois la référence de votre acte de naissance.</p>
    <form onSubmit={submit} noValidate>
      <label htmlFor="subject-ref"><strong>Référence de l’acte de naissance</strong></label>
      <input id="subject-ref" value={value} maxLength={160} autoComplete="off" disabled={busy} placeholder="ACTE:OUAGA:2004:01234" onChange={(e) => { setValue(e.target.value); setError(""); }} />
      <p><label><input type="checkbox" checked={confirmed} disabled={busy} onChange={(e) => { setConfirmed(e.target.checked); setError(""); }} /> Je confirme qu’il s’agit de mon propre acte de naissance.</label></p>
      {error && <p role="alert">{error}</p>}
      <button className={styles.primary} type="submit" disabled={busy}>{busy ? "Rattachement…" : "Rattacher mon compte"}</button>
    </form>
    <p className={styles.journalNote}>Démonstration : Awa, compte citoyen-demo, acte ACTE:OUAGA:2004:01234.</p>
  </section>;
}
