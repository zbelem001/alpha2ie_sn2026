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
    "citoyen-demo": {},
}
demo_phone = os.getenv("CITIZEN_DEMO_PHONE", "").strip()
if demo_phone:
    DEMO_ATTRIBUTES["citoyen-demo"].update({
        "phone_number": [demo_phone],
        "phone_number_verified": ["true"],
    })

PROFILE_ATTRIBUTES = {
    "administration_code": "Code de l’administration",
    "citizen_ref": "Référence citoyen",
    "phone_number": "Numéro de téléphone vérifié",
    "phone_number_verified": "Téléphone vérifié",
}


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
        user_attributes.update(claims)
        request_json(f"/admin/realms/dlnuf/users/{user['id']}", token, method="PUT", body=user)


def main() -> None:
    token = None
    for attempt in range(1, 61):
        try:
            token = admin_token()
            configure(token)
            print("Profil et claims des comptes Keycloak de démonstration configurés.", flush=True)
            return
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as error:
            if attempt == 60:
                raise SystemExit(f"Configuration Keycloak impossible après 60 tentatives: {error}")
            print(f"Keycloak pas encore prêt ({attempt}/60). Nouvelle tentative.", flush=True)
            time.sleep(2)


if __name__ == "__main__":
    main()
