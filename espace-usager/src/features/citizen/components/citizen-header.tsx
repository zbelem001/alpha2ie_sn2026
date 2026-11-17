"use client";
import Image from "next/image";
import Link from "next/link";
import { CircleHelp, LogOut, UserRound } from "lucide-react";
import styles from "@/features/citizen/styles/home.module.css";

export function CitizenHeader({ profile = false, help, onHelp }: { profile?: boolean; help?: boolean; onHelp?: () => void }) {
  return <header className={styles.header}>
    <Link href="/usager" className={styles.brand} aria-label="Mon espace citoyen"><Image src="/Coat_of_arms_of_Burkina_Faso_(2025-present)%20(1).svg" alt="Armoiries du Burkina Faso" width={44} height={54} /><span><small>BURKINA FASO</small><strong>Dites-le-nous une fois</strong></span></Link>
    <div className={styles.headerActions}>
      {onHelp && <button type="button" className={styles.helpButton} aria-label="Besoin d’aide ?" aria-expanded={help} aria-controls="citizen-help" onClick={onHelp}><CircleHelp size={19} aria-hidden="true" /><span>Besoin d’aide ?</span></button>}
      <Link href="/usager/profil" className={styles.profileIcon} aria-label="Mon profil" title="Mon profil" aria-current={profile ? "page" : undefined}><UserRound size={22} aria-hidden="true" /></Link>
      <Link className={styles.exit} href="/" aria-label="Quitter et revenir à la connexion"><LogOut size={18} aria-hidden="true" /><span>Quitter</span></Link>
    </div>
  </header>;
}
