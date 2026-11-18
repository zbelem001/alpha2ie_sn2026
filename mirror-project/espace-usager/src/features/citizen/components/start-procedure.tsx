"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Check } from "lucide-react";
import { api } from "@/lib/api";
import type { Procedure } from "@/modules/casework/types/cases";
import styles from "@/features/citizen/styles/home.module.css";

// Démarche lancée par le citoyen lui-même : l'administration qui la propose vérifie ses
// informations auprès des registres ; aucune pièce n'est demandée.
export function StartProcedure({ onStart }: { onStart: (procedureCode: string, title: string) => Promise<void> }) {
  const [procedures, setProcedures] = useState<Procedure[] | null>(null);
  const [code, setCode] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api<Procedure[]>("procedures")
      .then((items) => { if (active) setProcedures(items.filter((item) => item.active && item.published)); })
      .catch((cause) => { if (active) { setProcedures([]); setError(cause instanceof Error ? cause.message : "Catalogue indisponible."); } });
    return () => { active = false; };
  }, []);

  const selected = procedures?.find((item) => item.code === code);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    if (!selected) { setError("Choisissez une démarche."); return; }
    if (!confirmed) { setError("Cochez la case pour autoriser les vérifications de cette démarche."); return; }
    setBusy(true); setError("");
    try {
      await onStart(selected.code, selected.title);
      setCode(""); setConfirmed(false);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "La démarche n’a pas pu être lancée."); }
    finally { setBusy(false); }
  }

  if (procedures !== null && procedures.length === 0 && !error) return null;
  return <section className={styles.profilePanel} aria-labelledby="start-title">
    <h2 id="start-title">Faire une démarche</h2>
    <p>L’administration vérifie elle-même vos informations auprès des registres : vous n’avez aucune pièce à fournir.</p>
    <form onSubmit={submit} noValidate>
      <fieldset disabled={busy || procedures === null}>
        <legend><strong>Démarche</strong></legend>
        {procedures === null ? <p role="status">Chargement…</p> : procedures.map((item) => <p key={item.code}><label>
          <input type="radio" name="procedure" value={item.code} checked={code === item.code} onChange={() => { setCode(item.code); setConfirmed(false); setError(""); }} /> {item.title}
        </label></p>)}
      </fieldset>
      {selected && <div className={styles.requestBody}>
        <p>{selected.purpose}</p>
        <h3>Informations vérifiées</h3>
        <ul>{(selected.questions ?? []).map((question) => <li key={question.code}><Check size={17} aria-hidden="true" />{question.description}{question.required ? "" : " (facultatif)"}</li>)}</ul>
        <p className={styles.requestLimit}>Seule la réponse utile est transmise (par exemple « majeur : oui »), jamais le document. Votre accord vaut pour cette démarche seulement, pendant {selected.consentDays} jours, et vous pouvez le retirer.</p>
        <p><label><input type="checkbox" checked={confirmed} disabled={busy} onChange={(e) => { setConfirmed(e.target.checked); setError(""); }} /> J’autorise ces vérifications pour cette démarche.</label></p>
      </div>}
      {error && <p role="alert">{error}</p>}
      <button className={styles.primary} type="submit" disabled={busy || !selected}>{busy ? "Vérifications en cours…" : "Lancer la démarche"}</button>
    </form>
  </section>;
}
