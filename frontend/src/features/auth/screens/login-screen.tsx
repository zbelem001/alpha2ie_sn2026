"use client";

import { ArrowRight, CheckCircle2, Phone } from "lucide-react";
import { AuthShell } from "@/features/auth/components/auth-shell";
import { PinField } from "@/features/auth/components/pin-field";
import { useCitizenAccess } from "@/features/auth/hooks/use-citizen-access";
import { REGISTRATION_DEMO } from "@/features/auth/mocks/registration";

function SubmitButton({ label, loading = false }: { label: string; loading?: boolean }) {
  return <button type="submit" className="login-button" disabled={loading} aria-busy={loading}>
    <span>{loading ? "PATIENTEZ…" : label}</span>
    <span className="login-button-arrow"><ArrowRight size={20} aria-hidden="true" /></span>
  </button>;
}

export function LoginScreen() {
  const { step, phone, pin, confirmation, digits, errors, loading, cooldown, resent, inputs,
    setPhone, setPin, setConfirmation, setErrors, setResent, changeNumber, continueWithPhone,
    startChallenge, updateDigits, verifyOtp, submitPin } = useCitizenAccess();

  const title = step === "phone" ? "Connexion" : step === "otp" ? "Vérification" : step === "setup" ? "Créer mon PIN" : "Votre code PIN";

  return (
    <AuthShell>
      <div className="login-heading">
        <h1 id="login-title" className="login-title">{title}</h1>
        <p className="auth-description">
          {step === "phone" ? "Entrez votre numéro de téléphone pour continuer." :
            step === "pin" ? <>Entrez votre code PIN pour le numéro <strong>{phone}</strong>.</> :
            step === "otp" ? <>Saisissez le code à 6 chiffres pour vérifier le numéro <strong>{phone}</strong>.</> :
            "Choisissez un code de 4 à 6 chiffres pour vos prochaines connexions."}
        </p>
      </div>

      <div className="login-content">
        {step !== "phone" && <button className="auth-text-button access-change-number" type="button" disabled={loading} onClick={changeNumber}>Modifier mon numéro</button>}

        {step === "phone" && <form className="login-form" onSubmit={continueWithPhone} noValidate>
          <div className="field-group">
            <label className="field-label" htmlFor="phone">Numéro de téléphone</label>
            <div className={`field-wrapper${errors.phone ? " field-wrapper--error" : ""}`}>
              <Phone className="field-icon" size={16} aria-hidden="true" />
              <input id="phone" name="phone" className="field-input" type="tel" inputMode="numeric" autoComplete="tel-national"
                placeholder="00 00 00 00" value={phone} disabled={loading}
                onChange={(e) => { setPhone(e.target.value.replace(/[^\d\s]/g, "")); setErrors({}); }}
                aria-invalid={Boolean(errors.phone)} aria-describedby={errors.phone ? "phone-error" : undefined} />
            </div>
            {errors.phone && <p id="phone-error" className="field-error" role="alert">{errors.phone}</p>}
          </div>
          <SubmitButton label="CONTINUER" loading={loading} />
        </form>}

        {step === "otp" && <form className="login-form" onSubmit={verifyOtp} noValidate>
          <fieldset className="otp-fieldset">
            <legend className="field-label">Code de vérification</legend>
            <div className="otp-inputs" onPaste={(e) => { e.preventDefault(); updateDigits(e.clipboardData.getData("text"), 0); }}>
              {digits.map((digit, index) => <input key={index} ref={(element) => { inputs.current[index] = element; }}
                className={`otp-input${errors.otp ? " otp-input--error" : ""}`} type="text" inputMode="numeric"
                autoComplete={index === 0 ? "one-time-code" : "off"} aria-label={`Chiffre ${index + 1} du code`}
                aria-invalid={Boolean(errors.otp)} aria-describedby={errors.otp ? "otp-error" : "otp-help"}
                value={digit} autoFocus={index === 0} onChange={(e) => updateDigits(e.target.value, index)}
                onKeyDown={(e) => {
                  if (e.key === "Backspace" && !digit && index > 0) { e.preventDefault(); updateDigits("", index - 1); inputs.current[index - 1]?.focus(); }
                  if (e.key === "ArrowLeft") inputs.current[Math.max(0, index - 1)]?.focus();
                  if (e.key === "ArrowRight") inputs.current[Math.min(5, index + 1)]?.focus();
                }} />)}
            </div>
          </fieldset>
          {errors.otp && <p id="otp-error" className="field-error" role="alert">{errors.otp}</p>}
          <p id="otp-help" className="auth-demo">Mode démo · Code : <strong>{REGISTRATION_DEMO.code}</strong> · Aucun SMS envoyé.</p>
          <SubmitButton label="VÉRIFIER LE CODE" />
          <p className="otp-resend">Vous n&apos;avez pas reçu le code ? <button type="button" className="auth-text-button" disabled={cooldown > 0}
            onClick={() => { startChallenge(); setResent(true); inputs.current[0]?.focus(); }}>{cooldown > 0 ? `Renvoyer dans ${cooldown} s` : "Renvoyer le code"}</button></p>
          {resent && <p className="auth-demo" role="status">Nouveau code simulé disponible : {REGISTRATION_DEMO.code}.</p>}
        </form>}

        {(step === "pin" || step === "setup") && <div className="pin-reveal">
          {step === "setup" && <p className="auth-verified" role="status"><CheckCircle2 size={26} aria-hidden="true" /> Numéro vérifié</p>}
          <form className="login-form" onSubmit={submitPin} noValidate>
            <PinField key={step} id={step === "setup" ? "new-pin" : "pin"} label="Code PIN" value={pin}
              onChange={(value) => { setPin(value); setErrors({}); }} error={errors.pin} focus disabled={loading}
              autoComplete={step === "pin" ? "current-password" : "new-password"} />
            {step === "setup" && <PinField id="confirm-pin" label="Confirmer le code PIN" value={confirmation}
              onChange={(value) => { setConfirmation(value); setErrors({}); }} error={errors.confirmation} disabled={loading} />}
            <SubmitButton label={step === "pin" ? "SE CONNECTER" : "CONTINUER"} loading={loading} />
          </form>
        </div>}
        {errors.form && <p className="form-error access-form-error" role="alert">{errors.form}</p>}
      </div>
    </AuthShell>
  );
}
