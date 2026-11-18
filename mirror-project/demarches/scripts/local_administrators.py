"""Six local development administrators, one per administration."""
import urllib.parse

ACCOUNTS = (
    ("10000001", "BF/GOV/MAIRIE-OUAGA/ETAT-CIVIL", "État civil"),
    ("10000002", "BF/GOV/JUSTICE/REGISTRES", "Justice"),
    ("10000003", "BF/GOV/TRESOR/PAIEMENTS", "Trésor"),
    ("10000004", "BF/GOV/ONI/CNIB", "ONI"),
    ("10000005", "BF/GOV/DIPF/PASSEPORTS", "Police des frontières"),
    ("10000006", "BF/GOV/FONCTION-PUBLIQUE", "Fonction publique"),
)


def ensure_local_administrators(token):
    from scripts.configure_keycloak import request_json
    _, role = request_json("/admin/realms/dlnuf/roles/local-admin", token)
    for phone, administration, name in ACCOUNTS:
        query = urllib.parse.urlencode({"username": phone, "exact": "true"})
        _, existing = request_json(f"/admin/realms/dlnuf/users?{query}", token)
        if existing:
            # Ordinary startup must not overwrite credentials or reset a user.
            user = existing[0]
            attrs = user.get("attributes") or {}
            if attrs.get("account_kind") != ["local-admin"] or attrs.get("administration_code") != [administration]:
                raise RuntimeError(f"Le numéro {phone} appartient déjà à un autre compte")
        else:
            request_json("/admin/realms/dlnuf/users", token, method="POST", body={
                "username": phone, "firstName": "Administration", "lastName": name,
                "email": f"admin-{phone}@example.test", "emailVerified": True, "enabled": True,
                "requiredActions": [],
                "attributes": {"account_kind": ["local-admin"], "administration_code": [administration],
                               "phone_number": [f"+226{phone}"], "phone_number_verified": ["false"]},
                "credentials": [{"type": "password", "value": "1234", "temporary": False}],
            })
            _, users = request_json(f"/admin/realms/dlnuf/users?{query}", token)
            user = users[0]
        _, roles = request_json(f"/admin/realms/dlnuf/users/{user['id']}/role-mappings/realm", token)
        if not any(item["name"] == "local-admin" for item in roles):
            request_json(f"/admin/realms/dlnuf/users/{user['id']}/role-mappings/realm", token, method="POST", body=[role])


def reset_local_administrators(token):
    """Explicit reset only: citizens, agents and technical accounts are preserved."""
    from scripts.configure_keycloak import request_json
    users = []
    offset = 0
    while True:
        _, page = request_json(f"/admin/realms/dlnuf/users?first={offset}&max=100", token)
        users.extend(page)
        if len(page) < 100:
            break
        offset += 100
    administrators = []
    for user in users:
        if user.get("serviceAccountClientId"):
            continue
        _, roles = request_json(f"/admin/realms/dlnuf/users/{user['id']}/role-mappings/realm/composite", token)
        if any(role["name"] == "local-admin" for role in roles) or (user.get("attributes") or {}).get("account_kind") == ["local-admin"]:
            administrators.append(user)
    admin_ids = {user["id"] for user in administrators}
    phones = {item[0] for item in ACCOUNTS}
    if any(user["username"] in phones and user["id"] not in admin_ids for user in users):
        raise RuntimeError("Un numéro prévu est déjà utilisé par un citoyen ou un agent ; aucun compte supprimé")
    for user in administrators:
        request_json(f"/admin/realms/dlnuf/users/{user['id']}", token, method="DELETE")
    ensure_local_administrators(token)
    print(f"{len(administrators)} anciens administrateurs locaux supprimés ; 6 comptes créés.")


if __name__ == "__main__":
    from scripts.configure_keycloak import admin_token
    reset_local_administrators(admin_token())
