"use client";
import type { DocumentReferences, DocumentRequirement } from "@/lib/document-references";
import styles from "@/styles/document-fields.module.css";
export function DocumentFields({ requirements, values, onChange, disabled = false, prefix = "document" }: { requirements: DocumentRequirement[]; values: DocumentReferences; onChange: (values: DocumentReferences) => void; disabled?: boolean; prefix?: string }) {
  return <div className={styles.fields}>{requirements.map((doc) => <label key={doc.key} htmlFor={prefix + "-" + doc.key}><strong>{doc.label}</strong><span>{doc.provider}</span><input id={prefix + "-" + doc.key} value={values[doc.key] ?? ""} maxLength={160} disabled={disabled} autoComplete="off" onChange={(e) => onChange({ ...values, [doc.key]: e.target.value })} /><small>{doc.hint}</small></label>)}</div>;
}
