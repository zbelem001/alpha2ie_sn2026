import { hashDemoPin, type DemoPin } from "@/lib/demo-pin";

export const LOCAL_ORGANIZATION = { code: "BF/GOV/DIPF/PASSEPORTS", name: "Direction de l’Immigration et de la Police des Frontières", service: "Guichet passeports" };
export const LOCAL_QUESTIONS = [
  { code: "passport_cnib_valid", label: "CNIB enregistrée et valide", provider: "ONI", service: "cnib-status" },
  { code: "passport_birth_act_found", label: "Acte d’état civil retrouvé", provider: "État civil", service: "identity" },
  { code: "passport_nationality", label: "Nationalité burkinabè confirmée", provider: "Justice", service: "nationality" },
  { code: "passport_criminal_record_current", label: "Bulletin de casier en cours de validité", provider: "Justice", service: "criminal-record-current" },
  { code: "passport_fiscal_stamp_paid", label: "Timbre fiscal payé", provider: "Trésor", service: "payment-status" },
  { code: "loss_declared", label: "Perte du document déclarée", provider: "Police", service: "loss-declaration" },
];
export type LocalProcedure = { code: string; title: string; purpose: string; version: number; active: boolean; published: boolean; consentDays: number; checks: { questionCode: string; required: boolean }[] };
export type LocalAgent = { id: string; name: string; phone: string; active: boolean; createdAt: string; credentials?: DemoPin };
export type ExchangeRight = { questionCode: string; status: "approved" | "requested" | "suspended" | "not_requested"; purpose?: string; requestedAt?: string };
export type OfferedService = { id: string; code: string; title: string; description: string; active: boolean };
export type RegistrySettings = { name: string; url: string; lastTest?: { at: string; success: boolean } };
export type LocalAdministration = { procedures: LocalProcedure[]; agents: LocalAgent[]; rights: ExchangeRight[]; registry: RegistrySettings; offeredServices: OfferedService[] };
export type AdminAuditEntry = { id: string; at: string; actor: string; role: string; action: string; target: string; detail: string };
export type DemoStaff = { id: string; name: string; phone: string; role: "agent" | "local-admin" };

export const DEFAULT_PROCEDURE: LocalProcedure = { code: "passeport_ordinaire_precheck", title: "Passeport ordinaire — demandeur majeur", purpose: "Vérifier les informations nécessaires à la demande de passeport.", version: 1, active: true, published: true, consentDays: 30, checks: LOCAL_QUESTIONS.slice(0, 5).map((question) => ({ questionCode: question.code, required: true })) };
const initial: LocalAdministration = { procedures: [DEFAULT_PROCEDURE], agents: [{ id: "seed-agent", name: "Agent de démonstration", phone: "22222222", active: true, createdAt: "2026-11-17T00:00:00Z" }], rights: LOCAL_QUESTIONS.map((question, index) => ({ questionCode: question.code, status: index < 5 ? "approved" : "not_requested" })), registry: { name: "Registre local des passeports", url: "" }, offeredServices: [] };
const DEFAULT_SNAPSHOT = JSON.stringify(initial);
const KEY = "dlnuf:demo:administration:v1";
const AUDIT_KEY = "dlnuf:demo:administration-audit:v1";
const EVENT = "dlnuf-demo-administration";
const STAFF_KEY = "dlnuf:demo:staff";
export function administrationSnapshot() { return localStorage.getItem(KEY) ?? DEFAULT_SNAPSHOT; }
export function administrationServerSnapshot() { return DEFAULT_SNAPSHOT; }
export function parseAdministration(raw: string): LocalAdministration {
  try { const data = JSON.parse(raw); if (Array.isArray(data.procedures) && Array.isArray(data.agents) && Array.isArray(data.rights) && data.registry && Array.isArray(data.offeredServices)) return data; } catch { /* Repli sur les données fictives initiales. */ }
  return JSON.parse(DEFAULT_SNAPSHOT);
}
export function getDemoAdministration() { return parseAdministration(administrationSnapshot()); }
export function getDemoStaff(): DemoStaff | null {
  try { return JSON.parse(sessionStorage.getItem(STAFF_KEY) ?? "null"); } catch { return null; }
}
export function setDemoStaff(staff: DemoStaff | null) {
  if (staff) sessionStorage.setItem(STAFF_KEY, JSON.stringify(staff)); else sessionStorage.removeItem(STAFF_KEY);
  window.dispatchEvent(new Event(EVENT));
}
export function auditSnapshot() { return localStorage.getItem(AUDIT_KEY) ?? "[]"; }
export function parseAudit(raw: string): AdminAuditEntry[] { try { const value = JSON.parse(raw); return Array.isArray(value) ? value : []; } catch { return []; } }
export function appendAdminAudit(action: string, target: string, detail = "", actor?: { name: string; role: string }) {
  const staff = getDemoStaff();
  const entry: AdminAuditEntry = { id: crypto.randomUUID(), at: new Date().toISOString(), actor: actor?.name ?? staff?.name ?? "Agent de démonstration", role: actor?.role ?? staff?.role ?? "agent", action, target, detail };
  localStorage.setItem(AUDIT_KEY, JSON.stringify([entry, ...parseAudit(auditSnapshot())]));
  window.dispatchEvent(new Event(EVENT));
}
export function subscribeAdministration(callback: () => void) {
  const storage = (event: StorageEvent) => { if (event.key === KEY || event.key === AUDIT_KEY || event.key === null) callback(); };
  window.addEventListener("storage", storage); window.addEventListener(EVENT, callback);
  return () => { window.removeEventListener("storage", storage); window.removeEventListener(EVENT, callback); };
}
function save(config: LocalAdministration, action: string, target: string, detail = "") {
  localStorage.setItem(KEY, JSON.stringify(config));
  appendAdminAudit(action, target, detail, { name: getDemoStaff()?.role === "local-admin" ? getDemoStaff()!.name : "Administrateur local (démo)", role: "local-admin" });
}
export function questionIsAllowed(code: string) { return getDemoAdministration().rights.some((right) => right.questionCode === code && right.status === "approved"); }
export function saveLocalProcedure(input: LocalProcedure) {
  const config = getDemoAdministration();
  if (!/^[a-z][a-z0-9_]{2,63}$/.test(input.code)) throw new Error("Utilisez un code de 3 à 64 caractères : lettres minuscules, chiffres et tirets bas.");
  if (input.title.trim().length < 3 || input.purpose.trim().length < 5) throw new Error("Renseignez le nom et la finalité de la démarche.");
  if (!Number.isInteger(input.consentDays) || input.consentDays < 1 || input.consentDays > 30) throw new Error("La durée de l’accord doit être comprise entre 1 et 30 jours dans cette démonstration.");
  if (!input.checks.length || !input.checks.some((check) => check.required) || new Set(input.checks.map((check) => check.questionCode)).size !== input.checks.length || input.checks.some((check) => !LOCAL_QUESTIONS.some((question) => question.code === check.questionCode))) throw new Error("Choisissez des vérifications distinctes, dont au moins une obligatoire.");
  if (input.published && input.checks.some((check) => !questionIsAllowed(check.questionCode))) throw new Error("Publication impossible : certains droits d’échange ne sont pas validés. Enregistrez un brouillon.");
  const previous = config.procedures.find((item) => item.code === input.code);
  const procedure = { ...input, title: input.title.trim(), purpose: input.purpose.trim(), version: previous ? previous.version + 1 : 1 };
  config.procedures = [procedure, ...config.procedures.filter((item) => item.code !== procedure.code)];
  save(config, previous ? "Démarche mise à jour" : "Démarche créée", procedure.title, "Version " + procedure.version + (procedure.published ? " · publiée" : " · brouillon"));
}
export function toggleLocalProcedure(code: string) {
  const config = getDemoAdministration(), item = config.procedures.find((entry) => entry.code === code);
  if (!item) throw new Error("Démarche introuvable.");
  if (!item.active && (!item.published || item.checks.some((check) => !questionIsAllowed(check.questionCode)))) throw new Error("Publiez la démarche avec des droits validés avant de l’activer.");
  item.active = !item.active;
  save(config, item.active ? "Démarche activée" : "Démarche désactivée", item.title);
}
export function requestExchangeRight(questionCode: string, purpose: string) {
  if (purpose.trim().length < 5) throw new Error("Précisez la finalité de cette demande d’accès.");
  const config = getDemoAdministration(), item = config.rights.find((entry) => entry.questionCode === questionCode);
  if (!item || item.status === "approved" || item.status === "requested") throw new Error("Ce droit est déjà validé ou en attente.");
  item.status = "requested"; item.purpose = purpose.trim(); item.requestedAt = new Date().toISOString();
  save(config, "Droit d’échange demandé", LOCAL_QUESTIONS.find((question) => question.code === questionCode)!.label, purpose.trim());
}
export function suspendExchangeRight(questionCode: string) {
  const config = getDemoAdministration(), item = config.rights.find((entry) => entry.questionCode === questionCode);
  if (!item || item.status !== "approved") throw new Error("Ce droit n’est pas actif.");
  item.status = "suspended";
  save(config, "Droit d’échange suspendu localement", LOCAL_QUESTIONS.find((question) => question.code === questionCode)!.label);
}
export async function createLocalAgent(name: string, phone: string, pin: string) {
  const config = getDemoAdministration(); phone = phone.replace(/\s/g, "");
  if (name.trim().length < 2 || !/^\d{8}$/.test(phone)) throw new Error("Renseignez un nom et un numéro national à 8 chiffres.");
  if (["11111111", "33333333", "44444444", "99999999"].includes(phone) || config.agents.some((agent) => agent.phone === phone) || localStorage.getItem("dlnuf:demo:citizen:" + phone)) throw new Error("Ce numéro est déjà utilisé dans la démonstration.");
  const credentials = await hashDemoPin(pin);
  config.agents.push({ id: crypto.randomUUID(), name: name.trim(), phone, active: true, createdAt: new Date().toISOString(), credentials });
  save(config, "Compte agent créé", name.trim(), "Compte agent local activé");
}
export function toggleLocalAgent(id: string) {
  const config = getDemoAdministration(), agent = config.agents.find((item) => item.id === id);
  if (!agent) throw new Error("Agent introuvable.");
  agent.active = !agent.active;
  save(config, agent.active ? "Compte agent réactivé" : "Compte agent suspendu", agent.name);
}
export async function resetLocalAgentPin(id: string, pin: string) {
  const credentials = await hashDemoPin(pin), config = getDemoAdministration(), agent = config.agents.find((item) => item.id === id);
  if (!agent) throw new Error("Agent introuvable.");
  agent.credentials = credentials;
  save(config, "PIN agent réinitialisé", agent.name);
}
export function saveRegistry(name: string, url: string) {
  if (name.trim().length < 3) throw new Error("Renseignez le nom du registre.");
  let parsed: URL;
  try { parsed = new URL(url); } catch { throw new Error("Renseignez une URL HTTP ou HTTPS valide."); }
  if (!["http:", "https:"].includes(parsed.protocol) || parsed.username || parsed.password) throw new Error("Utilisez une URL HTTP ou HTTPS sans identifiants ni secrets.");
  const config = getDemoAdministration(); config.registry = { name: name.trim(), url: parsed.toString() };
  save(config, "Connexion du registre modifiée", name.trim());
}
export async function testRegistry(simulateFailure: boolean) {
  const registry = getDemoAdministration().registry;
  if (!registry.url) throw new Error("Enregistrez la connexion avant de la tester.");
  await new Promise((resolve) => setTimeout(resolve, 400));
  const config = getDemoAdministration();
  if (config.registry.url !== registry.url) throw new Error("La connexion a changé. Relancez le test.");
  config.registry.lastTest = { at: new Date().toISOString(), success: !simulateFailure };
  save(config, simulateFailure ? "Test du registre échoué" : "Test du registre réussi", config.registry.name, "Test simulé : aucun appel réseau réel");
}
export function addOfferedService(code: string, title: string, description: string) {
  const config = getDemoAdministration();
  if (!/^[a-z][a-z0-9-]{2,63}$/.test(code) || title.trim().length < 3 || description.trim().length < 5) throw new Error("Renseignez un code de service valide, un nom et une description.");
  if (config.offeredServices.some((item) => item.code === code)) throw new Error("Ce code de service existe déjà.");
  config.offeredServices.push({ id: crypto.randomUUID(), code, title: title.trim(), description: description.trim(), active: true });
  save(config, "Service fournisseur déclaré", title.trim(), "Réponse minimale booléenne");
}
export function toggleOfferedService(id: string) {
  const config = getDemoAdministration(), item = config.offeredServices.find((service) => service.id === id);
  if (!item) throw new Error("Service introuvable.");
  item.active = !item.active; save(config, item.active ? "Service fournisseur activé" : "Service fournisseur désactivé", item.title);
}
