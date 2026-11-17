import { demoAgentCaseService } from "@/modules/casework/mocks/case-service";
import type { AgentCaseService } from "@/modules/casework/types/cases";

// Adaptateur de démonstration. L'API réelle exige un jeton agent Keycloak.
// L'OTP de consentement assisté nécessitera un endpoint de preuve dédié côté backend.
export const agentCaseService: AgentCaseService = demoAgentCaseService;
