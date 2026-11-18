"""Répétition de l'épreuve « tenir quand un registre tombe », sur la pile Docker du miroir.

Depuis , pile démarrée (docker compose up -d) :
    python3 resilience/scenarios/registre_en_panne.py

1. arrête le registre de la Justice (docker compose stop justice-registry) ;
2. Awa lance la démarche « concours direct » depuis son espace : l'âge est confirmé, la
   nationalité et le casier sont « indisponibles », jamais « oui » ;
3. montre ces consultations au journal, côté demandeur et côté détenteur ;
4. redémarre le registre et attend la reprise automatique de la couche démarches
   (REGISTRY_RETRY_INTERVAL_S) : dossier terminé, une seule réponse réussie par vérification.

Bibliothèque standard uniquement. Code de sortie 0 si la reprise a eu lieu.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

KEYCLOAK = "http://localhost:8180/realms/dlnuf/protocol/openid-connect/token"
API = "http://localhost:8000/v1"
JOURNAL = "http://localhost:8108/v1/events"
AUDITOR = "dev-journal-auditeur"
JUSTICE_HEALTH = "http://localhost:8103/health"
AWA = {"subject_ref": "ACTE:OUAGA:2004:01234", "confirmed": True, "last_name": "KABORE", "first_names": "Awa",
       "birth_date": "2004-03-12", "mother_name": "COMPAORE Salimata"}


def request(method: str, url: str, *, token: str | None = None, body: dict | None = None,
            form: dict | None = None) -> tuple[int, object]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    data = None
    if body is not None:
        data, headers["Content-Type"] = json.dumps(body).encode(), "application/json"
    if form is not None:
        data, headers["Content-Type"] = urllib.parse.urlencode(form).encode(), "application/x-www-form-urlencoded"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method=method), timeout=60) as reply:
            content = reply.read()
            return reply.status, json.loads(content) if content else None
    except urllib.error.HTTPError as error:
        content = error.read()
        return error.code, json.loads(content) if content else None


def step(text: str) -> None:
    print(f"\n▶ {text}", flush=True)


def compose(*args: str) -> None:
    subprocess.run(["docker", "compose", *args], check=True, capture_output=True)


def journal(case_id: str) -> list[dict]:
    status, page = request("GET", f"{JOURNAL}?{urllib.parse.urlencode({'case_id': case_id, 'limit': 1000})}", token=AUDITOR)
    if status != 200:
        raise SystemExit(f"Journal illisible (HTTP {status})")
    return page["events"]


def show_checks(case: dict) -> None:
    for check in case["checks"]:
        result = {True: "oui", False: "non", None: "—"}[check["result"]]
        print(f"   {check['label'][:60]:<60} {check['status']:<12} réponse : {result} (tentatives : {check['attempt_count']})")


def main() -> int:
    status, tokens = request("POST", KEYCLOAK, form={"grant_type": "password", "client_id": "dlnuf-api",
                                                      "username": "citoyen-demo", "password": "CitoyenDemo-2026!"})
    if status != 200:
        raise SystemExit(f"Connexion d'Awa impossible (Keycloak, HTTP {status}) : {tokens}")
    citizen = tokens["access_token"]
    status, link = request("GET", f"{API}/citizen/identity-link", token=citizen)
    if not (isinstance(link, dict) and link.get("subject_ref")):
        request("POST", f"{API}/citizen/identity-link", token=citizen, body=AWA)
        status, tokens = request("POST", KEYCLOAK, form={"grant_type": "password", "client_id": "dlnuf-api",
                                                          "username": "citoyen-demo", "password": "CitoyenDemo-2026!"})
        citizen = tokens["access_token"]

    step("Arrêt du registre de la Justice (docker compose stop justice-registry)")
    compose("stop", "justice-registry")
    try:
        step("Awa lance la démarche « concours direct » depuis son espace")
        status, case = request("POST", f"{API}/citizen/cases", token=citizen,
                               body={"procedure_code": "concours_direct_preverification", "confirmed": True})
        if status != 201:
            raise SystemExit(f"Démarche refusée (HTTP {status}) : {case}")
        print(f"   dossier {case['reference']} : {case['status']}")
        show_checks(case)
        if any(check["result"] is True for check in case["checks"]
               if check["question_code"] in {"candidate_nationality", "criminal_record_indicator"}):
            raise SystemExit("ÉCHEC : un « oui » est sorti d'un registre arrêté")

        step("Au journal : chaque consultation, côté demandeur et côté détenteur")
        for event in journal(case["id"]):
            if event["event_type"] in {"registry_check", "holder_response"}:
                print(f"   {event['occurred_at'][11:19]} {event['source']:<26} {event['event_type']:<16} "
                      f"{event['service_code']:<16} {event['outcome']}")
    finally:
        step("Redémarrage du registre de la Justice")
        compose("start", "justice-registry")
    for _ in range(30):
        if _justice_up():
            break
        time.sleep(1)

    step("Attente de la reprise automatique (sans action du guichet)")
    started = time.monotonic()
    while time.monotonic() - started < 120:
        status, case = request("GET", f"{API}/cases/{case['id']}", token=citizen)
        if case["status"] == "completed":
            break
        time.sleep(3)
    print(f"   après {time.monotonic() - started:.0f} s : dossier {case['status']}")
    show_checks(case)

    successes = defaultdict(int)
    for event in journal(case["id"]):
        if event["event_type"] == "holder_response" and event["outcome"] == "ok":
            successes[event["correlation_id"]] += 1
    duplicates = [request_id for request_id, count in successes.items() if count > 1]
    if case["status"] != "completed" or duplicates:
        print("\nÉCHEC : reprise incomplète ou réponse obtenue deux fois", duplicates)
        return 1
    print("\nOK : jamais « oui » pendant la panne, tout au journal, reprise automatique sans doublon.")
    return 0


def _justice_up() -> bool:
    try:
        with urllib.request.urlopen(JUSTICE_HEALTH, timeout=2):
            return True
    except (urllib.error.URLError, OSError):
        return False


if __name__ == "__main__":
    sys.exit(main())
