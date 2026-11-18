"""One technical identity per administration; no supplier/requester role flag."""
import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AdministrationConnection:
    code: str
    member: str
    subsystem: str
    server: str
    base_url: str | None
    services: tuple[str, ...]
    allowed: tuple[tuple[str, str, str], ...]

    @property
    def client_id(self) -> str:
        return f"BF/GOV/{self.member}/{self.subsystem}"

    @property
    def client_key(self) -> str:
        return self.client_id.replace("/", ":")


def load_administrations() -> dict[str, AdministrationConnection]:
    path = Path(os.getenv("ADMINISTRATION_CONNECTIONS_FILE") or Path(__file__).with_name("administrations.json"))
    rows = json.loads(path.read_text(encoding="utf-8"))
    result = {}
    for row in rows:
        item = AdministrationConnection(**{**row, "services": tuple(row.get("services", [])),
                                            "allowed": tuple(tuple(right) for right in row.get("allowed", []))})
        if item.code in result:
            raise ValueError(f"Duplicate administration: {item.code}")
        result[item.code] = item
    return result


def administration_connection(code: str) -> AdministrationConnection:
    try:
        return load_administrations()[code]
    except KeyError as error:
        raise ValueError(f"Administration sans connexion X-Road configurée : {code}") from error
