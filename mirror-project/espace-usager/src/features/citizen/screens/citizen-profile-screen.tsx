"use client";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { FlashInfo } from "@/components/shared/flash-info";
import { CitizenHeader } from "@/features/citizen/components/citizen-header";
import { DocumentProfile } from "@/features/citizen/components/document-profile";
import styles from "@/features/citizen/styles/home.module.css";

export function CitizenProfileScreen() {
  return <div className={styles.page}>
    <FlashInfo /><CitizenHeader profile />
    <main className={styles.main} id="contenu">
      <Link href="/usager" className={styles.profileBack}><ArrowLeft size={17} aria-hidden="true" /> Retour à mes consultations</Link>
      <div className={styles.profileIntro}><h1>Mon profil</h1><p>Mes références pour les prochaines demandes.</p></div>
      <DocumentProfile />
    </main>
    <footer className={styles.footer}><span>Dites-le-nous une fois</span><span>Registres et SMS simulés</span></footer>
  </div>;
}
