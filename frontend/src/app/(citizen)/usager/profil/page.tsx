import type { Metadata } from "next";
import { CitizenProfileScreen } from "@/features/citizen/screens/citizen-profile-screen";

export const metadata: Metadata = { title: { absolute: "Mon profil | Dites-le-nous une fois" } };

export default function CitizenProfilePage() {
  return <CitizenProfileScreen />;
}
