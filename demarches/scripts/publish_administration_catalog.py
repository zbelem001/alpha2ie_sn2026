"""Explicitly publish the twelve configured demonstration procedures."""
from sqlalchemy import select

from app.admin_api import ProcedureInput, _procedure_payload, save_procedure, set_procedure_active, ActiveInput
from app.database.connection import SessionLocal
from app.database.models import Administration, Procedure, ProcedureQuestion, Question, Registry, RegistryService
from app.security import Principal
from app.xroad_sync import XRoadSync
from scripts.seed_administration_catalog import seed, DRAFTS
from scripts.seed_demo import DEMO_PROCEDURES


def main():
    sync = XRoadSync()
    if not sync.enabled:
        raise RuntimeError("Activez la synchronisation X-Road avant de publier le catalogue")
    with SessionLocal.begin() as db:
        seed(db)
    targets = [item[1] for item in DRAFTS] + [item["code"] for item in DEMO_PROCEDURES]
    synced = set()
    try:
        for code in targets:
            with SessionLocal() as db:
                procedure = db.scalar(select(Procedure).where(Procedure.code == code))
                owner = db.get(Administration, procedure.owner_administration_id)
                principal = Principal("catalogue-publication", frozenset({"local-admin"}), owner.code, None,
                                      display_name="Publication du catalogue demandée par l’utilisateur")
                payload = _procedure_payload(db, procedure)
                for link in db.scalars(select(ProcedureQuestion).where(ProcedureQuestion.procedure_id == procedure.id)):
                    question = db.get(Question, link.question_id)
                    registry = db.get(Registry, question.registry_id)
                    provider = db.get(Administration, registry.administration_id)
                    service = db.scalar(select(RegistryService).where(RegistryService.registry_id == registry.id,
                                                                    RegistryService.code == question.service_code))
                    if not service or not service.active or not question.active or not registry.active:
                        raise RuntimeError(f"Service non disponible pour {code}: {question.service_code}")
                    key = (provider.code, question.service_code)
                    if key not in synced:
                        sync.publish_service(provider.code, question.service_code, registry.base_url)
                        synced.add(key)
                    sync.grant_access(owner.code, provider.code, question.service_code)
                if not procedure.published:
                    body = ProcedureInput.model_validate({"code": code, "title": procedure.title,
                        "purpose": procedure.purpose, "consentDays": procedure.consent_days,
                        "published": True, "checks": [{"questionCode": item["questionCode"],
                            "required": item["required"], "document": item["document"]} for item in payload["checks"]]})
                    save_procedure(code, body, principal, db)
                elif not procedure.active:
                    set_procedure_active(code, ActiveInput(active=True), principal, db)
                print(f"Publiée : {owner.name} — {procedure.title}", flush=True)
    finally:
        sync.client.close()


if __name__ == "__main__":
    main()
