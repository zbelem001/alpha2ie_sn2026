// Journal de démonstration : métadonnées de vérification uniquement, sans données brutes.
export type DemoConsultation = {
  id: string; caseId: string; phone: string; dateTime: string; organization: string;
  information: string; purpose: string; source: string; basis: string; outcome: string;
};
const KEY = "dlnuf:demo:consultations:v1";
const EVENT = "dlnuf-demo-consultations";
export function consultationSnapshot() { return localStorage.getItem(KEY) ?? "[]"; }
export function parseConsultations(raw: string): DemoConsultation[] {
  try { const items = JSON.parse(raw); return Array.isArray(items) ? items.filter((item) => item && typeof item.id === "string" && typeof item.phone === "string" && typeof item.dateTime === "string") : []; }
  catch { return []; }
}
export function recordDemoConsultations(entries: DemoConsultation[]) {
  const existing = parseConsultations(consultationSnapshot());
  const ids = new Set(existing.map((item) => item.id));
  localStorage.setItem(KEY, JSON.stringify([...entries.filter((item) => !ids.has(item.id)), ...existing]));
  window.dispatchEvent(new Event(EVENT));
}
export function subscribeConsultations(callback: () => void) {
  const storage = (event: StorageEvent) => { if (event.key === KEY || event.key === null) callback(); };
  window.addEventListener("storage", storage); window.addEventListener(EVENT, callback);
  return () => { window.removeEventListener("storage", storage); window.removeEventListener(EVENT, callback); };
}
