"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { useEffect, useState } from "react";
import { getSession, logout } from "@/lib/api";
import { CaseWorkspace } from "@/modules/casework/components/case-workspace";
import { FlashInfo } from "@/components/shared/flash-info";
import styles from "@/modules/casework/styles/workspace.module.css";

// Libellés des administrations de démonstration (claim administration_code du jeton).
const ADMINISTRATIONS: Record<string, string> = {
  "BF/GOV/FONCTION-PUBLIQUE": "Fonction publique",
  "BF/GOV/DIPF/PASSEPORTS": "DIPF · Passeports",
};

export function AgentWorkspaceScreen() {
  const router = useRouter();
  const [workspaceKey, setWorkspaceKey] = useState(0);
  const [agent, setAgent] = useState({ name: "", service: "" });
  useEffect(() => {
    getSession().then((session) => {
      if (!session.authenticated || session.role !== "agent") { router.replace("/"); return; }
      const code = session.administrationCode ?? "";
      setAgent({ name: session.name, service: ADMINISTRATIONS[code] ?? code });
    }).catch(() => undefined);
  }, [router]);
  async function quit() {
    await logout().catch(() => undefined);
    router.replace("/");
  }
  return <div className={styles.page}>
    <FlashInfo />
    <header className={styles.header}><Link href="/guichet" className={styles.brand} onClick={(event) => { event.preventDefault(); setWorkspaceKey((value) => value + 1); }}><Image src="/Coat_of_arms_of_Burkina_Faso_(2025-present)%20(1).svg" alt="Armoiries du Burkina Faso" width={44} height={54} /><span><small>BURKINA FASO</small><strong>Dites-le-nous une fois</strong></span></Link><div className={styles.agentIdentity}><span>{agent.name}</span><strong>{agent.service}</strong></div><button className={styles.exit} type="button" onClick={quit} aria-label="Quitter le guichet"><LogOut size={18} aria-hidden="true" /><span>Quitter</span></button></header>
    <main className={styles.main} id="contenu">
      <div className={styles.accountLine}><span>Guichet agent</span><span>{agent.service}</span></div>
      <CaseWorkspace key={workspaceKey} />
    </main>
    <footer className={styles.footer}><span>{agent.service}</span><span>Démonstration · registres simulés, consentements et SMS simulés</span></footer>
  </div>;
}
