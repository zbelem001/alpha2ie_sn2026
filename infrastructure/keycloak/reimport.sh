#!/bin/sh
# Réimporte le realm « dlnuf » après une modification de import/realm-dlnuf.json.
# Keycloak n'importe un realm que s'il n'existe pas : on le supprime, puis on redémarre.
# ATTENTION : les comptes et réglages faits à la main dans la console sont perdus.
#
# Usage, depuis la racine du dépôt : sh infrastructure/keycloak/reimport.sh
set -eu

ADMIN_USER="${KEYCLOAK_ADMIN:-admin}"
ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin-dev}"
KCADM="/opt/keycloak/bin/kcadm.sh"

docker compose exec -T keycloak "$KCADM" config credentials \
  --server http://localhost:8080 --realm master --user "$ADMIN_USER" --password "$ADMIN_PASSWORD" >/dev/null 2>&1 \
  || { echo "Connexion à la console Keycloak impossible (Keycloak démarré ? identifiants admin ?)." >&2; exit 1; }
docker compose exec -T keycloak "$KCADM" delete realms/dlnuf 2>/dev/null \
  && echo "Realm dlnuf supprimé." \
  || echo "Realm dlnuf absent : import direct."
docker compose restart keycloak >/dev/null
echo "Keycloak redémarre et importe le realm. Suivre avec : docker compose logs -f keycloak"
