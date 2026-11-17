import type { Viewport } from "next";
import type { ReactNode } from "react";

export const viewport: Viewport = { themeColor: "#eef8f4" };

export default function AgentLayout({ children }: { children: ReactNode }) {
  return children;
}
