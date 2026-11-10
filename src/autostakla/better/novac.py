"""Novac u celim dinarima (INTEGER) – nikad float, da se zbirovi ne kvare. PDV stopa iz podešavanja."""
from __future__ import annotations

from autostakla.core import settings
from autostakla.lager.repo import LagerError

KEY_PDV = "pdv_stopa"
PDV_PODRAZUMEVANO = 20


def pdv_stopa(conn) -> int:
    v = settings.get(conn, KEY_PDV)
    try:
        return int(v) if v is not None else PDV_PODRAZUMEVANO
    except ValueError:
        return PDV_PODRAZUMEVANO


def bez_pdv(iznos_sa_pdv: int, stopa: int) -> int:
    """Osnovica iz iznosa sa PDV-om, zaokružena na ceo dinar (celobrojno)."""
    delilac = 100 + stopa
    return (iznos_sa_pdv * 100 + delilac // 2) // delilac


def fmt(din: int | None) -> str:
    if din is None:
        return "–"
    return ("-" if din < 0 else "") + f"{abs(din):,}".replace(",", ".") + " RSD"


def procenat(deo: int | None, celo: int | None) -> str:
    """Procenat sa jednom decimalom, računat celobrojno (npr. „23,4%“)."""
    if deo is None or not celo:
        return "–"
    znak = "-" if (deo < 0) != (celo < 0) else ""
    deo, celo = abs(deo), abs(celo)
    p10 = (deo * 1000 + celo // 2) // celo
    return f"{znak}{p10 // 10},{p10 % 10}%"


def parse(text: str | None, polje: str = "Cena") -> int:
    """„12.500“, „12500“, „12 500“, „12.500,00“ -> 12500. Pare nisu dozvoljene."""
    t = (text or "").strip().replace(" ", "").replace(" ", "")
    for suffix in ("RSD", "rsd", "din", "Din"):
        t = t.removesuffix(suffix)
    if not t:
        raise LagerError(f"{polje}: upišite iznos u dinarima.")
    if "," in t:
        ceo, dec = t.rsplit(",", 1)
        if dec.strip("0"):
            raise LagerError(f"{polje}: upišite cele dinare (bez para).")
        t = ceo
    t = t.replace(".", "")
    if not t.isdigit():
        raise LagerError(f"{polje}: „{text}“ nije iznos u dinarima.")
    return int(t)
