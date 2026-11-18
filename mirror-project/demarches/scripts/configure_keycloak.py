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

DEMO_AGENT_PHONE = os.getenv("DEMO_AGENT_PHONE", "70000000")
DEMO_PASSPORT_AGENT_PHONE = os.getenv("DEMO_PASSPORT_AGENT_PHONE", "60000000")
DEMO_LOCAL_ADMIN_PHONE = os.getenv("DEMO_LOCAL_ADMIN_PHONE", "50000000")
DEMO_PIN = os.getenv("DEMO_ADMIN_PIN", "1234")

DEMO_ATTRIBUTES = {"citoyen-demo": {"phone_number_verified": ["false"]}}

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
LOCAL_ADMIN_USERNAME = DEMO_LOCAL_ADMIN_PHONE
LOCAL_ADMIN_PASSWORD = DEMO_PIN
LOCAL_ADMINISTRATION_CODE = "BF/GOV/DIPF/PASSEPORTS"


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


def configure(token: str) -> None:
    request_json("/admin/realms/dlnuf", token, method="PUT", body={
        "bruteForceProtected": True, "permanentLockout": False,
        "failureFactor": 5, "waitIncrementSeconds": 60,
        "maxFailureWaitSeconds": 900, "maxDeltaTimeSeconds": 900,
    })
    status, profile = request_json("/admin/realms/dlnuf/users/profile", token)
    if status != 200 or not isinstance(profile, dict):
        raise RuntimeError("Keycloak returned an invalid user profile configuration")

    attributes = profile.setdefault("attributes", [])
    # Le parcours national ne demande que le téléphone et le PIN.
    # Ne pas imposer une adresse e-mail ou des noms factices pour autoriser le login.
    for attribute in attributes:
        if attribute.get("name") in {"email", "firstName", "lastName"}:
            attribute.pop("required", None)
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
        if not isinstance(users, list):
            raise RuntimeError(f"Keycloak returned an invalid demo user list: {username}")
        if not users and username != "citoyen-demo":
            request_json("/admin/realms/dlnuf/users", token, method="POST", body={
                "username": username,
                "enabled": True,
                "emailVerified": True,
                "attributes": claims,
                "credentials": [{"type": "password", "value": DEMO_PIN, "temporary": False}],
            })
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
        if username != "citoyen-demo":
            request_json(
                f"/admin/realms/dlnuf/users/{user['id']}/reset-password",
                token,
                method="PUT",
                body={"type": "password", "value": DEMO_PIN, "temporary": False},
            )
            _, local_admin_role = request_json("/admin/realms/dlnuf/roles/local-admin", token)
            _, mapped_roles = request_json(f"/admin/realms/dlnuf/users/{user['id']}/role-mappings/realm", token)
            mapped_names = {role.get("name") for role in mapped_roles or []}
            if "local-admin" not in mapped_names:
                request_json(
                    f"/admin/realms/dlnuf/users/{user['id']}/role-mappings/realm",
                    token,
                    method="POST",
                    body=[local_admin_role],
                )
            if "agent" in mapped_names:
                _, agent_role = request_json("/admin/realms/dlnuf/roles/agent", token)
                request_json(
                    f"/admin/realms/dlnuf/users/{user['id']}/role-mappings/realm",
                    token,
                    method="DELETE",
                    body=[agent_role],
                )

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

    from scripts.local_administrators import ensure_local_administrators
    ensure_local_administrators(token)


def main() -> None:
    token = None
    for attempt in range(1, 61):
        try:
            token = admin_token()
            configure(token)
            print("Profil et claims des comptes Keycloak de démonstration configurés.", flush=True)
            return
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as error:
            detail = f": {error}"
            if isinstance(error, urllib.error.HTTPError):
                try:
                    detail = f" HTTP {error.code}: {error.read().decode('utf-8', 'replace')}"
                except Exception:
                    detail = f" HTTP {error.code}: {error.reason}"
            if attempt == 60:
                raise SystemExit(f"Configuration Keycloak impossible après 60 tentatives{detail}")
            print(f"Keycloak pas encore prêt ({attempt}/60). Nouvelle tentative.{detail}", flush=True)
            time.sleep(2)


if __name__ == "__main__":
    main()
