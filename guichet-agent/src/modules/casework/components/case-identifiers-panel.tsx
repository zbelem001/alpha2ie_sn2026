"use client";
import { useState, type FormEvent } from "react";
import { CheckCircle2 } from "lucide-react";
import { DocumentFields } from "@/components/shared/document-fields";
import { cleanReferences, type DocumentReferences } from "@/lib/document-references";
import type { AgentCase } from "@/modules/casework/types/cases";
import styles from "@/modules/casework/styles/workspace.module.css";

export function CaseIdentifiersPanel({ item, busy, onSave }: { item: AgentCase; busy: boolean; onSave: (references: DocumentReferences) => Promise<void> }) {
  const [values, setValues] = useState<DocumentReferences>({});
  const [error, setError] = useState("");
  const status = item.identifierStatus;
  async function save(event: FormEvent) {
    event.preventDefault();
    if (!status || busy) return;
    try { setError(""); await onSave(cleanReferences(status.missing, values)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Vérifiez les références."); }
  }
  if (!status) return null;
  return <section className={styles.consentPanel} aria-label="Références du citoyen">
    {status.complete ? <><p className={styles.granted}><CheckCircle2 size={19} /> Références complètes pour cette démarche</p><p className={styles.hint}>Les références sont prêtes. Cliquez sur « Vérifier » pour interroger les registres.</p></> : <>
      <h3>Références à compléter</h3><p className={styles.hint}>Accord reçu. Demandez au citoyen uniquement les références manquantes ci-dessous.</p>
      <form onSubmit={save} noValidate>
        <DocumentFields requirements={status.missing} values={values} onChange={setValues} disabled={busy} prefix="missing-reference" />
        {error && <p className={styles.errorText} role="alert">{error}</p>}
        <button className={styles.primary} type="submit" disabled={busy}>Enregistrer les références</button>
      </form>
    </>}
  </section>;
}
