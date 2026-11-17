// Utilitaire de simulation locale ; ne remplace pas l'authentification serveur.
export type DemoPin = { salt: string; verifier: string };
async function derive(pin: string, salt: Uint8Array<ArrayBuffer>) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(pin), "PBKDF2", false, ["deriveBits"]);
  const result = await crypto.subtle.deriveBits({ name: "PBKDF2", salt, iterations: 100_000, hash: "SHA-256" }, key, 256);
  return Array.from(new Uint8Array(result), (byte) => byte.toString(16).padStart(2, "0")).join("");
}
export async function hashDemoPin(pin: string): Promise<DemoPin> {
  if (!/^\d{4,6}$/.test(pin)) throw new Error("Le PIN doit contenir de 4 à 6 chiffres.");
  const salt = crypto.getRandomValues(new Uint8Array(16));
  return { salt: Array.from(salt, (byte) => byte.toString(16).padStart(2, "0")).join(""), verifier: await derive(pin, salt) };
}
export async function verifyDemoPin(pin: string, stored: DemoPin) {
  const salt = Uint8Array.from(stored.salt.match(/../g)!, (byte) => parseInt(byte, 16));
  return await derive(pin, salt) === stored.verifier;
}
