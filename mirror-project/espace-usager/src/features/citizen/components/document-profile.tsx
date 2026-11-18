"use client";
import { useEffect, useState } from "react";
import { DocumentFields } from "@/components/shared/document-fields";
import { IdentityLinkForm, linkIdentity } from "@/features/citizen/components/identity-link-form";
import { DOCUMENT_TYPES, cleanReferences, type DocumentReferences } from "@/lib/document-references";
import { api } from "@/lib/api";
import styles from "@/features/citizen/styles/home.module.css";

type Profile = { linked: boolean; subject_ref: string | null; references: DocumentReferences };

// Références de documents enregistrées au profil (GET/PUT /v1/citizen/identifiers), chiffrées
// par l'API démarches. Elles servent aux prochaines démarches si l'administration en a besoin.
export function DocumentProfile() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [values, setValues] = useState<DocumentReferences>({});
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  async function load() {
    try {
      const current = await api<Profile>("citizen/identifiers");
      setProfile(current); setValues(current.references ?? {});
    } catch (cause) { setNotice(cause instanceof Error ? cause.message : "Impossible de charger votre profil."); }
  }
  useEffect(() => { const first = setTimeout(load, 0); return () => clearTimeout(first); }, []);
  async function save() {
    setBusy(true); setNotice("");
    try {
      const references = cleanReferences([...DOCUMENT_TYPES], values, false);
      await api("citizen/identifiers", { method: "PUT", body: { confirmed: true, references } });
      setNotice("Votre profil est enregistré.");
      await load();
    } catch (cause) { setNotice(cause instanceof Error ? cause.message : "Vérifiez les références."); }
    finally { setBusy(false); }
  }
  if (!profile) return <div className={styles.profilePanel}><p role="status">{notice || "Chargement…"}</p></div>;
  if (!profile.linked) return <IdentityLinkForm onLink={async (proof) => { await linkIdentity(proof); await load(); }} />;
  return <div className={styles.profilePanel}>
    <p>Compte rattaché à l’acte de naissance <strong>{profile.subject_ref}</strong>.</p>
    <form onSubmit={(e) => { e.preventDefault(); if (!busy) void save(); }}>
      <DocumentFields prefix="profile" requirements={[...DOCUMENT_TYPES]} values={values} onChange={setValues} disabled={busy} />
      <button className={styles.primary} type="submit" disabled={busy}>{busy ? "Enregistrement…" : "Enregistrer mon profil"}</button>
      <p role="status">{notice}</p>
    </form>
  </div>;
}
