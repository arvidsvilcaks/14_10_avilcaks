-- Ezermalas CRM datubāzes shēma (SQLite).

CREATE TABLE IF NOT EXISTS lietotaji (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vards TEXT NOT NULL,
    epasts TEXT NOT NULL UNIQUE,
    paroles_salt BLOB NOT NULL,
    paroles_hash BLOB NOT NULL,
    izveidots TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
