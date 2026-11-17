"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { CheckCircle2, Clock3, Send, ShieldCheck } from "lucide-react";
import { CaseStatusBadge } from "@/modules/casework/components/case-status";
import type { AgentCase, AssistedChallenge, CheckStatus, ConsentChannel } from "@/modules/casework/types/cases";
import type { DemoAuthorization } from "@/lib/demo-authorizations";
import { useBrowserClock } from "@/lib/use-browser-clock";
import styles from "@/modules/casework/styles/workspace.module.css";

const checkLabels: Record<CheckStatus, string> = { queued: "Non lancé", confirmed: "Oui", rejected: "Non", ambiguous: "Identité ambiguë", not_found: "Introuvable", unavailable: "Indisponible", blocked: "Accès bloqué", error: "À reprendre" };

export function CaseDetail({ item, authorization, challenge, busy, focusSection, onSendCode, onVerifyCode, onChangeChannel, onRunChecks }: {
  item: AgentCase; authorization?: DemoAuthorization; challenge: AssistedChallenge | null; busy: string;
  focusSection?: "consent" | "checks";
  onSendCode: (resend?: boolean) => Promise<void>; onVerifyCode: (code: string) => Promise<void>;
  onChangeChannel: (channel: ConsentChannel) => Promise<void>; onRunChecks: () => Promise<void>;
}) {
  const [code, setCode] = useState("");
  useEffect(() => {
    if (!focusSection) return;
    const frame = requestAnimationFrame(() => document.getElementById(focusSection === "consent" ? "consent-title" : "checks-title")?.focus());
    return () => cancelAnimationFrame(frame);
  }, [focusSection]);
  const now = useBrowserClock();
  const consentGranted = now > 0 && authorization?.status === "granted" && Boolean(authorization.expiresAt) && new Date(authorization.expiresAt!).getTime() > now;
  const consentRefused = authorization?.status === "refused";
  const consentExpired = now > 0 && authorization?.status === "granted" && !consentGranted;
  const resendIn = challenge ? Math.max(0, Math.ceil((challenge.resendAt - (now || challenge.resendAt - 30_000)) / 1000)) : 0;
  const hasUnavailable = item.checks.some((check) => check.status === "unavailable");
  const canRun = consentGranted && item.status !== "completed" && item.checks.some((check) => ["queued", "unavailable", "error", "blocked"].includes(check.status));
  async function submit(e: FormEvent) { e.preventDefault(); if (!busy) await onVerifyCode(code); }

  return <>
    <div className={styles.caseOverview}><div><span className={styles.smallLabel}>Dossier {item.reference} · démarche v{item.procedureVersion}</span><h2>{item.procedureTitle}</h2><p>Identifiant citoyen : {item.citizenId} · Téléphone : {item.phone.match(/.{1,2}/g)?.join(" ")}</p></div><CaseStatusBadge item={item} authorization={authorization} /></div>
    <div className={styles.detailGrid}>
      <section className={styles.consentPanel} aria-labelledby="consent-title">
        <div className={styles.panelTitle}><ShieldCheck size={19} aria-hidden="true" /><h3 id="consent-title" tabIndex={-1}>Accord du citoyen</h3></div>
        <p className={styles.hint}>{item.procedurePurpose}</p>
        {consentGranted ? <><p className={styles.granted}><CheckCircle2 size={18} aria-hidden="true" /> Accord reçu {authorization?.channel === "assisted" ? "au guichet" : "depuis le portail citoyen"}</p><p className={styles.hint}>Limité aux vérifications de ce dossier, pour {item.consentDays} jours.</p></> : consentRefused ? <><p className={styles.refused}>Le citoyen a refusé cette demande.</p><p className={styles.hint}>Aucune consultation ne peut être lancée pour ce dossier.</p></> : consentExpired ? <><p className={styles.refused}>L’accord a expiré.</p><p className={styles.hint}>Un nouvel accord est nécessaire avant de poursuivre.</p>{item.status !== "completed" && <button className={styles.secondary} type="button" disabled={Boolean(busy)} onClick={() => onChangeChannel(item.channel)}>Demander un nouvel accord</button>}</> : <>
          <p className={styles.hint}>L’accord porte sur les {item.checks.length} vérifications de ce dossier. L’agent accompagne le citoyen ; il ne répond pas à sa place.</p>
          {item.channel === "assisted" ? <>
            <p className={styles.channelLabel}>Sur place, au guichet</p>
            {!challenge ? <><p className={styles.hint}>Expliquez les vérifications au citoyen, puis adressez le code à son numéro de contact associé.</p><button className={styles.primary} type="button" disabled={Boolean(busy)} onClick={() => onSendCode()}><Send size={16} aria-hidden="true" />{busy === "code" ? "Envoi…" : "Envoyer le code d’accord"}</button></> : <>
              <p className={styles.hint}>Code demandé au numéro {challenge.phone.slice(0, 2)} ** ** {challenge.phone.slice(-2)}. Le citoyen vous le communique uniquement s’il accepte. Ne demandez jamais son PIN personnel.</p>
              <form onSubmit={submit} noValidate className={styles.codeForm}>
                <label className={styles.label} htmlFor="consent-code">Code communiqué par le citoyen</label>
                <input className={`${styles.input} ${styles.codeInput}`} id="consent-code" name="consent_code" type="text" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code} placeholder="000000" disabled={Boolean(busy)} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))} />
                <button className={styles.primary} type="submit" disabled={Boolean(busy) || code.length !== 6}>{busy === "verify" ? "Vérification…" : "Valider le code"}</button>
              </form>
              <button className={styles.textButton} type="button" disabled={Boolean(busy) || resendIn > 0} onClick={() => { setCode(""); void onSendCode(true); }}>{resendIn > 0 ? `Renvoyer dans ${resendIn} s` : "Renvoyer un code"}</button>
              <details className={styles.demoTools}><summary>SMS de démonstration · aucun envoi réel</summary><p>{challenge.message}</p><p>Code de ce dossier : <strong data-demo-code={challenge.code}>{challenge.code}</strong></p></details>
            </>}
            <button className={styles.textButton} type="button" disabled={Boolean(busy)} onClick={() => onChangeChannel("web")}>Le citoyen répondra à distance</button>
          </> : <>
            <p className={styles.channelLabel}><Clock3 size={17} aria-hidden="true" /> En attente de sa réponse</p>
            <p className={styles.hint}>La demande est disponible dans son espace citoyen. Les vérifications restent bloquées jusqu’à son accord.</p>
            <button className={styles.textButton} type="button" disabled={Boolean(busy)} onClick={() => onChangeChannel("assisted")}>Le citoyen est maintenant au guichet</button>
          </>}
        </>}
      </section>

      <section className={styles.checkPanel} aria-labelledby="checks-title">
        <div className={styles.panelTitle}><h3 id="checks-title" tabIndex={-1}>Vérifications du dossier</h3><span>{item.checks.filter((check) => check.status === "confirmed").length} / {item.checks.length}</span></div>
        <ul className={styles.checks}>{item.checks.map((check) => <li key={check.questionCode}><div><strong>{check.label}</strong><span>{check.registry}{check.required ? "" : " \u00b7 Facultatif"}{check.attemptCount > 0 ? ` · ${check.attemptCount} tentative${check.attemptCount > 1 ? "s" : ""}` : ""}</span></div><span className={`${styles.checkResult} ${check.status === "confirmed" ? styles.success : ["rejected", "blocked", "error"].includes(check.status) ? styles.danger : styles.waiting}`}>{checkLabels[check.status]}</span></li>)}</ul>
        {hasUnavailable && <p className={styles.pendingNote}>Le dossier est conservé. Une reprise automatique est prévue ; vous pouvez aussi réessayer maintenant.</p>}
        {item.checks.some((check) => ["ambiguous", "not_found"].includes(check.status)) && <p className={styles.pendingNote}>Une identité ambiguë ou introuvable nécessite un examen humain. Ce résultat ne signifie pas « non ».</p>}
        {item.status === "completed" ? <p className={styles.completion}><CheckCircle2 size={18} aria-hidden="true" /> Vérifications terminées. L’examen des pièces physiques et la décision de délivrance restent à l’administration.</p> : <div className={styles.checkActions}><button className={styles.primary} type="button" disabled={Boolean(busy) || !canRun} onClick={onRunChecks}>{busy === "checks" || busy === "auto" ? "Vérifications…" : hasUnavailable ? "Reprendre les vérifications" : "Lancer les vérifications"}</button>{!consentGranted && <p className={styles.hint}>Accord citoyen requis avant tout appel aux registres.</p>}</div>}
      </section>
    </div>
    <details className={styles.demoTools}><summary>Tester la réponse à distance</summary><p>Dans un autre onglet de ce navigateur, connectez-vous avec le numéro associé au citoyen du dossier. La réponse sera visible ici automatiquement. Cet aperçu ne crée aucune authentification réelle.</p><Link href="/" target="_blank" rel="noopener noreferrer">Ouvrir l’entrée citoyenne dans un autre onglet</Link><p>Pour Awa : 11111111 / 0000. Les autres numéros passent par le parcours de première connexion.</p></details>
  </>;
}
