from collections import Counter

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.database.models import Administration, Registry, RegistryService, Procedure, ProcedureQuestion, Question
from scripts import seed_demo, seed_administration_catalog


def test_catalog_covers_each_administration_and_preserves_edits(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine)
    monkeypatch.setattr(seed_demo, "SessionLocal", sessions)
    seed_demo.main()
    with sessions.begin() as db:
        seed_administration_catalog.seed(db)
    with sessions.begin() as db:
        services = Counter(db.execute(select(Administration.code).join(Registry).join(RegistryService)).scalars())
        procedures = Counter(db.execute(select(Administration.code).join(Procedure, Procedure.owner_administration_id == Administration.id)).scalars())
        assert len(services) == len(procedures) == 6
        assert all(count >= 2 for count in services.values())
        assert all(count >= 2 for count in procedures.values())
        assert db.scalar(select(func.count()).select_from(RegistryService).where(RegistryService.active.is_(False))) == 6
        counts = [db.scalar(select(func.count()).select_from(model)) for model in (RegistryService, Procedure, ProcedureQuestion, Question)]
        draft = db.scalar(select(Procedure).where(Procedure.code == "etat_civil_preparation_rectification"))
        draft.title = "Titre personnalisé conservé"
        assert not draft.published and not draft.active
        db.flush()
        seed_administration_catalog.seed(db)
        db.flush()
        assert draft.title == "Titre personnalisé conservé"
        assert counts == [db.scalar(select(func.count()).select_from(model)) for model in (RegistryService, Procedure, ProcedureQuestion, Question)]
