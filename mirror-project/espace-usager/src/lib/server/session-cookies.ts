// Noms des cookies de session (jetons Keycloak, httpOnly), propres à cette application.
// Un navigateur ne distingue pas les ports : avec des noms communs aux deux applications,
// se connecter au guichet (localhost:3001) remplaçait la session citoyenne (localhost:3000),
// et se déconnecter de l'une fermait l'autre.
export const ACCESS_COOKIE = "dlnuf_usager_access";
export const REFRESH_COOKIE = "dlnuf_usager_refresh";
