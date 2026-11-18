"use client";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CircleHelp, LogOut } from "lucide-react";
import { logout } from "@/lib/api";
import styles from "@/features/citizen/styles/home.module.css";

export function CitizenHeader({ profile = false, help, onHelp }: { profile?: boolean; help?: boolean; onHelp?: () => void }) {
  const router = useRouter();
  async function quit() {
    await logout().catch(() => undefined);
    router.replace("/");
  }
  return <header className={styles.header}>
    <Link href="/usager" className={styles.brand} aria-label="Mon espace citoyen"><Image src="/Coat_of_arms_of_Burkina_Faso_(2025-present)%20(1).svg" alt="Armoiries du Burkina Faso" width={44} height={54} /><span><small>BURKINA FASO</small><strong>Dites-le-nous une fois</strong></span></Link>
    <nav className={styles.nav} aria-label="Espace citoyen">
      <Link href="/usager" className={styles.navLink} aria-current={profile ? undefined : "page"}>Mes consultations</Link>
      <Link href="/usager/profil" className={styles.navLink} aria-current={profile ? "page" : undefined}>Mon profil</Link>
    </nav>
    <div className={styles.headerActions}>
      {onHelp && <button type="button" className={styles.helpButton} aria-label="Besoin d’aide ?" aria-expanded={help} aria-controls="citizen-help" onClick={onHelp}><CircleHelp size={19} aria-hidden="true" /><span>Besoin d’aide ?</span></button>}
      <button className={styles.exit} type="button" onClick={quit} aria-label="Quitter et revenir à la connexion"><LogOut size={18} aria-hidden="true" /><span>Quitter</span></button>
    </div>
  </header>;
}
