// Simulation locale uniquement. L'accès réel doit être contrôlé par Keycloak / le backend.
import { appendAdminAudit, getDemoAdministration, setDemoStaff } from "@/lib/demo-administration";
import { hashDemoPin, verifyDemoPin, type DemoPin } from "@/lib/demo-pin";

const CITIZEN = { phone: "11111111", pin: "0000" };
const ADMIN = { phone: "99999999", pin: "1234" };
export type DemoRole = "citizen" | "agent" | "local-admin";
const key = (phone: string) => "dlnuf:demo:citizen:" + phone.replace(/\s/g, "");

function readProfile(phone: string): DemoPin | null {
  const raw = localStorage.getItem(key(phone));
  if (!raw) return null;
  const profile = JSON.parse(raw) as DemoPin;
  if (!/^[a-f0-9]{32}$/.test(profile.salt) || !/^[a-f0-9]{64}$/.test(profile.verifier)) throw new Error("Profil de démonstration invalide");
  return profile;
}
export async function demoAccountExists(phone: string) {
  const normalized = phone.replace(/\s/g, "");
  return normalized === ADMIN.phone || getDemoAdministration().agents.some((agent) => agent.phone === normalized) || normalized === CITIZEN.phone || readProfile(normalized) !== null;
}
export async function createDemoCitizen(phone: string, pin: string) {
  const normalized = phone.replace(/\s/g, "");
  if (normalized === ADMIN.phone || getDemoAdministration().agents.some((agent) => agent.phone === normalized)) throw new Error("Ce numéro appartient à un compte de l’administration.");
  localStorage.setItem(key(normalized), JSON.stringify(await hashDemoPin(pin)));
}
export async function authenticateDemoAccount(phone: string, pin: string): Promise<DemoRole | null> {
  await new Promise((resolve) => setTimeout(resolve, 250));
  const normalized = phone.replace(/\s/g, "");
  if (normalized === ADMIN.phone) {
    const actor = { name: "Administrateur local", role: "local-admin" };
    if (pin !== ADMIN.pin) { appendAdminAudit("Connexion administrateur refusée", "Console locale", "Identifiants incorrects", actor); return null; }
    setDemoStaff({ id: "seed-admin", name: actor.name, phone: normalized, role: "local-admin" });
    appendAdminAudit("Connexion administrateur", "Console locale", "", actor);
    return "local-admin";
  }
  const agent = getDemoAdministration().agents.find((item) => item.phone === normalized);
  if (agent) {
    const valid = agent.active && (agent.credentials ? await verifyDemoPin(pin, agent.credentials) : agent.id === "seed-agent" && pin === "1234");
    if (!valid) { appendAdminAudit("Connexion agent refusée", agent.name, agent.active ? "Identifiants incorrects" : "Compte suspendu", { name: agent.name, role: "agent" }); return null; }
    setDemoStaff({ id: agent.id, name: agent.name, phone: agent.phone, role: "agent" });
    appendAdminAudit("Connexion agent", "Guichet", "", { name: agent.name, role: "agent" });
    return "agent";
  }
  const profile = readProfile(normalized);
  if (profile) return await verifyDemoPin(pin, profile) ? "citizen" : null;
  return normalized === CITIZEN.phone && pin === CITIZEN.pin ? "citizen" : null;
}
