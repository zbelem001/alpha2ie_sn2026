"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { HoldConsentButton } from "@/features/citizen/components/hold-consent-button";
import { api } from "@/lib/api";
import styles from "@/features/citizen/styles/home.module.css";

type Administration = { code: string; name: string };
type Procedure = { administration: Administration; code: string; title: string; purpose: string; consentDays: number; questions: { code: string; description: string }[] };
export function CitizenProcedureForm({ onCreated }: { onCreated?: () => void }) {
  const [procedures, setProcedures] = useState<Procedure[]>([]);
  const [selected, setSelected] = useState("");
  const [administrations, setAdministrations] = useState<Administration[]>([]);
  const [administration, setAdministration] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ reference: string; identifierStatus?: { complete: boolean } | null } | null>(null);
  useEffect(() => {
    let active = true;
    Promise.all([api<Procedure[]>("procedures"), api<Administration[]>("citizen/administrations")])
      .then(([items, ministries]) => { if (active) { setProcedures(items); setAdministrations(ministries); } })
      .catch((cause) => { if (active) setError(cause.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  const available = procedures.filter((item) => item.administration.code === administration);
  const procedure = available.find((item) => item.code === selected);
  async function start() {
    if (!procedure || busy) return;
    setBusy(true); setError("");
    try { setResult(await api("citizen/cases", { body: { procedureCode: procedure.code, confirmed: true } })); onCreated?.(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "La démarche n’a pas pu être envoyée."); }
    finally { setBusy(false); }
  }

  return <section className={styles.procedureArea} aria-labelledby="start-procedure-title">
      <h1 id="start-procedure-title">Faire une démarche</h1>
      {error && <p role="alert">{error}</p>}
      {result ? <section className={styles.procedureForm} role="status"><h2>Demande envoyée</h2><p>Dossier {result.reference}. Votre accord est enregistré.</p><p>{result.identifierStatus?.complete ? "Les références nécessaires sont disponibles." : "L’administration vous demandera uniquement les références manquantes."}</p><Link className={styles.primary} href="#cases-title">Suivre mon dossier</Link></section> : <section className={styles.procedureForm}>
        <label htmlFor="citizen-administration">Ministère ou administration</label>
        <select id="citizen-administration" value={administration} disabled={loading || busy} onChange={(event) => { setAdministration(event.target.value); setSelected(""); setError(""); }}><option value="">Choisir une administration</option>{administrations.map((item) => <option value={item.code} key={item.code}>{item.name}</option>)}</select>
        <label htmlFor="citizen-procedure">Démarche</label>
        <select id="citizen-procedure" value={selected} disabled={loading || busy || !administration} onChange={(event) => { setSelected(event.target.value); setError(""); }}><option value="">Choisir une démarche</option>{available.map((item) => <option value={item.code} key={item.code}>{item.title}</option>)}</select>
        {loading && <p role="status">Chargement…</p>}
        {!loading && administration && !available.length && <p>Cette administration n’a pas encore publié de démarche.</p>}
        {procedure && <><details><summary>Vérifications et conditions de mon accord</summary><p>{procedure.purpose}</p><ul>{procedure.questions.map((question) => <li key={question.code}>{question.description}</li>)}</ul>
          <p>L’accord porte uniquement sur ces vérifications, pour {procedure.consentDays} jours. Vous pouvez le retirer depuis votre dossier.</p></details>
          <p>En maintenant le bouton, j’autorise les administrations concernées à effectuer uniquement ces vérifications pour ma démarche.</p>
          <HoldConsentButton key={selected} disabled={busy} onConfirm={() => { void start(); }} />
          {busy && <p role="status">Envoi de votre demande…</p>}</>}
      </section>}

    </section>;
}
