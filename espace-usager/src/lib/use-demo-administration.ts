"use client";

import { useMemo, useSyncExternalStore } from "react";
import { administrationSnapshot, administrationServerSnapshot, auditSnapshot, parseAdministration, parseAudit, subscribeAdministration } from "@/lib/demo-administration";

export function useDemoAdministration() {
  const raw = useSyncExternalStore(subscribeAdministration, administrationSnapshot, administrationServerSnapshot);
  return useMemo(() => parseAdministration(raw), [raw]);
}
export function useAdministrationAudit() {
  const raw = useSyncExternalStore(subscribeAdministration, auditSnapshot, () => "[]");
  return useMemo(() => parseAudit(raw), [raw]);
}
