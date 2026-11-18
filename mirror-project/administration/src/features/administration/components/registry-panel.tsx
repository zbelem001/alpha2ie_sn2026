"use client";

import { Plus } from "lucide-react";
import { AdminDialog } from "./admin-dialog";
import { useState } from "react";
import { addOfferedService, toggleOfferedService, type LocalAdministration } from "@/lib/administration-api";
import type { AdminActionRunner } from "@/features/administration/types/actions";
import styles from "@/features/administration/styles/dashboard.module.css";

export function RegistryPanel({ config, run, busy, error }: { config: LocalAdministration; run: AdminActionRunner; busy: boolean; error?: string }) {
  const [serviceCode, setServiceCode] = useState(""); const [title, setTitle] = useState(""); const [description, setDescription] = useState("");
  const [open, setOpen] = useState(false);
  return <>
    <div className={styles.sectionToolbar}><p>{config.offeredServices.length} service(s)</p><button className={styles.primary} type="button" disabled={busy} onClick={() => setOpen(true)}><Plus size={17} /> Ajouter un service</button></div>
    <section className={styles.block}><h2>Services fournis par votre administration</h2><p className={styles.hint}>Déclarez ici les vérifications que votre registre permet aux autres administrations de demander. L’API correspondante doit déjà exister.</p>
      {config.offeredServices.length > 0 ? <div className={styles.tableScroll}><table className={styles.table}><caption className={styles.srOnly}>Services du registre local</caption><thead><tr><th>Service</th><th>Réponse</th><th>État</th><th>Action</th></tr></thead><tbody>{config.offeredServices.map((service) => <tr key={service.id}><td><strong>{service.title}</strong><small>{service.code}</small></td><td>Oui / non</td><td>{service.active ? "Actif" : "Désactivé"}</td><td><button className={styles.textButton} type="button" disabled={busy} onClick={() => run("service", () => toggleOfferedService(service.id), service.active ? "Service désactivé." : "Service réactivé.")}>{service.active ? "Désactiver" : "Activer"}</button></td></tr>)}</tbody></table></div> : <p className={styles.empty}>Aucun service local déclaré.</p>}
    </section>
    {open && <AdminDialog title="Ajouter un service" busy={busy} error={error} onClose={() => setOpen(false)}><form className={styles.editor} onSubmit={async (e) => { e.preventDefault(); if (await run("service", () => addOfferedService(serviceCode, title, description), "Le service est déclaré dans le catalogue de votre administration.")) { setServiceCode(""); setTitle(""); setDescription(""); setOpen(false); } }}><div className={styles.formGrid}><label>Nom du service<input className={styles.input} id="offered-title" required minLength={3} maxLength={200} value={title} disabled={busy} onChange={(e) => setTitle(e.target.value)} /></label><label>Code du service<input className={styles.input} id="offered-code" required minLength={3} maxLength={64} pattern="[a-z](?:[a-z0-9]|-){2,63}" title="Entre 3 et 64 lettres minuscules, chiffres ou tirets, en commençant par une lettre" aria-describedby="service-code-help" placeholder="statut-demande" value={serviceCode} disabled={busy} onChange={(e) => setServiceCode(e.target.value)} /></label></div><p id="service-code-help" className={styles.hint}>Code du service : utilisez des minuscules et des tirets, sans espace ni accent. Exemple : verification-majorite.</p><label className={styles.formLabel}>Description de la réponse minimale<textarea className={styles.input} id="offered-description" required minLength={5} maxLength={1000} value={description} disabled={busy} rows={2} onChange={(e) => setDescription(e.target.value)} /></label><label className={styles.formLabel}>Réponse du service<input className={styles.input} value="Oui / Non" readOnly /><small>Le service confirme uniquement si la condition est remplie.</small></label><button className={styles.primary} type="submit" disabled={busy}>Déclarer le service</button></form></AdminDialog>}
  </>;
}
