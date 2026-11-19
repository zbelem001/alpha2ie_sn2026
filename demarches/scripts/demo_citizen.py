"""Compte local de démonstration relié aux fiches fictives des six registres."""

DEMO_CITIZEN = {
    "username": "62000001",
    "phone_number": "+22662000001",
    "pin": "4821",
    "first_name": "Awa",
    "last_name": "Demo",
    "subject_ref": "ACTE:OUAGA:1985:98001",
    "identifiers": {
        "cnib_number": "CNIB-TEST-0001",
        "birth_act_number": "ACTE-TEST-0001",
        "nationality_reference": "NAT-TEST-0001",
        "criminal_record_number": "CASIER-TEST-0001",
        "payment_reference": "PAY-TEST-PASSEPORT-0001",
        "loss_report_number": "PV-TEST-0001",
    },
}

IDENTIFIER_REGISTRIES = {
    "cnib_number": "BF/GOV/ONI/CNIB",
    "birth_act_number": "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL",
    "nationality_reference": "BF/GOV/JUSTICE/REGISTRES",
    "criminal_record_number": "BF/GOV/JUSTICE/REGISTRES",
    "payment_reference": "BF/GOV/TRESOR/PAIEMENTS",
    "loss_report_number": "BF/GOV/POLICE/PERTES",
}
