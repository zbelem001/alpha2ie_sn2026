"use client";

import { useState } from "react";
import type { AdminAuditEntry } from "@/lib/demo-administration";
import styles from "@/features/administration/styles/dashboard.module.css";

export function AuditPanel({ entries, compact = false }: { entries: AdminAuditEntry[]; compact?: boolean }) {
  const [query, setQuery] = useState(""); const [role, setRole] = useState("all");
  const visible = entries.filter((entry) => (role === "all" || entry.role === role) && [entry.actor, entry.action, entry.target, entry.detail].join(" ").toLowerCase().includes(query.toLowerCase()));
  const shown = compact ? visible.slice(0, 6) : visible;
  return <section>
    {!compact && <div className={styles.filters}><input className={styles.input} aria-label="Rechercher une action" placeholder="Action, acteur ou dossier" value={query} onChange={(e) => setQuery(e.target.value)} /><select className={styles.input} aria-label="Filtrer le journal par acteur" value={role} onChange={(e) => setRole(e.target.value)}><option value="all">Tous les acteurs</option><option value="local-admin">Administrateur local</option><option value="agent">Agents</option><option value="citizen">Citoyens</option></select></div>}
    <p className={styles.hint}>{compact ? "Dernières actions enregistrées" : visible.length + " action(s) enregistrée(s)"}</p>
    <div className={styles.tableScroll}><table className={styles.table}><caption className={styles.srOnly}>Historique des actions dans l’administration</caption><thead><tr><th>Date et heure</th><th>Acteur</th><th>Action</th><th>Cible</th>{!compact && <th>Détails</th>}</tr></thead><tbody>{shown.length === 0 ? <tr><td colSpan={compact ? 4 : 5} className={styles.empty}>Aucune action à afficher.</td></tr> : shown.map((entry) => <tr key={entry.id}><td className={styles.dateCell}>{new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short", timeZone: "Africa/Ouagadougou" }).format(new Date(entry.at))}</td><td><strong>{entry.actor}</strong><small>{entry.role === "local-admin" ? "Administrateur local" : entry.role === "citizen" ? "Citoyen" : "Agent"}</small></td><td>{entry.action}</td><td className={styles.auditTarget}>{entry.target}</td>{!compact && <td>{entry.detail || "—"}</td>}</tr>)}</tbody></table></div>
    {!compact && <p className={styles.footnote}>Journal local de démonstration. Le journal réel devra être produit et protégé côté serveur ; les codes SMS et les PIN n’y figurent jamais.</p>}
  </section>;
}
