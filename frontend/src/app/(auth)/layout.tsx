import type { ReactNode } from "react";
import { FlashInfo } from "@/components/shared/flash-info";
import "@/features/auth/styles/auth.css";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return <div className="auth-space"><FlashInfo />{children}</div>;
}
