#!/bin/sh
# Exécuté une seule fois, à la création du volume PostgreSQL.
# Une base par composant : keycloak (identité) et backend (Personne 2).
set -eu

for database in keycloak backend; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
    -c "CREATE DATABASE \"$database\" OWNER \"$POSTGRES_USER\";"
done
