// Accès de démonstration uniquement, sans session ni authentification serveur.
const DEMO_CITIZEN = { phone: "11111111", pin: "0000" } as const;

export async function authenticateDemoCitizen(phone: string, pin: string) {
  await new Promise((resolve) => setTimeout(resolve, 300));
  return phone.replace(/\s/g, "") === DEMO_CITIZEN.phone && pin === DEMO_CITIZEN.pin;
}
