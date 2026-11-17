"use client";
import type { DocumentReferences } from "@/lib/document-references";

import { useCallback, useEffect, useState } from "react";
import { subscribeAuthorizations } from "@/lib/demo-authorizations";
import { useDemoAuthorizations } from "@/lib/use-demo-authorizations";
import { appendAdminAudit } from "@/lib/demo-administration";
import { agentCaseService } from "@/modules/casework/services/agent-cases";
import type { AgentCase, AssistedChallenge, ConsentChannel } from "@/modules/casework/types/cases";

export function useAgentWorkspace() {
  const [cases, setCases] = useState<AgentCase[]>([]);
  const [view, setView] = useState<"list" | "new" | "case">("list");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<"consent" | "checks" | undefined>();
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [challenge, setChallenge] = useState<AssistedChallenge | null>(null);
  const authorizations = useDemoAuthorizations();

  const refresh = useCallback(async () => {
    const items = await agentCaseService.list();
    setCases(items);
  }, []);

  useEffect(() => {
    if (busy) return;
    const waiting = cases.find((item) => item.checks.some((check) => check.status === "unavailable") && authorizations.some((authorization) => authorization.id === item.authorizationId && authorization.status === "granted" && authorization.expiresAt && new Date(authorization.expiresAt).getTime() > Date.now()));
    if (!waiting) return;
    const timer = setTimeout(async () => {
      setBusy("auto");
      try { await agentCaseService.runChecks(waiting.id); await refresh(); }
      catch (cause) { setError(cause instanceof Error ? cause.message : "La reprise n’a pas abouti."); }
      finally { setBusy(""); }
    }, 15_000);
    return () => clearTimeout(timer);
  }, [cases, authorizations, busy, refresh]);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try { const items = await agentCaseService.list(); if (active) setCases(items); }
      catch { if (active) setError("Impossible de charger les dossiers de démonstration."); }
      finally { if (active) setLoading(false); }
    };
    void load();
    const unsubscribe = subscribeAuthorizations(() => { void load(); });
    window.addEventListener("focus", load);
    window.addEventListener("dlnuf-demo-cases", load);
    window.addEventListener("storage", load);
    return () => { active = false; unsubscribe(); window.removeEventListener("focus", load); window.removeEventListener("dlnuf-demo-cases", load); window.removeEventListener("storage", load); };
  }, []);

  async function task(name: string, action: () => Promise<void>) {
    if (busy) return;
    setBusy(name); setError("");
    try { await action(); await refresh(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Cette action n’a pas abouti. Réessayez."); }
    finally { setBusy(""); }
  }
  function openCase(id: string, section?: "consent" | "checks") { appendAdminAudit("Dossier consulté", id); setSelectedId(id); setSelectedSection(section); setChallenge(null); setError(""); setView("case"); }
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
  return { cases, view, loading, busy, error, challenge, selectedSection, selected: cases.find((item) => item.id === selectedId),
    showList, showNew, openCase, create, sendCode, verifyCode, changeChannel, runChecks, clearChallenge: () => setChallenge(null) };
}
