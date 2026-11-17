"use client";

import { useState } from "react";
import { LOCAL_QUESTIONS, requestExchangeRight, suspendExchangeRight, type LocalAdministration } from "@/lib/demo-administration";
import type { AdminActionRunner } from "@/features/administration/types/actions";
import styles from "@/features/administration/styles/dashboard.module.css";

const labels = { approved: "Convention validée · démo", requested: "Validation attendue", suspended: "Suspendu localement", not_requested: "Non demandé" };
export function RightsPanel({ config, run, busy }: { config: LocalAdministration; run: AdminActionRunner; busy: boolean }) {
  const [selected, setSelected] = useState("");
  const [purpose, setPurpose] = useState("");
  return <>
    <p className={styles.explanation}>Votre administration définit ses besoins. L’accès à un registre tiers nécessite une convention acceptée et validée par la gouvernance du réseau. Une demande ne vaut pas autorisation.</p>
    <div className={styles.tableScroll}><table className={styles.table}><caption className={styles.srOnly}>Droits d’échange avec les fournisseurs</caption><thead><tr><th>Information demandée</th><th>Fournisseur</th><th>État du droit</th><th>Action locale</th></tr></thead><tbody>{config.rights.map((right) => { const question = LOCAL_QUESTIONS.find((item) => item.code === right.questionCode)!; return <tr key={right.questionCode}><td><strong>{question.label}</strong><small>{question.service}</small></td><td>{question.provider}</td><td><span className={styles.tag}>{labels[right.status]}</span></td><td>{right.status === "approved" ? <button className={styles.textButton} type="button" disabled={busy} onClick={() => run("right", () => suspendExchangeRight(right.questionCode), "Ce droit est suspendu. Les nouvelles consultations correspondantes sont bloquées.")}>Suspendre localement</button> : right.status === "requested" ? <span className={styles.muted}>En attente de validation</span> : <button className={styles.textButton} type="button" disabled={busy} onClick={() => { setSelected(right.questionCode); setPurpose(""); }}>Demander l’accès</button>}</td></tr>; })}</tbody></table></div>
    {selected && <form className={styles.editor} onSubmit={async (e) => { e.preventDefault(); if (await run("right", () => requestExchangeRight(selected, purpose), "Demande enregistrée en attente de validation. Aucun accès supplémentaire n’est accordé.")) setSelected(""); }} noValidate><div className={styles.editorHeading}><h2>Demander un droit d’échange</h2><button className={styles.textButton} type="button" onClick={() => setSelected("")}>Fermer</button></div><p>{LOCAL_QUESTIONS.find((question) => question.code === selected)?.label}</p><label className={styles.formLabel}>Pourquoi cet accès est-il nécessaire ?<textarea className={styles.input} id="right-purpose" rows={3} value={purpose} disabled={busy} onChange={(e) => setPurpose(e.target.value)} /></label><button className={styles.primary} type="submit" disabled={busy}>Soumettre la demande</button></form>}
  </>;
}
