"""Datumi laika joslā Europe/Riga."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

RIGA = ZoneInfo("Europe/Riga")

MENESI = [
    "janvāris", "februāris", "marts", "aprīlis", "maijs", "jūnijs",
    "jūlijs", "augusts", "septembris", "oktobris", "novembris", "decembris",
]


def sodien() -> date:
    return datetime.now(RIGA).date()


def nedelas_sakums(diena: date) -> date:
    """Pirmdiena nedēļā, kurā ir `diena`."""
    return diena - timedelta(days=diena.weekday())


def garais_datums(diena: date) -> str:
    return f"{diena.year}. gada {diena.day}. {MENESI[diena.month - 1]}"
