// Espace servi par cette application : rôles Keycloak admis à la connexion,
// page d'arrivée de chaque rôle et routes de l'API démarches relayées.
export type SpaceRole = "citizen" | "agent";

type Space = {
  roles: SpaceRole[];
  home: Partial<Record<SpaceRole, string>>;
  backendRoutes: RegExp;
};

// Espace usager : le citoyen consulte ses démarches, répond aux demandes d'accord
// et retrouve chaque consultation de ses informations.
export const SPACE: Space = {
  roles: ["citizen"],
  home: { citizen: "/usager" },
  // Routes de l'API démarches (/v1/…) que le relais accepte pour le citoyen (catalogue compris,
  // pour lancer une démarche depuis son espace).
  backendRoutes: /^(cases|citizen|notifications|procedures)(\/|$)/,
};
