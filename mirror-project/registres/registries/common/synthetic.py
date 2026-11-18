"""100 personnes intégralement fictives, références locales distinctes par registre."""
BATCH = "synthetic-100-v1"

def synthetic_records(count=100):
    civil, justice, treasury = [], [], []
    for index in range(1, count + 1):
        year = 1975 + index % 37
        birth = f"{year:04d}-{1 + index % 12:02d}-{1 + index % 28:02d}"
        # Clé de compatibilité des scénarios de test, sans valeur d'identifiant officiel.
        pivot = f"ACTE:OUAGA:{year:04d}:{90000 + index:05d}"
        identity = {"pivot_id": pivot, "last_name": f"FICTIF_{index:03d}", "first_names": f"Personne test {index:03d}", "birth_date": birth}
        civil.append({**identity, "birth_act_number": f"ACTE-SYNTH-{index:04d}", "sex": "F" if index % 2 else "M", "birth_place": "Ouagadougou", "birth_country": "BF", "mother_name": f"MERE FICTIVE {index:03d}", "death_date": None, "_seed_batch": BATCH})
        justice.append({**identity, "criminal_record_number": f"CASIER-SYNTH-{index:04d}", "nationality_reference": f"NAT-SYNTH-{index:04d}", "burkinabe": index % 10 != 0, "acquisition": "birth", "convictions": 1 if index % 7 == 0 else 0, "criminal_record_valid": index % 9 != 0, "_seed_batch": BATCH})
        treasury.append({**identity, "reference": f"PAY-SYNTH-{index:04d}", "procedure": "passeport_ordinaire_precheck", "amount_xof": 200, "status": "pending" if index % 5 == 0 else "paid", "paid_at": None if index % 5 == 0 else "2026-11-18T08:00:00Z", "_seed_batch": BATCH})
    return {"civil": civil, "justice": justice, "treasury": treasury}
