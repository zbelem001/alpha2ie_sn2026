export type CheckStatus = "queued" | "confirmed" | "rejected" | "ambiguous" | "not_found" | "unavailable" | "blocked" | "error";
export type CaseStatus = "received" | "pending" | "completed" | "rejected";
export type ConsentChannel = "assisted" | "web";
export type AgentCheck = { questionCode: string; label: string; registry: string; status: CheckStatus; result: boolean | null; attemptCount: number };
export type AgentCase = {
  id: string; reference: string; procedureCode: string; subjectRef: string; createdAt: string;
  citizenId: string; phone: string;
  channel: ConsentChannel; status: CaseStatus; authorizationId: string;
  checks: AgentCheck[];
};
export type DemoCitizen = { uniqueId: string; subjectRef: string; displayName: string; phone: string; scenario: "normal" | "unavailable" | "ambiguous" };
export type AssistedChallenge = { caseId: string; code: string; phone: string; expiresAt: number; resendAt: number; message: string };
export type AgentCaseService = {
  list: () => Promise<AgentCase[]>;
  identify: (subjectRef: string) => Promise<DemoCitizen>;
  create: (citizenId: string, phone: string, procedureCode: string, channel: ConsentChannel) => Promise<AgentCase>;
  requestConsent: (id: string, channel: ConsentChannel) => Promise<AgentCase>;
  sendCode: (id: string, resend?: boolean) => Promise<AssistedChallenge>;
  verifyCode: (id: string, code: string) => Promise<void>;
  runChecks: (id: string) => Promise<AgentCase>;
};
