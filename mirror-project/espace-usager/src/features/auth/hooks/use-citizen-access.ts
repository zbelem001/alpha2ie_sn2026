"use client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";

async function access(action: string, payload: object) {
  const response = await fetch("/api/auth/phone", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action, ...payload }) });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Vérifiez les informations saisies.");
  return data;
}
export function useCitizenAccess() {
  const router = useRouter();
  const [step, setStep] = useState<"phone" | "pin" | "otp" | "setup">("phone");
  const [phone, setPhone] = useState(""); const [pin, setPin] = useState(""); const [confirmation, setConfirmation] = useState("");
  const [digits, setDigits] = useState<string[]>(Array(6).fill("")); const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false); const [cooldown, setCooldown] = useState(0); const [resent, setResent] = useState(false);
  const [challenge, setChallenge] = useState(""); const [ticket, setTicket] = useState(""); const [simulationCode, setSimulationCode] = useState("");
  const inputs = useRef<(HTMLInputElement | null)[]>([]);
  useEffect(() => { if (cooldown <= 0) return; const timer = setTimeout(() => setCooldown(cooldown - 1), 1000); return () => clearTimeout(timer); }, [cooldown]);
  function changeNumber() { if (loading) return; setStep("phone"); setPin(""); setConfirmation(""); setDigits(Array(6).fill("")); setErrors({}); setTicket(""); setChallenge(""); setSimulationCode(""); setCooldown(0); }
  async function startChallenge() {
    if (loading) return;
    const normalized = phone.replace(/\s/g, "");
    if (!/^\d{8}$/.test(normalized)) { setErrors({ phone: "Entrez un numéro de téléphone à 8 chiffres." }); return; }
    setLoading(true); setErrors({});
    try {
      const data = await access("continue", { phone: normalized }); setPhone(normalized);
      if (data.step === "pin") setStep("pin");
      else { setChallenge(data.challengeId); setSimulationCode(data.mode === "simulation" ? data.code ?? "" : ""); setDigits(Array(6).fill("")); setCooldown(Math.max(0, Math.ceil((data.resendAt - Date.now()) / 1000))); setStep("otp"); }
    } catch (cause) { setErrors({ form: cause instanceof Error ? cause.message : "Accès impossible." }); }
    finally { setLoading(false); }
  }
  function continueWithPhone(e: FormEvent) { e.preventDefault(); void startChallenge(); }
  function updateDigits(value: string, index: number) { const clean = value.replace(/\D/g, "").slice(0, 6); const start = clean.length === 6 ? 0 : index; setDigits((old) => { const next = [...old]; if (!clean) next[index] = ""; else [...clean].forEach((digit, offset) => { if (start + offset < 6) next[start + offset] = digit; }); return next; }); setErrors({}); if (clean) inputs.current[Math.min(start + clean.length, 5)]?.focus(); }
  async function verifyOtp(e: FormEvent) { e.preventDefault(); if (loading) return; if (!/^\d{6}$/.test(digits.join(""))) { setErrors({ otp: "Saisissez les 6 chiffres du code." }); return; } setLoading(true); setErrors({}); try { const data = await access("verify", { challenge_id: challenge, code: digits.join("") }); setTicket(data.ticket); setDigits(Array(6).fill("")); setSimulationCode(""); setStep("setup"); } catch (cause) { setErrors({ otp: cause instanceof Error ? cause.message : "Code invalide." }); } finally { setLoading(false); } }
  async function submitPin(e: FormEvent) { e.preventDefault(); if (loading) return; if (!/^\d{4,6}$/.test(pin)) { setErrors({ pin: "Le PIN doit contenir de 4 à 6 chiffres." }); return; } if (step === "setup" && pin !== confirmation) { setErrors({ confirmation: "Les deux codes PIN doivent être identiques." }); return; } setLoading(true); setErrors({}); try { if (step === "setup") { await access("register", { challenge_id: challenge, ticket, pin }); setTicket(""); setStep("pin"); } const session = await login(phone, pin); setPin(""); setConfirmation(""); setPhone(""); setStep("phone"); setChallenge(""); setTicket(""); setSimulationCode(""); router.replace(session.home); } catch (cause) { setErrors({ form: cause instanceof Error ? cause.message : "Connexion impossible." }); } finally { setLoading(false); } }
  return { step, phone, pin, confirmation, digits, errors, loading, cooldown, resent, inputs, simulationCode, setPhone, setPin, setConfirmation, setErrors, setResent, changeNumber, continueWithPhone, startChallenge, updateDigits, verifyOtp, submitPin };
}
