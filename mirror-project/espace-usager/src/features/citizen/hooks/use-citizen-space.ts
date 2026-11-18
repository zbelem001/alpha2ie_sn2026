"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { consentFromJournal, consultationsFromJournal, reportsFromJournal, requesterFromJournal, type ConsentView, type Consultation, type JournalEvent, type ReportKind } from "@/lib/journal";
import type { ApiCase } from "@/modules/casework/types/cases";

const REFRESH_MS = 15_000;

export type CitizenCase = ApiCase & { consent: ConsentView; requester: string; events: JournalEvent[] };
type IdentityLink = { linked: boolean; subject_ref: string | null };

export function useCitizenSpace() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expired, setExpired] = useState(false);
  const [link, setLink] = useState<IdentityLink | null>(null);
  const [cases, setCases] = useState<CitizenCase[]>([]);

  const load = useCallback(async () => {
    try {
      const current = await api<IdentityLink>("citizen/identity-link");
      setLink(current);
      const items = await api<ApiCase[]>("cases");
      setCases(await Promise.all(items.map(async (item) => {
        const events = await api<JournalEvent[]>(`cases/${item.id}/journal`);
        return { ...item, events, requester: requesterFromJournal(events), consent: consentFromJournal(events, item.consentDays) };
      })));
      setError("");
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) setExpired(true);
      else setError(cause instanceof Error ? cause.message : "Impossible de charger votre espace.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Chargement initial, puis rafraîchissement : une demande ouverte au guichet apparaît sans recharger.
    const first = setTimeout(load, 0);
    const timer = setInterval(load, REFRESH_MS);
    window.addEventListener("focus", load);
    return () => { clearTimeout(first); clearInterval(timer); window.removeEventListener("focus", load); };
  }, [load]);

  async function respond(caseId: string, decision: "granted" | "refused") {
    const item = cases.find((entry) => entry.id === caseId);
    if (!item) throw new Error("Cette demande n’est plus disponible.");
    await api(`cases/${caseId}/consent`, {
      body: { decision, question_codes: item.checks.map((check) => check.questionCode), notice_version: "espace-usager-v1", channel: "web" },
    });
    await load();
  }

  async function report(caseId: string, consultationId: string, reason: ReportKind) {
    await api(`cases/${caseId}/journal/${consultationId}/report`, { body: { reason } });
    await load();
  }

  async function revokeConsent(caseId: string) {
    await api(`cases/${caseId}/consent`, { method: "DELETE" });
    await load();
  }

  const reports = cases.flatMap((item) => reportsFromJournal(item.events));
  const consultations: Consultation[] = cases.flatMap((item) => consultationsFromJournal(item, item.events))
    .sort((a, b) => b.dateTime.localeCompare(a.dateTime));
  // Seules les demandes « à distance » se règlent ici ; au guichet, seul le code SMS vaut accord.
  const requests = cases.filter((item) => item.channel === "web" && item.consent.status === "pending" && !["completed", "rejected"].includes(item.status));
  const atDesk = cases.filter((item) => item.channel === "assisted" && item.consent.status === "pending" && !["completed", "rejected"].includes(item.status));

  return { loading, error, expired, link, cases, consultations, requests, atDesk, reports, respond, revokeConsent, report, reload: load };
}
