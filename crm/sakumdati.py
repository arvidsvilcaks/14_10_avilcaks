"""Sintētiski sākumdati. Palaišana: CRM_SAKUMDATU_PAROLE=... make seed

Katra sadaļa tiek ielādēta tikai tad, ja attiecīgā tabula ir tukša, tāpēc
skriptu var palaist atkārtoti. Visiem lietotājiem ir viena parole no vides
mainīgā `CRM_SAKUMDATU_PAROLE`; repozitorijā paroles nav.
"""

import os
import sqlite3
import sys
from datetime import timedelta

from crm import db, laiks, paroles
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


MIJIEDARBIBU_VEIDI = ["zvans", "e-pasts", "tikšanās"]
MIJIEDARBIBU_TEMAS = [
    "Pārrunāta sadarbība nākamajam ceturksnim.",
    "Nosūtīts piedāvājums; gaida atbildi.",
    "Tikšanās par kopīgu pasākumu ezermalā.",
    "Precizēti rēķina rekvizīti.",
    "Organizācija interesējas par pašvaldības atbalstu.",
]


def mijiedarbibas(conn: sqlite3.Connection) -> None:
    """30 mijiedarbības pēdējo 20 dienu laikā; autors ir organizācijas atbildīgais."""
    if not _tuksa(conn, "mijiedarbibas"):
        return
    organizacijas = conn.execute("SELECT id, atbildigais_id FROM organizacijas ORDER BY id").fetchall()
    sodien = laiks.sodien()
    for i in range(30):
        org = organizacijas[i % len(organizacijas)]
        conn.execute(
            "INSERT INTO mijiedarbibas (datums, veids, organizacija_id, darbinieks_id, kopsavilkums) VALUES (?, ?, ?, ?, ?)",
            (
                (sodien - timedelta(days=(i * 2) % 21)).isoformat(),
                MIJIEDARBIBU_VEIDI[i % 3],
                org["id"],
                org["atbildigais_id"],
                MIJIEDARBIBU_TEMAS[i % len(MIJIEDARBIBU_TEMAS)],
            ),
        )


# (dienas līdz termiņam, statuss, apraksts); negatīvas dienas — termiņš pagātnē.
PIEPRASIJUMI = [
    (-5, "Darbā", "Lūgums sniegt informāciju par nomas noteikumiem."),
    (-2, "Jauns", "Jautājums par atkritumu izvešanas grafiku."),
    (-1, "Atbildēts", "Pieprasījums pēc sadarbības līguma kopijas."),
    (0, "Jauns", "Lūgums apstiprināt pasākuma norises vietu."),
    (1, "Darbā", "Piedāvājums kopīgam projektam."),
    (3, "Jauns", "Jautājums par ceļa remontu pie uzņēmuma."),
    (7, "Darbā", "Lūgums sagatavot atbalsta vēstuli."),
    (14, "Jauns", "Jautājums par tirgus vietu nomu."),
]


def pieprasijumi(conn: sqlite3.Connection) -> None:
    if not _tuksa(conn, "pieprasijumi"):
        return
    organizacijas = conn.execute("SELECT id, atbildigais_id FROM organizacijas ORDER BY id").fetchall()
    sodien = laiks.sodien()
    for i, (dienas, statuss, apraksts) in enumerate(PIEPRASIJUMI):
        org = organizacijas[i % len(organizacijas)]
        conn.execute(
            "INSERT INTO pieprasijumi (organizacija_id, apraksts, termins, statuss, atbildigais_id) VALUES (?, ?, ?, ?, ?)",
            (org["id"], apraksts, (sodien + timedelta(days=dienas)).isoformat(), statuss, org["atbildigais_id"]),
        )


# (lietotāja e-pasts, dienas līdz termiņam, izpildīts, nosaukums)
UZDEVUMI = [
    ("darbinieks1@example.com", -2, False, "Piezvanīt par līguma pagarinājumu"),
    ("darbinieks1@example.com", 0, False, "Sagatavot tikšanās darba kārtību"),
    ("darbinieks1@example.com", 0, True, "Nosūtīt piedāvājumu"),
    ("darbinieks1@example.com", 2, False, "Atjaunot organizācijas datus"),
    ("darbinieks2@example.com", -1, False, "Atbildēt uz e-pastu par pasākumu"),
    ("darbinieks2@example.com", 0, False, "Pārbaudīt rēķina rekvizītus"),
    ("darbinieks2@example.com", 5, False, "Plānot vizīti pie partnera"),
    ("vaditajs@example.com", 0, False, "Pārskatīt nedēļas kavējumus"),
]


def uzdevumi(conn: sqlite3.Connection) -> None:
    if not _tuksa(conn, "uzdevumi"):
        return
    sodien = laiks.sodien()
    for epasts, dienas, izpildits, nosaukums in UZDEVUMI:
        lietotaja_id = _lietotaja_id(conn, epasts)
        organizacija = conn.execute(
            "SELECT id FROM organizacijas WHERE atbildigais_id = ? ORDER BY id LIMIT 1", (lietotaja_id,)
        ).fetchone()
        conn.execute(
            "INSERT INTO uzdevumi (nosaukums, termins, izpildits, atbildigais_id, organizacija_id) VALUES (?, ?, ?, ?, ?)",
            (nosaukums, (sodien + timedelta(days=dienas)).isoformat(), int(izpildits), lietotaja_id,
             organizacija["id"] if organizacija else None),
        )


# Datu sadaļas pēc lietotājiem, atkarību secībā.
SADALAS: list = [organizacijas, mijiedarbibas, pieprasijumi, uzdevumi]


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
