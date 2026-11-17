"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowLeft, LogOut, Plus } from "lucide-react";
import { FlashInfo } from "@/components/shared/flash-info";
import { useDemoAuthorizations } from "@/lib/use-demo-authorizations";
import { useAgentWorkspace } from "@/features/agent/hooks/use-agent-workspace";
import { agentDemo } from "@/features/agent/mocks/catalogue";
import { CaseList } from "@/features/agent/components/case-list";
import { NewCaseForm } from "@/features/agent/components/new-case-form";
import { CaseDetail } from "@/features/agent/components/case-detail";
import styles from "@/features/agent/styles/workspace.module.css";

export function AgentWorkspaceScreen() {
  const workspace = useAgentWorkspace();
  const authorizations = useDemoAuthorizations();
  const { view, busy, selected } = workspace;
  return <div className={styles.page}>
    <FlashInfo />
    <header className={styles.header}><Link href="/guichet" className={styles.brand} onClick={(e) => { e.preventDefault(); workspace.showList(); }}><Image src="/Coat_of_arms_of_Burkina_Faso_(2025-present)%20(1).svg" alt="Armoiries du Burkina Faso" width={44} height={54} /><span><small>BURKINA FASO</small><strong>Dites-le-nous une fois</strong></span></Link><div className={styles.agentIdentity}><span>{agentDemo.name}</span><strong>{agentDemo.service}</strong></div><Link className={styles.exit} href="/" aria-label="Quitter le guichet"><LogOut size={18} aria-hidden="true" /><span>Quitter</span></Link></header>
    <main className={styles.main}>
      <div className={styles.accountLine}><span>Guichet agent</span><span>DIPF · Passeports</span></div>
      {view !== "list" && <button className={styles.back} type="button" disabled={Boolean(busy)} onClick={workspace.showList}><ArrowLeft size={17} aria-hidden="true" /> Retour aux dossiers</button>}
      <div className={styles.pageHeading}><div><h1>{view === "list" ? "Dossiers des citoyens" : view === "new" ? "Ouvrir un dossier" : "Suivi du dossier"}</h1><p>{view === "list" ? "Ouvrir un dossier, recueillir l’accord du citoyen et suivre ses vérifications." : view === "new" ? "Identifiez le citoyen avant de préparer les vérifications de sa démarche." : "Chaque vérification est limitée à cette démarche et à l’accord donné."}</p></div>{view === "list" && <button type="button" className={styles.primary} onClick={workspace.showNew} disabled={Boolean(busy) || workspace.loading}><Plus size={18} aria-hidden="true" /> Nouveau dossier</button>}</div>
      {workspace.error && <p className={styles.errorBanner} role="alert">{workspace.error}</p>}
      {view === "list" && <CaseList cases={workspace.cases} authorizations={authorizations} loading={workspace.loading} onOpen={workspace.openCase} />}
      {view === "new" && <NewCaseForm busy={Boolean(busy)} onCreate={workspace.create} />}
      {view === "case" && selected && <CaseDetail key={selected.id} item={selected} authorization={authorizations.find((entry) => entry.id === selected.authorizationId)} challenge={workspace.challenge} busy={busy} focusSection={workspace.selectedSection} onSendCode={workspace.sendCode} onVerifyCode={workspace.verifyCode} onChangeChannel={workspace.changeChannel} onRunChecks={workspace.runChecks} />}
    </main>
    <footer className={styles.footer}><span>{agentDemo.service}</span><span>Démonstration locale · registres, consentements et SMS simulés</span></footer>
  </div>;
}
