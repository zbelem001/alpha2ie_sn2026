"use client";

import { useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import styles from "@/features/citizen/styles/home.module.css";
import fieldStyles from "@/styles/document-fields.module.css";

export type IdentityProof = { subject_ref: string; last_name: string; first_names: string; birth_date: string; mother_name: string };

/** Rattache le compte à l'acte de naissance, avec la preuve de titularité vérifiée par l'état civil. */
export function linkIdentity(proof: IdentityProof) {
  return api("citizen/identity-link", { body: { ...proof, confirmed: true } });
}

const EMPTY: IdentityProof = { subject_ref: "", last_name: "", first_names: "", birth_date: "", mother_name: "" };
const FIELDS: { key: keyof IdentityProof; label: string; hint?: string; type?: string; autoComplete?: string }[] = [
  { key: "subject_ref", label: "Référence de l’acte de naissance", hint: "Exemple : ACTE:OUAGA:2004:01234" },
  { key: "last_name", label: "Nom", autoComplete: "family-name" },
  { key: "first_names", label: "Prénoms", autoComplete: "given-name" },
  { key: "birth_date", label: "Date de naissance", type: "date", autoComplete: "bday" },
  { key: "mother_name", label: "Nom et prénom de votre mère", hint: "Tels qu’inscrits sur votre acte de naissance" },
];

// Rattachement du compte à l'acte de naissance : c'est lui qui permet aux administrations de
// retrouver le citoyen dans les registres. L'état civil compare les informations saisies à l'acte
// et répond seulement « correspond » ou non ; elles ne sont pas conservées.
export function IdentityLinkForm({ onLink }: { onLink: (proof: IdentityProof) => Promise<void> }) {
  const [values, setValues] = useState<IdentityProof>(EMPTY);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    const missing = FIELDS.find((field) => !values[field.key].trim());
    if (missing) { setError(`Renseignez : ${missing.label.toLowerCase()}.`); return; }
    if (!confirmed) { setError("Confirmez qu’il s’agit bien de votre acte de naissance."); return; }
    setBusy(true); setError("");
    try { await onLink({ ...values, subject_ref: values.subject_ref.trim().toUpperCase() }); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Le rattachement n’a pas abouti."); }
    finally { setBusy(false); }
  }
  return <section className={styles.profilePanel} aria-labelledby="identity-link-title">
    <h2 id="identity-link-title">Rattacher mon compte</h2>
    <p>Pour voir vos démarches et les consultations de vos informations, rattachez une fois votre compte à votre acte de naissance. L’état civil vérifie que ces informations correspondent à l’acte ; elles ne sont pas conservées.</p>
    <form onSubmit={submit} noValidate>
      <div className={fieldStyles.fields}>{FIELDS.map((field) => <label key={field.key} htmlFor={`identity-${field.key}`}>
        <strong>{field.label}</strong>
        <input id={`identity-${field.key}`} type={field.type ?? "text"} value={values[field.key]} maxLength={160} disabled={busy}
          autoComplete={field.autoComplete ?? "off"} onChange={(e) => { setValues({ ...values, [field.key]: e.target.value }); setError(""); }} />
        {field.hint && <small>{field.hint}</small>}
      </label>)}</div>
      <p><label><input type="checkbox" checked={confirmed} disabled={busy} onChange={(e) => { setConfirmed(e.target.checked); setError(""); }} /> Je confirme qu’il s’agit de mon propre acte de naissance.</label></p>
      {error && <p role="alert">{error}</p>}
      <button className={styles.primary} type="submit" disabled={busy}>{busy ? "Vérification…" : "Rattacher mon compte"}</button>
    </form>
    <p className={styles.journalNote}>Démonstration : Awa (compte citoyen-demo) — acte ACTE:OUAGA:2004:01234, KABORE Awa, née le 12/03/2004, mère : COMPAORE Salimata.</p>
  </section>;
}
