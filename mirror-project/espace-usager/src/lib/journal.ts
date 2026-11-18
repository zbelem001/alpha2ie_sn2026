// Journal d'un dossier (GET /v1/cases/{id}/journal) : état de l'accord et consultations.
import type { AgentCase, ConsentChannel } from "@/modules/casework/types/cases";

export type JournalEvent = {
  id: string;
  occurred_at: string;
  event_type: string;
  requester: string | null;
  registry: string | null;
  question_code: string | null;
  purpose: string;
  outcome: string | null;
  data_categories: string[] | null;
};

export type ConsentView = {
  status: "pending" | "granted" | "refused" | "revoked";
  decidedAt?: string;
  expiresAt?: string;
};

export type Consultation = {
  id: string; caseId: string; dateTime: string; organization: string; information: string;
  purpose: string; source: string; basis: string; outcome: string;
};

/** Dernière décision du citoyen inscrite au journal ; l'accord vaut au plus `consentDays` jours. */
export function consentFromJournal(events: JournalEvent[], consentDays: number): ConsentView {
  const last = [...events].reverse().find((event) => event.event_type === "consent_recorded" || event.event_type === "consent_revoked");
  if (!last) return { status: "pending" };
  if (last.event_type === "consent_revoked") return { status: "revoked", decidedAt: last.occurred_at };
  if (last.outcome !== "granted") return { status: "refused", decidedAt: last.occurred_at };
  const expiresAt = new Date(new Date(last.occurred_at).getTime() + consentDays * 86_400_000).toISOString();
  return { status: "granted", decidedAt: last.occurred_at, expiresAt };
}

export function consentIsActive(consent: ConsentView, now = Date.now()) {
  return consent.status === "granted" && Boolean(consent.expiresAt) && new Date(consent.expiresAt!).getTime() > now;
}

const CONSULTATION_EVENTS = new Set(["registry_check", "check_blocked", "checks_blocked"]);

/** Consultations d'un registre, et tentatives refusées ou bloquées : tout apparaît au journal. */
export function consultationsFromJournal(item: Pick<AgentCase, "id" | "procedureTitle" | "checks" | "channel">, events: JournalEvent[]): Consultation[] {
  return events.filter((event) => CONSULTATION_EVENTS.has(event.event_type)).map((event) => {
    const check = item.checks.find((entry) => entry.questionCode === event.question_code);
    const blocked = event.event_type !== "registry_check";
    return {
      id: event.id,
      caseId: item.id,
      dateTime: event.occurred_at,
      organization: event.requester ?? "Administration",
      information: check?.label ?? (event.event_type === "checks_blocked" ? "Toutes les vérifications du dossier" : event.purpose),
      purpose: item.procedureTitle,
      source: check?.registry ?? event.registry ?? "Registre",
      basis: blocked && event.outcome === "blocked" ? "Aucun accord valide" : channelBasis(item.channel),
      outcome: event.outcome ?? "error",
    };
  });
}

function channelBasis(channel: ConsentChannel) {
  return channel === "assisted" ? "Votre accord au guichet" : "Votre accord sur le portail";
}

/** Administration qui a ouvert le dossier, d'après le premier événement du journal. */
export function requesterFromJournal(events: JournalEvent[]) {
  return events.find((event) => event.requester)?.requester ?? "Administration";
}

export function formatPhone(phone: string) {
  const local = phone.replace(/^\+226/, "").replace(/\s/g, "");
  return local.match(/.{1,2}/g)?.join(" ") ?? local;
}
