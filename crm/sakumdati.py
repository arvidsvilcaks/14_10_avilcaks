"""Sintētiski sākumdati. Palaišana: CRM_SAKUMDATU_PAROLE=... make seed

Katra sadaļa tiek ielādēta tikai tad, ja attiecīgā tabula ir tukša, tāpēc
skriptu var palaist atkārtoti. Visiem lietotājiem ir viena parole no vides
mainīgā `CRM_SAKUMDATU_PAROLE`; repozitorijā paroles nav.
"""

import os
import sqlite3
import sys

from crm import db, paroles
from crm.auth import PAROLES_MIN_GARUMS

LIETOTAJI = [
    ("Vadītājs Paraugs", "vaditajs@example.com", "vaditajs"),
    ("Darbiniece Viena", "darbinieks1@example.com", "darbinieks"),
    ("Darbinieks Divi", "darbinieks2@example.com", "darbinieks"),
]


def _tuksa(conn: sqlite3.Connection, tabula: str) -> bool:
    return conn.execute(f"SELECT COUNT(*) FROM {tabula}").fetchone()[0] == 0


def lietotaji(conn: sqlite3.Connection, parole: str) -> None:
    if not _tuksa(conn, "lietotaji"):
        return
    for vards, epasts, loma in LIETOTAJI:
        salt, hash_ = paroles.jauna(parole)
        conn.execute(
            "INSERT INTO lietotaji (vards, epasts, paroles_salt, paroles_hash, loma) VALUES (?, ?, ?, ?, ?)",
            (vards, epasts, salt, hash_, loma),
        )


ORGANIZACIJAS = [
    ("SIA Ezermalas Koks", "40003000001", "darbinieks1@example.com"),
    ("SIA Ziemeļu Būve", "40003000002", "darbinieks1@example.com"),
    ("Biedrība „Zaļais Krasts”", "40008000003", "darbinieks1@example.com"),
    ("AS Lauku Piens", "40003000004", "darbinieks1@example.com"),
    ("SIA Mežmalas Tūrisms", "40003000005", "darbinieks2@example.com"),
    ("Nodibinājums „Ezera Fonds”", "40008000006", "darbinieks2@example.com"),
    ("SIA Ūdens Tehnika", "40003000007", "darbinieks2@example.com"),
    ("IK Kalniņa Darbnīca", "40002000008", "darbinieks2@example.com"),
    ("SIA Rīgas Loģistika", "40003000009", "vaditajs@example.com"),
    ("Ezermalas amatnieku biedrība", None, "vaditajs@example.com"),
]


def _lietotaja_id(conn: sqlite3.Connection, epasts: str) -> int:
    return conn.execute("SELECT id FROM lietotaji WHERE epasts = ?", (epasts,)).fetchone()[0]


def organizacijas(conn: sqlite3.Connection) -> None:
    from crm.organizacijas import normalizet

    if not _tuksa(conn, "organizacijas"):
        return
    for nosaukums, reg_nr, epasts in ORGANIZACIJAS:
        conn.execute(
            "INSERT INTO organizacijas (nosaukums, nosaukums_meklesanai, reg_nr, atbildigais_id) VALUES (?, ?, ?, ?)",
            (nosaukums, normalizet(nosaukums), reg_nr, _lietotaja_id(conn, epasts)),
        )


# Datu sadaļas pēc lietotājiem, atkarību secībā.
SADALAS: list = [organizacijas]


def ieladet(parole: str) -> None:
    db.inicializet()
    with db.savienojums() as conn:
        lietotaji(conn, parole)
        for sadala in SADALAS:
            sadala(conn)


def main() -> int:
    parole = os.environ.get("CRM_SAKUMDATU_PAROLE", "")
    if len(parole) < PAROLES_MIN_GARUMS:
        print(f"Norādiet CRM_SAKUMDATU_PAROLE (vismaz {PAROLES_MIN_GARUMS} rakstzīmes).", file=sys.stderr)
        return 2
    ieladet(parole)
    print(f"Sākumdati ielādēti: {db.db_cels()}")
    print("Lietotāji: " + ", ".join(epasts for _, epasts, _ in LIETOTAJI))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
