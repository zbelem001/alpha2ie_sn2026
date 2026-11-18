"""Every administration may provide services and request another one's services."""
import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from connectors.administrations import load_administrations
from connectors import build_connector
from app import xroad_sync
from app.admin_api import ServiceInput, create_offered_service, ProcedureInput, save_procedure
from app.database.base import Base
from app.database.models import Administration, Registry, RegistryService, Question, Permission, ProcedureQuestion
from app.security import Principal


@pytest.mark.parametrize("code", list(load_administrations()))
def test_each_administration_can_provide_and_request(monkeypatch, code):
    monkeypatch.setenv("XROAD_SYNC_ENABLED", "true")
    calls = []
    def handle(request):
        calls.append(request)
        if request.url.path == "/login":
            return httpx.Response(200)
        if request.method == "GET":
            return httpx.Response(200, json=[])
        if request.method == "PUT":
            return httpx.Response(204)
        if request.url.path.endswith("/access-rights/delete"):
            return httpx.Response(204)
        return httpx.Response(201, json={"id": 7})
    original = httpx.Client
    monkeypatch.setattr(xroad_sync.httpx, "Client", lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(handle)))
    sync = xroad_sync.XRoadSync()
    connection = load_administrations()[code]
    sync.publish_service(code, "test-status", "http://own-registry:8000")
    assert any(r.url.host == connection.server and connection.client_key in r.url.path for r in calls)
    assert any(r.method == "POST" and b'own-registry' in r.content for r in calls)
    calls.clear()
    sync.grant_access(code, "BF/GOV/JUSTICE/REGISTRES", "nationality")
    assert any(r.method == "POST" and connection.client_key in r.url.path and r.url.host == "ss-registres" for r in calls)
    calls.clear()
    sync.revoke_access(code, "BF/GOV/JUSTICE/REGISTRES", "nationality")
    assert any(r.method == "POST" and r.url.path.endswith("/access-rights/delete") for r in calls)
    sync.client.close()


@pytest.mark.parametrize("code", list(load_administrations()))
def test_connector_uses_actual_requester_identity_and_host(code):
    connection = load_administrations()[code]
    connector = build_connector({"REGISTRY_CONNECTOR": "xroad", "XROAD_CLIENT_ID": "BF/GOV/ONI/CNIB"}, administration_code=code)
    assert connector.client_id == connection.client_id
    assert connector.security_server_url == f"http://{connection.server}:8080"
    assert connector._url("BF/GOV/FONCTION-PUBLIQUE", "test-status").endswith("/BF/GOV/FONCTION-PUBLIQUE/RECRUTEMENT/test-status")


def test_former_requester_can_declare_service_and_former_provider_can_use_it(monkeypatch):
    monkeypatch.setenv("XROAD_SYNC_ENABLED", "false")
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False) as db:
        public = Administration(code="BF/GOV/FONCTION-PUBLIQUE", name="Fonction publique")
        justice = Administration(code="BF/GOV/JUSTICE/REGISTRES", name="Justice")
        db.add_all([public, justice]); db.flush()
        db.add(Registry(administration_id=public.id, code="main", name="Registre FP", base_url="http://fp-registry")); db.commit()
        principal = Principal("test", frozenset(["local-admin"]), public.code, None, display_name="Admin")
        create_offered_service(ServiceInput(code="agent-status", title="Agent public actif", description="Confirmer uniquement le statut actif", responseKey="active"), principal, db)
        service = db.scalar(select(RegistryService))
        question = db.scalar(select(Question))
        assert service and question.service_code == service.code and question.response_key == "active"
        principal = Principal("test-justice", frozenset(["local-admin"]), justice.code, None, display_name="Admin Justice")
        result = save_procedure("verification_agent", ProcedureInput(code="verification_agent", title="Vérification d’un agent", purpose="Confirmer le statut pour instruire le dossier", published=True, consentDays=30, checks=[{"questionCode": question.code, "required": True, "document": {"key": "cnib", "label": "Numéro de CNIB", "provider": "Fonction publique", "hint": "Référence du registre"}}]), principal, db)
        assert result["published"]
        assert db.scalar(select(ProcedureQuestion)).document_type == "cnib"
        assert db.scalar(select(Permission)).requester_administration_id == justice.id
