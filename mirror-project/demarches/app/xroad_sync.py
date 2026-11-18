"""Synchronisation limitée entre les actions métier et le banc X-Road."""

from __future__ import annotations

import os
from urllib.parse import urlsplit, urlunsplit

import httpx
from connectors.administrations import administration_connection


class XRoadSyncError(RuntimeError):
    pass


class XRoadSync:
    def __init__(self) -> None:
        self.enabled = os.getenv("XROAD_SYNC_ENABLED", "false").strip().lower() == "true"
        self.base_url = os.getenv("XROAD_ADMIN_URL", "https://ss-registres:4000").rstrip("/")
        self.username = os.getenv("XROAD_ADMIN_USER", "xrd")
        self.password = os.getenv("XROAD_ADMIN_PASSWORD", "secret")
        self.client = httpx.Client(base_url=self.base_url, verify=False, timeout=15.0)
        self.xsrf: str | None = None

    def _connection(self, code: str):
        try:
            return administration_connection(code)
        except ValueError as error:
            raise XRoadSyncError(str(error)) from error

    def _use_server(self, administration) -> None:
        # The hosting server is a location, never a business role.
        primary = urlsplit(os.getenv("XROAD_ADMIN_URL", "https://ss-registres:4000"))
        key = "XROAD_ADMIN_URL_" + administration.server.upper().replace("-", "_")
        url = os.getenv(key)
        if not url:
            netloc = administration.server + (f":{primary.port}" if primary.port else "")
            url = urlunsplit((primary.scheme, netloc, primary.path, "", ""))
        url = url.rstrip("/")
        if url != self.base_url:
            self.client.close()
            self.base_url = url
            self.client = httpx.Client(base_url=url, verify=False, timeout=15.0)
            self.xsrf = None

    def login(self) -> None:
        response = self.client.post("/login", data={"username": self.username, "password": self.password})
        if response.status_code != 200:
            raise XRoadSyncError(f"Connexion X-Road refusée (HTTP {response.status_code})")
        self.xsrf = self.client.cookies.get("XSRF-TOKEN")

    def request(self, method: str, path: str, *, ok: tuple[int, ...] = (200, 201, 204), json: object = None):
        headers = {"X-XSRF-TOKEN": self.xsrf} if self.xsrf else {}
        response = self.client.request(method, path, headers=headers, json=json)
        if response.status_code == 401:
            self.login()
            response = self.client.request(
                method,
                path,
                headers={"X-XSRF-TOKEN": self.xsrf} if self.xsrf else {},
                json=json,
            )
        if response.status_code not in ok:
            raise XRoadSyncError(f"X-Road {method} {path}: HTTP {response.status_code} {response.text[:300]}")
        return response

    def publish_service(self, provider_code: str, service_code: str, base_url: str | None = None) -> None:
        if not self.enabled:
            return
        provider = self._connection(provider_code)
        service_url = (base_url or provider.base_url or "").rstrip("/")
        if not service_url:
            raise XRoadSyncError("Configurez l'URL du registre avant de publier un service")
        self._use_server(provider)
        self.login()
        client = provider.client_key
        descriptions = self.request("GET", f"/api/v1/clients/{client}/service-descriptions").json()
        published = {
            service["service_code"]
            for description in descriptions or []
            for service in description.get("services", [])
        }
        if service_code in published:
            return
        description = self.request(
            "POST",
            f"/api/v1/clients/{client}/service-descriptions",
            ok=(200, 201),
            json={
                "url": f"{service_url}/services/{service_code}",
                "type": "REST",
                "rest_service_code": service_code,
            },
        ).json()
        self.request(
            "PUT",
            f"/api/v1/service-descriptions/{description['id']}/enable",
            ok=(200, 204, 409),
        )

    def set_service_active(self, provider_code: str, service_code: str, active: bool) -> None:
        if not self.enabled:
            return
        provider = self._connection(provider_code)
        self._use_server(provider)
        self.login()
        client = provider.client_key
        descriptions = self.request("GET", f"/api/v1/clients/{client}/service-descriptions").json()
        for description in descriptions or []:
            for service in description.get("services", []):
                if service.get("service_code") != service_code:
                    continue
                path = f"/api/v1/service-descriptions/{description['id']}/{'enable' if active else 'disable'}"
                self.request("PUT", path, ok=(200, 204, 409))
                return

    def grant_access(self, consumer_code: str, provider_code: str, service_code: str) -> None:
        if not self.enabled:
            return
        consumer = self._connection(consumer_code)
        provider = self._connection(provider_code)
        self._use_server(provider)
        self.login()
        consumer_id = consumer.client_key
        provider_id = provider.client_key
        path = f"/api/v1/clients/{provider_id}/service-clients/{consumer_id}/access-rights"
        response = self.request("GET", path, ok=(200, 404))
        rights = response.json() if response.status_code == 200 else []
        if any(right.get("service_code") == service_code for right in rights):
            return
        self.request("POST", path, ok=(200, 201), json={"items": [{"service_code": service_code}]})

    def revoke_access(self, consumer_code: str, provider_code: str, service_code: str) -> None:
        if not self.enabled:
            return
        consumer = self._connection(consumer_code)
        provider = self._connection(provider_code)
        self._use_server(provider)
        self.login()
        consumer_id = consumer.client_key
        provider_id = provider.client_key
        path = f"/api/v1/clients/{provider_id}/service-clients/{consumer_id}/access-rights"
        self.request("POST", f"{path}/delete", ok=(200, 204, 404), json={"items": [{"service_code": service_code}]})
