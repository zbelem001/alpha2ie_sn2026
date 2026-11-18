// Espace servi par cette application : rôles Keycloak admis à la connexion,
// page d'arrivée de chaque rôle et routes de l'API démarches relayées.
export type SpaceRole = "citizen" | "agent" | "local-admin";

type Space = {
  roles: SpaceRole[];
  home: Partial<Record<SpaceRole, string>>;
  backendRoutes: RegExp;
};

// Guichet agent : l'agent ouvre le dossier, recueille l'accord du citoyen et lance
// les vérifications, sans demander de pièce.
export const SPACE: Space = {
  roles: ["agent"],
  home: { agent: "/guichet" },
  // Routes de l'API démarches (/v1/…) que le relais accepte pour l'agent.
  backendRoutes: /^(procedures|cases)(\/|$)/,
};
