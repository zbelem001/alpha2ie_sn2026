"use client";

import { Bell, Check, ChevronDown, X } from "lucide-react";
import type { CitizenHomeData } from "@/features/citizen/mocks/home";
import { useBrowserClock } from "@/lib/use-browser-clock";
import { DocumentFields } from "@/components/shared/document-fields";
import { readDocumentProfile, saveDocumentProfile, type DocumentReferences } from "@/lib/document-references";
import { useState } from "react";
import { useDocumentProfile } from "@/lib/use-document-profile";
import { updateAuthorizationReferences, type DemoAuthorization } from "@/lib/demo-authorizations";
import styles from "@/features/citizen/styles/home.module.css";

type Request = NonNullable<CitizenHomeData["pendingRequest"]> & Partial<DemoAuthorization>;

export function AuthorizationRequest({ request, onDecision }: { request: Request; onDecision: (decision: "granted" | "refused") => void }) {
  const documents = request.documents ?? [];
  const profile = useDocumentProfile(request.phone);
  const [draft, setValues] = useState<DocumentReferences>({});
  const values = Object.fromEntries(documents.map((doc) => [doc.key, draft[doc.key] ?? request.references?.[doc.key] ?? profile[doc.key] ?? ""]));
  const [remember, setRemember] = useState(false); const [error, setError] = useState("");
  function grant() {
    try {
      if (request.phone && request.documents) {
        updateAuthorizationReferences(request.id, request.phone, values);
        if (remember) saveDocumentProfile(request.phone, { ...readDocumentProfile(request.phone), ...values });
      }
      setError(""); onDecision("granted");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Vérifiez les références."); }
  }
  const now = useBrowserClock();
  const minutes = request.requestedAt ? Math.max(0, Math.floor(((now || new Date(request.requestedAt).getTime()) - new Date(request.requestedAt).getTime()) / 60_000)) : 30;
  return <section className={styles.attention} aria-labelledby={`request-${request.id}`}>
    <div className={styles.requestNotification}><span>{minutes === 0 ? "À l’instant" : `Il y a ${minutes} minute${minutes === 1 ? "" : "s"}`}</span><Bell size={18} aria-label="Nouvelle demande" /></div>
    <details className={styles.requestDetails}>
      <summary><span className={styles.requestCopy}><span className={styles.actionLabel}>Demande d’autorisation</span><strong id={`request-${request.id}`}>{request.organization}</strong><span className={styles.requestPurpose}>Vérification de vos informations pour {request.purpose}.</span></span><span className={styles.reviewAction}>Répondre <ChevronDown size={17} aria-hidden="true" /></span></summary>
      <div className={styles.requestBody}><h3>Informations à vérifier</h3><ul>{request.checks.map((check) => <li key={check}><Check size={17} aria-hidden="true" />{check}</li>)}</ul><p className={styles.requestLimit}>Cet accord concerne uniquement cette démarche, pour {request.duration}.</p>{documents.length > 0 && <><h3>Références des documents concernés</h3><p>Complétez ou corrigez les références avant de donner votre accord. Vos références enregistrées sont préremplies.</p><DocumentFields prefix={request.id} requirements={documents} values={values} onChange={setValues} /><label><input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} /> Conserver ces références dans mon profil</label></>}{error && <p role="alert">{error}</p>}<div className={styles.decisions}><button className={styles.primary} type="button" onClick={grant}><Check size={18} aria-hidden="true" /> Je donne mon accord</button><button className={styles.secondary} type="button" onClick={() => onDecision("refused")}><X size={18} aria-hidden="true" /> Je refuse</button></div></div>
    </details>
  </section>;
}
