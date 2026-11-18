"""Provision the Keycloak service client used by agent-management routes."""

from __future__ import annotations

import os
import time

import httpx


BASE_URL = os.getenv("KEYCLOAK_ADMIN_URL", "http://keycloak:8080").rstrip("/")
ADMIN_USERNAME = os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "")
REALM = os.getenv("KEYCLOAK_REALM", "dlnuf")
CLIENT_ID = os.getenv("KEYCLOAK_ADMIN_CLIENT_ID", "dlnuf-admin-api")
CLIENT_SECRET = os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET", "")


def provision() -> None:
    if not ADMIN_PASSWORD or not CLIENT_SECRET:
        raise SystemExit("Configurez KEYCLOAK_ADMIN_PASSWORD et KEYCLOAK_ADMIN_CLIENT_SECRET dans .env.")
    token_response = httpx.post(
        f"{BASE_URL}/realms/master/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": "admin-cli",
              "username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    token_response.raise_for_status()
    token = token_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=10) as client:
        clients = client.get(f"/admin/realms/{REALM}/clients", params={"clientId": CLIENT_ID})
        clients.raise_for_status()
        existing = clients.json()
        client_representation = {
            "clientId": CLIENT_ID,
            "name": "DLNUF scoped agent management API",
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": False,
            "clientAuthenticatorType": "client-secret",
            "secret": CLIENT_SECRET,
            "serviceAccountsEnabled": True,
            "standardFlowEnabled": False,
            "directAccessGrantsEnabled": False,
        }
        if existing:
            client_uuid = existing[0]["id"]
            client_representation.update(existing[0])
            client_representation["secret"] = CLIENT_SECRET
            client.put(f"/admin/realms/{REALM}/clients/{client_uuid}", json=client_representation).raise_for_status()
        else:
            created = client.post(f"/admin/realms/{REALM}/clients", json=client_representation)
            created.raise_for_status()
            location = created.headers.get("Location", "").rstrip("/")
            client_uuid = location.rsplit("/", 1)[-1]
            if not client_uuid:
                lookup = client.get(f"/admin/realms/{REALM}/clients", params={"clientId": CLIENT_ID})
                lookup.raise_for_status()
                client_uuid = lookup.json()[0]["id"]

        service_account = client.get(f"/admin/realms/{REALM}/clients/{client_uuid}/service-account-user")
        service_account.raise_for_status()
        service_user_id = service_account.json()["id"]
        management_clients = client.get(f"/admin/realms/{REALM}/clients", params={"clientId": "realm-management"})
        management_clients.raise_for_status()
        management_id = management_clients.json()[0]["id"]
        roles = []
        for role_name in ("manage-users", "view-realm"):
            role_response = client.get(f"/admin/realms/{REALM}/clients/{management_id}/roles/{role_name}")
            role_response.raise_for_status()
            roles.append(role_response.json())
        mapped = client.get(
            f"/admin/realms/{REALM}/users/{service_user_id}/role-mappings/clients/{management_id}"
        )
        mapped.raise_for_status()
        current = {role["id"] for role in mapped.json()}
        missing = [role for role in roles if role["id"] not in current]
        if missing:
            client.post(
                f"/admin/realms/{REALM}/users/{service_user_id}/role-mappings/clients/{management_id}",
                json=missing,
            ).raise_for_status()


def main() -> None:
    for attempt in range(1, 31):
        try:
            provision()
            print("Client Keycloak de gestion des comptes agents configuré.", flush=True)
            return
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as error:
            if attempt == 30:
                raise SystemExit(f"Configuration du client Keycloak impossible: {error}") from error
            time.sleep(2)


if __name__ == "__main__":
    main()
