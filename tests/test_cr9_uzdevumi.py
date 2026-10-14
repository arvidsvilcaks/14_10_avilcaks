"""CR-9: uzdevumi (F5, bez atgādinājumiem)."""

from datetime import date, timedelta

import pytest

from crm import laiks
from crm.uzdevumi import drosa_atpakal_adrese
from tests.conftest import HTML, pieslegt, pieslegt_vaditaju

SODIEN = date(2026, 10, 14)


@pytest.fixture(autouse=True)
def fiksets_datums(monkeypatch):
    monkeypatch.setattr(laiks, "sodien", lambda: SODIEN)


def izveidot(klients, nosaukums="Piezvanīt", dienas=0, **papildus) -> dict:
    dati = {"nosaukums": nosaukums, "termins": (SODIEN + timedelta(days=dienas)).isoformat()} | papildus
    atbilde = klients.post("/uzdevumi", json=dati)
    assert atbilde.status_code == 201, atbilde.text
    return atbilde.json()


def test_izveido_uzdevumu(klients):  # AC1
    anna = pieslegt(klients, "anna@example.com", "Anna")
    u = izveidot(klients)
    assert u["atbildigais_id"] == anna["id"]
    assert u["izpildits"] is False
    assert u["organizacija_id"] is None


@pytest.mark.parametrize("dati", [{"termins": "2026-10-14"}, {"nosaukums": " ", "termins": "2026-10-14"}, {"nosaukums": "X"}])
def test_bez_nosaukuma_vai_termina_422(klients, dati):  # AC2
    pieslegt(klients, "anna@example.com")
    assert klients.post("/uzdevumi", json=dati).status_code == 422


def test_atzime_savu_ar_prg(klients):  # AC3
    pieslegt(klients, "anna@example.com")
    u = izveidot(klients)
    atbilde = klients.post(f"/uzdevumi/{u['id']}/izpildits", data={"atpakal": "/uzdevumi"}, follow_redirects=False)
    assert atbilde.status_code == 303
    assert atbilde.headers["location"] == "/uzdevumi?pazinojums=uzdevums-izpildits"
    lapa = klients.get(atbilde.headers["location"], headers=HTML).text
    assert '<div class="zina" role="status">Uzdevums atzīmēts kā izpildīts.</div>' in lapa
    assert klients.get("/uzdevumi").json()[0]["izpildits"] is True


def test_atzime_json(klients):  # AC3
    pieslegt(klients, "anna@example.com")
    u = izveidot(klients)
    atbilde = klients.post(f"/uzdevumi/{u['id']}/izpildits")
    assert atbilde.status_code == 200 and atbilde.json()["izpildits"] is True


@pytest.mark.parametrize("vaditajs", [False, True])
def test_svesu_uzdevumu_atzimet_nevar(jauns_klients, vaditajs):  # AC4
    anna, cits = jauns_klients(), jauns_klients()
    pieslegt(anna, "anna@example.com")
    pieslegt_vaditaju(cits) if vaditajs else pieslegt(cits, "juris@example.com")
    u = izveidot(anna)
    assert cits.post(f"/uzdevumi/{u['id']}/izpildits").status_code == 403
    assert cits.post(f"/uzdevumi/{u['id']}/izpildits", data={"atpakal": "/panelis"}).status_code == 403
    assert anna.get("/uzdevumi").json()[0]["izpildits"] is False


def test_neeksistejoss_404(klients):  # AC5
    pieslegt(klients, "anna@example.com")
    assert klients.post("/uzdevumi/999/izpildits").status_code == 404


def test_atkartota_atzimesana(klients):  # AC6
    pieslegt(klients, "anna@example.com")
    u = izveidot(klients)
    klients.post(f"/uzdevumi/{u['id']}/izpildits")
    atbilde = klients.post(f"/uzdevumi/{u['id']}/izpildits")
    assert atbilde.status_code == 200 and atbilde.json()["izpildits"] is True


def test_filtrs_lidz_sodienai(klients):  # AC7
    pieslegt(klients, "anna@example.com")
    izveidot(klients, "vakar", -1)
    izveidot(klients, "šodien", 0)
    izveidot(klients, "rīt", 1)
    izpildits = izveidot(klients, "izpildīts", -1)
    klients.post(f"/uzdevumi/{izpildits['id']}/izpildits")
    assert [u["nosaukums"] for u in klients.get("/uzdevumi", params={"lidz_sodienai": "true"}).json()] == ["vakar", "šodien"]
    assert len(klients.get("/uzdevumi").json()) == 4


def test_darbinieks_redz_savus(jauns_klients):  # AC8
    anna, juris, vaditajs = jauns_klients(), jauns_klients(), jauns_klients()
    pieslegt(anna, "anna@example.com")
    pieslegt(juris, "juris@example.com")
    pieslegt_vaditaju(vaditajs)
    izveidot(anna, "annas")
    izveidot(juris, "jura")
    assert [u["nosaukums"] for u in anna.get("/uzdevumi").json()] == ["annas"]
    assert {u["nosaukums"] for u in vaditajs.get("/uzdevumi").json()} == {"annas", "jura"}


def test_pieskirsana(jauns_klients):
    anna, vaditajs = jauns_klients(), jauns_klients()
    a = pieslegt(anna, "anna@example.com")
    juris = pieslegt(jauns_klients(), "juris@example.com")
    pieslegt_vaditaju(vaditajs)
    assert anna.post("/uzdevumi", json={"nosaukums": "X", "termins": "2026-10-14", "atbildigais_id": juris["id"]}).status_code == 403
    assert izveidot(anna, atbildigais_id=a["id"])["atbildigais_id"] == a["id"]
    assert izveidot(vaditajs, atbildigais_id=juris["id"])["atbildigais_id"] == juris["id"]
    assert vaditajs.post("/uzdevumi", json={"nosaukums": "X", "termins": "2026-10-14", "atbildigais_id": 999}).status_code == 422


def test_organizacija(klients):
    pieslegt(klients, "anna@example.com")
    o = klients.post("/organizacijas", json={"nosaukums": "SIA Paraugs"}).json()["id"]
    assert izveidot(klients, organizacija_id=o)["organizacijas_nosaukums"] == "SIA Paraugs"
    assert klients.post("/uzdevumi", json={"nosaukums": "X", "termins": "2026-10-14", "organizacija_id": 999}).status_code == 422


@pytest.mark.parametrize(
    ("adrese", "rezultats"),
    [("/panelis", "/panelis"), ("https://ļauns.lv", "/uzdevumi"), ("//ļauns.lv", "/uzdevumi"), ("/\\ļauns.lv", "/uzdevumi"), (None, "/uzdevumi")],
)
def test_atpakal_tikai_uz_lietotni(adrese, rezultats):
    assert drosa_atpakal_adrese(adrese, "/uzdevumi") == rezultats


def test_html_forma(klients):
    pieslegt(klients, "anna@example.com")
    assert klients.post("/uzdevumi", data={"nosaukums": "Forma", "termins": "2026-10-14"}, follow_redirects=False).status_code == 303
    kluda = klients.post("/uzdevumi", data={"nosaukums": "", "termins": ""})
    assert kluda.status_code == 422 and kluda.text.count('aria-invalid="true"') == 2
    lapa = klients.get("/uzdevumi", headers=HTML).text
    assert "Atzīmēt kā izpildītu" in lapa and "<caption>" in lapa
