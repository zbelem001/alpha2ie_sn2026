"use client";

import { AdminDialog } from "./admin-dialog";
import { DOCUMENT_TYPES, documentForQuestion } from "@/lib/document-references";
import { useState, type FormEvent } from "react";
import { Plus } from "lucide-react";
import { LOCAL_QUESTIONS, saveLocalProcedure, toggleLocalProcedure, type LocalAdministration, type LocalProcedure } from "@/lib/administration-api";
import type { AdminActionRunner } from "@/features/administration/types/actions";
import styles from "@/features/administration/styles/dashboard.module.css";

const blank = (): LocalProcedure => ({ code: "", title: "", purpose: "", version: 0, active: false, published: false, consentDays: 30, checks: [] });
function serviceName(code: string) {
  const question = LOCAL_QUESTIONS.find((item) => item.code === code);
  const names: Record<string, string> = { "is-adult": "Majorité", "identity": "Acte de naissance", "nationality": "Nationalité burkinabè", "cnib-status": "Validité de la CNIB", "criminal-record": "Vérification du casier judiciaire", "criminal-record-current": "Validité du casier judiciaire", "payment-status": "Paiement confirmé" };
  return names[question?.service ?? ""] ?? question?.label ?? code;
}
function serviceDocument(code: string) {
  const service = LOCAL_QUESTIONS.find((item) => item.code === code)?.service;
  const types: Record<string, string> = { "is-adult": "birth", "identity": "birth", "nationality": "nationality", "cnib-status": "cnib", "criminal-record": "criminal", "criminal-record-current": "criminal", "payment-status": "payment" };
  return { ...(DOCUMENT_TYPES.find((item) => item.key === types[service ?? ""]) ?? documentForQuestion(code)) };
}
export function ProceduresPanel({ config, run, busy, error }: { config: LocalAdministration; run: AdminActionRunner; busy: boolean; error?: string }) {
  const [editor, setEditor] = useState<LocalProcedure | null>(null);
  const [original, setOriginal] = useState<string | null>(null);
  const [checksError, setChecksError] = useState("");
  function edit(item?: LocalProcedure) {
    setOriginal(item?.code ?? null);
    if (!item) setEditor(blank());
    else {
      const copy = structuredClone(item);
      const indexes = new Map<string, number>();
      copy.checks = [];
      for (const check of item.checks) {
        const question = LOCAL_QUESTIONS.find((entry) => entry.questionCodes.includes(check.questionCode));
        if (!question) continue;
        const key = `${question.providerCode}:${question.service}`;
        const index = indexes.get(key);
        if (index === undefined) {
          indexes.set(key, copy.checks.length);
          copy.checks.push({ ...check, questionCode: question.code });
        } else if (check.required) copy.checks[index] = { ...copy.checks[index], required: true };
      }
      setEditor(copy);
    }
    setChecksError("");
  }
  function toggleQuestion(code: string) {
    if (!editor) return;
    const question = LOCAL_QUESTIONS.find((item) => item.code === code);
    if (!question) return;
    const selected = editor.checks.some((check) => question.questionCodes.includes(check.questionCode));
    if (!question.active && !selected) return;
    setChecksError("");
    setEditor({ ...editor, checks: selected ? editor.checks.filter((check) => !question.questionCodes.includes(check.questionCode)) : [...editor.checks, { questionCode: code, required: true, document: serviceDocument(code) }] });
  }
  async function save(published: boolean) {
    if (!editor) return;
    const hasQuestionCode = editor.checks.some((check) => typeof check.questionCode === "string" && check.questionCode.trim().length >= 2);
    if (!hasQuestionCode) {
      setChecksError("Le champ questionCode est obligatoire : sélectionnez au moins une vérification dans la liste.");
      return;
    }
    setChecksError("");
    const ok = await run("procedure", () => {
      if (!original && config.procedures.some((item) => item.code === editor.code)) throw new Error("Ce code de démarche existe déjà.");
      return saveLocalProcedure({ ...editor, published, active: published });
    }, published ? "La démarche est publiée et disponible au guichet." : "Le brouillon est enregistré.");
    if (ok) setEditor(null);
  }
  return <>
    <p className={styles.hint}>Catalogue de {config.administration.name}. Les démarches des autres administrations restent dans leur propre espace.</p>
    <div className={styles.sectionToolbar}><p>{config.procedures.length} démarche(s) dans votre catalogue</p><button className={styles.primary} type="button" disabled={busy} onClick={() => edit()}><Plus size={17} aria-hidden="true" /> Ajouter une démarche</button></div>
    <div className={styles.tableScroll}><table className={styles.table}><caption className={styles.srOnly}>Démarches de l’administration</caption><thead><tr><th>Nom et code</th><th>Version</th><th>Vérifications</th><th>État</th><th>Actions</th></tr></thead><tbody>{config.procedures.map((item) => <tr key={item.code}><td><strong>{item.title}</strong><small>{item.code}</small></td><td>v{item.version}</td><td>{item.checks.length}</td><td><span className={styles.tag}>{!item.published ? "Brouillon" : item.active ? "Publiée" : "Désactivée"}</span></td><td><div className={styles.actions}><button className={styles.textButton} disabled={busy} type="button" onClick={() => edit(item)}>Modifier</button>{item.published && <button className={styles.textButton} disabled={busy} type="button" onClick={() => run("procedure", () => toggleLocalProcedure(item.code), item.active ? "Démarche désactivée pour les nouveaux dossiers." : "Démarche réactivée.")}>{item.active ? "Désactiver" : "Activer"}</button>}</div></td></tr>)}</tbody></table></div>

    {editor && <AdminDialog title={original ? "Modifier la démarche" : "Ajouter une démarche"} busy={busy} error={error} onClose={() => setEditor(null)}><form className={styles.editor} onSubmit={(e: FormEvent) => { e.preventDefault(); void save(false); }} noValidate>

      <div className={styles.formGrid}><label>Nom de la démarche<input className={styles.input} id="procedure-title" value={editor.title} disabled={busy} onChange={(e) => setEditor({ ...editor, title: e.target.value })} /></label><label>Code métier<input className={styles.input} id="procedure-code" value={editor.code} readOnly={Boolean(original)} disabled={busy} placeholder="demarche_exemple" onChange={(e) => setEditor({ ...editor, code: e.target.value })} /></label></div>
      <label className={styles.formLabel}>Finalité des vérifications<textarea className={styles.input} id="procedure-purpose" value={editor.purpose} disabled={busy} rows={2} onChange={(e) => setEditor({ ...editor, purpose: e.target.value })} /></label>
      <details className={styles.serviceDropdown} open={Boolean(checksError)}><summary>Vérifications obligatoires <span>{editor.checks.length} sélectionnée(s)</span></summary><fieldset className={styles.fieldset} disabled={busy} aria-describedby="question-code-help"><legend className={styles.srOnly}>Choisir les vérifications obligatoires</legend><p className={styles.hint} id="question-code-help">Choisissez les services disponibles pour cette démarche. Les services inactifs restent visibles pour signaler leur état, mais ne peuvent pas être sélectionnés. La publication configure automatiquement les accès X-Road des vérifications retenues.</p><div className={styles.questionChoices}>{LOCAL_QUESTIONS.map((question) => {
        const selected = editor.checks.some((check) => question.questionCodes.includes(check.questionCode));
        const accessLabel = question.status === "approved" ? "Accès X-Road autorisé" : question.status === "requested" ? "Accès en attente" : "Accès configuré à la publication";
        return <label key={`${question.providerCode}:${question.service}`}><input type="checkbox" checked={selected} disabled={!question.active && !selected} onChange={() => toggleQuestion(question.code)} /><span><strong title={question.label}>{serviceName(question.code)}</strong><small>{question.provider} · <b className={question.active ? styles.activeService : styles.inactiveService}>{question.active ? "Actif" : "Inactif"}</b> · {accessLabel}</small></span></label>;
      })}</div>{checksError && <p className={styles.error} role="alert">{checksError}</p>}</fieldset></details>
      <details className={styles.serviceDropdown}>
        <summary>Options avancées</summary>
        <div className={styles.advancedOptions}>
          <label className={styles.formLabel}>Durée de l’accord en jours<input className={styles.input} style={{ maxWidth: 140 }} type="number" min={1} max={30} value={editor.consentDays} disabled={busy} onChange={(event) => setEditor({ ...editor, consentDays: Number(event.target.value) })} /></label>
          <p className={styles.hint}>Les contrôles obligatoires doivent être confirmés. Une démarche déjà utilisée est verrouillée.</p>
        </div>
      </details>
      <div className={styles.formActions}><button className={styles.secondary} type="submit" disabled={busy}>Enregistrer le brouillon</button><button className={styles.primary} type="button" disabled={busy} onClick={() => save(true)}>Publier la démarche</button></div>
    </form></AdminDialog>}
  </>;
}
