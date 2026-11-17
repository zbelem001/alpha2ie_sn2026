"use client";
import { useMemo, useSyncExternalStore } from "react";
import type { DocumentReferences } from "@/lib/document-references";
function subscribe(callback: () => void) {
  window.addEventListener("storage", callback); window.addEventListener("dlnuf-demo-documents", callback);
  return () => { window.removeEventListener("storage", callback); window.removeEventListener("dlnuf-demo-documents", callback); };
}
export function useDocumentProfile(phone?: string) {
  const raw = useSyncExternalStore(subscribe, () => phone ? localStorage.getItem("dlnuf:demo:documents:" + phone) ?? "{}" : "{}", () => "{}");
  return useMemo<DocumentReferences>(() => { try { return JSON.parse(raw); } catch { return {}; } }, [raw]);
}
