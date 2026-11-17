"use client";
import { useState } from "react";
import { DocumentFields } from "@/components/shared/document-fields";
import { DOCUMENT_TYPES, saveDocumentProfile, type DocumentReferences } from "@/lib/document-references";
import { useDocumentProfile } from "@/lib/use-document-profile";
import styles from "@/features/citizen/styles/home.module.css";
export function DocumentProfile({ phone }: { phone: string }) {
  const stored = useDocumentProfile(phone);
  const [draft, setValues] = useState<DocumentReferences | null>(null);
  const values = draft ?? stored;
  const [notice, setNotice] = useState("");
  return <div className={styles.profilePanel}><form onSubmit={(e) => { e.preventDefault(); try { saveDocumentProfile(phone, values); setNotice("Votre profil est enregistré."); } catch (cause) { setNotice(cause instanceof Error ? cause.message : "Vérifiez les références."); } }}><DocumentFields prefix="profile" requirements={[...DOCUMENT_TYPES]} values={values} onChange={setValues} /><button className={styles.primary} type="submit">Enregistrer mon profil</button><p role="status">{notice}</p></form></div>;
}
