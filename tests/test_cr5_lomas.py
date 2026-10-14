"""CR-5: lomas „Darbinieks” un „Vadītājs” (N3)."""

import sqlite3

import pytest

from crm import sakumdati
from tests.conftest import HTML, iestatit_lomu, pieslegt, pieslegt_vaditaju, registret


def _loma(tmp_path, lietotaja_id: int) -> str:
    with sqlite3.connect(tmp_path / "crm.db") as conn:
        return conn.execute("SELECT loma FROM lietotaji WHERE id = ?", (lietotaja_id,)).fetchone()[0]


def test_jauns_lietotajs_ir_darbinieks(klients):  # AC1
    assert registret(klients, "anna@example.com")["loma"] == "darbinieks"


def test_vaditajs_maina_cita_lomu(jauns_klients, tmp_path):  # AC2
    vaditajs, darbinieks = jauns_klients(), jauns_klients()
    pieslegt_vaditaju(vaditajs)
    anna = pieslegt(darbinieks, "anna@example.com")
    atbilde = vaditajs.patch(f"/lietotaji/{anna['id']}/loma", json={"loma": "vaditajs"})
    assert atbilde.status_code == 200
    assert atbilde.json()["loma"] == "vaditajs"
    assert _loma(tmp_path, anna["id"]) == "vaditajs"


@pytest.mark.parametrize("sev", [True, False])
def test_darbinieks_nevar_mainit_lomu(jauns_klients, tmp_path, sev):  # AC3
    k1, k2 = jauns_klients(), jauns_klients()
    anna = pieslegt(k1, "anna@example.com")
    juris = pieslegt(k2, "juris@example.com")
    merkis = anna if sev else juris
    atbilde = k1.patch(f"/lietotaji/{merkis['id']}/loma", json={"loma": "vaditajs"})
    assert atbilde.status_code == 403
    assert atbilde.json()["error"]["code"] == "FORBIDDEN"
    assert _loma(tmp_path, merkis["id"]) == "darbinieks"


@pytest.mark.parametrize("loma", ["admins", "Vadītājs", "", None])
def test_nederiga_loma_422(jauns_klients, loma):  # AC4
    vaditajs, darbinieks = jauns_klients(), jauns_klients()
    pieslegt_vaditaju(vaditajs)
    anna = pieslegt(darbinieks, "anna@example.com")
    atbilde = vaditajs.patch(f"/lietotaji/{anna['id']}/loma", json={"loma": loma})
    assert atbilde.status_code == 422
    assert atbilde.json()["error"]["details"][0]["field"] == "loma"


def test_neeksistejoss_lietotajs_404(klients):
    pieslegt_vaditaju(klients)
    assert klients.patch("/lietotaji/999/loma", json={"loma": "darbinieks"}).status_code == 404


def test_lomas_maina_ietekme_aktivu_sesiju(jauns_klients):  # AC5
    vaditajs, darbinieks = jauns_klients(), jauns_klients()
    pieslegt_vaditaju(vaditajs)
    anna = pieslegt(darbinieks, "anna@example.com")
    juris = pieslegt(jauns_klients(), "juris@example.com")
    assert darbinieks.patch(f"/lietotaji/{juris['id']}/loma", json={"loma": "vaditajs"}).status_code == 403
    vaditajs.patch(f"/lietotaji/{anna['id']}/loma", json={"loma": "vaditajs"})
    # tā pati sesija, jaunā loma
    assert darbinieks.patch(f"/lietotaji/{juris['id']}/loma", json={"loma": "vaditajs"}).status_code == 200
    assert "Vadītājs" in darbinieks.get("/panelis", headers=HTML).text


def test_vienigais_vaditajs_nevar_noņemt_lomu_sev(klients, tmp_path):
    vaditajs = pieslegt_vaditaju(klients)
    atbilde = klients.patch(f"/lietotaji/{vaditajs['id']}/loma", json={"loma": "darbinieks"})
    assert atbilde.status_code == 409
    assert _loma(tmp_path, vaditajs["id"]) == "vaditajs"


def test_divu_vaditaju_gadijuma_var_noņemt_lomu_sev(jauns_klients):
    k = jauns_klients()
    vaditajs = pieslegt_vaditaju(k)
    pieslegt(jauns_klients(), "otrs@example.com")
    iestatit_lomu("otrs@example.com", "vaditajs")
    assert k.patch(f"/lietotaji/{vaditajs['id']}/loma", json={"loma": "darbinieks"}).status_code == 200


def test_macibu_rezima_parslegsana(klients, monkeypatch):  # AC6
    monkeypatch.setenv("CRM_MACIBU_REZIMS", "1")
    pieslegt(klients, "anna@example.com")
    assert "Mācību režīms" in klients.get("/panelis", headers=HTML).text
    atbilde = klients.post("/macibu-rezims/loma", data={"loma": "vaditajs"}, follow_redirects=False)
    assert atbilde.status_code == 303
    assert "· Vadītājs" in klients.get("/panelis", headers=HTML).text
    assert klients.post("/macibu-rezims/loma", json={"loma": "darbinieks"}).json()["loma"] == "darbinieks"


def test_bez_macibu_rezima_parslegsana_aizliegta(klients, monkeypatch, tmp_path):  # AC7
    monkeypatch.delenv("CRM_MACIBU_REZIMS", raising=False)
    anna = pieslegt(klients, "anna@example.com")
    assert "Mācību režīms" not in klients.get("/panelis", headers=HTML).text
    atbilde = klients.post("/macibu-rezims/loma", json={"loma": "vaditajs"})
    assert atbilde.status_code == 403
    assert _loma(tmp_path, anna["id"]) == "darbinieks"


def test_sakumdati_izveido_vaditaju(lietotne, monkeypatch, tmp_path, klients):  # AC8
    monkeypatch.setenv("CRM_SAKUMDATU_PAROLE", "sākumdatu-parole")
    assert sakumdati.main() == 0
    assert sakumdati.main() == 0  # atkārtoti — bez dublikātiem
    with sqlite3.connect(tmp_path / "crm.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM lietotaji WHERE loma = 'vaditajs'").fetchone()[0] == 1
    atbilde = klients.post("/auth/login", json={"epasts": "vaditajs@example.com", "parole": "sākumdatu-parole"})
    assert atbilde.json()["lietotajs"]["loma"] == "vaditajs"


def test_sakumdati_bez_paroles_neizpildas(monkeypatch, lietotne):
    monkeypatch.delenv("CRM_SAKUMDATU_PAROLE", raising=False)
    assert sakumdati.main() == 2


def test_vecas_datubazes_migracija(tmp_path, monkeypatch):
    cels = tmp_path / "vecā.db"
    with sqlite3.connect(cels) as conn:
        conn.execute(
            "CREATE TABLE lietotaji (id INTEGER PRIMARY KEY AUTOINCREMENT, vards TEXT NOT NULL, epasts TEXT NOT NULL UNIQUE,"
            " paroles_salt BLOB NOT NULL, paroles_hash BLOB NOT NULL, izveidots TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        conn.execute("INSERT INTO lietotaji (vards, epasts, paroles_salt, paroles_hash) VALUES ('A', 'a@example.com', x'00', x'00')")
    monkeypatch.setenv("CRM_DB_PATH", str(cels))
    from crm import db

    db.inicializet()
    with sqlite3.connect(cels) as conn:
        assert conn.execute("SELECT loma FROM lietotaji").fetchone()[0] == "darbinieks"
