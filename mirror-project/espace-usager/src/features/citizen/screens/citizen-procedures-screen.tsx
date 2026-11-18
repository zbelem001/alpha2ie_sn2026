import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { CitizenHeader } from "@/features/citizen/components/citizen-header";
import { CitizenProcedureForm } from "@/features/citizen/components/citizen-procedure-form";
import styles from "@/features/citizen/styles/home.module.css";

export function CitizenProceduresScreen() {
  return (
    <div className={styles.page}>
      <CitizenHeader />
      <main className={styles.main} id="contenu">
        <Link href="/usager" className={styles.profileBack}>
          <ArrowLeft size={17} aria-hidden="true" /> Retour à mes consultations
        </Link>
        <CitizenProcedureForm />
      </main>
      <footer className={styles.footer}><span>Dites-le-nous une fois</span><span>Services administratifs</span></footer>
    </div>
  );
}
