"""Jedini izvor verzije i izdanja. Build skript čita ove vrednosti."""

APP_ID = "AutoStakla"
VERSION = "2.0.0"

# "osnovna" = AutoStakla (osnovno izdanje), "better" = AutoStaklaBetter (prošireno izdanje)
EDITION = "better"

APP_NAME = "AutoStaklaBetter" if EDITION == "better" else "AutoStakla"


def is_better() -> bool:
    """Prošireni deo (prodaja, nabavka, analitika, reklamacije, dokumenti) vidi se samo u Better izdanju."""
    return EDITION == "better"


def version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))
