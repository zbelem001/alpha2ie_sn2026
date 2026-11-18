"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Building2, CheckCircle2, Database, Files, History, LayoutDashboard, LogOut, Users, Workflow, X } from "lucide-react";
import { FlashInfo } from "@/components/shared/flash-info";
import { CaseWorkspace } from "@/modules/casework/components/case-workspace";
import { useRouter } from "next/navigation";
import { api, getSession, logout } from "@/lib/api";
import { getAdministration, getAdministrationAudit, type LocalAdministration, type AdminAuditEntry } from "@/lib/administration-api";
import { ProceduresPanel } from "@/features/administration/components/procedures-panel";
import { AgentsPanel } from "@/features/administration/components/agents-panel";
import { RegistryPanel } from "@/features/administration/components/registry-panel";
import { AuditPanel } from "@/features/administration/components/audit-panel";
import type { AdminActionRunner } from "@/features/administration/types/actions";
import styles from "@/features/administration/styles/dashboard.module.css";

const navigation = [
  { id: "overview", title: "Vue d’ensemble", icon: LayoutDashboard, description: "L’activité et la configuration de votre administration." },
  { id: "cases", title: "Dossiers", icon: Files, description: "Les mêmes fonctions que le guichet agent." },
  { id: "procedures", title: "Démarches", icon: Workflow, description: "Définir les vérifications, leur ordre et leurs règles métier." },
  { id: "registry", title: "Services", icon: Database, description: "Gérer les services proposés par votre administration." },
  { id: "agents", title: "Comptes agents", icon: Users, description: "Créer les comptes de votre service et gérer leur accès au guichet." },
  { id: "audit", title: "Historique des actions", icon: History, description: "Retrouver les actions des agents, de l’administrateur et les réponses des citoyens." },
] as const;
type Section = typeof navigation[number]["id"];

export function LocalAdminScreen() {
  const [section, setSection] = useState<Section>("overview");
  const [caseKey, setCaseKey] = useState(0);
  const [busy, setBusy] = useState(""); const [notice, setNotice] = useState(""); const [error, setError] = useState("");
  const router = useRouter();
  const [config, setConfig] = useState<LocalAdministration | null>(null);
  const [audit, setAudit] = useState<AdminAuditEntry[]>([]);
  const [caseCount, setCaseCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    const session = await getSession();
    if (!session.authenticated || session.role !== "local-admin") throw new Error("Acces reserve a un administrateur de votre administration.");
    const [configuration, entries, cases] = await Promise.all([getAdministration(), getAdministrationAudit(), api<unknown[]>("cases")]);
    setConfig(configuration); setAudit(entries); setCaseCount(cases.length);
  }, []);
  useEffect(() => { let active = true; const timer = setTimeout(() => { void load().catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Chargement impossible."); }).finally(() => { if (active) setLoading(false); }); }, 0); return () => { active = false; clearTimeout(timer); }; }, [load]);
  const current = navigation.find((item) => item.id === section)!;
  function open(next: Section) { void load().catch((cause) => setError(cause instanceof Error ? cause.message : "Chargement impossible.")); setSection(next); setNotice(""); setError(""); if (next === "cases") setCaseKey((key) => key + 1); }
  const run: AdminActionRunner = async (name, action, success) => {
    if (busy) return false;
    setBusy(name); setNotice(""); setError("");
    try { await action(); await load(); setNotice(success); return true; }
    catch (cause) { setError(cause instanceof Error ? cause.message : "L’action n’a pas abouti."); return false; }
    finally { setBusy(""); }
  };
  if (!config) return <div className={styles.page}><FlashInfo /><main className={styles.main}><h1>Administration</h1>{error ? <p role="alert">{error}</p> : <p role="status">{loading ? "Chargement..." : "Configuration indisponible."}</p>}<Link href="/">Retour a la connexion</Link></main></div>;
  return <div className={styles.page}>
    <FlashInfo />
    <header className={styles.header}><Link className={styles.brand} href="/administration" onClick={(e) => { e.preventDefault(); open("overview"); }}><Image src="/Coat_of_arms_of_Burkina_Faso_(2025-present)%20(1).svg" alt="Armoiries du Burkina Faso" width={43} height={53} /><span><small>BURKINA FASO</small><strong>Dites-le-nous une fois</strong></span></Link><span className={styles.headerRole}>Administrateur local <span>{config.administration.name}</span></span><Link className={styles.exit} href="/" onClick={async (event) => { event.preventDefault(); await logout().catch(() => undefined); router.replace("/"); }} aria-label="Quitter la console locale"><LogOut size={18} aria-hidden="true" /><span>Quitter</span></Link></header>
    <div className={styles.shell}>
      <aside className={styles.sidebar}><div className={styles.sidebarHeading}><Building2 size={20} aria-hidden="true" /><span>Administration locale<strong>{config.administration.name}</strong></span></div><nav aria-label="Menu de l’administration">{navigation.map((item) => <button key={item.id} type="button" className={section === item.id ? styles.navActive : styles.navItem} aria-current={section === item.id ? "page" : undefined} disabled={Boolean(busy)} onClick={() => open(item.id)}><item.icon size={18} aria-hidden="true" /><span>{item.title}</span></button>)}</nav><div className={styles.sidebarFoot}>Configuration de votre administration</div></aside>
      <main className={styles.main}>
        {section !== "cases" && <div className={styles.pageHeading}><span>ADMINISTRATION LOCALE</span><h1>{current.title}</h1><p>{current.description}</p></div>}
        {error && <div className={styles.error} role="alert"><p>{error}</p><button type="button" aria-label="Fermer l’erreur" onClick={() => setError("")}><X size={18} /></button></div>}
        {notice && <div className={styles.notice} role="status"><CheckCircle2 size={19} aria-hidden="true" /><p>{notice}</p><button type="button" aria-label="Fermer la confirmation" onClick={() => setNotice("")}><X size={18} /></button></div>}
        {section === "overview" && <>
          <div className={styles.summary}><div><strong>{caseCount}</strong><span>Dossiers récents</span></div><div><strong>{config.procedures.filter((item) => item.active && item.published).length}</strong><span>Démarches actives</span></div><div><strong>{config.agents.filter((agent) => agent.active).length}</strong><span>Agents actifs</span></div></div>
          <div className={styles.overviewGrid}><section className={styles.block}><h2>Votre administration</h2><p className={styles.hint}>{config.administration.name}</p><dl className={styles.descriptionList}><div><dt>Services proposés</dt><dd>{config.offeredServices.filter((service) => service.active).length} actif(s)</dd></div></dl><div className={styles.formActions}><button className={styles.primary} type="button" onClick={() => open("cases")}>Accéder aux dossiers</button><button className={styles.secondary} type="button" onClick={() => open("registry")}>Gérer les services</button></div></section><section className={styles.block}><h2>À suivre</h2><p className={styles.hint}>{config.procedures.filter((procedure) => !procedure.published).length} démarche(s) en brouillon.</p><p className={styles.footnote}>Les besoins d’information sont configurés directement dans chaque démarche.</p></section></div>
          <section className={styles.block}><div className={styles.editorHeading}><h2>Activité récente</h2><button className={styles.textButton} type="button" onClick={() => open("audit")}>Tout l’historique</button></div><AuditPanel entries={audit} compact /></section>
        </>}
        {section === "cases" && <CaseWorkspace key={caseKey} />}
        {section === "procedures" && <ProceduresPanel error={error} config={config} run={run} busy={Boolean(busy)} />}
        {section === "registry" && <RegistryPanel error={error} key={config.registry.name + config.registry.url} config={config} run={run} busy={Boolean(busy)} />}
        {section === "agents" && !config.agentManagementAvailable && <p className={styles.warning}>La gestion des agents doit etre configuree cote serveur.</p>}
        {section === "agents" && config.agentManagementAvailable && <AgentsPanel config={config} run={run} busy={Boolean(busy)} />}
        {section === "audit" && <AuditPanel entries={audit} />}
      </main>
    </div>
  </div>;
}
