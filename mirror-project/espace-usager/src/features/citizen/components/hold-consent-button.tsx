"use client";
import { useEffect, useRef, useState } from "react";
import styles from "@/features/citizen/styles/home.module.css";

export function HoldConsentButton({ disabled, onConfirm }: { disabled: boolean; onConfirm: () => void }) {
  const [progress, setProgress] = useState(0);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const pressing = useRef(false);
  function cancel() {
    pressing.current = false;
    if (timer.current) clearInterval(timer.current);
    timer.current = null; setProgress(0);
  }
  function start() {
    if (disabled || pressing.current) return;
    pressing.current = true;
    const began = performance.now();
    setProgress(0.001);
    timer.current = setInterval(() => {
      const elapsed = performance.now() - began;
      if (elapsed >= 3000) {
        cancel(); onConfirm();
      } else setProgress(elapsed / 3000);
    }, 40);
  }
  useEffect(() => {
    const stop = () => { pressing.current = false; if (timer.current) clearInterval(timer.current); timer.current = null; setProgress(0); };
    window.addEventListener("blur", stop);
    document.addEventListener("visibilitychange", stop);
    return () => { if (timer.current) clearInterval(timer.current); window.removeEventListener("blur", stop); document.removeEventListener("visibilitychange", stop); };
  }, []);
  return <div>
    <button type="button" className={styles.holdConsent} disabled={disabled}
      aria-label="Maintenir 3 secondes pour donner mon accord et envoyer"
      onPointerDown={(event) => { if (event.button === 0) { event.preventDefault(); start(); } }}
      onPointerUp={cancel} onPointerCancel={cancel} onPointerLeave={cancel} onBlur={cancel}
      onContextMenu={(event) => event.preventDefault()}
      onKeyDown={(event) => { if (event.key === " " || event.key === "Enter") { event.preventDefault(); if (!event.repeat) start(); } }}
      onKeyUp={(event) => { if (event.key === " " || event.key === "Enter") { event.preventDefault(); cancel(); } }}>
      <span className={styles.holdProgress} style={{ width: `${progress * 100}%` }} aria-hidden="true" />
      <span>{progress > 0 ? `Maintenez… ${Math.ceil(3 * (1 - progress))} s` : "Donner mon accord et envoyer"}</span>
    </button>
    <p className={styles.holdHint} aria-live="polite">{progress > 0 ? `Envoi dans ${Math.ceil(3 * (1 - progress))} secondes. Relâchez pour annuler.` : "Maintenez le bouton pendant 3 secondes. Au clavier, maintenez Espace ou Entrée."}</p>
  </div>;
}
