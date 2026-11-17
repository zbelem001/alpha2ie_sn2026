"""Narrow Keycloak Admin API client used for administration-owned agent accounts."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException


class KeycloakAdminClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("KEYCLOAK_ADMIN_URL", "http://keycloak:8080").rstrip("/")
        self.realm = os.getenv("KEYCLOAK_REALM", "dlnuf")
        self.client_id = os.getenv("KEYCLOAK_ADMIN_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET", "").strip()
        if not self.client_id or not self.client_secret:
            raise HTTPException(
                status_code=503,
                detail="La gestion des comptes agents nécessite le client de service Keycloak configuré.",
            )

    def _request(self, method: str, path: str, *, json: object | None = None, params: dict | None = None) -> httpx.Response:
        try:
            token_response = httpx.post(
                f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=8,
            )
            token_response.raise_for_status()
            token = token_response.json()["access_token"]
            response = httpx.request(
                method,
                f"{self.base_url}/admin/realms/{self.realm}{path}",
                headers={"Authorization": f"Bearer {token}"},
                json=json,
                params=params,
                timeout=8,
            )
            if response.status_code >= 400:
                raise HTTPException(status_code=502, detail="Keycloak a refusé l’opération de gestion du compte agent.")
            return response
        except HTTPException:
            raise
        except (httpx.HTTPError, KeyError, ValueError) as error:
            raise HTTPException(status_code=502, detail="Le service de gestion des comptes Keycloak est indisponible.") from error

    def list_agents(self, administration_code: str) -> list[dict]:
        response = self._request("GET", "/users", params={"max": 1000})
        users = response.json()
        return [
            self._serialize_user(user)
            for user in users
            if administration_code in (user.get("attributes") or {}).get("administration_code", [])
            and (user.get("attributes") or {}).get("account_kind", []) == ["agent"]
        ]

    @staticmethod
    def _serialize_user(user: dict) -> dict:
        attributes = user.get("attributes") or {}
        created_timestamp = user.get("createdTimestamp")
        return {
            "id": user["id"],
            "name": " ".join(part for part in [user.get("firstName"), user.get("lastName")] if part).strip(),
            "phone": (attributes.get("phone_number") or [user.get("username", "")])[0],
            "active": bool(user.get("enabled")),
            "created_at": (datetime.fromtimestamp(created_timestamp / 1000, timezone.utc).isoformat()
                           if isinstance(created_timestamp, (int, float)) else None),
        }

    def create_agent(self, *, name: str, phone: str, pin: str, administration_code: str) -> dict:
        existing = self._request("GET", "/users", params={"username": phone, "exact": "true"}).json()
        if existing:
            raise HTTPException(status_code=409, detail="Un compte utilise déjà ce numéro de téléphone.")
        response = self._request(
            "POST",
            "/users",
            json={
                "username": phone,
                "firstName": name,
                "enabled": True,
                "attributes": {
                    "administration_code": [administration_code],
                    "phone_number": [phone],
                    "phone_number_verified": ["false"],
                    "account_kind": ["agent"],
                },
                "credentials": [{"type": "password", "value": pin, "temporary": False}],
            },
        )
        if response.status_code != 201:
            raise HTTPException(status_code=502, detail="Keycloak n’a pas créé le compte agent.")
        location = response.headers.get("Location", "").rstrip("/")
        user_id = location.rsplit("/", 1)[-1]
        if not user_id:
            raise HTTPException(status_code=502, detail="Keycloak n’a pas retourné la référence du compte créé.")
        role = self._request("GET", "/roles/agent").json()
        self._request("POST", f"/users/{user_id}/role-mappings/realm", json=[role])
        return {"id": user_id, "name": name, "phone": phone, "active": True, "created_at": None}

    def set_agent_enabled(self, user_id: str, enabled: bool, administration_code: str) -> dict:
        user = self._get_owned_agent(user_id, administration_code)
        user["enabled"] = enabled
        self._request("PUT", f"/users/{user_id}", json=user)
        return self._serialize_user(user)

    def reset_agent_pin(self, user_id: str, pin: str, administration_code: str) -> None:
        self._get_owned_agent(user_id, administration_code)
        self._request(
            "PUT",
            f"/users/{user_id}/reset-password",
            json={"type": "password", "value": pin, "temporary": False},
        )

    def _get_owned_agent(self, user_id: str, administration_code: str) -> dict:
        user = self._request("GET", f"/users/{user_id}").json()
        attributes = user.get("attributes") or {}
        if administration_code not in attributes.get("administration_code", []) or attributes.get("account_kind") != ["agent"]:
            raise HTTPException(status_code=404, detail="Compte agent introuvable dans cette administration.")
        return user
