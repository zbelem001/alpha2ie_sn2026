"""Keep the six selected business administrations; preserve historical cases."""
from sqlalchemy import select, func
from app.database.connection import SessionLocal
from app.database.models import Administration, Case
from connectors.administrations import load_administrations
from scripts.seed_demo import ADMINISTRATIONS


def main():
    allowed = set(load_administrations())
    assert allowed == set(ADMINISTRATIONS)
    with SessionLocal.begin() as db:
        for item in db.scalars(select(Administration)):
            if item.code in allowed:
                item.name = ADMINISTRATIONS[item.code]
                continue
            # Never destroy cases or traceability when an old organization is retired.
            has_cases = db.scalar(select(func.count()).select_from(Case).where(Case.requester_administration_id == item.id))
            item.active = False
            print(f"Administration hors périmètre retirée des portails : {item.code}; dossiers conservés : {has_cases}")
    print("Six administrations retenues ; noms harmonisés ; historiques conservés.")


if __name__ == "__main__":
    main()
