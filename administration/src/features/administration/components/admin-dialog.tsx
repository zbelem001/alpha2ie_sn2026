"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import styles from "@/features/administration/styles/dashboard.module.css";

export function AdminDialog({ title, busy, onClose, children, error }: {
  title: string; busy: boolean; onClose: () => void; children: ReactNode; error?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current!;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialog.showModal();
    return () => { dialog.close(); document.body.style.overflow = overflow; };
  }, []);
  if (typeof document === "undefined") return null;
  return createPortal(<dialog ref={ref} className={styles.adminDialog} aria-label={title}
    onCancel={(event) => { event.preventDefault(); if (!busy) onClose(); }}>
    <div className={styles.dialogHeader}><h2>{title}</h2><button className={styles.iconButton} type="button" disabled={busy} onClick={onClose} aria-label="Fermer"><X size={21} /></button></div>
    <div className={styles.dialogBody}>
      {error && <p className={styles.error} role="alert">{error}</p>}
      {children}
    </div>
  </dialog>, document.body);
}
