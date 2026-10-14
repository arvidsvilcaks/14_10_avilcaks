"""CR-6: organizācijas — izveidot, rediģēt, meklēt (F1)."""

import pytest

from crm import sakumdati
from tests.conftest import HTML, pieslegt, pieslegt_vaditaju


def izveidot(klients, nosaukums="SIA Paraugs", reg_nr=None) -> dict:
    dati = {"nosaukums": nosaukums} | ({"reg_nr": reg_nr} if reg_nr else {})
    atbilde = klients.post("/organizacijas", json=dati)
    assert atbilde.status_code == 201, atbilde.text
    return atbilde.json()


def test_darbinieks_izveido_organizaciju(klients):  # AC1
    anna = pieslegt(klients, "anna@example.com", "Anna")
    org = izveidot(klients, "  SIA Paraugs  ", "40003000001")
    assert org["nosaukums"] == "SIA Paraugs"
    assert org["atbildigais_id"] == anna["id"]
    assert org["atbildigais_vards"] == "Anna"


@pytest.mark.parametrize("dati", [{}, {"nosaukums": ""}, {"nosaukums": "    "}])
def test_bez_nosaukuma_422(klients, dati):  # AC2
    pieslegt(klients, "anna@example.com")
    atbilde = klients.post("/organizacijas", json=dati)
    assert atbilde.status_code == 422
    assert atbilde.json()["error"]["details"][0]["field"] == "nosaukums"


def test_dublets_reg_nr_409(klients):  # AC3
    pieslegt(klients, "anna@example.com")
    izveidot(klients, "SIA A", "40003000001")
    atbilde = klients.post("/organizacijas", json={"nosaukums": "SIA B", "reg_nr": "40003000001"})
    assert atbilde.status_code == 409
    assert len(klients.get("/organizacijas").json()) == 1


def test_atbildigais_labo_savu(klients):  # AC4
    pieslegt(klients, "anna@example.com")
    org = izveidot(klients)
    atbilde = klients.patch(f"/organizacijas/{org['id']}", json={"nosaukums": "SIA Jauns", "reg_nr": "123"})
    assert atbilde.status_code == 200
    assert klients.get(f"/organizacijas/{org['id']}").json() == atbilde.json()
    assert atbilde.json()["nosaukums"] == "SIA Jauns" and atbilde.json()["reg_nr"] == "123"


def test_darbinieks_nevar_labot_cita_organizaciju(jauns_klients):  # AC5
    anna, juris = jauns_klients(), jauns_klients()
    pieslegt(anna, "anna@example.com")
    pieslegt(juris, "juris@example.com")
    org = izveidot(anna)
    atbilde = juris.patch(f"/organizacijas/{org['id']}", json={"nosaukums": "Nozagts"})
    assert atbilde.status_code == 403
    assert anna.get(f"/organizacijas/{org['id']}").json()["nosaukums"] == "SIA Paraugs"
    assert juris.get(f"/organizacijas/{org['id']}/labot", headers=HTML).status_code == 403
    assert juris.get(f"/organizacijas/{org['id']}").status_code == 200  # skatīt drīkst


def test_darbinieks_nevar_mainit_atbildigo_pat_savai(jauns_klients):
    anna = jauns_klients()
    pieslegt(anna, "anna@example.com")
    juris = pieslegt(jauns_klients(), "juris@example.com")
    org = izveidot(anna)
    assert anna.patch(f"/organizacijas/{org['id']}", json={"atbildigais_id": juris["id"]}).status_code == 403


def test_vaditajs_maina_atbildigo(jauns_klients):  # AC6
    anna, vaditajs = jauns_klients(), jauns_klients()
    pieslegt(anna, "anna@example.com")
    juris = pieslegt(jauns_klients(), "juris@example.com", "Juris")
    pieslegt_vaditaju(vaditajs)
    org = izveidot(anna)
    atbilde = vaditajs.patch(f"/organizacijas/{org['id']}", json={"atbildigais_id": juris["id"]})
    assert atbilde.status_code == 200
    assert atbilde.json()["atbildigais_vards"] == "Juris"
    assert vaditajs.patch(f"/organizacijas/{org['id']}", json={"atbildigais_id": 999}).status_code == 422


@pytest.mark.parametrize("q", ["riga", "RĪG", "rigas log", "Loģistika"])
def test_meklesana_bez_garumzimem_un_burtu_lieluma(klients, q):  # AC7
    pieslegt(klients, "anna@example.com")
    izveidot(klients, "SIA Rīgas Loģistika")
    izveidot(klients, "SIA Ezermalas Koks")
    rezultats = klients.get("/organizacijas", params={"q": q}).json()
    assert [o["nosaukums"] for o in rezultats] == ["SIA Rīgas Loģistika"]


def test_meklesana_aizsarga_like_zimes(klients):
    pieslegt(klients, "anna@example.com")
    izveidot(klients, "SIA 100% Koks")
    izveidot(klients, "SIA Ezers")
    assert [o["nosaukums"] for o in klients.get("/organizacijas", params={"q": "%"}).json()] == ["SIA 100% Koks"]
    assert klients.get("/organizacijas", params={"q": "_"}).json() == []


def test_meklesana_bez_rezultatiem(klients):  # AC8
    pieslegt(klients, "anna@example.com")
    izveidot(klients)
    assert klients.get("/organizacijas", params={"q": "neesoša"}).json() == []
    lapa = klients.get("/organizacijas", params={"q": "neesoša"}, headers=HTML)
    assert lapa.status_code == 200
    assert "nav atrasta neviena organizācija" in lapa.text


def test_neeksistejosa_organizacija_404(klients):  # AC9
    pieslegt(klients, "anna@example.com")
    assert klients.get("/organizacijas/999").status_code == 404
    assert klients.get("/organizacijas/999", headers=HTML).status_code == 404
    assert klients.patch("/organizacijas/999", json={"nosaukums": "X"}).status_code == 404


def test_sakumdati_10_organizacijas_vismaz_2_darbiniekiem(lietotne, klients, monkeypatch):  # AC10
    monkeypatch.setenv("CRM_SAKUMDATU_PAROLE", "sākumdatu-parole")
    sakumdati.main()
    pieslegt(klients, "x@example.com")
    organizacijas = klients.get("/organizacijas").json()
    assert len(organizacijas) == 10
    assert len({o["atbildigais_id"] for o in organizacijas}) >= 2


def test_nepieslegtam_organizacijas_nav_pieejamas(klients):
    assert klients.get("/organizacijas").status_code == 401


def test_html_izveide_un_labosana(klients):
    pieslegt(klients, "anna@example.com")
    atbilde = klients.post("/organizacijas", data={"nosaukums": "SIA Forma"}, follow_redirects=False)
    assert atbilde.status_code == 303
    kartite = klients.get(atbilde.headers["location"], headers=HTML)
    assert "<h1>SIA Forma</h1>" in kartite.text
    org_id = int(atbilde.headers["location"].rsplit("/", 1)[1])
    labots = klients.post(f"/organizacijas/{org_id}/labot", data={"nosaukums": "SIA Forma 2", "reg_nr": ""}, follow_redirects=False)
    assert labots.status_code == 303
    assert klients.get(f"/organizacijas/{org_id}").json()["nosaukums"] == "SIA Forma 2"
    kluda = klients.post(f"/organizacijas/{org_id}/labot", data={"nosaukums": " "})
    assert kluda.status_code == 422 and 'aria-invalid="true"' in kluda.text


def test_html_saraksts_ar_pieejamu_tabulu(klients):
    pieslegt(klients, "anna@example.com")
    izveidot(klients)
    lapa = klients.get("/organizacijas", headers=HTML).text
    assert "<caption>" in lapa and 'scope="col"' in lapa and 'aria-current="page"' in lapa
