"use client";
import { useState } from "react";
import { DocumentFields } from "@/components/shared/document-fields";
import styles from "@/styles/document-fields.module.css";
import { readDocumentProfile, saveDocumentProfile, type DocumentReferences, type DocumentRequirement } from "@/lib/document-references";
export function RequestDocuments({ documents, initial, phone, onSave, allowProfile = false }: { documents: DocumentRequirement[]; initial: DocumentReferences; phone: string; onSave: (values: DocumentReferences) => void; allowProfile?: boolean }) {
  const [values, setValues] = useState(initial);
  const [remember, setRemember] = useState(false); const [notice, setNotice] = useState("");
  return <div className={styles.request}><DocumentFields requirements={documents} values={values} onChange={(next) => { setValues(next); setNotice(""); }} />
    {allowProfile && <><button type="button" onClick={() => { const profile = readDocumentProfile(phone); setValues(Object.fromEntries(documents.map((d) => [d.key, values[d.key] || profile[d.key] || ""]))); setNotice(""); }}>Utiliser mes références enregistrées</button><p><label><input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} /> Conserver aussi ces références dans mon profil</label></p></>}
    <button type="button" onClick={() => { try { onSave(values); if (remember) saveDocumentProfile(phone, { ...readDocumentProfile(phone), ...Object.fromEntries(documents.map((d) => [d.key, values[d.key] ?? ""])) }); setNotice("Références enregistrées pour cette demande."); } catch (cause) { setNotice(cause instanceof Error ? cause.message : "Vérifiez les références."); } }}>Enregistrer les références de cette demande</button><p role="status">{notice}</p>
  </div>;
}
