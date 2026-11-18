"""Configure the managed demo claims used by the API after realm import."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = os.getenv("KEYCLOAK_ADMIN_URL", "http://keycloak:8080")
ADMIN_USERNAME = os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ["KEYCLOAK_ADMIN_PASSWORD"]

DEMO_ATTRIBUTES = {
    "agent-demo": {"administration_code": ["BF/GOV/FONCTION-PUBLIQUE"]},
    "agent-passeport-demo": {"administration_code": ["BF/GOV/DIPF/PASSEPORTS"]},
    "citoyen-demo": {"phone_number_verified": ["false"]},
}
demo_phone = os.getenv("CITIZEN_DEMO_PHONE", "").strip()
demo_phone_verified = os.getenv("CITIZEN_DEMO_PHONE_VERIFIED", "false").strip().lower() == "true"
if demo_phone:
    DEMO_ATTRIBUTES["citoyen-demo"]["phone_number"] = [demo_phone]
if demo_phone and demo_phone_verified:
    DEMO_ATTRIBUTES["citoyen-demo"]["phone_number_verified"] = ["true"]

PROFILE_ATTRIBUTES = {
    "administration_code": "Code de l’administration",
    "account_kind": "Type de compte applicatif",
    "citizen_ref": "Référence citoyen",
    "phone_number": "Numéro de téléphone vérifié",
    "phone_number_verified": "Téléphone vérifié",
}
LOCAL_ADMIN_USERNAME = "admin-passeport-demo"
LOCAL_ADMIN_PASSWORD = os.getenv("LOCAL_ADMIN_DEMO_PASSWORD", "AdminPasseport-2026!")
LOCAL_ADMINISTRATION_CODE = "BF/GOV/DIPF/PASSEPORTS"
# HTTPS exigé par Keycloak : « none » pour la démonstration servie en HTTP (http://localhost:8180).
# Avec « external » (valeur par défaut de Keycloak), Keycloak refuse en HTTP les demandes qu'il ne
# juge pas locales : depuis la machine, à travers Docker Desktop, la connexion à la console et les
# jetons de `npm run dev` étaient refusés (« HTTPS required »). Hors démonstration : external ou all.
SSL_REQUIRED = os.getenv("KEYCLOAK_SSL_REQUIRED", "none").strip().lower()
if SSL_REQUIRED not in {"none", "external", "all"}:
    raise SystemExit(f"KEYCLOAK_SSL_REQUIRED inconnu : {SSL_REQUIRED!r} (none, external ou all)")


def request_json(path: str, token: str, *, method: str = "GET", body: object = None) -> tuple[int, object]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=10) as response:
        content = response.read()
        return response.status, json.loads(content) if content else None


def admin_token() -> str:
    data = urllib.parse.urlencode({
        "grant_type": "password",
        "client_id": "admin-cli",
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD,
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE_URL}/realms/master/protocol/openid-connect/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)["access_token"]


def require_ssl(token: str) -> None:
    """Applique SSL_REQUIRED aux realms master (console) et dlnuf (application), à chaque démarrage."""
    for realm in ("master", "dlnuf"):
        request_json(f"/admin/realms/{realm}", token, method="PUT", body={"sslRequired": SSL_REQUIRED})


def configure(token: str) -> None:
    status, profile = request_json("/admin/realms/dlnuf/users/profile", token)
    if status != 200 or not isinstance(profile, dict):
        raise RuntimeError("Keycloak returned an invalid user profile configuration")

    attributes = profile.setdefault("attributes", [])
    existing_names = {item.get("name") for item in attributes}
    for name, label in PROFILE_ATTRIBUTES.items():
        if name not in existing_names:
            attributes.append({
                "name": name,
                "displayName": label,
                "multivalued": False,
                "permissions": {"view": ["admin"], "edit": ["admin"]},
            })
    request_json("/admin/realms/dlnuf/users/profile", token, method="PUT", body=profile)

    for username, claims in DEMO_ATTRIBUTES.items():
        query = urllib.parse.urlencode({"username": username, "exact": "true"})
        _, users = request_json(f"/admin/realms/dlnuf/users?{query}", token)
        if not isinstance(users, list) or len(users) != 1:
            raise RuntimeError(f"Expected exactly one Keycloak demo user: {username}")
        user = users[0]
        user_attributes = user.get("attributes") or {}
        user["attributes"] = user_attributes
        if username == "citoyen-demo" and not demo_phone:
            user_attributes.pop("phone_number", None)
        user_attributes.update(claims)
        request_json(f"/admin/realms/dlnuf/users/{user['id']}", token, method="PUT", body=user)

    role_path = "/admin/realms/dlnuf/roles/local-admin"
    try:
        _, local_admin_role = request_json(role_path, token)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        request_json("/admin/realms/dlnuf/roles", token, method="POST", body={
            "name": "local-admin",
            "description": "Administrateur habilité de son administration locale",
        })
        _, local_admin_role = request_json(role_path, token)

    query = urllib.parse.urlencode({"username": LOCAL_ADMIN_USERNAME, "exact": "true"})
    _, users = request_json(f"/admin/realms/dlnuf/users?{query}", token)
    if not isinstance(users, list):
        raise RuntimeError("Keycloak returned an invalid local-admin user list")
    if users:
        admin_user = users[0]
        admin_user["enabled"] = True
        attrs = admin_user.get("attributes") or {}
        attrs["administration_code"] = [LOCAL_ADMINISTRATION_CODE]
        admin_user["attributes"] = attrs
        request_json(f"/admin/realms/dlnuf/users/{admin_user['id']}", token, method="PUT", body=admin_user)
    else:
        request_json("/admin/realms/dlnuf/users", token, method="POST", body={
            "username": LOCAL_ADMIN_USERNAME,
            "firstName": "Administrateur local",
            "lastName": "Passeport Demo",
            "email": "admin-passeport-demo@example.test",
            "enabled": True,
            "emailVerified": True,
            "attributes": {"administration_code": [LOCAL_ADMINISTRATION_CODE]},
            "credentials": [{"type": "password", "value": LOCAL_ADMIN_PASSWORD, "temporary": False}],
        })
        _, users = request_json(f"/admin/realms/dlnuf/users?{query}", token)
        if not isinstance(users, list) or len(users) != 1:
            raise RuntimeError("Keycloak did not return the created local-admin account")
        admin_user = users[0]

    _, mapped_roles = request_json(f"/admin/realms/dlnuf/users/{admin_user['id']}/role-mappings/realm", token)
    if not any(role.get("name") == "local-admin" for role in mapped_roles or []):
        request_json(f"/admin/realms/dlnuf/users/{admin_user['id']}/role-mappings/realm",
                     token, method="POST", body=[local_admin_role])


def main() -> None:
    token = None
    for attempt in range(1, 61):
        try:
            token = admin_token()
            require_ssl(token)
            configure(token)
            print(f"HTTPS exigé : {SSL_REQUIRED} (realms master et dlnuf).", flush=True)
            print("Profil et claims des comptes Keycloak de démonstration configurés.", flush=True)
            return
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as error:
            if attempt == 60:
                raise SystemExit(f"Configuration Keycloak impossible après 60 tentatives: {error}")
            print(f"Keycloak pas encore prêt ({attempt}/60). Nouvelle tentative.", flush=True)
            time.sleep(2)


if __name__ == "__main__":
    main()
