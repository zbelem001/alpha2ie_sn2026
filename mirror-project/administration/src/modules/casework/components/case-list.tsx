"use client";

import { useState } from "react";
import { Eye, ListChecks, MessageSquare, Search } from "lucide-react";
import type { AgentCase } from "@/modules/casework/types/cases";
import { formatPhone } from "@/lib/journal";
import { CaseStatusBadge, caseLabel } from "@/modules/casework/components/case-status";
import { useBrowserClock } from "@/lib/use-browser-clock";
import styles from "@/modules/casework/styles/workspace.module.css";

export function CaseList({ cases, loading, onOpen }: {
  cases: AgentCase[]; loading: boolean;
  onOpen: (id: string, section?: "consent" | "checks") => void;
}) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const now = useBrowserClock();
  const visible = cases.filter((item) => {
    const label = caseLabel(item, now);
    const searchable = [item.reference, item.applicantName, item.phone].join(" ").toLowerCase();
    const normalizedQuery = query.trim().toLowerCase();
    return (searchable.includes(normalizedQuery) || item.phone.includes(normalizedQuery.replace(/\s/g, ""))) &&
      (filter === "all" || filter === "waiting" && label === "En attente du citoyen" ||
        filter === "ready" && label === "Prêt à vérifier" ||
        filter === "pending" && (["Registre indisponible", "À examiner", "Accord expiré", "Accord refusé", "Accord retiré"].includes(label) || item.reports.length > 0) ||
        filter === "completed" && item.status === "completed");
  });
  return <section aria-label="Toutes les demandes">
    <div className={styles.listToolbar}>
      <div className={styles.search}><Search size={17} aria-hidden="true" /><input aria-label="Rechercher une demande" placeholder="Dossier, nom ou téléphone" value={query} onChange={(e) => setQuery(e.target.value)} /></div>
      <select className={styles.filter} aria-label="Filtrer les demandes" value={filter} onChange={(e) => setFilter(e.target.value)}>
        <option value="all">Toutes les demandes</option><option value="waiting">En attente du citoyen</option><option value="ready">Prêtes à vérifier</option><option value="pending">À reprendre ou examiner</option><option value="completed">Vérifications terminées</option>
      </select>
    </div>
    <p className={styles.listCount} aria-live="polite">{loading ? "Chargement des demandes…" : visible.length + " demande" + (visible.length === 1 ? "" : "s")}</p>
    <div className={styles.tableScroll} role="region" aria-label="Tableau des demandes, défilement horizontal disponible" tabIndex={0}>
      <table className={styles.requestsTable}>
        <caption className={styles.srOnly}>Demandes de l’administration</caption>
        <thead><tr><th scope="col">Dossier</th><th scope="col">Citoyen</th><th scope="col">Téléphone</th><th scope="col">Démarche</th><th scope="col">Accord</th><th scope="col">État</th><th scope="col">Créé le</th><th scope="col" className={styles.actionsHeading}>Actions</th></tr></thead>
        <tbody>
          {loading ? <tr><td colSpan={8} className={styles.tableEmpty}>Chargement…</td></tr> : visible.length === 0 ? <tr><td colSpan={8} className={styles.tableEmpty}><strong>{cases.length === 0 ? "Aucune demande enregistrée" : "Aucune demande correspondante"}</strong><p>{cases.length === 0 ? "Ouvrez le dossier d’un citoyen pour commencer." : "Modifiez votre recherche ou le filtre."}</p></td></tr> :
            visible.map((item) => {
              const label = caseLabel(item, now);
              const needsConsent = label === "En attente du citoyen" || label === "Accord expiré" || label === "Accord retiré";
              const hasShortcut = item.status !== "completed" && item.consent.status !== "refused";
              return <tr key={item.id} className={styles.requestRow}>
                <td><button type="button" className={styles.tableReference} onClick={() => onOpen(item.id)} aria-label={"Ouvrir le dossier " + item.reference}>{item.reference}</button></td>
                <td className={styles.applicantName}>{item.applicantName}</td>
                <td className={styles.phoneCell}>{formatPhone(item.phone)}</td>
                <td><span className={styles.tableProcedure} title={item.procedureTitle}>{item.procedureTitle}</span></td>
                <td><span className={styles.channelTag}>{item.channel === "assisted" ? "Au guichet" : "À distance"}</span></td>
                <td><div className={styles.statusStack}><CaseStatusBadge item={item} />{item.reports.length > 0 && <span className={`${styles.status} ${styles.danger}`}>Signalement</span>}</div></td>
                <td><time className={styles.tableDate} dateTime={item.createdAt}>{new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "2-digit", year: "2-digit", timeZone: "Africa/Ouagadougou" }).format(new Date(item.createdAt))}<span>{new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit", timeZone: "Africa/Ouagadougou" }).format(new Date(item.createdAt))}</span></time></td>
                <td className={styles.actionsCell}><div className={styles.rowActions}>
                  <button type="button" className={styles.iconAction} title="Voir le détail" aria-label={"Voir le détail du dossier " + item.reference} onClick={() => onOpen(item.id)}><Eye size={18} aria-hidden="true" /></button>
                  {hasShortcut && <button type="button" className={styles.iconAction} title={needsConsent ? "Recueillir l’accord" : "Accéder aux vérifications"} aria-label={(needsConsent ? "Recueillir l’accord pour " : "Accéder aux vérifications de ") + item.reference} onClick={() => onOpen(item.id, needsConsent ? "consent" : "checks")}>{needsConsent ? <MessageSquare size={17} aria-hidden="true" /> : <ListChecks size={18} aria-hidden="true" />}</button>}
                </div></td>
              </tr>;
            })}
        </tbody>
      </table>
    </div>
    <p className={styles.tableHint}>Faites défiler le tableau pour voir toutes les colonnes.</p>
  </section>;
}
