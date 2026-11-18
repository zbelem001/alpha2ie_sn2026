"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { CheckCircle2, ChevronDown, X } from "lucide-react";
import { FlashInfo } from "@/components/shared/flash-info";
import { CitizenHeader } from "@/features/citizen/components/citizen-header";
import { AuthorizationRequest } from "@/features/citizen/components/authorization-request";
import { ConsentControl } from "@/features/citizen/components/consent-control";
import { ReportActions } from "@/features/citizen/components/report-actions";
import { useCitizenSpace, type CitizenCase } from "@/features/citizen/hooks/use-citizen-space";
import { getSession } from "@/lib/api";
import styles from "@/features/citizen/styles/home.module.css";

const dateFormat = new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short", year: "numeric", timeZone: "Africa/Ouagadougou" });
const timeFormat = new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit", timeZone: "Africa/Ouagadougou" });

const OUTCOMES: Record<string, string> = {
  confirmed: "Vérification confirmée",
  rejected: "Vérification non confirmée",
  unavailable: "Registre indisponible — aucune réponse obtenue",
  ambiguous: "Identité ambiguë — examen nécessaire",
  not_found: "Introuvable — examen nécessaire",
  blocked: "Vérification bloquée — aucun registre consulté",
  missing_identifier: "Référence manquante — aucun registre consulté",
};
const CHECK_RESULTS: Record<string, string> = { queued: "Pas encore vérifié", confirmed: "Oui", rejected: "Non", ambiguous: "À examiner", not_found: "À examiner", unavailable: "Registre indisponible", blocked: "Bloqué", error: "À reprendre" };

function caseStatus(item: CitizenCase) {
  if (item.consent.status === "refused") return "Vous avez refusé cette demande";
  if (item.consent.status === "revoked") return "Vous avez retiré votre accord";
  if (item.status === "completed") return "Vérifications terminées";
  if (item.consent.status === "pending") return item.channel === "assisted" ? "Accord à donner au guichet" : "En attente de votre accord";
  return "Vérifications en cours";
}

export function CitizenHomeScreen() {
  const space = useCitizenSpace();
  const [help, setHelp] = useState(false);
  const [notice, setNotice] = useState("");
  const [name, setName] = useState("");
  useEffect(() => { getSession().then((session) => { if (session.authenticated) setName(session.name); }).catch(() => undefined); }, []);

  async function respond(id: string, decision: "granted" | "refused") {
    await space.respond(id, decision);
    setNotice(decision === "granted" ? "Votre accord a été enregistré pour cette demande." : "Vous avez refusé cette demande. Aucune vérification ne sera autorisée par cet accord.");
  }

  return (
    <div className={styles.page}>
      <FlashInfo />
      <CitizenHeader help={help} onHelp={() => setHelp(!help)} />

      <main className={styles.main} id="contenu">
        <div className={styles.accountLine}><span>Espace citoyen</span><span>{name ? `Bonjour ${name}` : "Mon espace"}</span></div>

        {help && <aside className={styles.help} id="citizen-help"><strong>Comprendre une consultation</strong><p>Choisissez « Voir le détail » pour connaître l’information vérifiée et la raison de la consultation. Si une consultation vous semble inhabituelle, vous pouvez la signaler depuis son détail.</p></aside>}

        {space.expired && <p className={styles.notice} role="alert">Votre session a expiré. <Link href="/">Reconnectez-vous</Link>.</p>}
        {space.error && <p className={styles.notice} role="alert">{space.error}</p>}
        {notice && <div className={styles.notice} role="status"><CheckCircle2 size={20} aria-hidden="true" /><p>{notice}</p><button onClick={() => setNotice("")} type="button" aria-label="Fermer la confirmation"><X size={18} aria-hidden="true" /></button></div>}

        <div className={styles.profilePrompt}>
          <span>Faire une démarche</span>
          <Link className={styles.primary} href="/usager/demarches">Faire une démarche</Link>
        </div>

        {[...space.requests, ...space.atDesk].map((request) => <AuthorizationRequest key={request.id} request={request} onDecision={(decision) => respond(request.id, decision)} />)}


        {space.cases.length > 0 && <details className={styles.caseHistory} open><summary>Suivi de mes dossiers ({space.cases.length})</summary><section className={styles.journal} aria-labelledby="cases-title">
          <div className={styles.journalHeading}><h2 id="cases-title">Mes démarches</h2><span>{space.cases.length} démarche{space.cases.length === 1 ? "" : "s"}</span></div>
          <ol className={styles.entries}>
            {space.cases.map((item) => <li key={item.id}>
              <details className={styles.entry}>
                <summary>
                  <time className={styles.date} dateTime={item.createdAt}>{dateFormat.format(new Date(item.createdAt))}<span>{item.reference}</span></time>
                  <span className={styles.entryCopy}><strong>{item.procedureTitle}</strong><span>{item.requester} · {caseStatus(item)}</span></span>
                  <span className={styles.detailLink}><span>Voir le résultat</span><ChevronDown size={18} aria-hidden="true" /></span>
                </summary>
                <div className={styles.entryBody}>
                  <dl>{item.checks.map((check) => <div key={check.questionCode}><dt>{check.label}</dt><dd>{CHECK_RESULTS[check.status] ?? "À reprendre"}{check.required ? "" : " · facultatif"}</dd></div>)}</dl>
                  <ConsentControl item={item} onRevoke={async (caseId) => { await space.revokeConsent(caseId); setNotice("Votre accord est retiré : plus aucune vérification ne peut être faite avec cet accord."); }} />
                </div>
              </details>
            </li>)}
          </ol>
        </section></details>}
        <section className={styles.journal} aria-labelledby="journal-title">
          <div className={styles.journalHeading}><h2 id="journal-title">Historique des consultations</h2><span>{space.consultations.length} consultation{space.consultations.length === 1 ? "" : "s"}</span></div>
          <div className={styles.columnHead} aria-hidden="true"><span>Date</span><span>Administration et démarche</span><span>Détail</span></div>
          {space.loading ? <p className={styles.empty}>Chargement…</p> : space.consultations.length === 0 ? <p className={styles.empty}>Aucune consultation pour le moment.</p> : <ol className={styles.entries}>
            {space.consultations.map((entry) => <li key={entry.id}>
              <details className={styles.entry}>
                <summary>
                  <time className={styles.date} dateTime={entry.dateTime}>{dateFormat.format(new Date(entry.dateTime))}<span>{timeFormat.format(new Date(entry.dateTime))}</span></time>
                  <span className={styles.entryCopy}><strong>{entry.organization}</strong><span>{entry.information}</span></span>
                  <span className={styles.detailLink}><span>Voir le détail</span><ChevronDown size={18} aria-hidden="true" /></span>
                </summary>
                <div className={styles.entryBody}>
                  <dl><div><dt>Démarche</dt><dd>{entry.purpose}</dd></div><div><dt>Information</dt><dd>{entry.information}</dd></div><div><dt>Registre</dt><dd>{entry.source}</dd></div><div><dt>Autorisation</dt><dd>{entry.basis}</dd></div><div><dt>Résultat</dt><dd>{OUTCOMES[entry.outcome] ?? "Vérification à examiner"}</dd></div></dl>
                  <ReportActions entry={entry} reports={space.reports.filter((item) => item.consultationId === entry.id)} onReport={(kind) => space.report(entry.caseId, entry.id, kind)} />
                </div>
              </details>
            </li>)}
          </ol>}
        </section>

      </main>
      <footer className={styles.footer}><span>Dites-le-nous une fois</span><span>Services administratifs</span></footer>
    </div>
  );
}
