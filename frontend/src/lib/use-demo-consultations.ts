"use client";

import { useMemo, useSyncExternalStore } from "react";
import { consultationSnapshot, parseConsultations, subscribeConsultations } from "@/lib/demo-consultations";

export function useDemoConsultations() {
  const raw = useSyncExternalStore(subscribeConsultations, consultationSnapshot, () => "[]");
  return useMemo(() => parseConsultations(raw), [raw]);
}
