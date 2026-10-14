-- Ezermalas CRM datubāzes shēma (SQLite).

CREATE TABLE IF NOT EXISTS lietotaji (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vards TEXT NOT NULL,
    epasts TEXT NOT NULL UNIQUE,
    paroles_salt BLOB NOT NULL,
    paroles_hash BLOB NOT NULL,
    loma TEXT NOT NULL DEFAULT 'darbinieks' CHECK (loma IN ('darbinieks', 'vaditajs')),
    izveidots TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS organizacijas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nosaukums TEXT NOT NULL,
    nosaukums_meklesanai TEXT NOT NULL,
    reg_nr TEXT UNIQUE,
    atbildigais_id INTEGER NOT NULL REFERENCES lietotaji(id),
    izveidots TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS organizacijas_atbildigais ON organizacijas(atbildigais_id);

CREATE TABLE IF NOT EXISTS mijiedarbibas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    datums TEXT NOT NULL,
    veids TEXT NOT NULL CHECK (veids IN ('zvans', 'e-pasts', 'tikšanās')),
    organizacija_id INTEGER NOT NULL REFERENCES organizacijas(id),
    darbinieks_id INTEGER NOT NULL REFERENCES lietotaji(id),
    kopsavilkums TEXT NOT NULL DEFAULT '',
    izveidots TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS mijiedarbibas_darbinieks ON mijiedarbibas(darbinieks_id, datums);
CREATE INDEX IF NOT EXISTS mijiedarbibas_organizacija ON mijiedarbibas(organizacija_id, datums);
