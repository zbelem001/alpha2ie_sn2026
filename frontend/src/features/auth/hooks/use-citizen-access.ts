"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { authenticateDemoAccount, createDemoCitizen, demoAccountExists } from "@/features/auth/mocks/login";
import { REGISTRATION_DEMO } from "@/features/auth/mocks/registration";
import { setDemoCitizenPhone } from "@/lib/demo-authorizations";

type Step = "phone" | "pin" | "otp" | "setup";

export function useCitizenAccess() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("phone");
  const [phone, setPhone] = useState("");
  const [pin, setPin] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [digits, setDigits] = useState<string[]>(Array(6).fill(""));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [expiresAt, setExpiresAt] = useState(0);
  const [cooldown, setCooldown] = useState(0);
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
    setStep("otp");
  }

  function changeNumber() {
    if (loading) return;
    setStep("phone");
    setPin("");
    setConfirmation("");
    setDigits(Array(6).fill(""));
    setErrors({});
    setExpiresAt(0);
    setCooldown(0);
    setResent(false);
  }

  async function continueWithPhone(e: FormEvent) {
    e.preventDefault();
    if (loading) return;
    const normalized = phone.replace(/\s/g, "");
    if (!/^\d{8}$/.test(normalized)) {
      setErrors({ phone: "Entrez un numéro de téléphone à 8 chiffres." });
      return;
    }
    setErrors({});
    setLoading(true);
    try {
      const known = await demoAccountExists(normalized);
      setPhone(normalized);
      if (known) setStep("pin");
      else startChallenge();
    } catch {
      setErrors({ form: "Impossible de vérifier ce numéro. Veuillez réessayer." });
    } finally { setLoading(false); }
  }

  function updateDigits(value: string, index: number) {
    const clean = value.replace(/\D/g, "").slice(0, 6);
    const start = clean.length === 6 ? 0 : index;
    setDigits((old) => {
      const next = [...old];
      if (!clean) next[index] = "";
      else [...clean].forEach((digit, offset) => { if (start + offset < 6) next[start + offset] = digit; });
      return next;
    });
    setErrors({});
    if (clean) inputs.current[Math.min(start + clean.length, 5)]?.focus();
  }

  function verifyOtp(e: FormEvent) {
    e.preventDefault();
    if (step !== "otp") return;
    if (Date.now() >= expiresAt) setErrors({ otp: "Ce code a expiré. Demandez un nouveau code." });
    else if (digits.join("") !== REGISTRATION_DEMO.code) setErrors({ otp: "Code incorrect. Vérifiez les 6 chiffres et réessayez." });
    else {
      setErrors({});
      setDigits(Array(6).fill(""));
      setCooldown(0);
      setStep("setup");
    }
  }

  async function submitPin(e: FormEvent) {
    e.preventDefault();
    if (loading || (step !== "pin" && step !== "setup")) return;
    const next: Record<string, string> = {};
    if (!/^\d{4,6}$/.test(pin)) next.pin = "Le code PIN doit contenir de 4 à 6 chiffres.";
    if (step === "setup" && (!confirmation || confirmation !== pin)) next.confirmation = "Les deux codes PIN doivent être identiques.";
    setErrors(next);
    if (Object.keys(next).length) return;
    setLoading(true);
    try {
      let destination = "/usager";
      if (step === "setup") await createDemoCitizen(phone, pin);
      else {
        const role = await authenticateDemoAccount(phone, pin);
        if (!role) {
          setErrors({ pin: "Code PIN incorrect. Veuillez réessayer." });
          return;
        }
        if (role === "agent") destination = "/guichet";
      }
      if (destination === "/usager") setDemoCitizenPhone(phone);
      setPin("");
      setConfirmation("");
      setPhone("");
      setStep("phone");
      setCooldown(0);
      setResent(false);
      router.replace(destination);
    } catch {
      setErrors({ form: "Accès impossible. Veuillez réessayer. Le mode démo nécessite un stockage local et une connexion sécurisée ou localhost." });
    } finally { setLoading(false); }
  }

  return { step, phone, pin, confirmation, digits, errors, loading, cooldown, resent, inputs,
    setPhone, setPin, setConfirmation, setErrors, setResent, changeNumber, continueWithPhone,
    startChallenge, updateDigits, verifyOtp, submitPin };
}
