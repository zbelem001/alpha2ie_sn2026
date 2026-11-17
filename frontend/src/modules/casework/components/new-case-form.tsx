"use client";

import { useState, type FormEvent } from "react";
import { CheckCircle2, Search } from "lucide-react";
import { agentCaseService } from "@/modules/casework/services/agent-cases";
import { demoCitizens, passportProcedure } from "@/modules/casework/mocks/catalogue";
import type { ConsentChannel, DemoCitizen } from "@/modules/casework/types/cases";
import styles from "@/modules/casework/styles/workspace.module.css";
import { useDemoAdministration } from "@/lib/use-demo-administration";

export function NewCaseForm({ busy, onCreate }: { busy: boolean; onCreate: (citizenId: string, phone: string, procedure: string, channel: ConsentChannel) => Promise<void> }) {
  const [citizenId, setCitizenId] = useState("");
  const [phone, setPhone] = useState("");
  const [citizen, setCitizen] = useState<DemoCitizen | null>(null);
  const [searching, setSearching] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [channel, setChannel] = useState<ConsentChannel>("assisted");
  const configuration = useDemoAdministration();
  const procedures = configuration.procedures.filter((procedure) => procedure.active && procedure.published);
  const [procedureCode, setProcedureCode] = useState(passportProcedure.code);
  const selectedProcedure = procedures.find((procedure) => procedure.code === procedureCode) ?? procedures[0];
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy || searching) return;
    const next: Record<string, string> = {};
    const normalizedPhone = phone.replace(/\s/g, "");
    if (!citizenId.trim()) next.citizenId = "Saisissez l’identifiant unique du citoyen.";
    if (!/^\d{8}$/.test(normalizedPhone)) next.phone = "Entrez un numéro de téléphone à 8 chiffres.";
    setErrors(next);
    if (Object.keys(next).length) return;
    if (citizen) {
      if (!selectedProcedure) { setErrors({ procedure: "Aucune démarche active n’est disponible. Contactez votre administrateur." }); return; }
      await onCreate(citizen.uniqueId, normalizedPhone, selectedProcedure.code, channel); return;
    }
    setSearching(true);
    try {
      const found = await agentCaseService.identify(citizenId.trim());
      if (found.phone !== normalizedPhone) {
        setErrors({ phone: "Ce numéro ne correspond pas au contact du citoyen identifié. Vérifiez-le avec le citoyen." });
        return;
      }
      setCitizen(found);
    } catch (cause) { setErrors({ citizenId: cause instanceof Error ? cause.message : "Recherche impossible." }); }
    finally { setSearching(false); }
  }
  return <form className={styles.newForm} onSubmit={submit} noValidate>
    <div className={styles.sectionTitle}><span>01</span><h2>Identifier le citoyen</h2></div>
    <p className={styles.hint}>Saisissez l’identifiant unique du citoyen et son numéro de téléphone.</p>
    <div className={styles.identityFields}>
      <div>
        <label className={styles.label} htmlFor="citizen-id">Identifiant unique du citoyen</label>
        <input className={styles.input} id="citizen-id" name="citizen_id" placeholder="BF-00000001" value={citizenId} autoComplete="off" autoCapitalize="characters" disabled={busy || searching}
          aria-invalid={Boolean(errors.citizenId)} aria-describedby={errors.citizenId ? "identity-error" : undefined}
          onChange={(e) => { setCitizenId(e.target.value); setCitizen(null); setErrors({}); }} />
        {errors.citizenId && <p className={styles.errorText} id="identity-error" role="alert">{errors.citizenId}</p>}
      </div>
      <div>
        <label className={styles.label} htmlFor="citizen-phone">Numéro de téléphone</label>
        <input className={styles.input} id="citizen-phone" name="phone" type="tel" inputMode="numeric" autoComplete="tel-national" placeholder="00 00 00 00" value={phone} disabled={busy || searching}
          aria-invalid={Boolean(errors.phone)} aria-describedby={errors.phone ? "citizen-phone-error" : undefined}
          onChange={(e) => { setPhone(e.target.value.replace(/[^\d\s]/g, "")); setCitizen(null); setErrors({}); }} />
        {errors.phone && <p className={styles.errorText} id="citizen-phone-error" role="alert">{errors.phone}</p>}
      </div>
    </div>
    {!citizen && <button className={styles.secondary + " " + styles.identitySearch} type="submit" disabled={busy || searching}><Search size={17} aria-hidden="true" />{searching ? "Recherche…" : "Rechercher le citoyen"}</button>}
    {citizen && <div className={styles.identified} role="status"><CheckCircle2 size={19} aria-hidden="true" /><div><strong>{citizen.displayName}</strong><span>Identifiant {citizen.uniqueId} · Le numéro saisi correspond au contact de ce profil.</span></div></div>}

    {citizen && <>
      <div className={styles.formSection}>
        <div className={styles.sectionTitle}><span>02</span><h2>Choisir la démarche</h2></div>
        <label className={styles.label} htmlFor="procedure">Démarche de votre administration</label>
        <select className={styles.input} id="procedure" name="procedure_code" value={selectedProcedure?.code ?? ""} disabled={busy || procedures.length === 0} onChange={(e) => { setProcedureCode(e.target.value); setErrors({}); }}>{procedures.length ? procedures.map((procedure) => <option key={procedure.code} value={procedure.code}>{procedure.title}</option>) : <option value="">Aucune démarche active</option>}</select>
        {errors.procedure && <p className={styles.errorText} role="alert">{errors.procedure}</p>}
        <p className={styles.hint}>Seules les démarches de votre administration sont proposées.</p>
      </div>
      <fieldset className={styles.formSection} disabled={busy}>
        <legend className={styles.legend}>03 · Comment le citoyen donnera-t-il son accord ?</legend>
        <label className={styles.radio}><input type="radio" name="channel" value="assisted" checked={channel === "assisted"} onChange={() => setChannel("assisted")} /><span><strong>Sur place, au guichet</strong><span>Le citoyen communique le code d’accord reçu sur son téléphone.</span></span></label>
        <label className={styles.radio}><input type="radio" name="channel" value="web" checked={channel === "web"} onChange={() => setChannel("web")} /><span><strong>À distance</strong><span>Le citoyen accepte ou refuse depuis son espace personnel.</span></span></label>
      </fieldset>
      <div className={styles.formBottom}><p>Ouvrir le dossier prépare les vérifications. Aucun registre n’est encore consulté.</p><button className={styles.primary} type="submit" disabled={busy || !selectedProcedure}>{busy ? "Ouverture…" : "Ouvrir le dossier"}</button></div>
    </>}
    <details className={styles.demoTools}><summary>Identifiants de démonstration</summary><ul>{demoCitizens.map((item) => <li key={item.uniqueId}><button type="button" disabled={busy || searching} onClick={() => { setCitizenId(item.uniqueId); setPhone(item.phone); setCitizen(null); setErrors({}); }}>{item.uniqueId} · {item.phone.match(/.{1,2}/g)?.join(" ")}</button><span>{item.scenario === "normal" ? "Parcours standard" : item.scenario === "unavailable" ? "Justice indisponible au premier essai" : "Identité à examiner"}</span></li>)}</ul></details>
  </form>;
}
