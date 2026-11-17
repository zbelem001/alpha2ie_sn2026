from __future__ import annotations

import os
from datetime import date


def reference_date() -> date:
    """Date du jour, ou REFERENCE_DATE (AAAA-MM-JJ) pour rejouer une démo à date fixe."""
    value = os.environ.get("REFERENCE_DATE")
    return date.fromisoformat(value) if value else date.today()


def age_on(birth: date, day: date) -> int:
    return day.year - birth.year - ((day.month, day.day) < (birth.month, birth.day))
