"""Add real provider services and draft business procedures without overwriting edits."""
from sqlalchemy import select
from connectors.administrations import load_administrations

from app.database.connection import SessionLocal
from app.database.models import Administration, Procedure, ProcedureQuestion, Question, Registry, RegistryService

CIVIL = "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL"
JUSTICE = "BF/GOV/JUSTICE/REGISTRES"
TREASURY = "BF/GOV/TRESOR/PAIEMENTS"
ONI = "BF/GOV/ONI/CNIB"
POLICE = "BF/GOV/DIPF/PASSEPORTS"
PUBLIC_SERVICE = "BF/GOV/FONCTION-PUBLIQUE"

# Only services implemented by the three registry APIs belong in this catalogue.
SERVICES = [
    (CIVIL, "http://civil-registry:8000", "is-adult", "Vérifier la majorité", "Réponse minimale : adult, booléen."),
    (CIVIL, "http://civil-registry:8000", "identity", "Retrouver un acte de naissance", "Avec une référence documentaire : found, booléen. La recherche historique par identité peut retourner davantage de données."),
    (JUSTICE, "http://justice-registry:8000", "nationality", "Confirmer la nationalité burkinabè", "Réponse minimale : burkinabe, booléen."),
    (JUSTICE, "http://justice-registry:8000", "criminal-record", "Vérifier l’indicateur de casier", "Réponse minimale : clean, booléen. Ne constitue pas une décision juridique."),
    (JUSTICE, "http://justice-registry:8000", "criminal-record-current", "Vérifier la validité d’un bulletin", "Réponse minimale : valid, booléen, sans détail des condamnations."),
    (TREASURY, "http://treasury-registry:8000", "payment-status", "Vérifier un paiement", "Avec une référence transactionnelle : paid, booléen. Ne constitue pas un identifiant permanent du citoyen."),
]

# These are proposals, not official administrative requirements. Publishing them
# remains an explicit business action, including the applicable X-Road rights.
DRAFTS = [
    (CIVIL, "etat_civil_copie_acte", "Préparation d’une copie d’acte de naissance", "Retrouver l’acte demandé sans réclamer une copie à l’usager.", [(CIVIL, "identity", "found", "birth", "Référence de l’acte de naissance")]),
    (JUSTICE, "justice_certificat_nationalite", "Pré-vérification d’un certificat de nationalité", "Retrouver l’acte de naissance utile à l’instruction ; la nationalité reste appréciée par le service compétent.", [(CIVIL, "identity", "found", "birth", "Référence de l’acte de naissance")]),
    (JUSTICE, "justice_bulletin_casier", "Préparation d’un bulletin de casier judiciaire", "Vérifier la disponibilité du bulletin demandé, sans exposer les condamnations.", [(JUSTICE, "criminal-record-current", "valid", "criminal", "Numéro du casier judiciaire")]),
    (TREASURY, "tresor_verification_paiement", "Vérification d’un paiement administratif", "Confirmer un paiement à partir de sa référence transactionnelle.", [(TREASURY, "payment-status", "paid", "payment", "Référence du reçu de paiement")]),
    ("BF/GOV/ONI/CNIB", "cnib_preverification_etat_civil", "Pré-vérification d’une demande de CNIB", "Confirmer la présence d’un acte et la nationalité pour préparer l’instruction par l’ONI.", [(CIVIL, "identity", "found", "birth", "Référence de l’acte de naissance"), (JUSTICE, "nationality", "burkinabe", "nationality", "Numéro du certificat de nationalité")]),
]

# Business catalogue entries without an implemented API remain inactive.
EXTRA_SERVICES = [
    (ONI, "http://oni-registry:8000", "cnib-status", "Vérifier la validité d’une CNIB", "Réponse minimale : valid, booléen. API disponible dans le registre ONI.", True),
    (ONI, "http://oni-registry:8000", "cnib-request-ready", "Confirmer la disponibilité d’une CNIB", "À raccorder — confirmer si la carte peut être retirée, sans exposer le dossier.", False),
    (TREASURY, "http://treasury-registry:8000", "receipt-valid", "Vérifier l’authenticité d’un reçu", "À raccorder — confirmer la validité d’un reçu, sans transmettre le détail du paiement.", False),
    (POLICE, None, "passport-status", "Vérifier la validité d’un passeport", "À raccorder — confirmer la validité du titre à partir de sa référence locale.", False),
    (POLICE, None, "passport-loss-declared", "Confirmer une déclaration de perte de passeport", "À raccorder — confirmer une déclaration dans le registre compétent. Ne pas confondre avec le registre optionnel des pertes de CNIB.", False),
    (PUBLIC_SERVICE, None, "public-agent-active", "Confirmer le statut actif d’un agent public", "À raccorder — confirmer uniquement le statut actif à partir de la référence du dossier agent.", False),
    (PUBLIC_SERVICE, None, "competition-admission", "Confirmer l’admission à un concours", "À raccorder — confirmer une admission à partir de la référence de candidature.", False),
]

DRAFTS += [
    (CIVIL, "etat_civil_preparation_rectification", "Préparation d’une rectification d’acte de naissance", "Retrouver l’acte concerné avant instruction de la demande. Cette vérification ne décide pas de la rectification.", [(CIVIL, "identity", "found", "birth", "Référence de l’acte de naissance")]),
    (TREASURY, "tresor_duplicata_recu", "Préparation d’un duplicata de reçu de paiement", "Retrouver et confirmer le paiement avant traitement du duplicata par un agent.", [(TREASURY, "payment-status", "paid", "payment", "Référence du paiement")]),
    (ONI, "cnib_correction_etat_civil", "Préparation d’une correction d’état civil sur une CNIB", "Retrouver l’acte de naissance avant instruction de la correction. La modification du titre reste une décision de l’ONI.", [(CIVIL, "identity", "found", "birth", "Référence de l’acte de naissance")]),
    (POLICE, "passeport_renouvellement_precheck", "Pré-vérification d’un renouvellement de passeport", "Confirmer les informations nécessaires à la préparation du dossier, sans décider de la délivrance du passeport.", [(ONI, "cnib-status", "valid", "cnib", "Numéro de CNIB"), (JUSTICE, "nationality", "burkinabe", "nationality", "Numéro du certificat de nationalité"), (TREASURY, "payment-status", "paid", "payment", "Référence du paiement")]),
    (PUBLIC_SERVICE, "fonction_publique_prise_service", "Pré-vérification d’une prise de service", "Préparer les vérifications d’un dossier de prise de service. La décision et les autres exigences restent à instruire par le service compétent.", [(JUSTICE, "nationality", "burkinabe", "nationality", "Numéro du certificat de nationalité"), (JUSTICE, "criminal-record-current", "valid", "criminal", "Numéro du casier judiciaire")]),
]


def seed(db):
    registries = {}
    for connection in load_administrations().values():
        administration = db.scalar(select(Administration).where(Administration.code == connection.code))
        if administration is None:
            raise RuntimeError(f"Administration absente : {connection.code}")
        registry = db.scalar(select(Registry).where(Registry.administration_id == administration.id, Registry.code == "main"))
        if registry is None:
            db.add(Registry(administration_id=administration.id, code="main", name=f"Registre — {administration.name}", base_url=connection.base_url))
        elif not registry.base_url and connection.base_url:
            registry.base_url = connection.base_url
    db.flush()
    for provider, url, code, title, description, active in [(*item, True) for item in SERVICES] + EXTRA_SERVICES:
        administration = db.scalar(select(Administration).where(Administration.code == provider))
        if administration is None:
            raise RuntimeError(f"Administration absente : {provider}; lancer seed_demo d’abord")
        registry = db.scalar(select(Registry).where(Registry.administration_id == administration.id, Registry.code == "main"))
        if registry is None:
            registry = Registry(administration_id=administration.id, code="main", name=f"Registre — {administration.name}", base_url=url)
            db.add(registry)
            db.flush()
        elif not registry.base_url:
            registry.base_url = url
        registries[provider] = registry
        service = db.scalar(select(RegistryService).where(RegistryService.registry_id == registry.id, RegistryService.code == code))
        if service is None:
            db.add(RegistryService(registry_id=registry.id, code=code, title=title, description=description, active=active))
        db.flush()
        if active:
            question = db.scalar(select(Question).where(Question.registry_id == registry.id, Question.service_code == code))
            if question is None:
                keys = {"is-adult": "adult", "identity": "found", "nationality": "burkinabe", "criminal-record": "clean", "payment-status": "paid"}
                db.add(Question(code=f"catalog_{registry.id.hex}_{code}", registry_id=registry.id,
                                service_code=code, response_key=keys.get(code, "valid"), description=title, active=True))

    for owner, code, title, purpose, checks in DRAFTS:
        if db.scalar(select(Procedure).where(Procedure.code == code)):
            continue  # Preserve all subsequent edits, publication and configuration.
        administration = db.scalar(select(Administration).where(Administration.code == owner))
        if administration is None:
            raise RuntimeError(f"Administration absente : {owner}")
        procedure = Procedure(code=code, owner_administration_id=administration.id, title=title, purpose=purpose, consent_days=30, published=False, active=False, config_version=1)
        db.add(procedure)
        db.flush()
        for position, (provider, service, response, document, label) in enumerate(checks):
            question_code = f"{code}_{position + 1}"
            question = db.scalar(select(Question).where(Question.code == question_code))
            if question is None:
                question = Question(code=question_code, registry_id=registries[provider].id, service_code=service, response_key=response, description=f"{label} : vérifier uniquement {response}.", active=True)
                db.add(question)
                db.flush()
            db.add(ProcedureQuestion(procedure_id=procedure.id, question_id=question.id, position=position, required=True, document_type=document, document_label=label, document_hint="Référence propre au registre fournisseur"))


def main():
    with SessionLocal.begin() as db:
        seed(db)
    print("Catalogue des six administrations initialisé sans écraser les modifications existantes.")


if __name__ == "__main__":
    main()
