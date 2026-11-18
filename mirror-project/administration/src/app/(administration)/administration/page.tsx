import type { Metadata } from "next";
import { LocalAdminScreen } from "@/features/administration/screens/local-admin-screen";

export const metadata: Metadata = { title: { absolute: "Administration | Dites-le-nous une fois" } };
export default function AdministrationPage() { return <LocalAdminScreen />; }
