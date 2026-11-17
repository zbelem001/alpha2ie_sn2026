"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { Building2, CheckCircle2, Database, Files, History, LayoutDashboard, LogOut, ShieldCheck, Users, Workflow, X } from "lucide-react";
import { FlashInfo } from "@/components/shared/flash-info";
import { CaseWorkspace } from "@/modules/casework/components/case-workspace";
import { useCaseCount } from "@/modules/casework/hooks/use-case-count";
import { useAdministrationAudit, useDemoAdministration } from "@/lib/use-demo-administration";
import { LOCAL_ORGANIZATION, setDemoStaff } from "@/lib/demo-administration";
import { ProceduresPanel } from "@/features/administration/components/procedures-panel";
import { AgentsPanel } from "@/features/administration/components/agents-panel";
import { RightsPanel } from "@/features/administration/components/rights-panel";
import { RegistryPanel } from "@/features/administration/components/registry-panel";
import { AuditPanel } from "@/features/administration/components/audit-panel";
import type { AdminActionRunner } from "@/features/administration/types/actions";
import styles from "@/features/administration/styles/dashboard.module.css";

const navigation = [
  { id: "overview", title: "Vue d’ensemble", icon: LayoutDashboard, description: "L’activité et la configuration de votre administration." },
  { id: "cases", title: "Dossiers", icon: Files, description: "Les mêmes fonctions que le guichet agent." },
  { id: "procedures", title: "Démarches", icon: Workflow, description: "Définir les vérifications, leur ordre et leurs règles métier." },
  { id: "rights", title: "Droits d’échange", icon: ShieldCheck, description: "Demander et suivre les accès aux registres des autres administrations." },
  { id: "registry", title: "Registre et services", icon: Database, description: "Configurer votre connexion et les services que vous proposez au réseau." },
  { id: "agents", title: "Comptes agents", icon: Users, description: "Créer les comptes de votre service et gérer leur accès au guichet." },
  { id: "audit", title: "Historique des actions", icon: History, description: "Retrouver les actions des agents, de l’administrateur et les réponses des citoyens." },
] as const;
type Section = typeof navigation[number]["id"];

export function LocalAdminScreen() {
  const [section, setSection] = useState<Section>("overview");
  const [caseKey, setCaseKey] = useState(0);
  const [busy, setBusy] = useState(""); const [notice, setNotice] = useState(""); const [error, setError] = useState("");
  const config = useDemoAdministration(); const audit = useAdministrationAudit();
  const caseCount = useCaseCount();
  const current = navigation.find((item) => item.id === section)!;
  function open(next: Section) { setSection(next); setNotice(""); setError(""); if (next === "cases") setCaseKey((key) => key + 1); }
  const run: AdminActionRunner = async (name, action, success) => {
    if (busy) return false;
    setBusy(name); setNotice(""); setError("");
    try { await action(); setNotice(success); return true; }
    catch (cause) { setError(cause instanceof Error ? cause.message : "L’action n’a pas abouti."); return false; }
    finally { setBusy(""); }
  };
  return <div className={styles.page}>
    <FlashInfo />
    <header className={styles.header}><Link className={styles.brand} href="/administration" onClick={(e) => { e.preventDefault(); open("overview"); }}><Image src="/Coat_of_arms_of_Burkina_Faso_(2025-present)%20(1).svg" alt="Armoiries du Burkina Faso" width={43} height={53} /><span><small>BURKINA FASO</small><strong>Dites-le-nous une fois</strong></span></Link><span className={styles.headerRole}>Administrateur local <span>DIPF · Passeports</span></span><Link className={styles.exit} href="/" onClick={() => setDemoStaff(null)} aria-label="Quitter la console locale"><LogOut size={18} aria-hidden="true" /><span>Quitter</span></Link></header>
    <div className={styles.shell}>
      <aside className={styles.sidebar}><div className={styles.sidebarHeading}><Building2 size={20} aria-hidden="true" /><span>Administration locale<strong>DIPF · Passeports</strong></span></div><nav aria-label="Menu de l’administration">{navigation.map((item) => <button key={item.id} type="button" className={section === item.id ? styles.navActive : styles.navItem} aria-current={section === item.id ? "page" : undefined} disabled={Boolean(busy)} onClick={() => open(item.id)}><item.icon size={18} aria-hidden="true" /><span>{item.title}</span></button>)}</nav><div className={styles.sidebarFoot}>Console de démonstration<br />Aucune modification sur un service réel</div></aside>
      <main className={styles.main}>
        {section !== "cases" && <div className={styles.pageHeading}><span>ADMINISTRATION LOCALE</span><h1>{current.title}</h1><p>{current.description}</p></div>}
        {error && <div className={styles.error} role="alert"><p>{error}</p><button type="button" aria-label="Fermer l’erreur" onClick={() => setError("")}><X size={18} /></button></div>}
        {notice && <div className={styles.notice} role="status"><CheckCircle2 size={19} aria-hidden="true" /><p>{notice}</p><button type="button" aria-label="Fermer la confirmation" onClick={() => setNotice("")}><X size={18} /></button></div>}
        {section === "overview" && <>
          <div className={styles.summary}><div><strong>{caseCount}</strong><span>Dossiers enregistrés</span></div><div><strong>{config.procedures.filter((item) => item.active && item.published).length}</strong><span>Démarches actives</span></div><div><strong>{config.agents.filter((agent) => agent.active).length}</strong><span>Agents actifs</span></div><div><strong>{config.rights.filter((right) => right.status === "requested").length}</strong><span>Droits en attente</span></div></div>
          <div className={styles.overviewGrid}><section className={styles.block}><h2>Votre administration</h2><p className={styles.hint}>{LOCAL_ORGANIZATION.name}</p><dl className={styles.descriptionList}><div><dt>Registre local</dt><dd>{config.registry.url ? config.registry.name : "Connexion à configurer"}</dd></div><div><dt>Dernier test</dt><dd>{!config.registry.lastTest ? "Non effectué" : config.registry.lastTest.success ? "Disponible · test simulé" : "Indisponible · test simulé"}</dd></div><div><dt>Services fournisseurs</dt><dd>{config.offeredServices.filter((service) => service.active).length} actif(s)</dd></div></dl><div className={styles.formActions}><button className={styles.primary} type="button" onClick={() => open("cases")}>Accéder aux dossiers</button><button className={styles.secondary} type="button" onClick={() => open("registry")}>Configurer le registre</button></div></section><section className={styles.block}><h2>À suivre</h2><p className={styles.hint}>{config.procedures.filter((procedure) => !procedure.published).length} démarche(s) en brouillon.</p><p className={styles.hint}>{config.rights.filter((right) => right.status === "requested").length} demande(s) de droit en attente de validation.</p><p className={styles.footnote}>Les autorisations d’accès aux autres administrations dépendent des conventions du réseau.</p><button className={styles.textButton} type="button" onClick={() => open("rights")}>Voir les droits d’échange</button></section></div>
          <section className={styles.block}><div className={styles.editorHeading}><h2>Activité récente</h2><button className={styles.textButton} type="button" onClick={() => open("audit")}>Tout l’historique</button></div><AuditPanel entries={audit} compact /></section>
        </>}
        {section === "cases" && <CaseWorkspace key={caseKey} />}
        {section === "procedures" && <ProceduresPanel config={config} run={run} busy={Boolean(busy)} />}
        {section === "rights" && <RightsPanel config={config} run={run} busy={Boolean(busy)} />}
        {section === "registry" && <RegistryPanel key={config.registry.name + config.registry.url} config={config} run={run} busy={Boolean(busy)} />}
        {section === "agents" && <AgentsPanel config={config} run={run} busy={Boolean(busy)} />}
        {section === "audit" && <AuditPanel entries={audit} />}
      </main>
    </div>
  </div>;
}
