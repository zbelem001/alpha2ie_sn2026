"use client";

import { useMemo, useSyncExternalStore } from "react";
import { getAuthorizationSnapshot, getDemoCitizenPhone, parseAuthorizations, subscribeAuthorizations } from "@/lib/demo-authorizations";

export function useDemoAuthorizations() {
  const raw = useSyncExternalStore(subscribeAuthorizations, getAuthorizationSnapshot, () => "[]");
  return useMemo(() => parseAuthorizations(raw), [raw]);
}

export function useDemoCitizenPhone() {
  return useSyncExternalStore(subscribeAuthorizations, getDemoCitizenPhone, () => "11111111");
}
