"use client";
import type { DocumentReferences } from "@/lib/document-references";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { consentIsActive } from "@/lib/journal";
import { agentCaseService } from "@/modules/casework/services/agent-cases";
import type { AgentCase, AssistedChallenge, ConsentChannel, Procedure } from "@/modules/casework/types/cases";

const REFRESH_MS = 10_000;
const AUTO_RETRY_MS = 15_000;

function messageOf(cause: unknown, fallback: string) {
  return cause instanceof Error ? cause.message : fallback;
}

export function useAgentWorkspace() {
  const [cases, setCases] = useState<AgentCase[]>([]);
  const [procedures, setProcedures] = useState<Procedure[]>([]);
  const [view, setView] = useState<"list" | "new" | "case">("list");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<"consent" | "checks" | undefined>();
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [expired, setExpired] = useState(false);
  const [challenge, setChallenge] = useState<AssistedChallenge | null>(null);

  const refresh = useCallback(async () => {
    try {
      setCases(await agentCaseService.list());
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) setExpired(true);
      throw cause;
    }
  }, []);

  // Premier chargement, puis rafraîchissement régulier : l'accord donné par le citoyen
  // depuis son espace apparaît ici sans recharger la page.
  useEffect(() => {
    let active = true;
    const load = async () => {
      try { const items = await agentCaseService.list(); if (active) setCases(items); }
      catch (cause) {
        if (!active) return;
        if (cause instanceof ApiError && cause.status === 401) setExpired(true);
        else setError(messageOf(cause, "Impossible de charger les dossiers."));
      }
      finally { if (active) setLoading(false); }
    };
    void load();
    agentCaseService.procedures().then((items) => { if (active) setProcedures(items); }).catch(() => undefined);
    const timer = setInterval(load, REFRESH_MS);
    window.addEventListener("focus", load);
    return () => { active = false; clearInterval(timer); window.removeEventListener("focus", load); };
  }, []);

  // Reprise automatique : un registre indisponible est réinterrogé, tant que l'accord est valide.
  useEffect(() => {
    if (busy) return;
    const waiting = cases.find((item) => item.checks.some((check) => check.status === "unavailable") && consentIsActive(item.consent));
    if (!waiting) return;
    const timer = setTimeout(async () => {
      setBusy("auto");
      try { await agentCaseService.runChecks(waiting.id); await refresh(); }
      catch (cause) { setError(messageOf(cause, "La reprise n’a pas abouti.")); }
      finally { setBusy(""); }
    }, AUTO_RETRY_MS);
    return () => clearTimeout(timer);
  }, [cases, busy, refresh]);

  async function task(name: string, action: () => Promise<void>) {
    if (busy) return;
    setBusy(name); setError("");
    try { await action(); await refresh(); }
    catch (cause) { setError(messageOf(cause, "Cette action n’a pas abouti. Réessayez.")); }
    finally { setBusy(""); }
  }
  function openCase(id: string, section?: "consent" | "checks") { setSelectedId(id); setSelectedSection(section); setChallenge(null); setError(""); setView("case"); }
  function showList() { setError(""); setView("list"); setChallenge(null); }
  function showNew() { setError(""); setView("new"); setChallenge(null); }
  async function create(applicantName: string, phone: string, procedureCode: string, channel: ConsentChannel, references: DocumentReferences) {
    await task("create", async () => {
      const item = await agentCaseService.create(applicantName, phone, procedureCode, channel, references);
      openCase(item.id);
    });
  }
  async function sendCode(resend = false) {
    if (!selectedId) return;
    await task("code", async () => setChallenge(await agentCaseService.sendCode(selectedId, resend)));
  }
  async function verifyCode(code: string) {
    if (!selectedId) return;
    await task("verify", async () => { await agentCaseService.verifyCode(selectedId, code); setChallenge(null); });
  }
  async function changeChannel(channel: ConsentChannel) {
    if (!selectedId) return;
    await task("channel", async () => { await agentCaseService.requestConsent(selectedId, channel); setChallenge(null); });
  }
  async function runChecks() {
    if (!selectedId) return;
    await task("checks", async () => { await agentCaseService.runChecks(selectedId); });
  }
  return { cases, procedures, view, loading, busy, error, expired, challenge, selectedSection, selected: cases.find((item) => item.id === selectedId),
    showList, showNew, openCase, create, sendCode, verifyCode, changeChannel, runChecks };
}
