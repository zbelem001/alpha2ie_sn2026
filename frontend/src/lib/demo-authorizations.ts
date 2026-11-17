// Contrat d'échange local commun aux deux espaces, sans dépendance vers leur UI.
// Simulation uniquement : le backend doit vérifier l'identité, la preuve et les droits.
import { appendAdminAudit } from "@/lib/demo-administration";
export type DemoAuthorization = {
  id: string;
  caseId: string;
  subjectRef: string;
  phone: string;
  organization: string;
  purpose: string;
  checks: string[];
  duration: string;
  validityDays?: number;
  channel: "assisted" | "web";
  status: "pending" | "granted" | "refused";
  requestedAt: string;
  decidedAt?: string;
  expiresAt?: string;
};

const KEY = "dlnuf:demo:authorizations:v1";
const EVENT = "dlnuf-demo-authorizations";
export const DEMO_CITIZEN_PHONE_KEY = "dlnuf:demo:active-citizen";

export function setDemoCitizenPhone(phone: string) {
  sessionStorage.setItem(DEMO_CITIZEN_PHONE_KEY, phone);
  window.dispatchEvent(new Event(EVENT));
}
export function getDemoCitizenPhone() { return sessionStorage.getItem(DEMO_CITIZEN_PHONE_KEY) ?? "11111111"; }

export function getAuthorizationSnapshot() { return localStorage.getItem(KEY) ?? "[]"; }
export function parseAuthorizations(raw: string): DemoAuthorization[] {
  try {
    const value = JSON.parse(raw);
    return Array.isArray(value) ? value.filter((item) => item && typeof item.id === "string" && typeof item.caseId === "string" && typeof item.phone === "string" && Array.isArray(item.checks) && ["pending", "granted", "refused"].includes(item.status)) : [];
  } catch { return []; }
}
export function readAuthorizations() { return parseAuthorizations(getAuthorizationSnapshot()); }
export function putAuthorization(item: DemoAuthorization) {
  const items = readAuthorizations();
  localStorage.setItem(KEY, JSON.stringify([...items.filter((old) => old.id !== item.id), item]));
  window.dispatchEvent(new Event(EVENT));
}
export function answerAuthorization(id: string, decision: "granted" | "refused", phone: string, channel: "web" | "assisted" = "web") {
  const item = readAuthorizations().find((entry) => entry.id === id);
  if (!item || item.phone !== phone || item.status !== "pending") throw new Error("Cette demande n’est plus disponible.");
  const now = Date.now();
  const days = Math.min(30, Math.max(1, item.validityDays ?? 30));
  putAuthorization({ ...item, channel, status: decision, decidedAt: new Date(now).toISOString(), expiresAt: decision === "granted" ? new Date(now + days * 86400_000).toISOString() : undefined });
  appendAdminAudit(decision === "granted" ? "Accord citoyen donné" : "Accord citoyen refusé", item.caseId, channel === "assisted" ? "Recueil assisté au guichet" : "Réponse sur le portail citoyen", { name: "Citoyen concerné", role: "citizen" });
}
export function subscribeAuthorizations(callback: () => void) {
  const onStorage = (event: StorageEvent) => { if (event.key === KEY || event.key === null) callback(); };
  window.addEventListener("storage", onStorage);
  window.addEventListener(EVENT, callback);
  return () => { window.removeEventListener("storage", onStorage); window.removeEventListener(EVENT, callback); };
}
