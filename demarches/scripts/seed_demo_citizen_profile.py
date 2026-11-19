"""Préremplit, sans écraser les choix existants, le profil du compte citoyen démo."""

from sqlalchemy import select

from app.database.connection import SessionLocal
from app.database.models import CitizenDocumentIdentifier, CitizenIdentityLink
from app.identifiers import encrypt_identifier, identifier_digest
from app.keycloak_admin import KeycloakAdminClient
from scripts.demo_citizen import DEMO_CITIZEN, IDENTIFIER_REGISTRIES


def seed() -> None:
    users = KeycloakAdminClient()._request(
        "GET", "/users", params={"username": DEMO_CITIZEN["username"], "exact": "true"}
    ).json()
    if not isinstance(users, list) or len(users) != 1:
        raise RuntimeError("Le compte citoyen de démonstration est introuvable dans Keycloak.")
    principal_sub = users[0]["id"]

    with SessionLocal() as db:
        link = db.scalar(
            select(CitizenIdentityLink).where(CitizenIdentityLink.principal_sub == principal_sub)
        )
        if link is None:
            by_subject = db.scalar(
                select(CitizenIdentityLink).where(
                    CitizenIdentityLink.subject_ref == DEMO_CITIZEN["subject_ref"]
                )
            )
            if by_subject is not None:
                raise RuntimeError("La référence démo est déjà rattachée à un autre compte.")
            link = CitizenIdentityLink(
                principal_sub=principal_sub,
                subject_ref=DEMO_CITIZEN["subject_ref"],
                phone_number=DEMO_CITIZEN["phone_number"],
            )
            db.add(link)
            db.flush()
        elif link.subject_ref != DEMO_CITIZEN["subject_ref"]:
            raise RuntimeError("Le compte citoyen démo est déjà rattaché à une autre fiche.")

        existing = {
            row.identifier_type: row
            for row in db.scalars(
                select(CitizenDocumentIdentifier).where(
                    CitizenDocumentIdentifier.principal_sub == principal_sub
                )
            ).all()
        }
        added = 0
        for identifier_type, value in DEMO_CITIZEN["identifiers"].items():
            if identifier_type in existing:
                continue
            digest = identifier_digest(identifier_type, value)
            if db.scalar(
                select(CitizenDocumentIdentifier).where(
                    CitizenDocumentIdentifier.identifier_digest == digest
                )
            ):
                raise RuntimeError(f"La référence démo {identifier_type} est déjà attribuée.")
            db.add(
                CitizenDocumentIdentifier(
                    principal_sub=principal_sub,
                    subject_ref=DEMO_CITIZEN["subject_ref"],
                    identifier_type=identifier_type,
                    registry_code=IDENTIFIER_REGISTRIES[identifier_type],
                    identifier_ciphertext=encrypt_identifier(value),
                    identifier_digest=digest,
                )
            )
            added += 1
        db.commit()
        print(
            f"Profil citoyen démo prêt : {DEMO_CITIZEN['username']} "
            f"({len(existing) + added} références, conservées si déjà présentes).",
            flush=True,
        )


if __name__ == "__main__":
    seed()
