import type { Metadata } from "next";
import { CitizenHomeScreen } from "@/features/citizen/screens/citizen-home-screen";

export const metadata: Metadata = {
  title: { absolute: "Mon espace citoyen | Dites-le-nous une fois" },
};

export default function CitizenHomePage() {
  return <CitizenHomeScreen />;
}
