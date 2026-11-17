// Simulation locale uniquement. À remplacer par le backend / Keycloak.
// Le PIN n'est jamais conservé en clair ; ces profils ne créent aucune session serveur.
const DEMO_CITIZEN = { phone: "11111111", pin: "0000" } as const;
const DEMO_AGENT = { phone: "22222222", pin: "1234" } as const;
export type DemoRole = "citizen" | "agent";
const storageKey = (phone: string) => `dlnuf:demo:citizen:${phone.replace(/\s/g, "")}`;

type DemoProfile = { salt: string; verifier: string };

function readProfile(phone: string): DemoProfile | null {
  const raw = localStorage.getItem(storageKey(phone));
  if (!raw) return null;
  const profile = JSON.parse(raw) as DemoProfile;
  if (!/^[a-f0-9]{32}$/.test(profile.salt) || !/^[a-f0-9]{64}$/.test(profile.verifier)) {
    throw new Error("Profil de démonstration invalide");
  }
  return profile;
}

async function derivePin(pin: string, salt: Uint8Array<ArrayBuffer>) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(pin), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({ name: "PBKDF2", salt, iterations: 100_000, hash: "SHA-256" }, key, 256);
  return Array.from(new Uint8Array(bits), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function demoAccountExists(phone: string) {
  const normalized = phone.replace(/\s/g, "");
  return normalized === DEMO_AGENT.phone || normalized === DEMO_CITIZEN.phone || readProfile(normalized) !== null;
}

export async function createDemoCitizen(phone: string, pin: string) {
  if (phone.replace(/\s/g, "") === DEMO_AGENT.phone) throw new Error("Ce numéro est réservé au compte agent de démonstration.");
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const profile: DemoProfile = {
    salt: Array.from(salt, (byte) => byte.toString(16).padStart(2, "0")).join(""),
    verifier: await derivePin(pin, salt),
  };
  localStorage.setItem(storageKey(phone), JSON.stringify(profile));
}

export async function authenticateDemoAccount(phone: string, pin: string): Promise<DemoRole | null> {
  await new Promise((resolve) => setTimeout(resolve, 300));
  // Le compte agent préconfiguré ne peut pas être remplacé par un profil citoyen local.
  if (phone.replace(/\s/g, "") === DEMO_AGENT.phone) return pin === DEMO_AGENT.pin ? "agent" : null;
  const profile = readProfile(phone);
  if (profile) {
    const salt = Uint8Array.from(profile.salt.match(/../g)!, (byte) => parseInt(byte, 16));
    return await derivePin(pin, salt) === profile.verifier ? "citizen" : null;
  }
  return phone.replace(/\s/g, "") === DEMO_CITIZEN.phone && pin === DEMO_CITIZEN.pin ? "citizen" : null;
}
