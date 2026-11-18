"use client";

import type { AgentCase } from "@/modules/casework/types/cases";
import { useBrowserClock } from "@/lib/use-browser-clock";
import { consentIsActive } from "@/lib/journal";
import styles from "@/modules/casework/styles/workspace.module.css";

export function caseLabel(item: AgentCase, now = 0) {
  if (item.consent.status === "refused") return "Accord refusé";
  if (item.status === "completed") return "Vérifications terminées";
  if (item.checks.some((check) => check.status === "unavailable")) return "Registre indisponible";
  if (item.checks.some((check) => ["ambiguous", "not_found", "rejected", "blocked", "error"].includes(check.status))) return "À examiner";
  if (item.consent.status === "revoked") return "Accord retiré";
  if (item.consent.status === "granted") return consentIsActive(item.consent, now || Date.now()) ? "Prêt à vérifier" : "Accord expiré";
  return "En attente du citoyen";
}
export function CaseStatusBadge({ item }: { item: AgentCase }) {
  const now = useBrowserClock();
  const label = caseLabel(item, now);
  return <span className={`${styles.status} ${item.status === "completed" ? styles.success : ["refused", "revoked"].includes(item.consent.status) ? styles.danger : styles.waiting}`}>{label}</span>;
}
