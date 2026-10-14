"""SQLite savienojums un shēma."""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SAKNE = Path(__file__).resolve().parent
NOKLUSETA_DB = SAKNE.parent / "data" / "crm.db"


def db_cels() -> Path:
    return Path(os.environ.get("CRM_DB_PATH", NOKLUSETA_DB))


@contextmanager
def savienojums() -> Iterator[sqlite3.Connection]:
    """Atver savienojumu; veiksmīgas izpildes beigās izmaiņas tiek saglabātas."""
    cels = db_cels()
    cels.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(cels)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


# Kolonnas, kas pievienotas pēc tabulas izveides: (tabula, kolonna, definīcija).
MIGRACIJAS = [
    ("lietotaji", "loma", "TEXT NOT NULL DEFAULT 'darbinieks' CHECK (loma IN ('darbinieks', 'vaditajs'))"),
    ("uzdevumi", "atgadinat", "TEXT"),
    ("mijiedarbibas", "mi_kopsavilkums", "TEXT"),
    ("mijiedarbibas", "mi_nakamais_solis", "TEXT"),
    ("mijiedarbibas", "mi_apstiprinaja_id", "INTEGER REFERENCES lietotaji(id)"),
]

# N2: piekļuves žurnāla ierakstu glabāšanas termiņš.
ZURNALA_GLABASANAS_DIENAS = 365


def inicializet() -> None:
    with savienojums() as conn:
        conn.executescript((SAKNE / "shema.sql").read_text(encoding="utf-8"))
        for tabula, kolonna, definicija in MIGRACIJAS:
            esosas = {rinda["name"] for rinda in conn.execute(f"PRAGMA table_info({tabula})")}
            if kolonna not in esosas:
                conn.execute(f"ALTER TABLE {tabula} ADD COLUMN {kolonna} {definicija}")
        conn.execute(
            "DELETE FROM piekluves_zurnals WHERE laiks < datetime('now', ?)", (f"-{ZURNALA_GLABASANAS_DIENAS} days",)
        )
