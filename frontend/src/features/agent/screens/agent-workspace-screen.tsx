"use client";

import Image from "next/image";
import Link from "next/link";
import { LogOut } from "lucide-react";
import { useState, useSyncExternalStore } from "react";
import { getDemoStaff, setDemoStaff, subscribeAdministration } from "@/lib/demo-administration";
import { CaseWorkspace } from "@/modules/casework/components/case-workspace";
import { FlashInfo } from "@/components/shared/flash-info";
import { agentDemo } from "@/modules/casework/mocks/catalogue";
import styles from "@/modules/casework/styles/workspace.module.css";

export function AgentWorkspaceScreen() {
  const [workspaceKey, setWorkspaceKey] = useState(0);
  const name = useSyncExternalStore(subscribeAdministration, () => getDemoStaff()?.name ?? agentDemo.name, () => agentDemo.name);
  return <div className={styles.page}>
    <FlashInfo />
    <header className={styles.header}><Link href="/guichet" className={styles.brand} onClick={(event) => { event.preventDefault(); setWorkspaceKey((value) => value + 1); }}><Image src="/Coat_of_arms_of_Burkina_Faso_(2025-present)%20(1).svg" alt="Armoiries du Burkina Faso" width={44} height={54} /><span><small>BURKINA FASO</small><strong>Dites-le-nous une fois</strong></span></Link><div className={styles.agentIdentity}><span>{name}</span><strong>{agentDemo.service}</strong></div><Link className={styles.exit} href="/" onClick={() => setDemoStaff(null)} aria-label="Quitter le guichet"><LogOut size={18} aria-hidden="true" /><span>Quitter</span></Link></header>
    <main className={styles.main}>
      <div className={styles.accountLine}><span>Guichet agent</span><span>DIPF · Passeports</span></div>
      <CaseWorkspace key={workspaceKey} />
    </main>
    <footer className={styles.footer}><span>{agentDemo.service}</span><span>Démonstration locale · registres, consentements et SMS simulés</span></footer>
  </div>;
}
