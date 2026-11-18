// Espace servi par cette application : rôles Keycloak admis à la connexion,
// page d'arrivée de chaque rôle et routes de l'API démarches relayées.
export type SpaceRole = "citizen" | "agent";

export const SPACE = {
  roles: ["citizen", "agent"] as SpaceRole[],
  home: { citizen: "/usager", agent: "/guichet" } satisfies Record<SpaceRole, string>,
  // Routes de l'API démarches (/v1/…) que le relais accepte. Les routes d'administration
  // et d'inscription n'ont pas d'écran dans cette application.
  backendRoutes: /^(procedures|cases|citizen|notifications)(\/|$)/,
  // Comptes fictifs du realm de démonstration (infrastructure/keycloak/dlnuf-realm.json).
  demoAccounts: [
    { label: "Citoyenne (Awa)", username: "citoyen-demo", password: "CitoyenDemo-2026!" },
    { label: "Agent · Fonction publique", username: "agent-demo", password: "AgentDemo-2026!" },
  ],
};
