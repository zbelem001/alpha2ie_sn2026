"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2, Phone } from "lucide-react";
import { AuthShell } from "@/features/auth/components/auth-shell";
import { PinField } from "@/features/auth/components/pin-field";
import { useRegistration } from "@/features/auth/hooks/use-registration";
import { REGISTRATION_DEMO } from "@/features/auth/mocks/registration";

export function RegistrationScreen() {
  const { stage, phone, digits, verified, pin, confirmation, errors, cooldown, completed, resent, inputs,
    setStage, setPhone, setDigits, setPin, setConfirmation, setErrors, setResent,
    startChallenge, continueWithPhone, updateDigits, verifyOtp, finish } = useRegistration();

  return (
    <AuthShell registration>
      <div className="login-heading">
        <h1 id="login-title" className="login-title">{stage === "phone" ? "Inscription" : "Vérification"}</h1>
        <p className="auth-description">{stage === "phone" ? "Votre espace commence avec votre numéro de téléphone." : verified ? <>Le numéro <strong>{phone}</strong> est maintenant vérifié.</> : <>Saisissez le code à 6 chiffres pour vérifier le numéro <strong>{phone}</strong>.</>}</p>
      </div>
      <div className="login-content">
        {stage === "phone" ? (
          <form className="login-form" onSubmit={continueWithPhone} noValidate>
            <div className="field-group">
              <label className="field-label" htmlFor="register-phone">Numéro de téléphone</label>
              <div className={`field-wrapper${errors.phone ? " field-wrapper--error" : ""}`}>
                <Phone className="field-icon" size={16} aria-hidden="true" />
                <input id="register-phone" name="phone" className="field-input" type="tel" inputMode="numeric" autoComplete="tel-national"
                  placeholder="00 00 00 00" value={phone} onChange={(e) => { setPhone(e.target.value.replace(/[^\d\s]/g, "")); setErrors({}); }}
                  aria-invalid={Boolean(errors.phone)} aria-describedby={errors.phone ? "register-phone-error" : undefined} />
              </div>
              {errors.phone && <p id="register-phone-error" className="field-error" role="alert">{errors.phone}</p>}
            </div>
            <button className="login-button" type="submit"><span>CONTINUER</span><span className="login-button-arrow"><ArrowRight size={20} aria-hidden="true" /></span></button>
            <p className="auth-demo">Démonstration : aucun SMS ne sera envoyé.</p>
          </form>
        ) : (
          <>
            {!verified && <button className="auth-text-button" type="button" onClick={() => { setStage("phone"); setDigits(Array(6).fill("")); setErrors({}); setResent(false); }}>Modifier mon numéro</button>}
            {!verified && <form className="login-form" onSubmit={verifyOtp} noValidate>
              <fieldset className="otp-fieldset">
                <legend className="field-label">Code de vérification</legend>
                <div className="otp-inputs" onPaste={(e) => { e.preventDefault(); updateDigits(e.clipboardData.getData("text"), 0); }}>
                  {digits.map((digit, index) => <input key={index} ref={(element) => { inputs.current[index] = element; }}
                    className={`otp-input${errors.otp ? " otp-input--error" : ""}`} type="text" inputMode="numeric"
                    autoComplete={index === 0 ? "one-time-code" : "off"} aria-label={`Chiffre ${index + 1} du code`}
                    aria-invalid={Boolean(errors.otp)} aria-describedby={errors.otp ? "otp-error" : verified ? undefined : "otp-help"}
                    value={digit} autoFocus={index === 0} onChange={(e) => updateDigits(e.target.value, index)}
                    onKeyDown={(e) => {
                      if (e.key === "Backspace" && !digit && index > 0) { e.preventDefault(); updateDigits("", index - 1); inputs.current[index - 1]?.focus(); }
                      if (e.key === "ArrowLeft") inputs.current[Math.max(0, index - 1)]?.focus();
                      if (e.key === "ArrowRight") inputs.current[Math.min(5, index + 1)]?.focus();
                    }} />)}
                </div>
              </fieldset>
              {errors.otp && <p id="otp-error" className="field-error" role="alert">{errors.otp}</p>}
              {!verified && <>
                <p id="otp-help" className="auth-demo">Mode démo · Code : <strong>{REGISTRATION_DEMO.code}</strong> · Valable 5 minutes.</p>
                <button type="submit" className="login-button"><span>VÉRIFIER LE CODE</span><span className="login-button-arrow"><ArrowRight size={20} aria-hidden="true" /></span></button>
                <p className="otp-resend">Vous n&apos;avez pas reçu le code ? <button type="button" className="auth-text-button" disabled={cooldown > 0} onClick={() => { startChallenge(); setResent(true); inputs.current[0]?.focus(); }}>{cooldown > 0 ? `Renvoyer dans ${cooldown} s` : "Renvoyer le code"}</button></p>
                {resent && <p className="auth-demo" role="status">Nouveau code simulé disponible : 123456.</p>}
              </>}
            </form>}
            {verified && <div className="pin-reveal">
              <p className="auth-verified" role="status"><CheckCircle2 size={26} aria-hidden="true" /> Code validé</p>
              {completed ? <div className="auth-complete" role="status"><h2>Tout est prêt !</h2><p>Le parcours de démonstration est terminé. La création réelle du compte sera disponible après connexion au service d’inscription.</p><Link className="auth-text-button" href="/">Revenir à la connexion</Link></div> : <>
                <h2 className="pin-title">Choisissez votre code PIN</h2>
                <p className="auth-description">De 4 à 6 chiffres pour vos prochaines connexions.</p>
                <form className="login-form" onSubmit={finish} noValidate>
                  <PinField id="new-pin" label="Code PIN" value={pin} onChange={(value) => { setPin(value); setErrors({}); }} error={errors.pin} focus />
                  <PinField id="confirm-pin" label="Confirmer le code PIN" value={confirmation} onChange={(value) => { setConfirmation(value); setErrors({}); }} error={errors.confirmation} />
                  <button type="submit" className="login-button"><span>CRÉER MON COMPTE</span><span className="login-button-arrow"><ArrowRight size={20} aria-hidden="true" /></span></button>
                </form>
              </>}
            </div>}
          </>
        )}
        <p className="register-prompt">Vous avez déjà un compte ? <Link href="/">SE CONNECTER</Link></p>
      </div>
    </AuthShell>
  );
}
