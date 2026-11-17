import { cleanReferences, documentForQuestion, requirementsFor } from "@/lib/document-references";
import { answerAuthorization, putAuthorization, readAuthorizations } from "@/lib/demo-authorizations";
import { recordDemoConsultations } from "@/lib/demo-consultations";
import { appendAdminAudit, DEFAULT_PROCEDURE, getDemoAdministration, questionIsAllowed } from "@/lib/demo-administration";
import { agentDemo, demoCitizens, newChecks, passportProcedure } from "@/modules/casework/mocks/catalogue";
import type { AgentCase, AgentCaseService, AssistedChallenge, ConsentChannel } from "@/modules/casework/types/cases";

const KEY = "dlnuf:demo:agent-cases:v1";
const challenges = new Map<string, AssistedChallenge>();
const wait = () => new Promise<void>((resolve) => setTimeout(resolve, 180));

function readCases(): AgentCase[] {
  const raw = localStorage.getItem(KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((item) => item && typeof item.id === "string" && typeof item.procedureCode === "string" && Array.isArray(item.checks)).map((item: AgentCase) => ({ ...item,
      applicantName: item.applicantName ?? "Citoyen",
      phone: item.phone ?? "",
      procedureTitle: item.procedureTitle ?? passportProcedure.title,
      procedurePurpose: item.procedurePurpose ?? DEFAULT_PROCEDURE.purpose,
      procedureVersion: item.procedureVersion ?? 1, consentDays: item.consentDays ?? 30,
      checks: item.checks.map((check) => ({ ...check, document: check.document ?? documentForQuestion(check.questionCode), required: check.required ?? true })),
    })) : [];
  } catch { return []; }
}
function saveCase(item: AgentCase) {
  localStorage.setItem(KEY, JSON.stringify([item, ...readCases().filter((entry) => entry.id !== item.id)]));
  window.dispatchEvent(new Event("dlnuf-demo-cases"));
  return item;
}
function getCase(id: string) {
  const item = readCases().find((entry) => entry.id === id);
  if (!item) throw new Error("Dossier introuvable.");
  return item;
}
function getAuthorization(item: AgentCase) {
  const previous = readAuthorizations().find((entry) => entry.id === item.authorizationId && entry.caseId === item.id);
  if (!previous || previous.documents) return previous;
  const updated = { ...previous, documents: requirementsFor(item.checks), references: {}, status: previous.status === "refused" ? "refused" as const : "pending" as const, decidedAt: undefined, expiresAt: undefined };
  putAuthorization(updated);
  return updated;
}
function publishRequest(item: AgentCase, channel: ConsentChannel) {
  const previous = getAuthorization(item);
  if (previous && previous.status !== "pending") throw new Error("Le citoyen a déjà répondu à cette demande.");
  putAuthorization({ id: item.authorizationId, caseId: item.id, phone: item.phone, documents: requirementsFor(item.checks), references: previous?.references ?? {},
    organization: agentDemo.administration, purpose: "votre démarche « " + item.procedureTitle + " »", checks: item.checks.map((check) => check.label),
    duration: item.consentDays + " jours", validityDays: item.consentDays, channel, status: "pending", requestedAt: previous?.requestedAt ?? new Date().toISOString() });
}

export const demoAgentCaseService: AgentCaseService = {
  async list() { await wait(); const items = readCases(); items.filter((item) => item.status !== "completed").forEach(getAuthorization); return items.sort((a, b) => b.createdAt.localeCompare(a.createdAt)); },
  async create(applicantName, phone, procedureCode, channel, references) {
    await wait();
    const procedure = getDemoAdministration().procedures.find((entry) => entry.code === procedureCode && entry.active && entry.published);
    if (!procedure) throw new Error("Cette démarche n’est pas disponible dans votre administration.");
    if (procedure.checks.some((check) => !questionIsAllowed(check.questionCode))) throw new Error("Les droits d’échange requis ne sont pas tous actifs pour cette démarche.");
    const normalizedPhone = phone.replace(/\s/g, "");
    if (!/^\d{8}$/.test(normalizedPhone)) throw new Error("Le numéro de téléphone doit contenir 8 chiffres.");
    const documents = requirementsFor(procedure.checks);
    const cleaned = cleanReferences(documents, references, channel === "assisted");
    const id = crypto.randomUUID();
    const item: AgentCase = { id, reference: `${procedureCode === DEFAULT_PROCEDURE.code ? "PAS" : "DOS"}-${new Date().getUTCFullYear()}-${id.slice(0, 6).toUpperCase()}`, procedureCode,
      procedureTitle: procedure.title, procedurePurpose: procedure.purpose, procedureVersion: procedure.version, consentDays: procedure.consentDays,
      applicantName: applicantName.trim() || "Citoyen", phone: normalizedPhone, createdAt: new Date().toISOString(), channel, status: "received", authorizationId: `consent-${id}`, checks: newChecks(procedure) };
    publishRequest(item, channel);
    const request = getAuthorization(item)!;
    putAuthorization({ ...request, references: cleaned });
    saveCase(item);
    appendAdminAudit("Dossier ouvert", item.reference, item.procedureTitle + " · " + (channel === "assisted" ? "accord au guichet" : "accord à distance"));
    return item;
  },
  async requestConsent(id, channel) {
    await wait();
    let item = getCase(id);
    const previous = getAuthorization(item);
    if (previous?.status === "granted" && previous.expiresAt && new Date(previous.expiresAt).getTime() <= Date.now()) {
      item = { ...item, authorizationId: `consent-${crypto.randomUUID()}` };
    }
    publishRequest(item, channel);
    if (previous?.references) putAuthorization({ ...getAuthorization(item)!, references: previous.references });
    challenges.delete(id);
    appendAdminAudit("Mode de consentement modifié", item.reference, channel === "assisted" ? "Au guichet" : "À distance");
    return saveCase({ ...item, channel });
  },
  async sendCode(id, resend = false) {
    await wait();
    const item = getCase(id);
    const authorization = getAuthorization(item);
    if (!authorization || authorization.status !== "pending" || item.channel !== "assisted") throw new Error("Cette demande ne peut pas être confirmée au guichet.");
    cleanReferences(authorization.documents ?? requirementsFor(item.checks), authorization.references ?? {});
    const referencesSnapshot = JSON.stringify(authorization.references);
    const existing = challenges.get(id);
    if (!resend && existing && existing.expiresAt > Date.now() && existing.referencesSnapshot === referencesSnapshot) return existing;
    if (resend && existing && existing.resendAt > Date.now()) throw new Error("Patientez 30 secondes avant de renvoyer le code.");
    const code = String(100000 + crypto.getRandomValues(new Uint32Array(1))[0] % 900000);
    const challenge: AssistedChallenge = { caseId: id, code, phone: item.phone, referencesSnapshot,
      expiresAt: Date.now() + 5 * 60_000, resendAt: Date.now() + 30_000,
      message: `${agentDemo.service} — dossier ${item.reference}. Ce code vaut accord pour : ${item.checks.map((check) => check.label.toLowerCase()).join(", ")}. References : ${Object.values(authorization.references ?? {}).join(", ")}. Valable 5 minutes. Communiquez-le uniquement si vous acceptez ces vérifications.` };
    challenges.set(id, challenge);
    appendAdminAudit(resend ? "Code d’accord renvoyé" : "Code d’accord demandé", item.reference, "SMS simulé, sans conserver le code dans le journal");
    return challenge;
  },
  async verifyCode(id, code) {
    await wait();
    const item = getCase(id);
    const challenge = challenges.get(id);
    if (!challenge || item.channel !== "assisted") throw new Error("Demandez d’abord un code pour ce dossier.");
    if (challenge.referencesSnapshot !== JSON.stringify(getAuthorization(item)?.references)) { challenges.delete(id); throw new Error("Les references ont change. Demandez un nouveau code."); }
    if (Date.now() >= challenge.expiresAt) { challenges.delete(id); throw new Error("Ce code a expiré. Demandez un nouveau code."); }
    if (code !== challenge.code) { appendAdminAudit("Code d’accord incorrect", item.reference); throw new Error("Code incorrect. Vérifiez le code communiqué par le citoyen."); }
    answerAuthorization(item.authorizationId, "granted", challenge.phone, "assisted");
    challenges.delete(id);
    appendAdminAudit("Accord recueilli au guichet", item.reference, "Preuve de démonstration validée");
  },
  async runChecks(id) {
    await wait();
    const item = getCase(id);
    const authorization = getAuthorization(item);
    if (!authorization || authorization.status !== "granted" || !authorization.expiresAt || new Date(authorization.expiresAt).getTime() <= Date.now()) { appendAdminAudit("Vérifications bloquées", item.reference, "Accord absent, refusé ou expiré"); throw new Error("Un accord citoyen valide est nécessaire avant toute vérification."); }
    cleanReferences(authorization.documents ?? requirementsFor(item.checks), authorization.references ?? {});
    const scenario = demoCitizens.find((entry) => entry.phone === item.phone)?.scenario;
    const checks = item.checks.map((check) => {
      // Les vérifications déjà terminées ne sont pas rejouées lors d'une reprise.
      if (["confirmed", "rejected", "ambiguous", "not_found"].includes(check.status)) return check;
      if (!questionIsAllowed(check.questionCode)) return { ...check, status: "blocked" as const, result: null };
      const attemptCount = check.attemptCount + 1;
      if (scenario === "unavailable" && check.registry === "Justice" && attemptCount === 1) return { ...check, status: "unavailable" as const, result: null, attemptCount };
      if (scenario === "ambiguous" && check.questionCode === "passport_nationality") return { ...check, status: "ambiguous" as const, result: null, attemptCount };
      return { ...check, status: "confirmed" as const, result: true, attemptCount };
    });
    const required = checks.filter((check) => check.required);
    const updated = saveCase({ ...item, checks, status: required.some((check) => check.status === "rejected") ? "rejected" : required.length > 0 && required.every((check) => check.status === "confirmed") ? "completed" : "pending" });
    recordDemoConsultations(checks.filter((check, index) => check.attemptCount > item.checks[index].attemptCount).map((check) => ({
      id: `${item.id}:${check.questionCode}:${check.attemptCount}`, caseId: item.id, phone: item.phone,
      dateTime: new Date().toISOString(), organization: agentDemo.administration, information: check.label,
      purpose: item.procedurePurpose, source: check.registry,
      basis: authorization.channel === "assisted" ? "Votre accord au guichet" : "Votre accord sur le portail", outcome: check.status,
    })));
    appendAdminAudit("Vérifications exécutées", item.reference, checks.filter((check, index) => check.attemptCount > item.checks[index].attemptCount).length + " contrôle(s) tenté(s) · " + (updated.status === "completed" ? "contrôles requis terminés" : "dossier à reprendre ou examiner"));
    return updated;
  },
};
