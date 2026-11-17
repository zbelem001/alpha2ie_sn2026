"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { Bell, Check, CheckCircle2, ChevronDown, CircleHelp, LogOut, X } from "lucide-react";
import { FlashInfo } from "@/components/shared/flash-info";
import { citizenHomeDemo, type CitizenHomeData } from "@/features/citizen/mocks/home";
import styles from "@/features/citizen/styles/home.module.css";

export function CitizenHomeScreen({ data = citizenHomeDemo }: { data?: CitizenHomeData }) {
  const [decision, setDecision] = useState<"pending" | "granted" | "refused">("pending");
  const [help, setHelp] = useState(false);
  const [notice, setNotice] = useState("");
  const [reported, setReported] = useState<string[]>([]);
  const request = data.pendingRequest;
  const hasPendingRequest = request !== null && decision === "pending";

  function decide(next: "granted" | "refused") {
    setDecision(next);
    setNotice(next === "granted" ? "Votre accord a été enregistré pour cette demande." : "Vous avez refusé cette demande. Aucune vérification ne sera autorisée par cet accord.");
  }

  return (
    <div className={styles.page}>
      <FlashInfo />
      <header className={styles.header}>
        <Link href="/usager" className={styles.brand} aria-label="Mon espace citoyen">
          <Image src="/Coat_of_arms_of_Burkina_Faso_(2025-present)%20(1).svg" alt="Armoiries du Burkina Faso" width={44} height={54} />
          <span><small>BURKINA FASO</small><strong>Dites-le-nous une fois</strong></span>
        </Link>
        <div className={styles.headerActions}>
          <button type="button" className={styles.helpButton} aria-label="Besoin d’aide ?" aria-expanded={help} aria-controls="citizen-help" onClick={() => setHelp(!help)}><CircleHelp size={19} aria-hidden="true" /><span>Besoin d’aide ?</span></button>
          <Link className={styles.exit} href="/" aria-label="Quitter et revenir à la connexion"><LogOut size={18} aria-hidden="true" /><span>Quitter</span></Link>
        </div>
      </header>

      <main className={styles.main}>
        <div className={styles.accountLine}><span>Espace citoyen</span><span>Bonjour {data.firstName}</span></div>
        <div className={styles.intro}>
          <h1>Mes consultations</h1>
          <p>Qui a consulté mes informations, quand et pour quelle raison.</p>
        </div>

        {help && <aside className={styles.help} id="citizen-help"><strong>Comprendre une consultation</strong><p>Choisissez « Voir le détail » pour connaître l’information vérifiée et la raison de la consultation. Si une consultation vous semble inhabituelle, vous pouvez la signaler depuis son détail.</p></aside>}

        {notice && <div className={styles.notice} role="status"><CheckCircle2 size={20} aria-hidden="true" /><p>{notice}</p><button onClick={() => setNotice("")} type="button" aria-label="Fermer la confirmation"><X size={18} aria-hidden="true" /></button></div>}

        {hasPendingRequest && <section className={styles.attention} aria-labelledby="attention-title">
          <div className={styles.requestNotification}>
            <span>Il y a 30 minutes</span>
            <Bell size={18} aria-label="Nouvelle demande" />
          </div>
          <details className={styles.requestDetails}>
            <summary>
              <span className={styles.requestCopy}>
                <span className={styles.actionLabel}>Demande d’autorisation</span>
                <strong id="attention-title">{request.organization}</strong>
                <span className={styles.requestPurpose}>Vérification de vos informations pour {request.purpose}.</span>
              </span>
              <span className={styles.reviewAction}>Répondre <ChevronDown size={17} aria-hidden="true" /></span>
            </summary>
            <div className={styles.requestBody}>
              <h3>Informations à vérifier</h3>
              <ul>{request.checks.map((check) => <li key={check}><Check size={17} aria-hidden="true" />{check}</li>)}</ul>
              <p className={styles.requestLimit}>Cet accord concerne uniquement cette démarche, pour {request.duration}.</p>
              <div className={styles.decisions}>
                <button className={styles.primary} type="button" onClick={() => decide("granted")}><Check size={18} aria-hidden="true" /> Je donne mon accord</button>
                <button className={styles.secondary} type="button" onClick={() => decide("refused")}><X size={18} aria-hidden="true" /> Je refuse</button>
              </div>
            </div>
          </details>
        </section>}

        <section className={styles.journal} aria-labelledby="journal-title">
          <div className={styles.journalHeading}><h2 id="journal-title">Historique des consultations</h2><span>{data.consultations.length} consultation{data.consultations.length === 1 ? "" : "s"}</span></div>
          <div className={styles.columnHead} aria-hidden="true"><span>Date</span><span>Administration et démarche</span><span>Détail</span></div>
          {data.consultations.length === 0 ? <p className={styles.empty}>Aucune administration n’a encore consulté vos informations.</p> : <ol className={styles.entries}>
            {data.consultations.map((entry) => <li key={entry.id}>
              <details className={styles.entry}>
                <summary>
                  <time className={styles.date} dateTime={entry.dateTime}>{entry.date}<span>{entry.time}</span></time>
                  <span className={styles.entryCopy}><strong>{entry.organization}</strong><span>{entry.purpose}</span></span>
                  <span className={styles.detailLink}><span>Voir le détail</span><ChevronDown size={18} aria-hidden="true" /></span>
                </summary>
                <div className={styles.entryBody}>
                  <dl><div><dt>Information vérifiée</dt><dd>{entry.information}</dd></div><div><dt>Registre consulté</dt><dd>{entry.source}</dd></div><div><dt>Autorisation utilisée</dt><dd>{entry.basis}</dd></div></dl>
                  <button className={styles.reportButton} type="button" disabled={reported.includes(entry.id)} onClick={() => setReported((old) => [...old, entry.id])}>{reported.includes(entry.id) ? "Signalement simulé" : "Je ne reconnais pas cette consultation"}</button>
                  {reported.includes(entry.id) && <p className={styles.reportNote} role="status">Ce signalement est une démonstration. Aucune administration n’a été contactée.</p>}
                </div>
              </details>
            </li>)}
          </ol>}
          <p className={styles.journalNote}>Les consultations les plus récentes apparaissent en premier.</p>
        </section>
      </main>
      <footer className={styles.footer}><span>Dites-le-nous une fois</span><span>Données de démonstration</span></footer>
    </div>
  );
}
