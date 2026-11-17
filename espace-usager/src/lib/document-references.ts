export const DOCUMENT_TYPES = [
  { key: "cnib", label: "Numéro de CNIB", provider: "ONI", hint: "Ex. fictif : CNIB-123456" },
  { key: "birth", label: "Référence de l’acte de naissance", provider: "État civil", hint: "Numéro, année et centre d’état civil si nécessaires" },
  { key: "nationality", label: "Numéro du certificat de nationalité", provider: "Justice", hint: "Référence du certificat dans le registre concerné" },
  { key: "criminal", label: "Numéro du casier judiciaire", provider: "Justice", hint: "Référence du bulletin dans le registre concerné" },
  { key: "payment", label: "Référence du timbre fiscal", provider: "Trésor", hint: "Numéro du reçu ou de la transaction" },
  { key: "loss", label: "Numéro de déclaration de perte", provider: "Police", hint: "Référence de la déclaration" },
] as const;
export type DocumentRequirement = { key: string; label: string; provider: string; hint: string };
export type DocumentReferences = Record<string, string>;
export function documentForQuestion(code: string): DocumentRequirement {
  const keys: Record<string, string> = { passport_cnib_valid: "cnib", passport_birth_act_found: "birth", passport_nationality: "nationality", passport_criminal_record_current: "criminal", passport_fiscal_stamp_paid: "payment", loss_declared: "loss" };
  return { ...DOCUMENT_TYPES.find((item) => item.key === keys[code])! };
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
const profileKey = (phone: string) => "dlnuf:demo:documents:" + phone;
export function readDocumentProfile(phone: string): DocumentReferences {
  try { return JSON.parse(localStorage.getItem(profileKey(phone)) ?? "{}"); } catch { return {}; }
}
export function saveDocumentProfile(phone: string, values: DocumentReferences) {
  localStorage.setItem(profileKey(phone), JSON.stringify(cleanReferences([...DOCUMENT_TYPES], values, false)));
  window.dispatchEvent(new Event("dlnuf-demo-documents"));
}
