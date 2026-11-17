"use client";
import { useState, type FormEvent } from "react";
import { useDemoAdministration } from "@/lib/use-demo-administration";
import { requirementsFor, cleanReferences, type DocumentReferences } from "@/lib/document-references";
import { DocumentFields } from "@/components/shared/document-fields";
import type { ConsentChannel } from "@/modules/casework/types/cases";
import styles from "@/modules/casework/styles/workspace.module.css";

export function NewCaseForm({ busy, onCreate }: { busy: boolean; onCreate: (name: string, phone: string, procedure: string, channel: ConsentChannel, references: DocumentReferences) => Promise<void> }) {
  const config = useDemoAdministration();
  const procedures = config.procedures.filter((item) => item.active && item.published);
  const [code, setCode] = useState(""); const [name, setName] = useState(""); const [phone, setPhone] = useState("");
  const [channel, setChannel] = useState<ConsentChannel>("assisted");
  const [references, setReferences] = useState<DocumentReferences>({}); const [error, setError] = useState("");
  const procedure = procedures.find((item) => item.code === code) ?? procedures[0];
  const documents = requirementsFor(procedure?.checks ?? []);
  async function submit(e: FormEvent) {
    e.preventDefault(); if (busy || !procedure) return;
    try {
      if (!/^\d{8}$/.test(phone.replace(/\s/g, ""))) throw new Error("Entrez un numéro de téléphone à 8 chiffres.");
      const values = cleanReferences(documents, references, channel === "assisted");
      setError(""); await onCreate(name, phone, procedure.code, channel, values);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Vérifiez les informations saisies."); }
  }
  return <form className={styles.newForm} onSubmit={submit} noValidate>
    <h2>Démarche et contact du citoyen</h2>
    <label className={styles.label} htmlFor="procedure">Démarche</label><select id="procedure" className={styles.input} disabled={busy || !procedures.length} value={procedure?.code ?? ""} onChange={(e) => { setCode(e.target.value); setReferences({}); setError(""); }}>{procedures.map((item) => <option key={item.code} value={item.code}>{item.title}</option>)}</select>
    {!procedure && <p className={styles.errorText}>Aucune démarche active. Contactez votre administrateur.</p>}
    <div className={styles.identityFields}><div><label className={styles.label} htmlFor="applicant-name">Nom du citoyen (facultatif)</label><input id="applicant-name" className={styles.input} value={name} maxLength={100} disabled={busy} onChange={(e) => setName(e.target.value)} /></div><div><label className={styles.label} htmlFor="citizen-phone">Téléphone pour l’accord</label><input id="citizen-phone" className={styles.input} type="tel" inputMode="numeric" value={phone} disabled={busy} onChange={(e) => setPhone(e.target.value.replace(/[^\d\s]/g, ""))} /><p className={styles.hint}>Ce numéro sert à joindre le citoyen. Il n’identifie pas ses documents.</p></div></div>
    <fieldset className={styles.formSection} disabled={busy}><legend className={styles.legend}>Où le citoyen donnera-t-il son accord ?</legend><label className={styles.radio}><input type="radio" name="channel" value="assisted" checked={channel === "assisted"} onChange={() => setChannel("assisted")} /><span>Sur place, avec un code reçu par SMS</span></label><label className={styles.radio}><input type="radio" name="channel" value="web" checked={channel === "web"} onChange={() => setChannel("web")} /><span>Depuis son espace citoyen</span></label></fieldset>
    <div className={styles.formSection}><h2>Références des documents demandés</h2><p className={styles.hint}>{channel === "assisted" ? "Demandez au citoyen les références ci-dessous avant d’envoyer la demande d’accord." : "Le citoyen pourra compléter ces références depuis son profil ou au moment de répondre."} Chaque référence est propre au registre concerné.</p><DocumentFields requirements={documents} values={references} onChange={setReferences} disabled={busy} /></div>
    {error && <p role="alert" className={styles.errorText}>{error}</p>}
    <div className={styles.formBottom}><p>Aucun registre n’est consulté avant l’accord du citoyen.</p><button className={styles.primary} disabled={busy || !procedure} type="submit">{busy ? "Ouverture…" : "Ouvrir le dossier"}</button></div>
  </form>;
}
