"use client";

import type { AgentCase } from "@/modules/casework/types/cases";
import { useBrowserClock } from "@/lib/use-browser-clock";
import type { DemoAuthorization } from "@/lib/demo-authorizations";
import styles from "@/modules/casework/styles/workspace.module.css";

export function caseLabel(item: AgentCase, authorization?: DemoAuthorization, now = 0) {
  if (authorization?.status === "refused") return "Accord refusé";
  if (item.status === "completed") return "Vérifications terminées";
  if (item.checks.some((check) => check.status === "unavailable")) return "Registre indisponible";
  if (item.checks.some((check) => ["ambiguous", "not_found", "rejected", "blocked", "error"].includes(check.status))) return "À examiner";
  if (authorization?.status === "granted") return authorization.expiresAt && new Date(authorization.expiresAt).getTime() > now ? "Prêt à vérifier" : "Accord expiré";
  return "En attente du citoyen";
}
export function CaseStatusBadge({ item, authorization }: { item: AgentCase; authorization?: DemoAuthorization }) {
  const now = useBrowserClock();
  const label = caseLabel(item, authorization, now);
  return <span className={`${styles.status} ${item.status === "completed" ? styles.success : authorization?.status === "refused" ? styles.danger : styles.waiting}`}>{label}</span>;
}
