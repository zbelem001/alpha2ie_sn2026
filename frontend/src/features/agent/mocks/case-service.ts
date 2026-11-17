import { answerAuthorization, putAuthorization, readAuthorizations } from "@/lib/demo-authorizations";
import { recordDemoConsultations } from "@/lib/demo-consultations";
import { agentDemo, demoCitizens, newChecks, passportProcedure } from "@/features/agent/mocks/catalogue";
import type { AgentCase, AgentCaseService, AssistedChallenge, ConsentChannel } from "@/features/agent/types/cases";

const KEY = "dlnuf:demo:agent-cases:v1";
const challenges = new Map<string, AssistedChallenge>();
const wait = () => new Promise<void>((resolve) => setTimeout(resolve, 180));

function readCases(): AgentCase[] {
  const raw = localStorage.getItem(KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((item) => item && typeof item.id === "string" && item.procedureCode === passportProcedure.code && Array.isArray(item.checks)).map((item: AgentCase) => ({ ...item,
      citizenId: item.citizenId ?? citizenFor(item.subjectRef).uniqueId,
      phone: item.phone ?? citizenFor(item.subjectRef).phone,
    })) : [];
  } catch { return []; }
}
function saveCase(item: AgentCase) {
  localStorage.setItem(KEY, JSON.stringify([item, ...readCases().filter((entry) => entry.id !== item.id)]));
  return item;
}
function getCase(id: string) {
  const item = readCases().find((entry) => entry.id === id);
  if (!item) throw new Error("Dossier introuvable.");
  return item;
}
function citizenFor(subjectRef: string) {
  const normalized = subjectRef.trim().toUpperCase();
  const citizen = demoCitizens.find((item) => item.uniqueId === normalized || item.subjectRef === normalized);
  if (!citizen) throw new Error("Aucun citoyen retrouvé avec cet identifiant unique. Vérifiez la saisie avant de continuer.");
  return citizen;
}
function getAuthorization(item: AgentCase) {
  const authorization = readAuthorizations().find((entry) => entry.id === item.authorizationId && entry.caseId === item.id);
  // Aligner les demandes encore en attente avec le contact actuel du profil fictif.
  const phone = citizenFor(item.subjectRef).phone;
  if (authorization?.status === "pending" && authorization.phone !== phone) {
    const updated = { ...authorization, phone };
    putAuthorization(updated);
    return updated;
  }
  return authorization;
}
function publishRequest(item: AgentCase, channel: ConsentChannel) {
  const previous = getAuthorization(item);
  if (previous && previous.status !== "pending") throw new Error("Le citoyen a déjà répondu à cette demande.");
  const citizen = citizenFor(item.subjectRef);
  putAuthorization({ id: item.authorizationId, caseId: item.id, subjectRef: item.subjectRef, phone: citizen.phone,
    organization: agentDemo.administration, purpose: "votre demande de passeport", checks: item.checks.map((check) => check.label),
    duration: "30 jours", channel, status: "pending", requestedAt: previous?.requestedAt ?? new Date().toISOString() });
}

export const demoAgentCaseService: AgentCaseService = {
  async list() { await wait(); return readCases().sort((a, b) => b.createdAt.localeCompare(a.createdAt)); },
  async identify(subjectRef) { await wait(); return citizenFor(subjectRef); },
  async create(citizenId, phone, procedureCode, channel) {
    await wait();
    if (procedureCode !== passportProcedure.code || passportProcedure.owner !== agentDemo.administrationCode) throw new Error("Cette démarche n’appartient pas à votre administration.");
    const citizen = citizenFor(citizenId);
    const normalizedPhone = phone.replace(/\s/g, "");
    if (!/^\d{8}$/.test(normalizedPhone)) throw new Error("Le numéro de téléphone doit contenir 8 chiffres.");
    if (normalizedPhone !== citizen.phone) throw new Error("Ce numéro ne correspond pas au contact du citoyen identifié.");
    const subjectRef = citizen.subjectRef;
    const duplicate = readCases().find((item) => item.subjectRef === subjectRef && item.procedureCode === procedureCode && item.status !== "completed" && getAuthorization(item)?.status !== "refused");
    if (duplicate) return duplicate;
    const id = crypto.randomUUID();
    const item: AgentCase = { id, reference: `PAS-${new Date().getUTCFullYear()}-${id.slice(0, 6).toUpperCase()}`, procedureCode,
      subjectRef, citizenId: citizen.uniqueId, phone: normalizedPhone, createdAt: new Date().toISOString(), channel, status: "received", authorizationId: `consent-${id}`, checks: newChecks() };
    publishRequest(item, channel);
    return saveCase(item);
  },
  async requestConsent(id, channel) {
    await wait();
    let item = getCase(id);
    const previous = getAuthorization(item);
    if (previous?.status === "granted" && previous.expiresAt && new Date(previous.expiresAt).getTime() <= Date.now()) {
      item = { ...item, authorizationId: `consent-${crypto.randomUUID()}` };
    }
    publishRequest(item, channel);
    challenges.delete(id);
    return saveCase({ ...item, channel });
  },
  async sendCode(id, resend = false) {
    await wait();
    const item = getCase(id);
    const authorization = getAuthorization(item);
    if (!authorization || authorization.status !== "pending" || item.channel !== "assisted") throw new Error("Cette demande ne peut pas être confirmée au guichet.");
    const existing = challenges.get(id);
    if (!resend && existing && existing.expiresAt > Date.now()) return existing;
    if (resend && existing && existing.resendAt > Date.now()) throw new Error("Patientez 30 secondes avant de renvoyer le code.");
    const code = String(100000 + crypto.getRandomValues(new Uint32Array(1))[0] % 900000);
    const challenge: AssistedChallenge = { caseId: id, code, phone: citizenFor(item.subjectRef).phone,
      expiresAt: Date.now() + 5 * 60_000, resendAt: Date.now() + 30_000,
      message: `${agentDemo.service} — dossier ${item.reference}. Ce code vaut accord pour : ${item.checks.map((check) => check.label.toLowerCase()).join(", ")}. Valable 5 minutes. Communiquez-le uniquement si vous acceptez ces vérifications.` };
    challenges.set(id, challenge);
    return challenge;
  },
  async verifyCode(id, code) {
    await wait();
    const item = getCase(id);
    const challenge = challenges.get(id);
    if (!challenge || item.channel !== "assisted") throw new Error("Demandez d’abord un code pour ce dossier.");
    if (Date.now() >= challenge.expiresAt) { challenges.delete(id); throw new Error("Ce code a expiré. Demandez un nouveau code."); }
    if (code !== challenge.code) throw new Error("Code incorrect. Vérifiez le code communiqué par le citoyen.");
    answerAuthorization(item.authorizationId, "granted", challenge.phone, "assisted");
    challenges.delete(id);
  },
  async runChecks(id) {
    await wait();
    const item = getCase(id);
    const authorization = getAuthorization(item);
    if (!authorization || authorization.status !== "granted" || !authorization.expiresAt || new Date(authorization.expiresAt).getTime() <= Date.now()) throw new Error("Un accord citoyen valide est nécessaire avant toute vérification.");
    const citizen = citizenFor(item.subjectRef);
    const checks = item.checks.map((check) => {
      // Les vérifications déjà terminées ne sont pas rejouées lors d'une reprise.
      if (["confirmed", "rejected", "ambiguous", "not_found"].includes(check.status)) return check;
      const attemptCount = check.attemptCount + 1;
      if (citizen.scenario === "unavailable" && check.registry === "Justice" && attemptCount === 1) return { ...check, status: "unavailable" as const, result: null, attemptCount };
      if (citizen.scenario === "ambiguous" && check.questionCode === "passport_nationality") return { ...check, status: "ambiguous" as const, result: null, attemptCount };
      return { ...check, status: "confirmed" as const, result: true, attemptCount };
    });
    const updated = saveCase({ ...item, checks, status: checks.every((check) => check.status === "confirmed") ? "completed" : "pending" });
    recordDemoConsultations(checks.filter((check, index) => check.attemptCount > item.checks[index].attemptCount).map((check) => ({
      id: `${item.id}:${check.questionCode}:${check.attemptCount}`, caseId: item.id, phone: citizen.phone,
      dateTime: new Date().toISOString(), organization: agentDemo.administration, information: check.label,
      purpose: "Demande de passeport ordinaire", source: check.registry,
      basis: authorization.channel === "assisted" ? "Votre accord au guichet" : "Votre accord sur le portail", outcome: check.status,
    })));
    return updated;
  },
};
