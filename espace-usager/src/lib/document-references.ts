export const DOCUMENT_TYPES = [
  { key: "cnib", label: "Numéro de CNIB", provider: "ONI", hint: "Référence inscrite sur la pièce CNIB" },
  { key: "nationality", label: "Référence du certificat de nationalité", provider: "Justice", hint: "Référence du certificat de nationalité" },
  { key: "criminal", label: "Référence du casier judiciaire", provider: "Justice", hint: "Référence du bulletin de casier judiciaire" },
] as const;
export type DocumentRequirement = { key: string; label: string; provider: string; hint: string };
export type DocumentReferences = Record<string, string>;
export function documentForQuestion(code: string): DocumentRequirement {
  const keys: Record<string, string> = {
    candidate_nationality: "nationality",
    criminal_record_indicator: "criminal",
    passport_cnib_valid: "cnib",
    passport_nationality: "nationality",
    passport_criminal_record_current: "criminal",
  };
  const key = keys[code];
  const requirement = DOCUMENT_TYPES.find((item) => item.key === key);
  return requirement ? { ...requirement } : { key: "birth", label: "Référence du document", provider: "Administration", hint: "Référence unique du document requis" };
}
/**
 * Références proposées au profil du citoyen.
 * Compte rattaché à un acte (ACTE:…) : les registres le retrouvent par cet acte ; la référence de
 * l'acte ferait doublon, et aucune démarche ne demande la déclaration de perte.
 */
export function profileDocumentTypes(subjectRef: string | null): DocumentRequirement[] {
  const hidden = subjectRef?.startsWith("ACTE:") ? new Set(["birth", "loss"]) : new Set<string>();
  return DOCUMENT_TYPES.filter((doc) => !hidden.has(doc.key));
}
export function requirementsFor(checks: { questionCode: string; document?: DocumentRequirement }[]) {
  return [...new Map(checks.map((check) => { const doc = check.document ?? documentForQuestion(check.questionCode); return [doc.key, doc]; })).values()];
}
export function cleanReferences(requirements: DocumentRequirement[], values: DocumentReferences, requireAll = true) {
  const result: DocumentReferences = {};
  for (const doc of requirements) {
    const value = (values[doc.key] ?? "").trim();
    if (requireAll && !value) throw new Error("Renseignez : " + doc.label + ".");
    if (value.length > 160 || /[\u0000-\u001f]/.test(value)) throw new Error("Référence invalide : " + doc.label + ".");
    if (value) result[doc.key] = value;
  }
  return result;
}
