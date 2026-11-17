"use client";

import { DOCUMENT_TYPES, documentForQuestion } from "@/lib/document-references";
import { useState, type FormEvent } from "react";
import { ArrowDown, ArrowUp, Plus } from "lucide-react";
import { LOCAL_QUESTIONS, saveLocalProcedure, toggleLocalProcedure, type LocalAdministration, type LocalProcedure } from "@/lib/demo-administration";
import type { AdminActionRunner } from "@/features/administration/types/actions";
import styles from "@/features/administration/styles/dashboard.module.css";

const blank = (): LocalProcedure => ({ code: "", title: "", purpose: "", version: 0, active: false, published: false, consentDays: 30, checks: [] });
export function ProceduresPanel({ config, run, busy }: { config: LocalAdministration; run: AdminActionRunner; busy: boolean }) {
  const [editor, setEditor] = useState<LocalProcedure | null>(null);
  const [original, setOriginal] = useState<string | null>(null);
  function edit(item?: LocalProcedure) { setOriginal(item?.code ?? null); setEditor(item ? structuredClone(item) : blank()); }
  function toggleQuestion(code: string) {
    if (!editor) return;
    const selected = editor.checks.some((check) => check.questionCode === code);
    setEditor({ ...editor, checks: selected ? editor.checks.filter((check) => check.questionCode !== code) : [...editor.checks, { questionCode: code, required: true, document: documentForQuestion(code) }] });
  }
  function move(index: number, direction: number) {
    if (!editor || index + direction < 0 || index + direction >= editor.checks.length) return;
    const checks = [...editor.checks]; [checks[index], checks[index + direction]] = [checks[index + direction], checks[index]]; setEditor({ ...editor, checks });
  }
  async function save(published: boolean) {
    if (!editor) return;
    const ok = await run("procedure", () => {
      if (!original && config.procedures.some((item) => item.code === editor.code)) throw new Error("Ce code de démarche existe déjà.");
      saveLocalProcedure({ ...editor, published, active: published });
    }, published ? "La démarche est publiée et disponible au guichet." : "Le brouillon est enregistré.");
    if (ok) setEditor(null);
  }
  const missingRights = editor?.checks.filter((check) => !config.rights.some((right) => right.questionCode === check.questionCode && right.status === "approved")) ?? [];
  return <>
    <div className={styles.sectionToolbar}><p>{config.procedures.length} démarche(s) dans votre catalogue</p><button className={styles.primary} type="button" disabled={busy} onClick={() => edit()}><Plus size={17} aria-hidden="true" /> Nouvelle démarche</button></div>
    <div className={styles.tableScroll}><table className={styles.table}><caption className={styles.srOnly}>Démarches de l’administration</caption><thead><tr><th>Nom et code</th><th>Version</th><th>Vérifications</th><th>État</th><th>Actions</th></tr></thead><tbody>{config.procedures.map((item) => <tr key={item.code}><td><strong>{item.title}</strong><small>{item.code}</small></td><td>v{item.version}</td><td>{item.checks.length}</td><td><span className={styles.tag}>{!item.published ? "Brouillon" : item.active ? "Publiée" : "Désactivée"}</span></td><td><div className={styles.actions}><button className={styles.textButton} disabled={busy} type="button" onClick={() => edit(item)}>Modifier</button>{item.published && <button className={styles.textButton} disabled={busy} type="button" onClick={() => run("procedure", () => toggleLocalProcedure(item.code), item.active ? "Démarche désactivée pour les nouveaux dossiers." : "Démarche réactivée.")}>{item.active ? "Désactiver" : "Activer"}</button>}</div></td></tr>)}</tbody></table></div>

    {editor && <form className={styles.editor} onSubmit={(e: FormEvent) => { e.preventDefault(); void save(false); }} noValidate>
      <div className={styles.editorHeading}><h2>{original ? "Modifier la démarche" : "Nouvelle démarche"}</h2><button className={styles.textButton} type="button" disabled={busy} onClick={() => setEditor(null)}>Fermer</button></div>
      <div className={styles.formGrid}><label>Nom de la démarche<input className={styles.input} id="procedure-title" value={editor.title} disabled={busy} onChange={(e) => setEditor({ ...editor, title: e.target.value })} /></label><label>Code métier<input className={styles.input} id="procedure-code" value={editor.code} readOnly={Boolean(original)} disabled={busy} placeholder="demarche_exemple" onChange={(e) => setEditor({ ...editor, code: e.target.value })} /></label></div>
      <label className={styles.formLabel}>Finalité des vérifications<textarea className={styles.input} id="procedure-purpose" value={editor.purpose} disabled={busy} rows={2} onChange={(e) => setEditor({ ...editor, purpose: e.target.value })} /></label>
      <fieldset className={styles.fieldset} disabled={busy}><legend>Vérifications à demander aux autres administrations</legend><p className={styles.hint}>Sélectionnez uniquement les informations nécessaires à cette démarche.</p><div className={styles.questionChoices}>{LOCAL_QUESTIONS.map((question) => <label key={question.code}><input type="checkbox" checked={editor.checks.some((check) => check.questionCode === question.code)} onChange={() => toggleQuestion(question.code)} /><span><strong>{question.label}</strong><small>{question.provider} · {config.rights.find((right) => right.questionCode === question.code)?.status === "approved" ? "Droit validé" : "Droit à obtenir"}</small></span></label>)}</div></fieldset>
      {editor.checks.length > 0 && <div className={styles.orderedChecks}><h3>Ordre et règles métier</h3><ol>{editor.checks.map((check, index) => <li key={check.questionCode}><span>{index + 1}. {LOCAL_QUESTIONS.find((question) => question.code === check.questionCode)?.label}</span><label><input type="checkbox" checked={check.required} disabled={busy} onChange={(e) => setEditor({ ...editor, checks: editor.checks.map((entry) => entry.questionCode === check.questionCode ? { ...entry, required: e.target.checked } : entry) })} />Obligatoire</label><div className={styles.documentConfig}><label>Document et référence de recherche<select className={styles.input} value={(check.document ?? documentForQuestion(check.questionCode)).key} disabled={busy} onChange={(e) => setEditor({ ...editor, checks: editor.checks.map((c) => c.questionCode === check.questionCode ? { ...c, document: { ...DOCUMENT_TYPES.find((d) => d.key === e.target.value)! } } : c) })}>{DOCUMENT_TYPES.filter((d) => d.provider === documentForQuestion(check.questionCode).provider).map((d) => <option value={d.key} key={d.key}>{d.label}</option>)}</select></label><label>Précision à afficher au citoyen<input className={styles.input} value={(check.document ?? documentForQuestion(check.questionCode)).hint} disabled={busy} onChange={(e) => setEditor({ ...editor, checks: editor.checks.map((c) => c.questionCode === check.questionCode ? { ...c, document: { ...(c.document ?? documentForQuestion(c.questionCode)), hint: e.target.value } } : c) })} /></label></div><div className={styles.actions}><button className={styles.iconButton} type="button" disabled={busy || index === 0} aria-label={"Monter la vérification " + (index + 1)} onClick={() => move(index, -1)}><ArrowUp size={16} /></button><button className={styles.iconButton} type="button" disabled={busy || index === editor.checks.length - 1} aria-label={"Descendre la vérification " + (index + 1)} onClick={() => move(index, 1)}><ArrowDown size={16} /></button></div></li>)}</ol><p className={styles.hint}>Tous les contrôles obligatoires doivent être confirmés. Un contrôle facultatif reste visible, mais ne décide pas seul du résultat.</p></div>}
      <label className={styles.formLabel}>Durée de l’accord en jours<input className={styles.input} style={{ maxWidth: 140 }} type="number" min={1} max={30} value={editor.consentDays} disabled={busy} onChange={(e) => setEditor({ ...editor, consentDays: Number(e.target.value) })} /></label>
      {missingRights.length > 0 && <p className={styles.warning}>Certains droits ne sont pas validés. Vous pouvez enregistrer le brouillon, puis demander ces droits dans « Droits d’échange ».</p>}
      <p className={styles.hint}>Une nouvelle version s’applique aux futurs dossiers. Les dossiers déjà ouverts conservent leurs vérifications et leur durée d’accord.</p>
      <div className={styles.formActions}><button className={styles.secondary} type="submit" disabled={busy}>Enregistrer le brouillon</button><button className={styles.primary} type="button" disabled={busy || missingRights.length > 0} onClick={() => save(true)}>Publier la démarche</button></div>
    </form>}
  </>;
}
