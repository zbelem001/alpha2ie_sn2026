"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, LockKeyhole, UserRound } from "lucide-react";
import { AuthShell } from "@/features/auth/components/auth-shell";
import { login } from "@/lib/api";
import { SPACE } from "@/lib/space";

// Connexion par le compte Keycloak du realm dlnuf : la session (jetons) reste côté serveur.
export function LoginScreen() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (loading) return;
    if (!username.trim() || !password) { setError("Saisissez votre identifiant et votre mot de passe."); return; }
    setLoading(true); setError("");
    try {
      const session = await login(username.trim(), password);
      setPassword("");
      router.replace(session.home);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Connexion impossible. Réessayez.");
    } finally { setLoading(false); }
  }

  return (
    <AuthShell>
      <div className="login-heading">
        <h1 id="login-title" className="login-title">Connexion</h1>
        <p className="auth-description">Entrez l’identifiant et le mot de passe de votre compte.</p>
      </div>
      <div className="login-content">
        <form className="login-form" onSubmit={submit} noValidate>
          <div className="field-group">
            <label className="field-label" htmlFor="username">Identifiant</label>
            <div className={`field-wrapper${error ? " field-wrapper--error" : ""}`}>
              <UserRound className="field-icon" size={16} aria-hidden="true" />
              <input id="username" name="username" className="field-input" type="text" autoComplete="username" autoCapitalize="none" spellCheck={false}
                value={username} disabled={loading} onChange={(e) => { setUsername(e.target.value); setError(""); }} />
            </div>
          </div>
          <div className="field-group">
            <label className="field-label" htmlFor="password">Mot de passe</label>
            <div className={`field-wrapper${error ? " field-wrapper--error" : ""}`}>
              <LockKeyhole className="field-icon" size={16} aria-hidden="true" />
              <input id="password" name="password" className="field-input" type="password" autoComplete="current-password"
                value={password} disabled={loading} onChange={(e) => { setPassword(e.target.value); setError(""); }} />
            </div>
          </div>
          {error && <p className="form-error access-form-error" role="alert">{error}</p>}
          <button type="submit" className="login-button" disabled={loading} aria-busy={loading}>
            <span>{loading ? "PATIENTEZ…" : "SE CONNECTER"}</span>
            <span className="login-button-arrow"><ArrowRight size={20} aria-hidden="true" /></span>
          </button>
        </form>
        <p className="auth-demo">Comptes de démonstration : {SPACE.demoAccounts.map((account, index) => <span key={account.username}>{index > 0 ? " · " : ""}{account.label} : <strong>{account.username}</strong> / {account.password}</span>)}</p>
      </div>
    </AuthShell>
  );
}
