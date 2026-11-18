import { expect, test } from "@playwright/test";
import { consentFromJournal, consentIsActive, formatPhone, reportsFromJournal, type JournalEvent } from "@/lib/journal";

const event = (overrides: Partial<JournalEvent>): JournalEvent => ({
  id: "e0", occurred_at: "2026-11-18T10:00:00Z", event_type: "case_created", requester: "Fonction publique",
  registry: null, question_code: null, purpose: "", outcome: null, data_categories: null, ...overrides,
});

test("le guichet ne vérifie qu'avec un accord actif", () => {
  expect(consentFromJournal([event({})], 30).status).toBe("pending");
  const granted = consentFromJournal([event({ event_type: "consent_recorded", outcome: "granted" })], 7);
  expect(consentIsActive(granted, Date.parse("2026-11-20T00:00:00Z"))).toBe(true);
  expect(consentIsActive(granted, Date.parse("2026-11-26T00:00:00Z"))).toBe(false);
  const revoked = consentFromJournal([event({ event_type: "consent_recorded", outcome: "granted" }), event({ event_type: "consent_revoked" })], 30);
  expect(revoked.status).toBe("revoked");
  expect(consentIsActive(revoked)).toBe(false);
});

test("le guichet voit les signalements du citoyen, rattachés à leur consultation", () => {
  const reports = reportsFromJournal([
    event({ id: "r1", event_type: "registry_check", question_code: "candidate_nationality" }),
    event({ event_type: "correction_requested", correlation_id: "r1", question_code: "candidate_nationality", outcome: "open" }),
  ]);
  expect(reports).toEqual([{ kind: "wrong_result", consultationId: "r1", occurredAt: "2026-11-18T10:00:00Z", questionCode: "candidate_nationality" }]);
});

test("téléphone du citoyen affiché sans indicatif", () => {
  expect(formatPhone("+22670000001")).toBe("70 00 00 01");
});
