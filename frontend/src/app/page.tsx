"use client";

import Image from "next/image";
import { useId, useState, type ChangeEvent, type FormEvent } from "react";
import { ArrowRight, Eye, EyeOff, LockKeyhole, Phone } from "lucide-react";

type Errors = {
  phone?: string;
  pin?: string;
  form?: string;
};

/**
 * Motif turquoise : capsules à 45° avec bouts arrondis en escalier,
 * dégradé, bandes claires et petites décorations.
 * Utilisé en haut sur mobile et en grand dans le panneau de droite sur desktop.
 */
function PaintCapsules({ className }: { className?: string }) {
  const uid = useId().replace(/:/g, "");
  const mint = `mint-${uid}`;
  const mintLight = `mint-light-${uid}`;

  return (
    <svg
      className={className}
      viewBox="0 0 305 215"
      preserveAspectRatio="xMinYMin slice"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <linearGradient
          id={mint}
          gradientUnits="userSpaceOnUse"
          x1="0"
          y1="60"
          x2="300"
          y2="10"
        >
          <stop offset="0%" stopColor="#8ED6C6" />
          <stop offset="55%" stopColor="#B4E6DA" />
          <stop offset="100%" stopColor="#D8F3EC" />
        </linearGradient>
        <linearGradient
          id={mintLight}
          gradientUnits="userSpaceOnUse"
          x1="0"
          y1="0"
          x2="300"
          y2="40"
        >
          <stop offset="0%" stopColor="#BFEADF" />
          <stop offset="100%" stopColor="#E6F8F3" />
        </linearGradient>
      </defs>

      {/* Capsules principales */}
      <g stroke={`url(#${mint})`} strokeWidth="44" strokeLinecap="round">
        <line x1="-62" y1="80" x2="28" y2="170" />
        <line x1="-52" y1="18" x2="68" y2="138" />
        <line x1="-42" y1="-44" x2="108" y2="106" />
        <line x1="-2" y1="-76" x2="148" y2="74" />
        <line x1="58" y1="-88" x2="188" y2="42" />
        <line x1="118" y1="-100" x2="228" y2="10" />
      </g>

      {/* Petite capsule claire en haut à droite */}
      <line
        x1="235"
        y1="-12"
        x2="278"
        y2="31"
        stroke={`url(#${mintLight})`}
        strokeWidth="26"
        strokeLinecap="round"
      />

      {/* Bandes claires à l'intérieur */}
      <g
        stroke="#FFFFFF"
        strokeOpacity="0.5"
        strokeWidth="6"
        strokeLinecap="round"
      >
        <line x1="-10" y1="60" x2="40" y2="110" />
        <line x1="20" y1="18" x2="80" y2="78" />
        <line x1="100" y1="26" x2="132" y2="58" />
        <line x1="150" y1="-10" x2="176" y2="16" />
      </g>

      {/* Traits fins bleu marine */}
      <g stroke="#1B2A6B" strokeWidth="1.6" strokeLinecap="round">
        <line x1="238" y1="26" x2="262" y2="48" />
        <line x1="246" y1="22" x2="266" y2="40" />
      </g>

      {/* Petits ronds */}
      <circle cx="20" cy="85" r="4.5" fill="#FFF3D6" />
      <circle cx="65" cy="123" r="5" fill="#1B2A6B" />
      <circle cx="190" cy="82" r="5.5" fill="#A9E3D5" />
      <circle cx="227" cy="77" r="12" fill="#1B2A6B" />

      {/* Quatre points */}
      <g fill="#1B2A6B">
        <circle cx="157" cy="114" r="1.6" />
        <circle cx="164" cy="114" r="1.6" />
        <circle cx="157" cy="121" r="1.6" />
        <circle cx="164" cy="121" r="1.6" />
      </g>

      {/* Cercle contour + trait */}
      <circle cx="240" cy="136" r="22" stroke="#CDEFE7" strokeWidth="3" />
      <line
        x1="248"
        y1="146"
        x2="264"
        y2="164"
        stroke="#1B2A6B"
        strokeWidth="1.6"
        strokeLinecap="round"
      />

      {/* Rond jaune */}
      <circle cx="38" cy="195" r="11" fill="#FFCE45" />
    </svg>
  );
}

export default function Home() {
  const [phone, setPhone] = useState("");
  const [pin, setPin] = useState("");
  const [showPin, setShowPin] = useState(false);
  const [remember, setRemember] = useState(true);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Errors>({});

  const handlePhoneChange = (e: ChangeEvent<HTMLInputElement>) => {
    // On garde uniquement chiffres, espaces et "+"
    setPhone(e.target.value.replace(/[^\d+\s]/g, ""));
    if (errors.phone) setErrors((prev) => ({ ...prev, phone: undefined }));
  };

  const handlePinChange = (e: ChangeEvent<HTMLInputElement>) => {
    // Le PIN est strictement numérique
    setPin(e.target.value.replace(/\D/g, "").slice(0, 6));
    if (errors.pin) setErrors((prev) => ({ ...prev, pin: undefined }));
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    const next: Errors = {};
    if (phone.replace(/\D/g, "").length < 8) {
      next.phone = "Entrez un numéro de téléphone valide.";
    }
    if (pin.length < 4) {
      next.pin = "Le code PIN doit contenir au moins 4 chiffres.";
    }

    setErrors(next);
    if (Object.keys(next).length > 0) return;

    setLoading(true);
    try {
      // TODO : remplace ce délai par ton appel API de connexion
      await new Promise((resolve) => setTimeout(resolve, 900));
      console.log({ phone, pin, remember });
    } catch {
      setErrors({ form: "Connexion impossible. Veuillez réessayer." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="login-page">
      <section className="login-panel">
        {/* Motif visible uniquement sur mobile */}
        <PaintCapsules className="paint paint--mobile" />

        <header className="login-logo">
          <Image
            src="/armoiries-bf.svg"
            alt="Armoiries du Burkina Faso"
            fill
            sizes="52px"
            priority
          />
        </header>

        <div className="login-block">
          <div className="login-heading">
            <h1 className="login-title">Connexion</h1>
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
                    inputMode="tel"
                    autoComplete="tel"
                    placeholder="+226 00 00 00 00"
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
              <a href="#register">S&apos;INSCRIRE</a>
            </p>
          </div>
        </div>
      </section>

      {/* Panneau visuel visible uniquement sur desktop */}
      <section className="visual-panel" aria-label="Illustration">
        <PaintCapsules className="paint paint--visual" />
        <div className="visual-copy">
          <h2>Bienvenue sur FurtArt</h2>
          <p>
            Connectez-vous pour accéder à votre espace et retrouver tout ce qui
            compte pour vous, en toute simplicité.
          </p>
        </div>
      </section>
    </main>
  );
}