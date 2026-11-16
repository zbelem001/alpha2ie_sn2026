"""Validation des jetons d’accès Keycloak et autorisation métier."""
import os
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: frozenset[str]
    administration_code: str | None
    citizen_ref: str | None


@lru_cache(maxsize=1)
def _jwk_client() -> PyJWKClient:
    url = os.getenv(
        "KEYCLOAK_JWKS_URL",
        "http://localhost:8180/realms/dlnuf/protocol/openid-connect/certs",
    )
    return PyJWKClient(url, cache_keys=True, lifespan=300)


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton Bearer requis",
            headers={"WWW-Authenticate": "Bearer"},
        )

    issuer = os.getenv("KEYCLOAK_ISSUER", "http://localhost:8180/realms/dlnuf")
    client_id = os.getenv("KEYCLOAK_CLIENT_ID", "dlnuf-api")
    try:
        signing_key = _jwk_client().get_signing_key_from_jwt(credentials.credentials)
        claims = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            audience=client_id,
            options={"require": ["exp", "iat", "iss", "jti"]},
            leeway=5,
        )
        if claims.get("azp") != client_id:
            raise jwt.InvalidTokenError("mauvais client autorisé")
        realm_roles = claims.get("realm_access", {}).get("roles", [])
        if not isinstance(realm_roles, list):
            raise jwt.InvalidTokenError("rôles invalides")
        return Principal(
            subject=claims.get("sub") or claims["jti"],
            roles=frozenset(role for role in realm_roles if isinstance(role, str)),
            administration_code=claims.get("administration_code"),
            citizen_ref=claims.get("citizen_ref"),
        )
    except (jwt.PyJWTError, jwt.PyJWKClientError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def require_role(role: str):
    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if role not in principal.roles:
            raise HTTPException(status_code=403, detail="Rôle insuffisant")
        return principal

    return dependency
