"""Insert the demo procedure and registry questions idempotently."""
from sqlalchemy import select

from app.database.connection import SessionLocal
from app.database.models import (
    Administration,
    Permission,
    Procedure,
    ProcedureQuestion,
    Question,
    Registry,
)

ADMINISTRATIONS = {
    "BF/GOV/FONCTION-PUBLIQUE": "Fonction publique (demandeur de démonstration)",
    "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL": "Mairie de Ouagadougou — état civil",
    "BF/GOV/JUSTICE/REGISTRES": "Justice — nationalité et casier",
}

QUESTIONS = [
    ("is_adult", "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL", "is-adult", "adult", "Vérifier si la personne est majeure", 1),
    ("nationality", "BF/GOV/JUSTICE/REGISTRES", "nationality", "burkinabe", "Vérifier la nationalité burkinabè", 2),
    ("criminal_record", "BF/GOV/JUSTICE/REGISTRES", "criminal-record", "clean", "Vérifier si le casier est vierge", 3),
]


def main() -> None:
    with SessionLocal.begin() as db:
        administrations = {}
        for code, name in ADMINISTRATIONS.items():
            row = db.scalar(select(Administration).where(Administration.code == code))
            if row is None:
                row = Administration(code=code, name=name)
                db.add(row)
                db.flush()
            administrations[code] = row

        registries = {}
        for code in ADMINISTRATIONS:
            if code == "BF/GOV/FONCTION-PUBLIQUE":
                continue
            row = db.scalar(select(Registry).where(Registry.administration_id == administrations[code].id,
                                                  Registry.code == "main"))
            if row is None:
                row = Registry(administration_id=administrations[code].id, code="main")
                db.add(row)
                db.flush()
            registries[code] = row

        questions = []
        for code, registry_code, service, response, description, position in QUESTIONS:
            row = db.scalar(select(Question).where(Question.code == code))
            if row is None:
                row = Question(code=code, registry_id=registries[registry_code].id,
                               service_code=service, response_key=response, description=description)
                db.add(row)
                db.flush()
            questions.append((row, position))

        requester_id = administrations["BF/GOV/FONCTION-PUBLIQUE"].id
        procedure = db.scalar(select(Procedure).where(Procedure.code == "prise_de_service"))
        if procedure is None:
            procedure = Procedure(code="prise_de_service", owner_administration_id=requester_id,
                                  title="Prise de service", config_version=1)
            db.add(procedure)
            db.flush()

        for question, position in questions:
            if db.scalar(select(ProcedureQuestion).where(ProcedureQuestion.procedure_id == procedure.id,
                                                       ProcedureQuestion.question_id == question.id)) is None:
                db.add(ProcedureQuestion(procedure_id=procedure.id, question_id=question.id,
                                         required=True, position=position))
            if db.scalar(select(Permission).where(Permission.requester_administration_id == requester_id,
                                                  Permission.question_id == question.id)) is None:
                db.add(Permission(requester_administration_id=requester_id, question_id=question.id, active=True))
    print("Données de démonstration créées ou déjà présentes : prise_de_service (3 vérifications).")


if __name__ == "__main__":
    main()
