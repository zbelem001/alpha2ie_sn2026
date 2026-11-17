"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { REGISTRATION_DEMO } from "@/features/auth/mocks/registration";

export function useRegistration() {
  const [stage, setStage] = useState<"phone" | "otp">("phone");
  const [phone, setPhone] = useState("");
  const [digits, setDigits] = useState<string[]>(Array(6).fill(""));
  const [verified, setVerified] = useState(false);
  const [pin, setPin] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [expiresAt, setExpiresAt] = useState(0);
  const [cooldown, setCooldown] = useState(0);
  const [completed, setCompleted] = useState(false);
  const [resent, setResent] = useState(false);
  const inputs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setTimeout(() => setCooldown(cooldown - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  function startChallenge() {
    setDigits(Array(6).fill(""));
    setErrors({});
    setExpiresAt(Date.now() + REGISTRATION_DEMO.lifetimeMs);
    setCooldown(30);
  }

  function continueWithPhone(e: FormEvent) {
    e.preventDefault();
    if (!/^\d{8}$/.test(phone.replace(/\s/g, ""))) {
      setErrors({ phone: "Entrez un numéro de téléphone à 8 chiffres." });
      return;
    }
    startChallenge();
    setStage("otp");
  }

  function updateDigits(value: string, index: number) {
    const clean = value.replace(/\D/g, "").slice(0, 6);
    if (!clean) {
      setDigits((old) => old.map((digit, i) => i === index ? "" : digit));
      setErrors({});
      return;
    }
    const start = clean.length === 6 ? 0 : index;
    setDigits((old) => {
      const next = [...old];
      [...clean].forEach((digit, offset) => { if (start + offset < 6) next[start + offset] = digit; });
      return next;
    });
    setErrors({});
    inputs.current[Math.min(start + clean.length, 5)]?.focus();
  }

  function verifyOtp(e: FormEvent) {
    e.preventDefault();
    if (Date.now() > expiresAt) {
      setErrors({ otp: "Ce code a expiré. Demandez un nouveau code." });
    } else if (digits.join("") !== REGISTRATION_DEMO.code) {
      setErrors({ otp: "Code incorrect. Vérifiez les 6 chiffres et réessayez." });
    } else {
      setVerified(true);
      setErrors({});
    }
  }

  function finish(e: FormEvent) {
    e.preventDefault();
    const next: Record<string, string> = {};
    if (!/^\d{4,6}$/.test(pin)) next.pin = "Choisissez un PIN de 4 à 6 chiffres.";
    if (!confirmation || confirmation !== pin) next.confirmation = "Les deux codes PIN doivent être identiques.";
    setErrors(next);
    if (Object.keys(next).length === 0 && verified) {
      setPin("");
      setConfirmation("");
      setCompleted(true);
    }
  }

  return { stage, phone, digits, verified, pin, confirmation, errors, cooldown, completed, resent, inputs,
    setStage, setPhone, setDigits, setPin, setConfirmation, setErrors, setResent,
    startChallenge, continueWithPhone, updateDigits, verifyOtp, finish };
}
