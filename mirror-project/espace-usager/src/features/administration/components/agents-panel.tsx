"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { createLocalAgent, resetLocalAgentPin, toggleLocalAgent, type LocalAdministration } from "@/lib/demo-administration";
import type { AdminActionRunner } from "@/features/administration/types/actions";
import styles from "@/features/administration/styles/dashboard.module.css";

export function AgentsPanel({ config, run, busy }: { config: LocalAdministration; run: AdminActionRunner; busy: boolean }) {
  const [editing, setEditing] = useState<string | null>(null);
  const [name, setName] = useState(""); const [phone, setPhone] = useState("");
  const [pin, setPin] = useState(""); const [confirmation, setConfirmation] = useState("");
  function open(id = "new") { setEditing(id); setName(""); setPhone(""); setPin(""); setConfirmation(""); }
  async function save() {
    if (!editing) return;
    const ok = await run("agent", async () => {
      if (!confirmation || confirmation !== pin) throw new Error("Les deux codes PIN doivent être identiques.");
      if (editing === "new") await createLocalAgent(name, phone, pin); else await resetLocalAgentPin(editing, pin);
    }, editing === "new" ? "Le compte agent est créé. Il peut se connecter depuis l’entrée habituelle." : "Le PIN de l’agent est réinitialisé.");
    if (ok) { setEditing(null); setPin(""); setConfirmation(""); }
  }
  return <>
    <div className={styles.sectionToolbar}><p>{config.agents.filter((agent) => agent.active).length} agent(s) actif(s)</p><button className={styles.primary} type="button" disabled={busy} onClick={() => open()}><Plus size={17} aria-hidden="true" /> Ajouter un agent</button></div>
    <div className={styles.tableScroll}><table className={styles.table}><caption className={styles.srOnly}>Comptes des agents de l’administration</caption><thead><tr><th>Agent</th><th>Téléphone de connexion</th><th>État</th><th>Actions</th></tr></thead><tbody>{config.agents.map((agent) => <tr key={agent.id}><td><strong>{agent.name}</strong><small>Rôle agent · administration locale</small></td><td>{agent.phone.match(/.{1,2}/g)?.join(" ")}</td><td><span className={styles.tag}>{agent.active ? "Actif" : "Suspendu"}</span></td><td><div className={styles.actions}><button className={styles.textButton} type="button" disabled={busy} aria-label={(agent.active ? "Suspendre " : "Réactiver ") + agent.name} onClick={() => run("agent", () => toggleLocalAgent(agent.id), agent.active ? "Le compte est suspendu. La connexion est refusée." : "Le compte est réactivé.")}>{agent.active ? "Suspendre" : "Réactiver"}</button><button className={styles.textButton} type="button" disabled={busy} aria-label={"Réinitialiser le PIN de " + agent.name} onClick={() => open(agent.id)}>Réinitialiser le PIN</button></div></td></tr>)}</tbody></table></div>
    {editing && <form className={styles.editor} onSubmit={(e) => { e.preventDefault(); void save(); }} noValidate><div className={styles.editorHeading}><h2>{editing === "new" ? "Ajouter un agent" : "Réinitialiser le PIN"}</h2><button className={styles.textButton} type="button" disabled={busy} onClick={() => setEditing(null)}>Fermer</button></div>{editing === "new" && <div className={styles.formGrid}><label>Nom de l’agent<input className={styles.input} id="agent-name" value={name} disabled={busy} autoComplete="off" onChange={(e) => setName(e.target.value)} /></label><label>Téléphone de connexion<input className={styles.input} id="agent-phone" type="tel" inputMode="numeric" placeholder="00 00 00 00" value={phone} disabled={busy} autoComplete="off" onChange={(e) => setPhone(e.target.value.replace(/[^\d\s]/g, ""))} /></label></div>}<div className={styles.formGrid}><label>Code PIN<input className={styles.input} id="agent-pin" type="password" inputMode="numeric" maxLength={6} autoComplete="new-password" value={pin} disabled={busy} onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} /></label><label>Confirmer le PIN<input className={styles.input} id="agent-confirm" type="password" inputMode="numeric" maxLength={6} autoComplete="new-password" value={confirmation} disabled={busy} onChange={(e) => setConfirmation(e.target.value.replace(/\D/g, ""))} /></label></div><p className={styles.hint}>Les codes PIN ne sont ni affichés dans la liste ni enregistrés dans le journal des actions.</p><button className={styles.primary} type="submit" disabled={busy}>{editing === "new" ? "Créer le compte agent" : "Enregistrer le nouveau PIN"}</button></form>}
  </>;
}
