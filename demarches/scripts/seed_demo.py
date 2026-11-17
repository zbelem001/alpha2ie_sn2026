"""Insert or refresh the public-service competition pre-check demo catalog."""
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
    "BF/GOV/DIPF/PASSEPORTS": "Direction de l’Immigration et de la Police des Frontières (passeports)",
    "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL": "Mairie de Ouagadougou — état civil",
    "BF/GOV/JUSTICE/REGISTRES": "Justice — nationalité et casier",
    "BF/GOV/ONI/CNIB": "ONI — registre CNIB simulé",
    "BF/GOV/TRESOR/PAIEMENTS": "Trésor — paiements simulés",
}

QUESTION_DEFINITIONS = [
    (
        "candidate_minimum_age",
        "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL",
        "is-adult",
        "adult",
        "Vérifier le seuil minimum de 18 ans. Ce contrôle ne vérifie ni le plafond d’âge ni les dérogations du concours.",
        1,
        True,
    ),
    (
        "candidate_nationality",
        "BF/GOV/JUSTICE/REGISTRES",
        "nationality",
        "burkinabe",
        "Vérifier la nationalité burkinabè, sous réserve des règles du concours concerné.",
        2,
        True,
    ),
    (
        "criminal_record_indicator",
        "BF/GOV/JUSTICE/REGISTRES",
        "criminal-record",
        "clean",
        "Indicateur de casier à examiner par un agent. Il ne décide pas de l’admissibilité et ne représente pas les seuils légaux de condamnation.",
        3,
        False,
    ),
    (
        "passport_cnib_valid",
        "BF/GOV/ONI/CNIB",
        "cnib-status",
        "valid",
        "Vérifier auprès de l’ONI que la CNIB est enregistrée et valide ; ne transmettre ni son numéro ni ses dates.",
    ),
    (
        "passport_nationality",
        "BF/GOV/JUSTICE/REGISTRES",
        "nationality",
        "burkinabe",
        "Vérifier la nationalité burkinabè requise pour le passeport ordinaire adulte.",
    ),
    (
        "passport_criminal_record_current",
        "BF/GOV/JUSTICE/REGISTRES",
        "criminal-record-current",
        "valid",
        "Vérifier qu’un bulletin de casier judiciaire en cours de validité est disponible, sans divulguer les condamnations.",
    ),
    (
        "passport_birth_act_found",
        "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL",
        "identity",
        "found",
        "Confirmer que l’acte d’état civil lié à la référence du dossier est retrouvé ; les autres attributs ne sont pas conservés.",
    ),
    (
        "passport_fiscal_stamp_paid",
        "BF/GOV/TRESOR/PAIEMENTS",
        "payment-status",
        "paid",
        "Vérifier le paiement simulé du timbre fiscal requis ; un résultat négatif bloque la pré-vérification jusqu’à régularisation, sans décider de la délivrance du passeport.",
    ),
]

DEMO_PROCEDURES = [
    {
        "code": "concours_direct_preverification",
        "config_version": 1,
        "owner": "BF/GOV/FONCTION-PUBLIQUE",
        "title": "Pré-vérification partielle d’une candidature à un concours direct",
        "purpose": "Vérifier les critères déclarés pour une candidature à un concours direct.",
        "questions": [
            ("candidate_minimum_age", 1, True),
            ("candidate_nationality", 2, True),
            ("criminal_record_indicator", 3, False),
        ],
    },
    {
        "code": "passeport_ordinaire_precheck",
        "config_version": 1,
        "owner": "BF/GOV/DIPF/PASSEPORTS",
        "title": "Pré-vérification d’une demande de passeport ordinaire (majeur)",
        "purpose": "Vérifier les informations nécessaires à la demande de passeport ordinaire.",
        "questions": [
            ("passport_cnib_valid", 1, True),
            ("passport_birth_act_found", 2, True),
            ("passport_nationality", 3, True),
            ("passport_criminal_record_current", 4, True),
            ("passport_fiscal_stamp_paid", 5, True),
        ],
    },
]

QUESTION_DOCUMENTS = {
    "candidate_minimum_age": ("birth", "Référence de l’acte de naissance", "Numéro, année et centre d’état civil si nécessaires"),
    "candidate_nationality": ("nationality", "Numéro du certificat de nationalité", "Référence du certificat dans le registre concerné"),
    "criminal_record_indicator": ("criminal", "Numéro du casier judiciaire", "Référence du bulletin dans le registre concerné"),
    "passport_cnib_valid": ("cnib", "Numéro de CNIB", "Ex. référence fictive de CNIB"),
    "passport_birth_act_found": ("birth", "Référence de l’acte de naissance", "Numéro, année et centre d’état civil si nécessaires"),
    "passport_nationality": ("nationality", "Numéro du certificat de nationalité", "Référence du certificat dans le registre concerné"),
    "passport_criminal_record_current": ("criminal", "Numéro du casier judiciaire", "Référence du bulletin dans le registre concerné"),
    "passport_fiscal_stamp_paid": ("payment", "Référence du timbre fiscal", "Numéro du reçu ou de la transaction"),
    "loss_declared": ("loss", "Numéro de déclaration de perte", "Référence de la déclaration"),
}


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

        registry_codes = {definition[1] for definition in QUESTION_DEFINITIONS}
        registries = {}
        for code in registry_codes:
            row = db.scalar(select(Registry).where(Registry.administration_id == administrations[code].id,
                                                  Registry.code == "main"))
            if row is None:
                row = Registry(administration_id=administrations[code].id, code="main", name=f"Registre — {administrations[code].name}")
                db.add(row)
                db.flush()
            elif row.name == "Registre":
                row.name = f"Registre — {administrations[code].name}"
            registries[code] = row

        questions = {}
        for code, registry_code, service, response, description, *_ in QUESTION_DEFINITIONS:
            row = db.scalar(select(Question).where(Question.code == code))
            if row is None:
                row = Question(code=code, registry_id=registries[registry_code].id,
                               service_code=service, response_key=response, description=description)
                db.add(row)
            else:
                row.registry_id = registries[registry_code].id
                row.service_code = service
                row.response_key = response
                row.description = description
                row.active = True
            db.flush()
            questions[code] = row

        legacy_procedure = db.scalar(select(Procedure).where(Procedure.code == "prise_de_service"))
        if legacy_procedure is not None:
            legacy_procedure.active = False

        for definition in DEMO_PROCEDURES:
            requester_id = administrations[definition["owner"]].id
            procedure = db.scalar(select(Procedure).where(Procedure.code == definition["code"]))
            if procedure is None:
                procedure = Procedure(
                    code=definition["code"],
                    owner_administration_id=requester_id,
                    title=definition["title"],
                    purpose=definition["purpose"],
                    consent_days=30,
                    published=True,
                    config_version=definition.get("config_version", 1),
                )
                db.add(procedure)
            else:
                procedure.owner_administration_id = requester_id
                procedure.title = definition["title"]
                procedure.purpose = definition["purpose"]
                procedure.consent_days = 30
                procedure.published = True
                procedure.config_version = definition.get("config_version", procedure.config_version)
                procedure.active = True
            db.flush()

            for question_code, position, required in definition["questions"]:
                question = questions[question_code]
                link = db.scalar(select(ProcedureQuestion).where(
                    ProcedureQuestion.procedure_id == procedure.id,
                    ProcedureQuestion.question_id == question.id,
                ))
                if link is None:
                    link = ProcedureQuestion(procedure_id=procedure.id, question_id=question.id)
                    db.add(link)
                link.required = required
                link.position = position
                document = QUESTION_DOCUMENTS.get(question_code)
                if document:
                    link.document_type, link.document_label, link.document_hint = document

                permission = db.scalar(select(Permission).where(
                    Permission.requester_administration_id == requester_id,
                    Permission.question_id == question.id,
                ))
                if permission is None:
                    permission = Permission(
                        requester_administration_id=requester_id,
                        question_id=question.id,
                    )
                    db.add(permission)
                permission.active = True
                permission.status = "approved"
    print("Catalogue de démonstration initialisé : concours direct et passeport ordinaire.")


if __name__ == "__main__":
    main()
