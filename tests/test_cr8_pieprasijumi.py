"""CR-8: pieprasījumi no organizācijām (F4)."""

from datetime import date, timedelta

import pytest

from crm import laiks
from tests.conftest import HTML, pieslegt, pieslegt_vaditaju

SODIEN = date(2026, 10, 14)


@pytest.fixture(autouse=True)
def fiksets_datums(monkeypatch):
    monkeypatch.setattr(laiks, "sodien", lambda: SODIEN)


def org(klients) -> int:
    return klients.post("/organizacijas", json={"nosaukums": "SIA Paraugs"}).json()["id"]


def izveidot(klients, organizacija_id, dienas=3, apraksts="Jautājums", **papildus) -> dict:
    dati = {"organizacija_id": organizacija_id, "apraksts": apraksts, "termins": (SODIEN + timedelta(days=dienas)).isoformat()}
    atbilde = klients.post("/pieprasijumi", json=dati | papildus)
    assert atbilde.status_code == 201, atbilde.text
    return atbilde.json()


def test_izveido_ar_statusu_jauns(klients):  # AC1
    anna = pieslegt(klients, "anna@example.com", "Anna")
    p = izveidot(klients, org(klients), statuss="Atbildēts")
    assert p["statuss"] == "Jauns"
    assert p["atbildigais_id"] == anna["id"]
    assert p["atbildiga_vards"] == "Anna"
    assert p["kavets"] is False


@pytest.mark.parametrize("termins", [None, "", "14.10.2026", "2026-02-30"])
def test_bez_termina_vai_nederigs_datums_422(klients, termins):  # AC2
    pieslegt(klients, "anna@example.com")
    dati = {"organizacija_id": org(klients), "apraksts": "X"} | ({} if termins is None else {"termins": termins})
    atbilde = klients.post("/pieprasijumi", json=dati)
    assert atbilde.status_code == 422
    assert atbilde.json()["error"]["details"][0]["field"] == "termins"


@pytest.mark.parametrize("statuss", ["Slēgts", "darbā", ""])
def test_nederigs_statuss_422(klients, statuss):  # AC3
    pieslegt(klients, "anna@example.com")
    p = izveidot(klients, org(klients))
    atbilde = klients.patch(f"/pieprasijumi/{p['id']}", json={"statuss": statuss})
    assert atbilde.status_code == 422
    assert klients.get("/pieprasijumi", params={"statuss": statuss}).status_code == 422


@pytest.mark.parametrize(
    ("dienas", "statuss", "kavets"),
    [(-1, "Darbā", True), (0, "Jauns", False), (-1, "Atbildēts", False), (-30, "Jauns", True), (1, "Darbā", False)],
)
def test_kavets(klients, dienas, statuss, kavets):  # AC4, AC5, AC6
    pieslegt(klients, "anna@example.com")
    p = izveidot(klients, org(klients), dienas=dienas)
    assert klients.patch(f"/pieprasijumi/{p['id']}", json={"statuss": statuss}).json()["kavets"] is kavets
    lapa = klients.get("/pieprasijumi", headers=HTML).text
    assert ('<span class="atzime kavets">Kavēts</span>' in lapa) is kavets


def test_filtri_statuss_un_kavets(klients):  # AC7
    pieslegt(klients, "anna@example.com")
    o = org(klients)
    darba = izveidot(klients, o, dienas=2, apraksts="darbā")
    klients.patch(f"/pieprasijumi/{darba['id']}", json={"statuss": "Darbā"})
    kavets = izveidot(klients, o, dienas=-1, apraksts="kavēts")
    atbildets = izveidot(klients, o, dienas=-1, apraksts="atbildēts")
    klients.patch(f"/pieprasijumi/{atbildets['id']}", json={"statuss": "Atbildēts"})
    assert [p["apraksts"] for p in klients.get("/pieprasijumi", params={"statuss": "Darbā"}).json()] == ["darbā"]
    assert [p["apraksts"] for p in klients.get("/pieprasijumi", params={"kavets": "true"}).json()] == ["kavēts"]
    assert {p["apraksts"] for p in klients.get("/pieprasijumi", params={"kavets": "false"}).json()} == {"darbā", "atbildēts"}
    assert kavets["kavets"] is True
    lapa = klients.get("/pieprasijumi?statuss=Darb%C4%81", headers=HTML)
    assert "Pieprasījumi statusā „Darbā”" in lapa.text


def test_darbinieks_redz_savus_un_nevar_mainit_citu(jauns_klients):  # AC8
    anna, juris = jauns_klients(), jauns_klients()
    pieslegt(anna, "anna@example.com")
    pieslegt(juris, "juris@example.com")
    o = org(anna)
    annas = izveidot(anna, o, apraksts="annas")
    izveidot(juris, o, apraksts="jura")
    assert [p["apraksts"] for p in anna.get("/pieprasijumi").json()] == ["annas"]
    assert juris.patch(f"/pieprasijumi/{annas['id']}", json={"statuss": "Darbā"}).status_code == 403
    assert juris.post(f"/pieprasijumi/{annas['id']}/statuss", data={"statuss": "Darbā"}).status_code == 403
    assert anna.get("/pieprasijumi").json()[0]["statuss"] == "Jauns"


def test_vaditajs_redz_visus_ar_atbildigo(jauns_klients):  # AC9
    anna, juris, vaditajs = jauns_klients(), jauns_klients(), jauns_klients()
    pieslegt(anna, "anna@example.com", "Anna")
    pieslegt(juris, "juris@example.com", "Juris")
    pieslegt_vaditaju(vaditajs)
    o = org(anna)
    izveidot(anna, o)
    izveidot(juris, o)
    visi = vaditajs.get("/pieprasijumi").json()
    assert {p["atbildiga_vards"] for p in visi} == {"Anna", "Juris"}
    lapa = vaditajs.get("/pieprasijumi", headers=HTML).text
    assert "Atbildīgais</th>" in lapa and "Juris" in lapa


def test_atbildigo_maina_tikai_vaditajs(jauns_klients):
    anna, vaditajs = jauns_klients(), jauns_klients()
    pieslegt(anna, "anna@example.com")
    juris = pieslegt(jauns_klients(), "juris@example.com")
    pieslegt_vaditaju(vaditajs)
    o = org(anna)
    p = izveidot(anna, o)
    assert anna.patch(f"/pieprasijumi/{p['id']}", json={"atbildigais_id": juris["id"]}).status_code == 403
    assert anna.post("/pieprasijumi", json={"organizacija_id": o, "apraksts": "X", "termins": "2026-10-20", "atbildigais_id": juris["id"]}).status_code == 403
    assert vaditajs.patch(f"/pieprasijumi/{p['id']}", json={"atbildigais_id": juris["id"]}).json()["atbildigais_id"] == juris["id"]
    assert vaditajs.patch(f"/pieprasijumi/{p['id']}", json={"atbildigais_id": 999}).status_code == 422


def test_statuss_var_atgriezties(klients):
    pieslegt(klients, "anna@example.com")
    p = izveidot(klients, org(klients))
    klients.patch(f"/pieprasijumi/{p['id']}", json={"statuss": "Atbildēts"})
    assert klients.patch(f"/pieprasijumi/{p['id']}", json={"statuss": "Darbā"}).json()["statuss"] == "Darbā"


def test_neeksistejoss_un_nederigs(klients):
    pieslegt(klients, "anna@example.com")
    assert klients.patch("/pieprasijumi/999", json={"statuss": "Darbā"}).status_code == 404
    atbilde = klients.post("/pieprasijumi", json={"organizacija_id": 999, "apraksts": "X", "termins": "2026-10-20"})
    assert atbilde.status_code == 422 and atbilde.json()["error"]["details"][0]["field"] == "organizacija_id"
    p = izveidot(klients, org(klients))
    assert klients.patch(f"/pieprasijumi/{p['id']}", json={"termins": None}).status_code == 422


def test_html_forma_un_statusa_maina(klients):
    pieslegt(klients, "anna@example.com")
    o = org(klients)
    atbilde = klients.post("/pieprasijumi", data={"organizacija_id": o, "apraksts": "Forma", "termins": "2026-10-20"}, follow_redirects=False)
    assert atbilde.status_code == 303
    p = klients.get("/pieprasijumi").json()[0]
    atbilde = klients.post(f"/pieprasijumi/{p['id']}/statuss", data={"statuss": "Darbā"}, follow_redirects=False)
    assert atbilde.status_code == 303
    assert klients.get("/pieprasijumi").json()[0]["statuss"] == "Darbā"
    kluda = klients.post("/pieprasijumi", data={"organizacija_id": o, "apraksts": ""})
    assert kluda.status_code == 422 and 'aria-invalid="true"' in kluda.text
    assert "Pieprasījumi" in klients.get(f"/organizacijas/{o}", headers=HTML).text
