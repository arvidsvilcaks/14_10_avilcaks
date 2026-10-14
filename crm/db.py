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


def inicializet() -> None:
    with savienojums() as conn:
        conn.executescript((SAKNE / "shema.sql").read_text(encoding="utf-8"))
