"""CR-10: kopsavilkuma ekrāns — vadības panelis (F9)."""

import re
import time
from datetime import date, timedelta

import pytest

from crm import laiks, sakumdati
from tests.conftest import HTML, PAROLE, iestatit_lomu, pieslegt, pieslegt_vaditaju

SODIEN = date(2026, 10, 14)  # trešdiena


@pytest.fixture(autouse=True)
def fiksets_datums(monkeypatch):
    monkeypatch.setattr(laiks, "sodien", lambda: SODIEN)


def diena(n: int) -> str:
    return (SODIEN + timedelta(days=n)).isoformat()


def aizpildit(klients, vards: str) -> dict:
    """Viena darbinieka dati visos blokos; teksti satur vārdu, lai pārbaudītu filtrēšanu."""
    org = klients.post("/organizacijas", json={"nosaukums": f"SIA {vards}"}).json()["id"]
    uzdevums = klients.post("/uzdevumi", json={"nosaukums": f"uzdevums-{vards}", "termins": diena(0)}).json()
    klients.post("/pieprasijumi", json={"organizacija_id": org, "apraksts": f"kavēts-{vards}", "termins": diena(-1)})
    darba = klients.post("/pieprasijumi", json={"organizacija_id": org, "apraksts": f"tuvais-{vards}", "termins": diena(3)}).json()
    klients.patch(f"/pieprasijumi/{darba['id']}", json={"statuss": "Darbā"})
    klients.post("/pieprasijumi", json={"organizacija_id": org, "apraksts": f"tālais-{vards}", "termins": diena(4)})
    klients.post(
        "/mijiedarbibas",
        json={"datums": diena(0), "veids": "zvans", "organizacija_id": org, "kopsavilkums": f"slepens-kopsavilkums-{vards}"},
    )
    return {"org": org, "uzdevums": uzdevums}


@pytest.fixture
def divi_darbinieki(jauns_klients):
    anna, juris = jauns_klients(), jauns_klients()
    a = pieslegt(anna, "anna@example.com", "Anna")
    j = pieslegt(juris, "juris@example.com", "Juris")
    return {"anna": anna, "juris": juris, "a": a, "j": j, "annas": aizpildit(anna, "Anna"), "jura": aizpildit(juris, "Juris")}


def test_pieslegsanas_novirza_uz_paneli(klients):  # AC1
    klients.post("/auth/register", json={"vards": "Anna", "epasts": "anna@example.com", "parole": PAROLE})
    atbilde = klients.post("/auth/login", data={"epasts": "anna@example.com", "parole": PAROLE}, follow_redirects=False)
    assert atbilde.headers["location"] == "/panelis"


def test_nepieslegts_novirza(klients):  # AC2
    atbilde = klients.get("/panelis", headers=HTML, follow_redirects=False)
    assert (atbilde.status_code, atbilde.headers["location"]) == (303, "/auth/login")
    assert klients.get("/api/panelis").status_code == 401


def test_darbinieks_redz_tikai_savus_datus(divi_darbinieki):  # AC3
    anna = divi_darbinieki["anna"]
    lapa = anna.get("/panelis", headers=HTML).text
    assert "uzdevums-Anna" in lapa and "kavēts-Anna" in lapa and "SIA Anna" in lapa
    assert "Juris" not in lapa
    dati = anna.get("/api/panelis").json()
    assert dati["raditaji"] == {"uzdevumi_sodien": 1, "kaveti_pieprasijumi": 1, "pieprasijumi_darba": 1, "mijiedarbibas_sonedel": 1}
    assert dati["aktivitate"] is None


@pytest.mark.parametrize("parametri", ["?lietotajs_id={j}", "?atbildigais_id={j}", "?darbinieks_id={j}&loma=vaditajs"])
def test_parametri_neietekme_filtru(divi_darbinieki, parametri):  # AC4
    anna, j = divi_darbinieki["anna"], divi_darbinieki["j"]["id"]
    adrese = parametri.format(j=j)
    assert "Juris" not in anna.get("/panelis" + adrese, headers=HTML).text
    assert "Juris" not in anna.get("/api/panelis" + adrese).text


def test_vaditajs_redz_visus_un_aktivitati(divi_darbinieki, jauns_klients):  # AC5
    vaditajs = jauns_klients()
    pieslegt_vaditaju(vaditajs)
    lapa = vaditajs.get("/panelis", headers=HTML).text
    assert "kavēts-Anna" in lapa and "kavēts-Juris" in lapa
    assert "Atbildīgais</th>" in lapa and "Darbinieks</th>" in lapa
    assert "Aktivitāte pa darbiniekiem" in lapa
    assert "Atvērt pilnu pārskatu" not in lapa  # F7 vēl nav
    dati = vaditajs.get("/api/panelis").json()
    assert dati["raditaji"]["kaveti_pieprasijumi"] == 2
    aktivitate = {a["vards"]: a for a in dati["aktivitate"]}
    assert aktivitate["Anna"] | {"darbinieks_id": 0} == {
        "darbinieks_id": 0, "vards": "Anna", "mijiedarbibas": 1, "atverti_pieprasijumi": 3, "kaveti_pieprasijumi": 1,
    }
    assert dati["uzdevumi"] == []  # „Mani uzdevumi” — tikai paša


def test_galvene(klients):  # AC6
    pieslegt(klients, "anna@example.com", "Anna Paraugs")
    lapa = klients.get("/panelis", headers=HTML).text
    assert lapa.count("<h1>") == 1 and "<h1>Vadības panelis</h1>" in lapa
    assert "Anna Paraugs · Darbinieks · " in lapa
    assert '<time datetime="2026-10-14">2026. gada 14. oktobris</time>' in lapa


def test_raditaju_kartites(divi_darbinieki):  # AC7
    lapa = divi_darbinieki["anna"].get("/panelis", headers=HTML).text
    for saite, teksts in [
        ("/uzdevumi?lidz_sodienai=true", "1 uzdevums šodien"),
        ("/pieprasijumi?kavets=true", "1 kavētais pieprasījums"),
        ("/pieprasijumi?statuss=Darb%C4%81", "1 pieprasījums statusā „Darbā”"),
        ("/mijiedarbibas?periods=sonedel", "1 mijiedarbība šonedēļ"),
    ]:
        assert f'<a href="{saite}">{teksts}</a>' in lapa
        assert divi_darbinieki["anna"].get(saite, headers=HTML).status_code == 200


def test_atzime_uzdevumu_no_paneļa(divi_darbinieki):  # AC8
    anna = divi_darbinieki["anna"]
    uzdevums = divi_darbinieki["annas"]["uzdevums"]
    forma = anna.get("/panelis", headers=HTML).text
    assert f'action="/uzdevumi/{uzdevums["id"]}/izpildits"' in forma and 'name="atpakal" value="/panelis"' in forma
    atbilde = anna.post(f"/uzdevumi/{uzdevums['id']}/izpildits", data={"atpakal": "/panelis"}, follow_redirects=False)
    assert atbilde.status_code == 303 and atbilde.headers["location"] == "/panelis?pazinojums=uzdevums-izpildits"
    lapa = anna.get(atbilde.headers["location"], headers=HTML).text
    assert '<div class="zina" role="status">Uzdevums atzīmēts kā izpildīts.</div>' in lapa
    assert "uzdevums-Anna" not in lapa
    assert "Šodien uzdevumu nav." in lapa


def test_sveša_uzdevuma_atzimesana_403(divi_darbinieki):  # AC9
    jura_uzdevums = divi_darbinieki["jura"]["uzdevums"]
    atbilde = divi_darbinieki["anna"].post(f"/uzdevumi/{jura_uzdevums['id']}/izpildits", data={"atpakal": "/panelis"})
    assert atbilde.status_code == 403


def test_atbildets_vakar_nav_kavets(klients):  # AC10
    pieslegt(klients, "anna@example.com")
    org = klients.post("/organizacijas", json={"nosaukums": "SIA X"}).json()["id"]
    p = klients.post("/pieprasijumi", json={"organizacija_id": org, "apraksts": "atbildēts-vakar", "termins": diena(-1)}).json()
    klients.patch(f"/pieprasijumi/{p['id']}", json={"statuss": "Atbildēts"})
    dati = klients.get("/api/panelis").json()
    assert dati["raditaji"]["kaveti_pieprasijumi"] == 0
    assert dati["pieprasijumi"] == []
    assert "atbildēts-vakar" not in klients.get("/panelis", headers=HTML).text


def test_tuvakie_pieprasijumi_3_dienas(divi_darbinieki):
    dati = divi_darbinieki["anna"].get("/api/panelis").json()
    assert [p["apraksts"] for p in dati["pieprasijumi"]] == ["kavēts-Anna", "tuvais-Anna"]
    lapa = divi_darbinieki["anna"].get("/panelis", headers=HTML).text
    assert "tālais-Anna" not in lapa and '<span class="atzime kavets">Kavēts</span>' in lapa


def test_pedejas_5_mijiedarbibas_bez_kopsavilkuma(klients):  # AC11
    pieslegt(klients, "anna@example.com")
    org = klients.post("/organizacijas", json={"nosaukums": "SIA X"}).json()["id"]
    for i in range(7):
        klients.post("/mijiedarbibas", json={"datums": diena(-i), "veids": "e-pasts", "organizacija_id": org, "kopsavilkums": f"slepens-{i}"})
    dati = klients.get("/api/panelis").json()
    assert [m["datums"] for m in dati["mijiedarbibas"]] == [diena(-i) for i in range(5)]
    assert all("kopsavilkums" not in m for m in dati["mijiedarbibas"])
    lapa = klients.get("/panelis", headers=HTML).text
    assert "slepens-" not in lapa
    assert f'<a href="/organizacijas/{org}">SIA X</a>' in lapa
    assert "14.10.2026" in lapa and "E-pasts" in lapa


def test_tuksi_bloki_ar_paskaidrojumu(klients):  # AC12
    pieslegt(klients, "anna@example.com")
    lapa = klients.get("/panelis", headers=HTML).text
    assert "Šodien uzdevumu nav." in lapa
    assert "Kavētu vai tuvāko pieprasījumu nav." in lapa
    assert "Mijiedarbību vēl nav." in lapa
    assert "<table" not in lapa
    assert "0 uzdevumi šodien" in lapa


def test_macibu_rezima_lomas_maina(divi_darbinieki, monkeypatch):  # AC13
    monkeypatch.setenv("CRM_MACIBU_REZIMS", "1")
    anna = divi_darbinieki["anna"]
    assert "Aktivitāte pa darbiniekiem" not in anna.get("/panelis", headers=HTML).text
    anna.post("/macibu-rezims/loma", data={"loma": "vaditajs"})
    lapa = anna.get("/panelis", headers=HTML).text
    assert "Aktivitāte pa darbiniekiem" in lapa and "kavēts-Juris" in lapa
    anna.post("/macibu-rezims/loma", data={"loma": "darbinieks"})
    assert "Juris" not in anna.get("/panelis", headers=HTML).text


def test_pieejamibas_struktura(divi_darbinieki, jauns_klients):  # AC14 (strukturālā daļa; axe skatīt PR)
    vaditajs = jauns_klients()
    pieslegt_vaditaju(vaditajs)
    lapa = vaditajs.get("/panelis", headers=HTML).text
    assert '<html lang="lv">' in lapa
    for orientieris in ("<header", "<nav", "<main", "<footer"):
        assert orientieris in lapa
    assert lapa.count("<h1>") == 1
    h2 = re.findall(r"<h2[^>]*>(.*?)</h2>", lapa)
    assert h2 == ["Rādītāji visā sistēmā", "Mani uzdevumi šodien", "Kavētie un tuvākie pieprasījumi",
                  "Pēdējās mijiedarbības", "Ātrās darbības", "Aktivitāte pa darbiniekiem"]
    assert lapa.count("<table") == lapa.count("<caption>")
    assert not re.search(r"<th(?=[ >])(?![^>]*scope=)[^>]*>", lapa)
    for id_ in re.findall(r'<input id="([^"]+)"', lapa):
        assert f'for="{id_}"' in lapa


def test_atras_darbibas(klients):
    pieslegt(klients, "anna@example.com")
    lapa = klients.get("/panelis", headers=HTML).text
    for adrese in ("/organizacijas/jauna", "/mijiedarbibas/jauna", "/pieprasijumi/jauns"):
        assert f'href="{adrese}"' in lapa
        assert klients.get(adrese, headers=HTML).status_code == 200
    assert 'action="/organizacijas" role="search"' in lapa


def test_sakumdati_lapa_atrak_par_1_s(lietotne, klients, monkeypatch):  # AC15
    monkeypatch.setenv("CRM_SAKUMDATU_PAROLE", "sākumdatu-parole")
    sakumdati.main()
    klients.post("/auth/login", json={"epasts": "vaditajs@example.com", "parole": "sākumdatu-parole"})
    klients.get("/panelis", headers=HTML)  # sasildīšana (šablonu kompilācija)
    sakums = time.perf_counter()
    atbilde = klients.get("/panelis", headers=HTML)
    ilgums = time.perf_counter() - sakums
    assert atbilde.status_code == 200
    assert ilgums < 1.0, f"{ilgums:.3f} s"
    assert len(klients.get("/api/panelis").json()["aktivitate"]) == 3
