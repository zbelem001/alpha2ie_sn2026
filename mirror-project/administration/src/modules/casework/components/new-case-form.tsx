"use client";
import { useState, type FormEvent } from "react";
import { requirementsFor, cleanReferences, type DocumentReferences } from "@/lib/document-references";
import type { ConsentChannel, Procedure } from "@/modules/casework/types/cases";
import styles from "@/modules/casework/styles/workspace.module.css";

export function NewCaseForm({ busy, procedures, onCreate }: { busy: boolean; procedures: Procedure[]; onCreate: (name: string, phone: string, procedure: string, channel: ConsentChannel, references: DocumentReferences) => Promise<void> }) {
  const [code, setCode] = useState(""); const [name, setName] = useState(""); const [phone, setPhone] = useState("");
  const [channel, setChannel] = useState<ConsentChannel>("assisted");
  const [error, setError] = useState("");
  const procedure = procedures.find((item) => item.code === code);
  const documents = requirementsFor(procedure?.checks ?? []);
  async function submit(e: FormEvent) {
    e.preventDefault(); if (busy || !procedure) return;
    try {
      if (!name.trim()) throw new Error("Renseignez le nom complet du citoyen.");
      if (!/^\d{8}$/.test(phone.replace(/\s/g, ""))) throw new Error("Entrez un numéro de téléphone à 8 chiffres.");
      const values = cleanReferences(documents, {}, false);
      setError(""); await onCreate(name, phone, procedure.code, channel, values);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Vérifiez les informations saisies."); }
  }
  return <form className={styles.newForm} onSubmit={submit} noValidate>
    <h2>1. Choisir la démarche</h2>
    <label className={styles.label} htmlFor="procedure">Démarche</label><select id="procedure" className={styles.input} disabled={busy || !procedures.length} value={procedure?.code ?? ""} onChange={(e) => { setCode(e.target.value); setError(""); }}><option value="">Choisir une démarche</option>{procedures.map((item) => <option key={item.code} value={item.code}>{item.title}</option>)}</select>
    {!procedures.length && <p className={styles.errorText}>Aucune démarche publiée pour votre administration.</p>}
    <div className={styles.formSection}><h2>2. Identifier le citoyen</h2><div className={styles.identityFields}><div><label className={styles.label} htmlFor="applicant-name">Nom complet du citoyen</label><input id="applicant-name" className={styles.input} value={name} maxLength={100} disabled={busy} required onChange={(e) => setName(e.target.value)} /></div><div><label className={styles.label} htmlFor="citizen-phone">Numéro de téléphone</label><input id="citizen-phone" className={styles.input} type="tel" inputMode="numeric" maxLength={8} placeholder="8 chiffres" value={phone} disabled={busy || !procedure} required onChange={(e) => setPhone(e.target.value.replace(/[^\d\s]/g, ""))} /><p className={styles.hint}>Le numéro du compte citoyen qui recevra la demande d’accord.</p></div></div></div>
    <fieldset className={styles.formSection} disabled={busy}><legend className={styles.legend}>3. Recueillir son accord</legend><label className={styles.radio}><input type="radio" name="channel" value="assisted" checked={channel === "assisted"} onChange={() => setChannel("assisted")} /><span>Au guichet : code reçu par SMS</span></label><label className={styles.radio}><input type="radio" name="channel" value="web" checked={channel === "web"} onChange={() => setChannel("web")} /><span>À distance : espace citoyen</span></label></fieldset>
    {procedure && <p className={styles.hint}>Après son accord, les références déjà enregistrées seront utilisées. Vous demanderez uniquement celles qui manquent pour cette démarche.</p>}
    {error && <p role="alert" className={styles.errorText}>{error}</p>}
    <div className={styles.formBottom}><p>Aucun registre n’est consulté avant l’accord du citoyen.</p><button className={styles.primary} disabled={busy || !procedure} type="submit">{busy ? "Ouverture…" : "Ouvrir le dossier"}</button></div>
  </form>;
}
