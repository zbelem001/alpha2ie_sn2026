"use client";

import Link from "next/link";
import { ArrowLeft, Plus } from "lucide-react";
import { useAgentWorkspace } from "@/modules/casework/hooks/use-agent-workspace";
import { CaseList } from "@/modules/casework/components/case-list";
import { NewCaseForm } from "@/modules/casework/components/new-case-form";
import { CaseDetail } from "@/modules/casework/components/case-detail";
import styles from "@/modules/casework/styles/workspace.module.css";

export function CaseWorkspace() {
  const workspace = useAgentWorkspace();
  const { view, busy, selected } = workspace;
  if (workspace.expired) return <p className={styles.errorBanner} role="alert">Votre session a expiré. <Link href="/">Reconnectez-vous</Link>.</p>;
  return <>
      {view !== "list" && <button className={styles.back} type="button" disabled={Boolean(busy)} onClick={workspace.showList}><ArrowLeft size={17} aria-hidden="true" /> Retour aux dossiers</button>}
      <div className={styles.pageHeading}><div><h1>{view === "list" ? "Dossiers des citoyens" : view === "new" ? "Ouvrir un dossier" : "Suivi du dossier"}</h1><p>{view === "list" ? "Ouvrir un dossier, recueillir l’accord du citoyen et suivre ses vérifications." : view === "new" ? "Choisissez la démarche et les références des documents nécessaires." : "Chaque vérification est limitée à cette démarche et à l’accord donné."}</p></div>{view === "list" && <button type="button" className={styles.accent} onClick={workspace.showNew} disabled={Boolean(busy) || workspace.loading}><Plus size={18} aria-hidden="true" /> Nouveau dossier</button>}</div>
      {workspace.error && <p className={styles.errorBanner} role="alert">{workspace.error}</p>}
      {view === "list" && <CaseList cases={workspace.cases} loading={workspace.loading} onOpen={workspace.openCase} />}
      {view === "new" && <NewCaseForm busy={Boolean(busy)} procedures={workspace.procedures} onCreate={workspace.create} />}
      {view === "case" && selected && <CaseDetail key={selected.id} item={selected} challenge={workspace.challenge} busy={busy} focusSection={workspace.selectedSection} onSendCode={workspace.sendCode} onVerifyCode={workspace.verifyCode} onChangeChannel={workspace.changeChannel} onRunChecks={workspace.runChecks} />}
  </>;
}
