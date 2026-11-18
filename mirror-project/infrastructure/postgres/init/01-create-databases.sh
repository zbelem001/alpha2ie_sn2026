#!/bin/sh
# Exécuté une seule fois, à la création du volume PostgreSQL.
# Une base par composant : keycloak (identité), backend (couche démarches) et journal
# (couche journal, qui la crée aussi elle-même sur un volume plus ancien).
set -eu

for database in keycloak backend journal; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
    -c "CREATE DATABASE \"$database\" OWNER \"$POSTGRES_USER\";"
done
