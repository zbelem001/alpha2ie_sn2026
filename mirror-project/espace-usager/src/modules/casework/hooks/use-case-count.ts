"use client";

import { useSyncExternalStore } from "react";

const KEY = "dlnuf:demo:agent-cases:v1";
function snapshot() { try { const items = JSON.parse(localStorage.getItem(KEY) ?? "[]"); return Array.isArray(items) ? items.length : 0; } catch { return 0; } }
function subscribe(callback: () => void) {
  const storage = (event: StorageEvent) => { if (event.key === KEY || event.key === null) callback(); };
  window.addEventListener("storage", storage); window.addEventListener("dlnuf-demo-cases", callback);
  return () => { window.removeEventListener("storage", storage); window.removeEventListener("dlnuf-demo-cases", callback); };
}
export function useCaseCount() { return useSyncExternalStore(subscribe, snapshot, () => 0); }
