"use client";
import { useEffect, useState } from "react";
import { DocumentFields } from "@/components/shared/document-fields";
import { IdentityLinkForm, linkIdentity } from "@/features/citizen/components/identity-link-form";
import { DOCUMENT_TYPES, cleanReferences, profileDocumentTypes, type DocumentReferences } from "@/lib/document-references";
import { api } from "@/lib/api";
import styles from "@/features/citizen/styles/home.module.css";

type Profile = { linked: boolean; subject_ref: string | null; references: DocumentReferences };

// Références de documents enregistrées au profil (GET/PUT /v1/citizen/identifiers), chiffrées
// par l'API démarches. Toutes facultatives : elles sont jointes d'office aux prochaines démarches,
// pour que le registre retrouve une pièce précise. Les références masquées (profileDocumentTypes)
// gardent leur valeur enregistrée : l'enregistrement reprend tous les types.
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
  const byAct = Boolean(profile.subject_ref?.startsWith("ACTE:"));
  return <div className={styles.profilePanel}>
    {byAct
      ? <p>Compte rattaché à l’acte de naissance <strong>{profile.subject_ref}</strong>. Les administrations vous retrouvent par cet acte : <strong>tous les champs ci-dessous sont facultatifs</strong>. Une référence enregistrée est jointe d’office à vos prochaines démarches, pour retrouver une pièce précise.</p>
      : <p>Compte sans acte de naissance rattaché. <strong>Tous les champs ci-dessous sont facultatifs</strong>, mais sans référence, les administrations ne peuvent pas retrouver vos pièces : renseignez celles des démarches que vous faites.</p>}
    <form onSubmit={(e) => { e.preventDefault(); if (!busy) void save(); }}>
      <DocumentFields prefix="profile" requirements={profileDocumentTypes(profile.subject_ref)} values={values} onChange={setValues} disabled={busy} />
      <button className={styles.primary} type="submit" disabled={busy}>{busy ? "Enregistrement…" : "Enregistrer mon profil"}</button>
      <p role="status">{notice}</p>
    </form>
  </div>;
}
