"""CR-4: pieslēgšanās, reģistrēšanās un atteikšanās (F0)."""

import logging
import sqlite3

import pytest

from tests.conftest import HTML, PAROLE, pieslegt, registret


def test_registracija_izveido_kontu_bez_paroles_atbilde(klients):  # AC1
    atbilde = klients.post("/auth/register", json={"vards": "Anna Paraugs", "epasts": "anna@example.com", "parole": PAROLE})
    assert atbilde.status_code == 201
    dati = atbilde.json()
    assert dati["vards"] == "Anna Paraugs"
    assert dati["epasts"] == "anna@example.com"
    assert "parole" not in dati and PAROLE not in atbilde.text


@pytest.mark.parametrize("otrs", ["anna@example.com", "Anna@Example.COM"])
def test_dublets_epasts_409(klients, otrs, tmp_path):  # AC2
    registret(klients, "anna@example.com")
    atbilde = klients.post("/auth/register", json={"vards": "Cita", "epasts": otrs, "parole": PAROLE})
    assert atbilde.status_code == 409
    assert atbilde.json()["error"]["code"] == "CONFLICT"
    with sqlite3.connect(tmp_path / "crm.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM lietotaji").fetchone()[0] == 1


@pytest.mark.parametrize(
    ("ievade", "lauks"),
    [
        ({"vards": "Anna", "epasts": "anna@", "parole": PAROLE}, "epasts"),
        ({"vards": "   ", "epasts": "anna@example.com", "parole": PAROLE}, "vards"),
        ({"epasts": "anna@example.com", "parole": PAROLE}, "vards"),
    ],
)
def test_nederigs_epasts_vai_vards_422(klients, ievade, lauks):  # AC3
    atbilde = klients.post("/auth/register", json=ievade)
    assert atbilde.status_code == 422
    kluda = atbilde.json()["error"]
    assert kluda["code"] == "VALIDATION_ERROR"
    assert [d["field"] for d in kluda["details"]] == [lauks]


def test_isa_parole_422(klients):  # AC4
    atbilde = klients.post("/auth/register", json={"vards": "Anna", "epasts": "anna@example.com", "parole": "a" * 11})
    assert atbilde.status_code == 422
    assert atbilde.json()["error"]["details"] == [{"field": "parole", "issue": "TOO_SHORT"}]


def test_nederigs_json_400(klients):
    atbilde = klients.post("/auth/register", content=b"{", headers={"content-type": "application/json"})
    assert atbilde.status_code == 400
    assert atbilde.json()["error"]["code"] == "BAD_REQUEST"


def test_pieslegsanas_ar_formu_novirza_uz_paneli(klients):  # AC5
    registret(klients, "anna@example.com", "Anna Paraugs")
    atbilde = klients.post(
        "/auth/login", data={"epasts": "anna@example.com", "parole": PAROLE}, follow_redirects=False
    )
    assert atbilde.status_code == 303
    assert atbilde.headers["location"] == "/panelis"
    panelis = klients.get("/panelis", headers=HTML)
    assert panelis.status_code == 200
    assert "Anna Paraugs" in panelis.text


def test_pieslegsanas_json_izveido_sesiju(klients):  # AC5
    registret(klients, "anna@example.com")
    atbilde = klients.post("/auth/login", json={"epasts": "ANNA@example.com", "parole": PAROLE})
    assert atbilde.status_code == 200
    assert atbilde.json()["lietotajs"]["epasts"] == "anna@example.com"
    assert "crm_sesija" in klients.cookies


def test_nepareiza_parole_un_nezinams_epasts_vienads_zinojums(klients):  # AC6
    registret(klients, "anna@example.com")
    nepareiza = klients.post("/auth/login", json={"epasts": "anna@example.com", "parole": "nepareiza-parole"})
    nezinams = klients.post("/auth/login", json={"epasts": "nav@example.com", "parole": PAROLE})
    assert nepareiza.status_code == nezinams.status_code == 401
    assert nepareiza.json() == nezinams.json()
    assert "crm_sesija" not in klients.cookies


def test_nepareiza_parole_formā_rada_kludu(klients):  # AC6
    registret(klients, "anna@example.com")
    atbilde = klients.post("/auth/login", data={"epasts": "anna@example.com", "parole": "nepareiza-parole"})
    assert atbilde.status_code == 401
    assert "Nepareizs e-pasts vai parole" in atbilde.text
    assert 'role="alert"' in atbilde.text


def test_atteiksanas_dzes_sesiju(klients):  # AC7
    pieslegt(klients, "anna@example.com")
    assert klients.get("/panelis", headers=HTML).status_code == 200
    atbilde = klients.post("/auth/logout", data={}, headers=HTML, follow_redirects=False)
    assert atbilde.status_code == 303
    assert atbilde.headers["location"] == "/auth/login"
    panelis = klients.get("/panelis", headers=HTML, follow_redirects=False)
    assert panelis.status_code == 303
    assert panelis.headers["location"] == "/auth/login"


def test_atteiksanas_json_204(klients):  # AC7
    pieslegt(klients, "anna@example.com")
    assert klients.post("/auth/logout").status_code == 204
    assert klients.get("/panelis").status_code == 401


def test_nepieslegts_novirza_uz_pieslegsanos(klients):  # AC8
    atbilde = klients.get("/panelis", headers=HTML, follow_redirects=False)
    assert atbilde.status_code == 303
    assert atbilde.headers["location"] == "/auth/login"


def test_nepieslegts_api_401(klients):  # AC8
    atbilde = klients.get("/panelis")
    assert atbilde.status_code == 401
    assert atbilde.json()["error"]["code"] == "UNAUTHORIZED"


def test_parole_tikai_salota_jauktā_veidā_un_ne_zurnalos(klients, tmp_path, caplog):  # AC9
    caplog.set_level(logging.DEBUG)
    registret(klients, "anna@example.com")
    klients.post("/auth/login", json={"epasts": "anna@example.com", "parole": PAROLE})
    with sqlite3.connect(tmp_path / "crm.db") as conn:
        salt, hash_ = conn.execute("SELECT paroles_salt, paroles_hash FROM lietotaji").fetchone()
        visas_vertibas = conn.execute("SELECT * FROM lietotaji").fetchone()
    assert len(salt) == 16 and len(hash_) == 32
    assert PAROLE.encode() not in b"".join(v if isinstance(v, bytes) else str(v).encode() for v in visas_vertibas)
    assert PAROLE not in caplog.text


def test_sakumlapa_novirza(klients):  # AC10
    atbilde = klients.get("/", follow_redirects=False)
    assert atbilde.headers["location"] == "/auth/login"
    pieslegt(klients, "anna@example.com")
    atbilde = klients.get("/", follow_redirects=False)
    assert atbilde.status_code == 303
    assert atbilde.headers["location"] == "/panelis"


def test_registracijas_forma_ar_kludam_ir_pieejama(klients):
    atbilde = klients.post("/auth/register", data={"vards": "Anna", "epasts": "nederigs", "parole": "isa"})
    assert atbilde.status_code == 422
    assert 'aria-invalid="true"' in atbilde.text
    assert 'role="alert"' in atbilde.text
    assert 'value="isa"' not in atbilde.text  # parole netiek atgriezta formā


def test_registracijas_forma_novirza_uz_pieslegsanos(klients):
    atbilde = klients.post(
        "/auth/register",
        data={"vards": "Anna", "epasts": "anna@example.com", "parole": PAROLE},
        follow_redirects=False,
    )
    assert atbilde.status_code == 303
    assert atbilde.headers["location"] == "/auth/login?registrets=1"
    lapa = klients.get(atbilde.headers["location"], headers=HTML)
    assert 'role="status"' in lapa.text
