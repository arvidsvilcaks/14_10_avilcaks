"""CR-7: mijiedarbību žurnāls (F3)."""

from datetime import date, timedelta

import pytest

from crm import laiks, sakumdati
from tests.conftest import HTML, pieslegt, pieslegt_vaditaju


def org(klients, nosaukums="SIA Paraugs") -> int:
    return klients.post("/organizacijas", json={"nosaukums": nosaukums}).json()["id"]


def pievienot(klients, organizacija_id, datums=None, veids="zvans", kopsavilkums="Saruna") -> dict:
    dati = {
        "datums": (datums or laiks.sodien()).isoformat(),
        "veids": veids,
        "organizacija_id": organizacija_id,
        "kopsavilkums": kopsavilkums,
    }
    atbilde = klients.post("/mijiedarbibas", json=dati)
    assert atbilde.status_code == 201, atbilde.text
    return atbilde.json()


def test_pievieno_mijiedarbibu(klients):  # AC1
    anna = pieslegt(klients, "anna@example.com", "Anna")
    m = pievienot(klients, org(klients), veids="tikšanās")
    assert m["darbinieks_id"] == anna["id"]
    assert m["darbinieka_vards"] == "Anna"
    assert m["veids"] == "tikšanās"
    assert m["organizacijas_nosaukums"] == "SIA Paraugs"


@pytest.mark.parametrize("veids", ["vēstule", "Zvans", ""])
def test_nederigs_veids_422(klients, veids):  # AC2
    pieslegt(klients, "anna@example.com")
    atbilde = klients.post(
        "/mijiedarbibas", json={"datums": "2026-01-01", "veids": veids, "organizacija_id": org(klients)}
    )
    assert atbilde.status_code == 422
    assert atbilde.json()["error"]["details"][0]["field"] == "veids"


def test_neeksistejosa_organizacija_422(klients):  # AC3
    pieslegt(klients, "anna@example.com")
    atbilde = klients.post("/mijiedarbibas", json={"datums": "2026-01-01", "veids": "zvans", "organizacija_id": 999})
    assert atbilde.status_code == 422
    assert atbilde.json()["error"]["details"] == [{"field": "organizacija_id", "issue": "NOT_FOUND"}]


def test_datums_nakotne_422(klients):  # AC4
    pieslegt(klients, "anna@example.com")
    rit = laiks.sodien() + timedelta(days=1)
    atbilde = klients.post("/mijiedarbibas", json={"datums": rit.isoformat(), "veids": "zvans", "organizacija_id": org(klients)})
    assert atbilde.status_code == 422
    assert atbilde.json()["error"]["details"] == [{"field": "datums", "issue": "FUTURE_DATE"}]


def test_sodienas_datums_ir_atlauts(klients, monkeypatch):  # AC4 robeža, šodiena pēc Rīgas laika
    monkeypatch.setattr(laiks, "sodien", lambda: date(2026, 10, 14))
    pieslegt(klients, "anna@example.com")
    assert pievienot(klients, org(klients), datums=date(2026, 10, 14))["datums"] == "2026-10-14"


def test_cits_darbinieks_tiek_ignorets(jauns_klients):  # AC5
    anna = jauns_klients()
    a = pieslegt(anna, "anna@example.com")
    juris = pieslegt(jauns_klients(), "juris@example.com")
    atbilde = anna.post(
        "/mijiedarbibas",
        json={"datums": "2026-01-01", "veids": "zvans", "organizacija_id": org(anna), "darbinieks_id": juris["id"]},
    )
    assert atbilde.json()["darbinieks_id"] == a["id"]


def test_kartite_jaunakas_vispirms(jauns_klients):  # AC6
    anna, juris = jauns_klients(), jauns_klients()
    pieslegt(anna, "anna@example.com")
    pieslegt(juris, "juris@example.com")
    o = org(anna)
    sodien = laiks.sodien()
    pievienot(anna, o, sodien - timedelta(days=5), kopsavilkums="vecā")
    pievienot(juris, o, sodien, kopsavilkums="jaunā")  # cits darbinieks drīkst pievienot
    pievienot(anna, o, sodien - timedelta(days=2), kopsavilkums="vidējā")
    saraksts = anna.get(f"/organizacijas/{o}/mijiedarbibas").json()
    assert [m["kopsavilkums"] for m in saraksts] == ["jaunā", "vidējā", "vecā"]
    lapa = anna.get(f"/organizacijas/{o}", headers=HTML).text
    assert lapa.index("jaunā") < lapa.index("vidējā") < lapa.index("vecā")
    assert anna.get("/organizacijas/999/mijiedarbibas").status_code == 404


def test_darbinieks_redz_savas_vaditajs_visas(jauns_klients):  # AC7
    anna, juris, vaditajs = jauns_klients(), jauns_klients(), jauns_klients()
    pieslegt(anna, "anna@example.com")
    pieslegt(juris, "juris@example.com")
    pieslegt_vaditaju(vaditajs)
    o = org(anna)
    pievienot(anna, o, kopsavilkums="annas")
    pievienot(juris, o, kopsavilkums="jura")
    assert [m["kopsavilkums"] for m in anna.get("/mijiedarbibas").json()] == ["annas"]
    assert {m["kopsavilkums"] for m in vaditajs.get("/mijiedarbibas").json()} == {"annas", "jura"}
    assert "jura" not in anna.get("/mijiedarbibas", headers=HTML).text


def test_filtrs_sonedel_pirmdiena_lidz_svetdienai(klients, monkeypatch):  # AC8
    monkeypatch.setattr(laiks, "sodien", lambda: date(2026, 10, 14))  # trešdiena
    pieslegt(klients, "anna@example.com")
    o = org(klients)
    for datums in ["2026-10-11", "2026-10-12", "2026-10-14"]:  # svētdiena, pirmdiena, trešdiena
        pievienot(klients, o, date.fromisoformat(datums), kopsavilkums=datums)
    rezultats = klients.get("/mijiedarbibas", params={"periods": "sonedel"}).json()
    assert [m["kopsavilkums"] for m in rezultats] == ["2026-10-14", "2026-10-12"]
    assert klients.get("/mijiedarbibas", params={"periods": "gads"}).status_code == 422


def test_kopsavilkums_lidz_2000(klients):
    pieslegt(klients, "anna@example.com")
    o = org(klients)
    assert pievienot(klients, o, kopsavilkums="a" * 2000)
    atbilde = klients.post("/mijiedarbibas", json={"datums": "2026-01-01", "veids": "zvans", "organizacija_id": o, "kopsavilkums": "a" * 2001})
    assert atbilde.status_code == 422


def test_sakumdati_30_mijiedarbibas(lietotne, klients, monkeypatch):  # AC9
    monkeypatch.setenv("CRM_SAKUMDATU_PAROLE", "sākumdatu-parole")
    sakumdati.main()
    klients.post("/auth/login", json={"epasts": "vaditajs@example.com", "parole": "sākumdatu-parole"})
    visas = klients.get("/mijiedarbibas").json()
    assert len(visas) == 30
    nedela_atpakal = laiks.sodien() - timedelta(days=6)
    assert any(date.fromisoformat(m["datums"]) >= nedela_atpakal for m in visas)


def test_html_forma(klients):
    pieslegt(klients, "anna@example.com")
    o = org(klients)
    forma = klients.get(f"/mijiedarbibas/jauna?organizacija_id={o}", headers=HTML)
    assert forma.status_code == 200 and f'<option value="{o}" selected>' in forma.text
    atbilde = klients.post(
        "/mijiedarbibas",
        data={"organizacija_id": o, "veids": "e-pasts", "datums": laiks.sodien().isoformat()},
        follow_redirects=False,
    )
    assert atbilde.status_code == 303 and atbilde.headers["location"] == f"/organizacijas/{o}"
    kluda = klients.post("/mijiedarbibas", data={"organizacija_id": o, "datums": "2999-01-01"})
    assert kluda.status_code == 422
    assert "Datums nedrīkst būt nākotnē." in kluda.text and "Lauks ir obligāts." in kluda.text
