import type { Metadata } from "next";
import { AgentWorkspaceScreen } from "@/features/agent/screens/agent-workspace-screen";

export const metadata: Metadata = { title: { absolute: "Guichet agent | Dites-le-nous une fois" } };

export default function AgentPage() {
  return <AgentWorkspaceScreen />;
}
