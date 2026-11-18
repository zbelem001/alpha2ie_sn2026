import { expect, test } from "@playwright/test";
import { consentFromJournal, consentIsActive, consultationsFromJournal, formatPhone, requesterFromJournal, type JournalEvent } from "@/lib/journal";
import type { AgentCheck } from "@/modules/casework/types/cases";

const event = (overrides: Partial<JournalEvent>): JournalEvent => ({
  id: "e0", occurred_at: "2026-11-18T10:00:00Z", event_type: "case_created", requester: "Fonction publique",
  registry: null, question_code: null, purpose: "", outcome: null, data_categories: null, ...overrides,
});

const check: AgentCheck = {
  questionCode: "candidate_minimum_age", label: "Majorité", registry: "État civil",
  document: { key: "birth", label: "Acte de naissance", provider: "État civil", hint: "" },
  required: true, status: "confirmed", result: true, attemptCount: 1,
};

test.describe("accord tiré du journal", () => {
  test("sans décision, l'accord est en attente", () => {
    expect(consentFromJournal([event({}), event({ event_type: "consent_requested" })], 30)).toEqual({ status: "pending" });
  });

  test("un accord vaut la durée de la démarche, pas plus", () => {
    const consent = consentFromJournal([event({ event_type: "consent_recorded", outcome: "granted" })], 30);
    expect(consent).toMatchObject({ status: "granted", decidedAt: "2026-11-18T10:00:00Z", expiresAt: "2026-12-18T10:00:00.000Z" });
    expect(consentIsActive(consent, Date.parse("2026-12-18T09:59:00Z"))).toBe(true);
    expect(consentIsActive(consent, Date.parse("2026-12-18T10:01:00Z"))).toBe(false);
  });

  test("la dernière décision compte : refus, puis accord, puis retrait", () => {
    const refused = [event({ event_type: "consent_recorded", outcome: "refused" })];
    expect(consentFromJournal(refused, 30).status).toBe("refused");
    const revoked = [...refused, event({ event_type: "consent_recorded", outcome: "granted" }), event({ event_type: "consent_revoked", outcome: "revoked" })];
    expect(consentFromJournal(revoked, 30).status).toBe("revoked");
    expect(consentIsActive(consentFromJournal(revoked, 30))).toBe(false);
  });
});

test.describe("consultations tirées du journal", () => {
  test("consultations et blocages y figurent, les autres événements non", () => {
    const item = { id: "c1", procedureTitle: "Concours direct", channel: "web" as const, checks: [check] };
    const consultations = consultationsFromJournal(item, [
      event({ id: "a", event_type: "consent_recorded", outcome: "granted" }),
      event({ id: "b", event_type: "registry_check", question_code: "candidate_minimum_age", outcome: "confirmed" }),
      event({ id: "c", event_type: "registry_check", question_code: "candidate_minimum_age", outcome: "unavailable" }),
      event({ id: "d", event_type: "checks_blocked", outcome: "blocked" }),
    ]);
    expect(consultations.map((entry) => entry.id)).toEqual(["b", "c", "d"]);
    expect(consultations[0]).toMatchObject({ information: "Majorité", source: "État civil", purpose: "Concours direct", basis: "Votre accord sur le portail", outcome: "confirmed" });
    expect(consultations[1].outcome).toBe("unavailable");
    expect(consultations[2]).toMatchObject({ information: "Toutes les vérifications du dossier", basis: "Aucun accord valide" });
  });

  test("accord donné au guichet", () => {
    const item = { id: "c2", procedureTitle: "Passeport", channel: "assisted" as const, checks: [check] };
    const [entry] = consultationsFromJournal(item, [event({ event_type: "registry_check", question_code: "candidate_minimum_age", outcome: "confirmed" })]);
    expect(entry.basis).toBe("Votre accord au guichet");
  });
});

test("administration demandeuse et téléphone affiché sans indicatif", () => {
  expect(requesterFromJournal([event({ requester: null }), event({ requester: "ONI" })])).toBe("ONI");
  expect(formatPhone("+22670000001")).toBe("70 00 00 01");
});
