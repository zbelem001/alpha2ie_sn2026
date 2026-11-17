"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthShell } from "@/features/auth/components/auth-shell";
import { authenticateDemoCitizen } from "@/features/auth/mocks/login";
import { useState, type ChangeEvent, type FormEvent } from "react";
import { ArrowRight, Eye, EyeOff, LockKeyhole, Phone } from "lucide-react";

type Errors = {
  phone?: string;
  pin?: string;
  form?: string;
};

export function LoginScreen() {
  const router = useRouter();
  const [phone, setPhone] = useState("");
  const [pin, setPin] = useState("");
  const [showPin, setShowPin] = useState(false);
  const [remember, setRemember] = useState(true);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Errors>({});

  const handlePhoneChange = (e: ChangeEvent<HTMLInputElement>) => {
    // Numéro national : huit chiffres, avec espaces facultatifs.
    setPhone(e.target.value.replace(/[^\d\s]/g, ""));
    setErrors((prev) => ({ ...prev, phone: undefined, form: undefined }));
  };

  const handlePinChange = (e: ChangeEvent<HTMLInputElement>) => {
    // Le PIN est strictement numérique
    setPin(e.target.value.replace(/\D/g, "").slice(0, 6));
    setErrors((prev) => ({ ...prev, pin: undefined, form: undefined }));
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (loading) return;

    const next: Errors = {};
    if (!/^\d{8}$/.test(phone.replace(/\s/g, ""))) {
      next.phone = "Entrez un numéro de téléphone à 8 chiffres.";
    }
    if (pin.length < 4) {
      next.pin = "Le code PIN doit contenir au moins 4 chiffres.";
    }

    setErrors(next);
    if (Object.keys(next).length > 0) return;

    setLoading(true);
    try {
      const valid = await authenticateDemoCitizen(phone, pin);
      if (!valid) {
        setErrors({ form: "Numéro de téléphone ou code PIN incorrect." });
        return;
      }
      setPin("");
      router.replace("/usager");
    } catch {
      setErrors({ form: "Connexion impossible. Veuillez réessayer." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell>
          <div className="login-heading">
            <h1 id="login-title" className="login-title">Connexion</h1>
            <p className="login-subtitle">
              Heureux de vous revoir. Entrez vos identifiants pour continuer.
            </p>
          </div>

          <div className="login-content">
            <form className="login-form" onSubmit={handleSubmit} noValidate>
              {/* Téléphone */}
              <div className="field-group">
                <label className="field-label" htmlFor="phone">
                  Numéro de téléphone
                </label>
                <div
                  className={`field-wrapper${errors.phone ? " field-wrapper--error" : ""}`}
                >
                  <Phone
                    aria-hidden="true"
                    className="field-icon"
                    size={16}
                    strokeWidth={1.8}
                  />
                  <input
                    id="phone"
                    name="phone"
                    type="tel"
                    inputMode="numeric"
                    autoComplete="tel-national"
                    placeholder="00 00 00 00"
                    className="field-input"
                    value={phone}
                    onChange={handlePhoneChange}
                    aria-invalid={Boolean(errors.phone)}
                    aria-describedby={errors.phone ? "phone-error" : undefined}
                  />
                </div>
                {errors.phone && (
                  <p id="phone-error" className="field-error" role="alert">
                    {errors.phone}
                  </p>
                )}
              </div>

              {/* Code PIN */}
              <div className="field-group">
                <label className="field-label" htmlFor="pin">
                  Code PIN
                </label>
                <div
                  className={`field-wrapper${errors.pin ? " field-wrapper--error" : ""}`}
                >
                  <LockKeyhole
                    aria-hidden="true"
                    className="field-icon"
                    size={16}
                    strokeWidth={1.8}
                  />
                  <input
                    id="pin"
                    name="pin"
                    type={showPin ? "text" : "password"}
                    inputMode="numeric"
                    autoComplete="current-password"
                    maxLength={6}
                    placeholder="••••"
                    className="field-input field-input--pin"
                    value={pin}
                    onChange={handlePinChange}
                    aria-invalid={Boolean(errors.pin)}
                    aria-describedby={errors.pin ? "pin-error" : undefined}
                  />
                  <button
                    type="button"
                    className="visibility-button"
                    aria-label={
                      showPin ? "Masquer le code PIN" : "Afficher le code PIN"
                    }
                    aria-pressed={showPin}
                    onClick={() => setShowPin((visible) => !visible)}
                  >
                    {showPin ? (
                      <EyeOff aria-hidden="true" size={16} strokeWidth={1.8} />
                    ) : (
                      <Eye aria-hidden="true" size={16} strokeWidth={1.8} />
                    )}
                  </button>
                </div>
                {errors.pin && (
                  <p id="pin-error" className="field-error" role="alert">
                    {errors.pin}
                  </p>
                )}
              </div>

              {/* Se souvenir / oublié */}
              <div className="form-row">
                <label className="remember">
                  <input
                    type="checkbox"
                    checked={remember}
                    onChange={(e) => setRemember(e.target.checked)}
                  />
                  Se souvenir de moi
                </label>
                <a className="forgot-link" href="#forgot-pin">
                  Code PIN oublié ?
                </a>
              </div>

              {errors.form && (
                <p className="form-error" role="alert">
                  {errors.form}
                </p>
              )}

              <button type="submit" className="login-button" disabled={loading}>
                {loading ? (
                  <>
                    <span style={{ flex: 1, textAlign: "center" }}>
                      <span
                        className="spinner"
                        style={{ display: "inline-block", verticalAlign: "middle" }}
                        aria-hidden="true"
                      />
                    </span>
                    <span className="sr-only">Connexion en cours…</span>
                  </>
                ) : (
                  <>
                    <span>SE CONNECTER</span>
                    <span className="login-button-arrow">
                      <ArrowRight aria-hidden="true" size={20} strokeWidth={2} />
                    </span>
                  </>
                )}
              </button>
            </form>

            <p className="register-prompt">
              Vous n&apos;avez pas de compte ?{" "}
              <Link href="/inscription">S&apos;INSCRIRE</Link>
            </p>
          </div>
    </AuthShell>
  );
}
