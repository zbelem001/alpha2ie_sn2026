"""Configuration automatique du banc X-Road « BF » par les API REST.

Lancé automatiquement par `docker compose --profile xroad up -d` (service
xroad-setup), en même temps que les serveurs : il attend qu'ils répondent.
À la main, depuis mirror-project/ :
    docker compose --profile xroad run --rm xroad-setup

Relançable : chaque étape vérifie d'abord si elle est déjà faite. Les attentes
sont normales : une modification du serveur central n'atteint les Security
Servers qu'avec la configuration globale suivante (une à deux minutes).

Suit l'ordre de development/hurl/scenarios/setup.hurl du dépôt X-Road (7.8.3,
licence MIT), adapté à notre réseau : instance BF, classe GOV, nos
administrations et nos registres simulés.
"""

from __future__ import annotations

import os
import sys
import time
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

# --- Réseau simulé ------------------------------------------------------------------

INSTANCE = "BF"
MEMBER_CLASS = "GOV"
CS_HOST = "xroad-cs"
CA_URL = "http://xroad-ca:8888"
TSA_URL = "http://xroad-ca:8899"
ACME_URL = "http://xroad-ca:8887"
CA_CERTS = Path(os.environ.get("XROAD_CA_CERTS_DIR", "/ca"))

# Démarrage à froid des quatre serveurs Java : 5 à 9 minutes mesurées. On attend
# jusqu'à 12 minutes que leur interface d'administration réponde.
STARTUP_TRIES = 72

ADMIN_USER = os.environ.get("XROAD_ADMIN_USER", "xrd")
ADMIN_PASSWORD = os.environ.get("XROAD_ADMIN_PASSWORD", "secret")
TOKEN_PIN = os.environ.get("XROAD_TOKEN_PIN", "Secret1234")

MEMBERS = {
    "CENTRALE": "Centrale de confiance",
    "ONI": "Office national d'identification",
    "FONCTION-PUBLIQUE": "Ministère de la Fonction publique",
    "MAIRIE-OUAGA": "Mairie de Ouagadougou",
    "TRANSPORT": "Direction générale des transports",
    "JUSTICE": "Ministère de la Justice",
    "POLICE": "Police nationale",
    "TRESOR": "Trésor public",
    "DIPF": "Direction de l'Immigration et de la Police des Frontières",
}

MANAGEMENT_SUBSYSTEM = ("CENTRALE", "MANAGEMENT")


@dataclass(frozen=True)
class Provider:
    member: str
    subsystem: str
    base_url: str
    services: tuple[str, ...]
    # Serveur de sécurité qui héberge le sous-système (l'ONI fournit et demande : ss-demandeurs).
    host: str = "ss-registres"


@dataclass(frozen=True)
class Consumer:
    member: str
    subsystem: str
    # (membre fournisseur, sous-système, service) autorisés : les « conventions » du banc.
    allowed: tuple[tuple[str, str, str], ...]


# Chaque service est publié à l'adresse de la garde de la couche consentement-minimisation,
# placée devant le registre : accord vérifié (en-tête X-Consent-Id), réponse réduite, journal.
GUARD = "http://consentement-minimisation:8000/holders"

PROVIDERS = (
    Provider("MAIRIE-OUAGA", "ETAT-CIVIL", f"{GUARD}/etat-civil", ("identity", "identity-match", "is-adult")),
    Provider("TRANSPORT", "PERMIS", f"{GUARD}/transport", ("driving-licence",)),
    Provider("JUSTICE", "REGISTRES", f"{GUARD}/justice", ("nationality", "criminal-record", "criminal-record-current")),
    Provider("POLICE", "PERTES", f"{GUARD}/police", ("loss-declaration",)),
    Provider("TRESOR", "PAIEMENTS", f"{GUARD}/tresor", ("payment-status",)),
    # Registre CNIB de l'ONI : le sous-système ONI/CNIB, déjà demandeur, devient aussi fournisseur.
    Provider("ONI", "CNIB", f"{GUARD}/oni", ("cnib-status",), host="ss-demandeurs"),
)

CONSUMERS = (
    # Démarche CNIB : ni casier, ni permis.
    Consumer(
        "ONI",
        "CNIB",
        (
            ("MAIRIE-OUAGA", "ETAT-CIVIL", "identity"),
            ("MAIRIE-OUAGA", "ETAT-CIVIL", "identity-match"),
            ("MAIRIE-OUAGA", "ETAT-CIVIL", "is-adult"),
            ("JUSTICE", "REGISTRES", "nationality"),
            ("POLICE", "PERTES", "loss-declaration"),
            ("TRESOR", "PAIEMENTS", "payment-status"),
        ),
    ),
    # Démarche « prise de service » du guide : majorité, nationalité, casier.
    Consumer(
        "FONCTION-PUBLIQUE",
        "RECRUTEMENT",
        (
            ("MAIRIE-OUAGA", "ETAT-CIVIL", "is-adult"),
            ("JUSTICE", "REGISTRES", "nationality"),
            ("JUSTICE", "REGISTRES", "criminal-record"),
        ),
    ),
    # Démarche « passeport ordinaire » : CNIB, acte de naissance, nationalité, bulletin n° 3, timbre.
    Consumer(
        "DIPF",
        "PASSEPORTS",
        (
            ("ONI", "CNIB", "cnib-status"),
            ("MAIRIE-OUAGA", "ETAT-CIVIL", "identity"),
            ("JUSTICE", "REGISTRES", "nationality"),
            ("JUSTICE", "REGISTRES", "criminal-record-current"),
            ("TRESOR", "PAIEMENTS", "payment-status"),
        ),
    ),
)


@dataclass(frozen=True)
class SecurityServerSpec:
    host: str
    code: str
    owner: str
    clients: tuple[tuple[str, str], ...] = field(default=())


SECURITY_SERVERS = (
    SecurityServerSpec(
        host="ss-registres",
        code="SS-REGISTRES",
        owner="CENTRALE",
        clients=tuple((p.member, p.subsystem) for p in PROVIDERS if p.host == "ss-registres"),
    ),
    SecurityServerSpec(
        host="ss-demandeurs",
        code="SS-DEMANDEURS",
        owner="ONI",
        # Demandeurs, et fournisseurs hébergés ici (ONI/CNIB), chacun une fois.
        clients=tuple(dict.fromkeys([(c.member, c.subsystem) for c in CONSUMERS]
                                    + [(p.member, p.subsystem) for p in PROVIDERS if p.host == "ss-demandeurs"])),
    ),
)

MANAGEMENT_SERVICE_CODES = (
    "authCertDeletion",
    "clientDeletion",
    "clientReg",
    "ownerChange",
    "clientEnable",
    "clientDisable",
    "addressChange",
    "clientRename",
    "maintenanceModeEnable",
    "maintenanceModeDisable",
)


def member_id(member: str) -> str:
    return f"{INSTANCE}:{MEMBER_CLASS}:{member}"


def subsystem_id(member: str, subsystem: str) -> str:
    return f"{INSTANCE}:{MEMBER_CLASS}:{member}:{subsystem}"


# --- Outils ---------------------------------------------------------------------------


def log(message: str) -> None:
    print(message, flush=True)


class ApiError(RuntimeError):
    pass


class Api:
    """Session sur l'interface d'administration d'un serveur X-Road (port 4000)."""

    def __init__(self, host: str) -> None:
        self.host = host
        self.client = httpx.Client(base_url=f"https://{host}:4000", verify=False, timeout=120)
        self.xsrf: str | None = None

    def login(self) -> None:
        response = self.client.post("/login", data={"username": ADMIN_USER, "password": ADMIN_PASSWORD})
        if response.status_code != 200:
            raise ApiError(f"{self.host} : connexion refusée (HTTP {response.status_code})")
        self.xsrf = self.client.cookies.get("XSRF-TOKEN")

    def request(self, method: str, path: str, *, ok: tuple[int, ...] = (200, 201, 204), **kwargs: Any) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        if self.xsrf:
            headers["X-XSRF-TOKEN"] = self.xsrf
        response = self.client.request(method, path, headers=headers, **kwargs)
        if response.status_code == 401:
            self.login()
            headers["X-XSRF-TOKEN"] = self.xsrf or ""
            response = self.client.request(method, path, headers=headers, **kwargs)
        if response.status_code not in ok:
            raise ApiError(f"{self.host} {method} {path} : HTTP {response.status_code} {response.text[:300]}")
        return response

    def get(self, path: str, **kwargs: Any) -> Any:
        response = self.request("GET", path, **kwargs)
        return response.json() if response.content else None

    def post(self, path: str, **kwargs: Any) -> Any:
        response = self.request("POST", path, **kwargs)
        try:
            return response.json() if response.content else None
        except ValueError:
            return response.text

    def put(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Any:
        response = self.request("PATCH", path, **kwargs)
        return response.json() if response.content else None


def eventually(description: str, action: Callable[[], Any], *, tries: int = 40, delay: float = 10) -> Any:
    """Réessaie une étape qui dépend de la propagation de la configuration globale."""
    for attempt in range(1, tries + 1):
        try:
            return action()
        except (ApiError, httpx.HTTPError, KeyError, IndexError, StopIteration) as exc:
            if attempt == tries:
                raise ApiError(f"Abandon : {description} ({exc})") from exc
            if attempt == 1 or attempt % 3 == 0:
                log(f"      … en attente : {description} ({str(exc)[:160]})")
            time.sleep(delay)
    raise AssertionError("inaccessible")


def sign_csr(csr_pem: str, kind: str) -> str:
    """Fait signer une demande de certificat par l'autorité de test (kind : auth ou sign)."""
    response = httpx.post(
        f"{CA_URL}/testca/sign",
        data={"type": kind},
        files={"certreq": (f"{kind}.csr.pem", csr_pem.encode(), "application/octet-stream")},
        timeout=60,
    )
    if response.status_code != 200:
        raise ApiError(f"Autorité de test : HTTP {response.status_code} {response.text[:200]}")
    return response.text


# --- Serveur central -------------------------------------------------------------------


def setup_central_server() -> tuple[Api, bytes]:
    log("1. Serveur central")
    cs = Api(CS_HOST)
    eventually("interface du serveur central", cs.login, tries=STARTUP_TRIES)

    def token_status() -> str:
        value = cs.get("/api/v1/initialization/status")["software_token_init_status"]
        if value == "UNKNOWN":
            raise ApiError("module de signature pas encore prêt")
        return value

    if eventually("état du serveur central", token_status) == "NOT_INITIALIZED":
        cs.post(
            "/api/v1/initialization",
            json={"software_token_pin": TOKEN_PIN, "instance_identifier": INSTANCE, "central_server_address": CS_HOST},
        )
        log(f"   instance {INSTANCE} initialisée")
    else:
        log("   déjà initialisé")

    classes = {item["code"] for item in cs.get("/api/v1/member-classes")}
    if MEMBER_CLASS not in classes:
        cs.post("/api/v1/member-classes", json={"code": MEMBER_CLASS, "description": "Administrations publiques"})
        log(f"   classe {MEMBER_CLASS} ajoutée")

    cs.request("PUT", "/api/v1/tokens/0/login", json={"password": TOKEN_PIN}, ok=tuple(range(200, 500)))

    tokens = cs.get("/api/v1/tokens")
    sources = {key.get("source_type") for token in tokens for key in token.get("configuration_signing_keys") or []}
    for source in ("INTERNAL", "EXTERNAL"):
        if source not in sources:
            cs.post(
                f"/api/v1/configuration-sources/{source}/signing-keys",
                json={"key_label": f"{source.capitalize()} signing key", "token_id": 0},
            )
            log(f"   clé de signature {source} créée")

    for code, name in MEMBERS.items():
        if cs.request("GET", f"/api/v1/members/{member_id(code)}", ok=(200, 404)).status_code == 404:
            cs.post(
                "/api/v1/members",
                json={"member_id": {"member_class": MEMBER_CLASS, "member_code": code}, "member_name": name},
            )
            log(f"   membre {member_id(code)} ajouté")

    management_id = subsystem_id(*MANAGEMENT_SUBSYSTEM)
    config = cs.get("/api/v1/management-services-configuration")
    # L'identifiant revient préfixé par son type : « SUBSYSTEM:BF:GOV:CENTRALE:MANAGEMENT ».
    if not str(config.get("service_provider_id", "")).endswith(management_id):
        cs.request(
            "POST",
            "/api/v1/subsystems",
            json={
                "subsystem_id": {
                    "member_class": MEMBER_CLASS,
                    "member_code": MANAGEMENT_SUBSYSTEM[0],
                    "subsystem_code": MANAGEMENT_SUBSYSTEM[1],
                }
            },
            ok=(200, 201, 409),
        )
        cs.patch("/api/v1/management-services-configuration", json={"service_provider_id": management_id})
        log(f"   services de gestion confiés à {management_id}")

    if not cs.get("/api/v1/certification-services"):
        ca = cs.post(
            "/api/v1/certification-services",
            data={
                "certificate_profile_info": "ee.ria.xroad.common.certificateprofile.impl.FiVRKCertificateProfileInfoProvider",
                "tls_auth": "false",
                "default_csr_format": "DER",
                "acme_server_directory_url": ACME_URL,
            },
            files={"certificate": ("ca.pem", (CA_CERTS / "ca.pem").read_bytes())},
        )
        cs.post(
            f"/api/v1/certification-services/{ca['id']}/ocsp-responders",
            data={"url": CA_URL, "cost_type": "FREE"},
            files={"certificate": ("ocsp.pem", (CA_CERTS / "ocsp.pem").read_bytes())},
        )
        log("   autorité de certification de test et OCSP déclarés")

    if not cs.get("/api/v1/timestamping-services"):
        cs.post(
            "/api/v1/timestamping-services",
            data={"url": TSA_URL, "cost_type": "FREE"},
            files={"certificate": ("tsa.pem", (CA_CERTS / "tsa.pem").read_bytes())},
        )
        log("   service d'horodatage déclaré")

    anchor = eventually(
        "première configuration globale",
        lambda: cs.request("GET", "/api/v1/configuration-sources/INTERNAL/anchor/download").content,
    )
    return cs, anchor


def server_code(request: dict[str, Any]) -> str:
    """Code du Security Server concerné par une demande de gestion (objet ou chaîne selon la version)."""
    server = request.get("security_server_id")
    if isinstance(server, dict):
        return server.get("server_code") or str(server.get("encoded_id", "")).split(":")[-1]
    return str(server or "").split(":")[-1]


def approve_pending(
    cs: Api, matches: Callable[[dict[str, Any]], bool], description: str, *, wait: bool = True
) -> None:
    """Approuve, côté serveur central, la demande en attente qui correspond.

    wait=False : la demande a pu être approuvée lors d'un passage précédent ; on approuve
    seulement si elle est encore en attente.
    """

    def find_and_approve() -> bool:
        data = cs.get("/api/v1/management-requests", params={"status": "WAITING", "sort": "id", "desc": "true"})
        pending = [item for item in data.get("items", []) if item.get("status") == "WAITING" and matches(item)]
        if not pending:
            if wait:
                raise ApiError("demande pas encore reçue")
            return False
        for item in pending:
            cs.post(f"/api/v1/management-requests/{item['id']}/approval")
        return True

    if eventually(f"approbation : {description}", find_and_approve, tries=30, delay=5):
        log(f"   approuvé par le serveur central : {description}")


# --- Security Servers -------------------------------------------------------------------


def keys_of(ss: Api) -> list[dict[str, Any]]:
    return ss.get("/api/v1/tokens/0").get("keys", [])


def find_cert(ss: Api, usage: str, owner: str | None = None) -> dict[str, Any] | None:
    for key in keys_of(ss):
        if key.get("usage") != usage:
            continue
        for cert in key.get("certificates", []):
            if owner is None or cert.get("owner_id") == owner:
                return cert
    return None


def create_certificate(ss: Api, spec: SecurityServerSpec, usage: str, ca_name: str, member: str | None) -> None:
    subject = {
        "C": "BF",
        "O": MEMBERS[member or spec.owner],
        "subjectAltName": spec.host,
        "serialNumber": f"{INSTANCE}/{spec.code}/{MEMBER_CLASS}",
    }
    request: dict[str, Any] = {
        "key_usage_type": usage,
        "ca_name": ca_name,
        "csr_format": "DER",
        "subject_field_values": {**subject, "CN": spec.host if usage == "AUTHENTICATION" else member},
    }
    if usage == "SIGNING":
        request["member_id"] = member_id(member or spec.owner)
    created = ss.post(
        "/api/v1/tokens/0/keys-with-csrs",
        json={"key_label": f"{usage.lower()} {member or spec.host}", "csr_generate_request": request},
    )
    key_id, csr_id = created["key"]["id"], created["csr_id"]
    csr_pem = ss.request("GET", f"/api/v1/keys/{key_id}/csrs/{csr_id}", params={"csr_format": "PEM"}).text
    certificate = sign_csr(csr_pem, "auth" if usage == "AUTHENTICATION" else "sign")
    eventually(
        "import du certificat",
        lambda: ss.post(
            "/api/v1/token-certificates",
            content=certificate.encode(),
            headers={"Content-Type": "application/octet-stream"},
        ),
        tries=12,
        delay=5,
    )


def ensure_sign_certificate(ss: Api, spec: SecurityServerSpec, member: str) -> None:
    if find_cert(ss, "SIGNING", member_id(member)) is not None:
        return
    ca_name = eventually("autorité de certification connue", lambda: ss.get("/api/v1/certificate-authorities")[0]["name"])
    create_certificate(ss, spec, "SIGNING", ca_name, member)
    log(f"   certificat de signature créé pour {member_id(member)}")


def client_status(ss: Api, client: str) -> str | None:
    for item in ss.get("/api/v1/clients", params={"show_members": "false"}) or []:
        if item.get("id") == client:
            return item.get("status")
    return None


def setup_security_server(cs: Api, anchor: bytes, spec: SecurityServerSpec) -> Api:
    log(f"2. Security Server {spec.host} (propriétaire {member_id(spec.owner)})")
    ss = Api(spec.host)
    eventually(f"interface de {spec.host}", ss.login, tries=STARTUP_TRIES)

    status = ss.get("/api/v1/initialization/status")
    if not status.get("is_anchor_imported"):
        ss.post("/api/v1/system/anchor", content=anchor, headers={"Content-Type": "application/octet-stream"})
        log("   ancre de configuration importée")
    if not status.get("is_server_code_initialized") or not status.get("is_server_owner_initialized"):
        ss.post(
            "/api/v1/initialization",
            json={
                "owner_member_class": MEMBER_CLASS,
                "owner_member_code": spec.owner,
                "security_server_code": spec.code,
                "software_token_pin": TOKEN_PIN,
                "ignore_warnings": True,
            },
        )
        log(f"   initialisé : {member_id(spec.owner)}:{spec.code}")
    ss.request("PUT", "/api/v1/tokens/0/login", json={"password": TOKEN_PIN}, ok=tuple(range(200, 500)))

    ca_name = eventually("autorité de certification connue", lambda: ss.get("/api/v1/certificate-authorities")[0]["name"])

    if find_cert(ss, "AUTHENTICATION") is None:
        create_certificate(ss, spec, "AUTHENTICATION", ca_name, None)
        log("   certificat d'authentification créé")
    # Certificat de signature du propriétaire ; ceux des membres hébergés viennent avec
    # leurs sous-systèmes (le serveur exige que le client existe avant).
    ensure_sign_certificate(ss, spec, spec.owner)

    auth = find_cert(ss, "AUTHENTICATION")
    auth_hash = auth["certificate_details"]["hash"]
    auth_status = auth.get("status") or "SAVED"
    if auth_status == "SAVED":
        ss.put(f"/api/v1/token-certificates/{auth_hash}/register", json={"address": spec.host})
    if auth_status in ("SAVED", "REGISTRATION_IN_PROGRESS"):
        approve_pending(
            cs,
            lambda item: item.get("type") == "AUTH_CERT_REGISTRATION_REQUEST"
            and server_code(item) == spec.code,
            f"certificat d'authentification de {spec.host}",
            wait=auth_status == "SAVED",
        )
    if not find_cert(ss, "AUTHENTICATION").get("active"):
        ss.put(f"/api/v1/token-certificates/{auth_hash}/activate", ok=(200, 204, 409))

    if not ss.get("/api/v1/system/timestamping-services"):
        tsa = eventually("service d'horodatage connu", lambda: ss.get("/api/v1/timestamping-services")[0])
        ss.post(
            "/api/v1/system/timestamping-services",
            json={"name": tsa["name"], "url": tsa["url"], "cost_type": tsa.get("cost_type", "FREE")},
        )
        log("   service d'horodatage configuré")
    return ss


def setup_management_services(cs: Api, ss: Api, spec: SecurityServerSpec) -> None:
    log(f"3. Services de gestion sur {spec.host}")
    server_id = f"{member_id(spec.owner)}:{spec.code}"
    config = cs.get("/api/v1/management-services-configuration")
    if not config.get("security_server_id"):
        eventually(
            "enregistrement du fournisseur des services de gestion",
            lambda: cs.post(
                "/api/v1/management-services-configuration/register-provider",
                json={"security_server_id": server_id},
            ),
        )
        log(f"   {server_id} fournit les services de gestion")
        config = cs.get("/api/v1/management-services-configuration")

    management = subsystem_id(*MANAGEMENT_SUBSYSTEM)
    if client_status(ss, management) is None:
        ss.post(
            "/api/v1/clients",
            json={
                "ignore_warnings": True,
                "client": {
                    "member_class": MEMBER_CLASS,
                    "member_code": MANAGEMENT_SUBSYSTEM[0],
                    "subsystem_code": MANAGEMENT_SUBSYSTEM[1],
                    "connection_type": "HTTP",
                },
            },
        )
    descriptions = ss.get(f"/api/v1/clients/{management}/service-descriptions")
    if not descriptions:
        description = eventually(
            "description WSDL des services de gestion",
            lambda: ss.post(
                f"/api/v1/clients/{management}/service-descriptions",
                json={"url": config["wsdl_address"], "type": "WSDL", "ignore_warnings": True},
            ),
        )
        ss.patch(
            f"/api/v1/services/{description['services'][0]['id']}",
            json={
                "ignore_warnings": True,
                "ssl_auth": False,
                "ssl_auth_all": True,
                "timeout": 60,
                "timeout_all": True,
                "url": config["services_address"],
                "url_all": True,
            },
        )
        ss.post(
            f"/api/v1/clients/{management}/service-clients/{INSTANCE}:security-server-owners/access-rights",
            json={"items": [{"service_code": code} for code in MANAGEMENT_SERVICE_CODES]},
        )
        ss.put(f"/api/v1/service-descriptions/{description['id']}/enable")
        log("   services de gestion publiés")


def register_clients(cs: Api, ss: Api, spec: SecurityServerSpec) -> None:
    log(f"4. Sous-systèmes hébergés par {spec.host}")
    for member, subsystem in spec.clients:
        client = subsystem_id(member, subsystem)
        status = client_status(ss, client)
        if status is None:
            ss.post(
                "/api/v1/clients",
                json={
                    "ignore_warnings": True,
                    "client": {
                        "member_class": MEMBER_CLASS,
                        "member_code": member,
                        "subsystem_code": subsystem,
                        "connection_type": "HTTP",
                    },
                },
            )
            status = "SAVED"
        ensure_sign_certificate(ss, spec, member)
        if status == "SAVED":
            eventually(f"demande d'enregistrement de {client}", lambda c=client: ss.put(f"/api/v1/clients/{c}/register"))
        if status in ("SAVED", "REGISTRATION_IN_PROGRESS"):
            # Une demande en attente n'indique que le serveur : on approuve celles de ce serveur.
            approve_pending(
                cs,
                lambda item: item.get("type") == "CLIENT_REGISTRATION_REQUEST"
                and server_code(item) == spec.code,
                f"sous-système {client}",
                wait=status == "SAVED",
            )
        elif status == "REGISTERED":
            log(f"   {client} déjà enregistré")


def publish_services(ss: Api, host: str) -> None:
    log(f"5. Services REST publiés par {host}")
    for provider in PROVIDERS:
        if provider.host != host:
            continue
        client = subsystem_id(provider.member, provider.subsystem)
        published = {
            service["service_code"]: (description["id"], description.get("url"))
            for description in ss.get(f"/api/v1/clients/{client}/service-descriptions") or []
            for service in description.get("services", [])
        }
        for code in provider.services:
            url = f"{provider.base_url}/services/{code}"
            if code in published:
                description_id, current_url = published[code]
                if current_url == url:
                    continue
                # Banc configuré avant la garde : le service pointait sur le registre. Il est republié
                # à la bonne adresse ; ses droits d'accès sont redonnés à l'étape suivante.
                ss.request("DELETE", f"/api/v1/service-descriptions/{description_id}")
                log(f"   {client}/{code} : ancienne adresse retirée ({current_url})")
            description = ss.post(
                f"/api/v1/clients/{client}/service-descriptions",
                json={"url": url, "type": "REST", "rest_service_code": code},
            )
            ss.put(f"/api/v1/service-descriptions/{description['id']}/enable")
            log(f"   {client}/{code} publié : {url}")


def grant_access(servers: dict[str, Api]) -> None:
    log("6. Droits d'accès (conventions du banc)")
    hosts = {(p.member, p.subsystem): p.host for p in PROVIDERS}
    for consumer in CONSUMERS:
        consumer_id = subsystem_id(consumer.member, consumer.subsystem)
        for member, subsystem, code in consumer.allowed:
            # Les droits se donnent sur le serveur de sécurité qui héberge le fournisseur.
            ss = servers[hosts[(member, subsystem)]]
            provider = subsystem_id(member, subsystem)
            path = f"/api/v1/clients/{provider}/service-clients/{consumer_id}/access-rights"

            def current(p: str = path) -> set[str]:
                # 404 tant que le demandeur n'a aucun droit sur ce fournisseur.
                response = ss.request("GET", p, ok=(200, 404))
                rights = response.json() if response.status_code == 200 else []
                return {item.get("service_code") for item in rights if isinstance(item, dict)}

            if code in current():
                continue
            eventually(
                f"droit {consumer_id} -> {provider}/{code}",
                lambda p=path, c=code: ss.post(p, json={"items": [{"service_code": c}]}),
            )
            log(f"   {consumer_id} -> {provider}/{code}")


def smoke_test() -> None:
    log("7. Vérification de bout en bout (X-Road, puis garde, puis registre)")
    base = f"http://ss-demandeurs:8080/r1/{INSTANCE}/{MEMBER_CLASS}/MAIRIE-OUAGA/ETAT-CIVIL"
    client = {"X-Road-Client": f"{INSTANCE}/{MEMBER_CLASS}/ONI/CNIB"}
    # Preuve de titularité demandée par le citoyen lui-même : ouverte sans accord enregistré.
    proof = {"request_id": "xroad-setup", "procedure": "citizen_identity_link", "parameters": {},
             "subject": {"pivot_id": "ACTE:OUAGA:2004:01234", "last_name": "KABORE", "first_names": "Awa",
                         "birth_date": "2004-03-12", "mother_name": "COMPAORE Salimata"}}

    def call() -> dict[str, Any]:
        response = httpx.post(f"{base}/identity-match", json=proof, headers=client, timeout=30)
        if response.status_code != 200 or response.json().get("status") != "ok":
            raise ApiError(f"HTTP {response.status_code} {response.headers.get('X-Road-Error', '')} {response.text[:200]}")
        return response.json()

    body = eventually("premier appel via X-Road", call, tries=30, delay=10)
    log(f"   ONI/CNIB -> état civil/identity-match : {body['status']}, match = {body['data']['match']}")

    payload = {"request_id": "xroad-setup-sans-accord", "procedure": "concours_direct_preverification",
               "subject": {"pivot_id": "ACTE:OUAGA:2004:01234"}, "parameters": {}}
    without_consent = httpx.post(f"{base}/is-adult", json=payload, headers=client, timeout=30).json()
    log(f"   ONI/CNIB -> état civil/is-adult sans accord : {without_consent.get('status')} "
        f"({without_consent.get('message')}) — refus de la garde")

    refused = httpx.post(
        f"http://ss-demandeurs:8080/r1/{INSTANCE}/{MEMBER_CLASS}/JUSTICE/REGISTRES/criminal-record",
        json=payload,
        headers={"X-Road-Client": f"{INSTANCE}/{MEMBER_CLASS}/ONI/CNIB"},
        timeout=30,
    )
    log(
        f"   ONI/CNIB -> Justice/criminal-record (hors convention) : HTTP {refused.status_code} "
        f"{refused.headers.get('X-Road-Error', '')}"
    )


def main() -> int:
    started = time.monotonic()
    try:
        cs, anchor = setup_central_server()
        servers = {spec.host: (spec, setup_security_server(cs, anchor, spec)) for spec in SECURITY_SERVERS}
        registres_spec, registres = servers["ss-registres"]
        setup_management_services(cs, registres, registres_spec)
        for spec, ss in servers.values():
            register_clients(cs, ss, spec)
        apis = {host: ss for host, (_, ss) in servers.items()}
        for host, ss in apis.items():
            publish_services(ss, host)
        grant_access(apis)
        smoke_test()
    except ApiError as exc:
        log(f"ÉCHEC : {exc}")
        log("Le script est relançable : les étapes déjà faites seront sautées.")
        return 1
    log(f"Banc X-Road prêt en {int(time.monotonic() - started)} s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
