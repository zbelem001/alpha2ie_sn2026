import { documentForQuestion } from "@/lib/document-references";
import type { DemoCitizen, AgentCheck } from "@/modules/casework/types/cases";
import { DEFAULT_PROCEDURE, LOCAL_ORGANIZATION, LOCAL_QUESTIONS, type LocalProcedure } from "@/lib/demo-administration";

export const agentDemo = {
  name: "Agent de démonstration",
  administrationCode: LOCAL_ORGANIZATION.code,
  administration: LOCAL_ORGANIZATION.name,
  service: LOCAL_ORGANIZATION.service,
};
export const passportProcedure = {
  code: "passeport_ordinaire_precheck",
  owner: agentDemo.administrationCode,
  title: "Passeport ordinaire — demandeur majeur",
  checks: [
    { questionCode: "passport_cnib_valid", label: "CNIB enregistrée et valide", registry: "ONI" },
    { questionCode: "passport_birth_act_found", label: "Acte d’état civil retrouvé", registry: "État civil" },
    { questionCode: "passport_nationality", label: "Nationalité burkinabè confirmée", registry: "Justice" },
    { questionCode: "passport_criminal_record_current", label: "Bulletin de casier en cours de validité", registry: "Justice" },
    { questionCode: "passport_fiscal_stamp_paid", label: "Timbre fiscal payé", registry: "Trésor" },
  ],
};
export const demoCitizens: DemoCitizen[] = [
  { displayName: "Awa · profil fictif", phone: "11111111", scenario: "normal" },
  { displayName: "Issa · profil fictif", phone: "44444444", scenario: "unavailable" },
  { displayName: "Mariam · profil fictif", phone: "33333333", scenario: "ambiguous" },
];
export function newChecks(procedure: LocalProcedure = DEFAULT_PROCEDURE): AgentCheck[] {
  return procedure.checks.map((check) => {
    const definition = LOCAL_QUESTIONS.find((question) => question.code === check.questionCode)!;
    return { questionCode: definition.code, label: definition.label, registry: definition.provider, document: check.document ?? documentForQuestion(check.questionCode), required: check.required, status: "queued", result: null, attemptCount: 0 };
  });
}
