import { api } from "@/lib/api";
import { documentForQuestion, type DocumentRequirement } from "@/lib/document-references";

export type LocalProcedure = { code: string; title: string; purpose: string; version: number; active: boolean; published: boolean; consentDays: number; checks: { questionCode: string; required: boolean; document?: DocumentRequirement }[] };
export type LocalAgent = { id: string; name: string; phone: string; active: boolean; createdAt?: string };
export type ExchangeRight = { questionCode: string; label: string; provider: string; providerCode: string; service_code: string; active: boolean; status: "approved" | "requested" | "suspended" | "not_requested"; purpose?: string };
export type LocalAdministration = {
  administration: { code: string; name: string };
  procedures: LocalProcedure[]; agents: LocalAgent[]; rights: ExchangeRight[];
  agentManagementAvailable: boolean;
  registry: { name: string; url: string; lastTest?: { at: string; success: boolean } };
  offeredServices: { id: string; code: string; title: string; description: string; active: boolean }[];
  availableServices: { id: string; code: string; title: string; description: string; provider: string; providerCode: string }[];
};
export type AdminAuditEntry = { id: string; at: string; actor: string; role: string; action: string; target: string; detail: string };
// Catalogue fourni par le serveur, jamais inventé ni autorisé par le navigateur.
export const LOCAL_QUESTIONS: { code: string; questionCodes: string[]; label: string; provider: string; providerCode: string; service: string; active: boolean; status: ExchangeRight["status"] }[] = [];
let configuration: LocalAdministration | null = null;
function current() { if (!configuration) throw new Error("Chargez la configuration avant de modifier un service."); return configuration; }
export async function getAdministration() {
  const config = await api<LocalAdministration>("admin/config");
  configuration = config;
  const unique = new Map<string, { right: ExchangeRight; codes: Set<string> }>();
  const priority = (right: ExchangeRight) => Number(right.active) * 2 + Number(right.status === "approved");
  for (const right of config.rights) {
    const key = `${right.providerCode}:${right.service_code}`;
    const current = unique.get(key);
    if (!current) unique.set(key, { right, codes: new Set([right.questionCode]) });
    else {
      current.codes.add(right.questionCode);
      if (priority(right) > priority(current.right)) current.right = right;
    }
  }
  LOCAL_QUESTIONS.splice(0, LOCAL_QUESTIONS.length, ...[...unique.values()].map(({ right, codes }) => ({
    code: right.questionCode, questionCodes: [...codes], label: right.label, provider: right.provider, providerCode: right.providerCode,
    service: right.service_code, active: right.active, status: right.status,
  })));
  return config;
}
export const getAdministrationAudit = () => api<AdminAuditEntry[]>("admin/audit");
export async function saveLocalProcedure(item: LocalProcedure) {
  const checks = item.checks.map((check) => ({
    questionCode: check.questionCode,
    required: check.required,
    document: check.document ?? documentForQuestion(check.questionCode),
  }));
  await api("admin/procedures/" + encodeURIComponent(item.code), { method: "PUT", body: { code: item.code, title: item.title, purpose: item.purpose, consentDays: item.consentDays, published: item.published, checks } });
}
export async function toggleLocalProcedure(code: string) {
  const item = current().procedures.find((entry) => entry.code === code);
  if (!item) throw new Error("Démarche introuvable.");
  await api("admin/procedures/" + encodeURIComponent(code) + "/active", { method: "PATCH", body: { active: !item.active } });
}
export async function requestExchangeRight(code: string, purpose: string) { await api("admin/rights/" + encodeURIComponent(code) + "/request", { body: { purpose } }); }
export async function suspendExchangeRight(code: string) { await api("admin/rights/" + encodeURIComponent(code) + "/suspend", { method: "POST" }); }
export async function saveRegistry(name: string, url: string) { await api("admin/registry", { method: "PUT", body: { name, url } }); }
export async function testRegistry() { await api("admin/registry/test", { method: "POST" }); }
export async function addOfferedService(code: string, title: string, description: string) { await api("admin/services", { body: { code, title, description } }); }
export async function toggleOfferedService(id: string) {
  const item = current().offeredServices.find((entry) => entry.id === id);
  if (!item) throw new Error("Service introuvable.");
  await api("admin/services/" + encodeURIComponent(id) + "/active", { method: "PATCH", body: { active: !item.active } });
}
export async function createLocalAgent(name: string, phone: string, pin: string) { await api("admin/agents", { body: { name, phone: phone.replace(/\s/g, ""), pin } }); }
export async function toggleLocalAgent(id: string) {
  const item = current().agents.find((entry) => entry.id === id);
  if (!item) throw new Error("Agent introuvable.");
  await api("admin/agents/" + encodeURIComponent(id) + "/active", { method: "PATCH", body: { active: !item.active } });
}
export async function resetLocalAgentPin(id: string, pin: string) { await api("admin/agents/" + encodeURIComponent(id) + "/pin", { method: "PUT", body: { pin } }); }
