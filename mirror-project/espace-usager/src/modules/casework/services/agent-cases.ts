import { api } from "@/lib/api";
import { consentFromJournal, type JournalEvent } from "@/lib/journal";
import type { AgentCase, AgentCaseService, ApiCase, AssistedChallenge, Procedure } from "@/modules/casework/types/cases";

// API démarches, par le relais de l'application (jeton agent Keycloak gardé côté serveur).
async function withConsent(item: ApiCase): Promise<AgentCase> {
  const events = await api<JournalEvent[]>(`cases/${item.id}/journal`);
  return { ...item, consent: consentFromJournal(events, item.consentDays) };
}

const reload = async (id: string) => withConsent(await api<ApiCase>(`cases/${id}`));

export const agentCaseService: AgentCaseService = {
  async list() {
    const items = await api<ApiCase[]>("cases");
    return Promise.all(items.map(withConsent));
  },
  async procedures() {
    const items = await api<Procedure[]>("procedures");
    return items.filter((item) => item.active && item.published);
  },
  async create(applicantName, phone, procedureCode, channel, references) {
    const item = await api<ApiCase>("cases", {
      body: { procedureCode, channel, phone: phone.replace(/\s/g, ""), applicantName: applicantName.trim() || "Citoyen", references },
    });
    return withConsent(item);
  },
  async requestConsent(id, channel) {
    await api(`cases/${id}/consent/request`, { body: { consent_channel: channel } });
    return reload(id);
  },
  sendCode(id, resend = false) {
    return api<AssistedChallenge>(`cases/${id}/consent/otp`, { body: { resend } });
  },
  async verifyCode(id, code) {
    await api(`cases/${id}/consent/otp/verify`, { body: { code } });
  },
  async runChecks(id) {
    await api(`cases/${id}/checks`, { method: "POST" });
    return reload(id);
  },
};
