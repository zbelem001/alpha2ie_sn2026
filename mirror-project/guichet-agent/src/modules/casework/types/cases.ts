import type { DocumentReferences, DocumentRequirement } from "@/lib/document-references";
import type { ConsentView, Report } from "@/lib/journal";
export type CheckStatus = "queued" | "confirmed" | "rejected" | "ambiguous" | "not_found" | "unavailable" | "blocked" | "error";
export type CaseStatus = "received" | "pending" | "completed" | "rejected";
export type ConsentChannel = "assisted" | "web";
export type AgentCheck = { questionCode: string; label: string; registry: string; document: DocumentRequirement; required: boolean; status: CheckStatus; result: boolean | null; attemptCount: number };
/** Dossier tel que le renvoie l'API démarches (GET /v1/cases). */
export type ApiCase = {
  id: string; reference: string; procedureCode: string; createdAt: string;
  applicantName: string; phone: string;
  procedureTitle: string; procedurePurpose: string; procedureVersion: number; consentDays: number;
  channel: ConsentChannel; status: CaseStatus; authorizationId: string;
  checks: AgentCheck[];
};
/** Dossier affiché : celui de l'API, avec l'accord et les signalements du citoyen tirés de son journal. */
export type AgentCase = ApiCase & { consent: ConsentView; reports: Report[] };
export type Procedure = {
  code: string; title: string; purpose: string; version: number; consentDays: number; active: boolean; published: boolean;
  checks: { questionCode: string; required: boolean; document: DocumentRequirement }[];
};
export type AssistedChallenge = { caseId: string; code?: string; phone: string; expiresAt: number; resendAt: number; message: string; mode?: string };
export type AgentCaseService = {
  list: () => Promise<AgentCase[]>;
  procedures: () => Promise<Procedure[]>;
  create: (applicantName: string, phone: string, procedureCode: string, channel: ConsentChannel, references: DocumentReferences) => Promise<AgentCase>;
  requestConsent: (id: string, channel: ConsentChannel) => Promise<AgentCase>;
  sendCode: (id: string, resend?: boolean) => Promise<AssistedChallenge>;
  verifyCode: (id: string, code: string) => Promise<void>;
  runChecks: (id: string) => Promise<AgentCase>;
};
