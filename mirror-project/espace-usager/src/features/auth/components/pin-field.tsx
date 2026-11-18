"use client";

import { useState } from "react";
import { Eye, EyeOff, LockKeyhole } from "lucide-react";

export function PinField({ id, label, value, onChange, error, focus = false, autoComplete = "new-password", disabled = false }: {
  id: string; label: string; value: string; onChange: (value: string) => void;
  error?: string; focus?: boolean;
  autoComplete?: "new-password" | "current-password"; disabled?: boolean;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="field-group">
      <label className="field-label" htmlFor={id}>{label}</label>
      <div className={`field-wrapper${error ? " field-wrapper--error" : ""}`}>
        <LockKeyhole className="field-icon" size={16} aria-hidden="true" />
        <input id={id} name={id} className="field-input field-input--pin" type={visible ? "text" : "password"}
          inputMode="numeric" autoComplete={autoComplete} maxLength={6} placeholder={label} disabled={disabled}
          value={value} onChange={(e) => onChange(e.target.value.replace(/\D/g, "").slice(0, 6))}
          aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : undefined} autoFocus={focus} />
        <button className="visibility-button" type="button" aria-label={`${visible ? "Masquer" : "Afficher"} : ${label}`}
          aria-pressed={visible} disabled={disabled} onClick={() => setVisible(!visible)}>
          {visible ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
        </button>
      </div>
      {error && <p id={`${id}-error`} className="field-error" role="alert">{error}</p>}
    </div>
  );
}

