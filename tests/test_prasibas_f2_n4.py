"""F2, F5 (atgādinājumi), F6, F7, F8, MI-1, MI-2, N1, N2, N4."""

import re
import time
from datetime import date, timedelta

import pytest

from crm import laiks, mi, sakumdati
from tests.conftest import HTML, pieslegt, pieslegt_vaditaju

SODIEN = date(2026, 10, 14)


@pytest.fixture(autouse=True)
def fiksets_datums(monkeypatch):
    monkeypatch.setattr(laiks, "sodien", lambda: SODIEN)


def organizacija(klients, nosaukums="SIA Ezermalas Koks") -> dict:
    atbilde = klients.post("/organizacijas", json={"nosaukums": nosaukums})
    assert atbilde.status_code == 201, atbilde.text
    return atbilde.json()


def kontakts(klients, org_id, **dati) -> dict:
    atbilde = klients.post(f"/organizacijas/{org_id}/kontakti", json={"vards": "Anna Ozola"} | dati)
    assert atbilde.status_code == 201, atbilde.text
    return atbilde.json()


@pytest.fixture
def divi(jauns_klients):
    anna, juris = jauns_klients(), jauns_klients()
    return {"anna": anna, "a": pieslegt(anna, "anna@example.com", "Anna"),
            "juris": juris, "j": pieslegt(juris, "juris@example.com", "Juris")}


def _strukturas_parbaude(lapa: str) -> None:
    """N1: orientieri, viens h1, tabulām paraksti, virsrakstu šūnām scope, laukiem etiķetes."""
    assert '<html lang="lv">' in lapa
    for orientieris in ("<header", "<main", "<footer"):
        assert orientieris in lapa
    assert lapa.count("<h1>") == 1
    assert lapa.count("<table") == lapa.count("<caption>")
    assert not re.search(r"<th(?=[ >])(?![^>]*scope=)[^>]*>", lapa)
    for id_ in re.findall(r'<(?:input|textarea|select) id="([^"]+)"', lapa):
        assert f'for="{id_}"' in lapa


# --- F2: kontaktpersonas ---

def test_f2_pievieno_labo_dzes(klients):
    pieslegt(klients, "anna@example.com")
    org = organizacija(klients)
    k = kontakts(klients, org["id"], amats="Valdes loceklis", epasts="Anna@Example.com", talrunis="+371 20000000")
    assert k["epasts"] == "anna@example.com"
    labots = klients.put(f"/kontakti/{k['id']}", json={"vards": "Anna Ozola-Liepa"}).json()
    assert labots["vards"] == "Anna Ozola-Liepa" and labots["epasts"] is None
    lapa = klients.get(f"/organizacijas/{org['id']}", headers=HTML).text
    assert "Anna Ozola-Liepa" in lapa and "Kontaktpersonas" in lapa
    assert klients.delete(f"/kontakti/{k['id']}").status_code == 204
    assert klients.get(f"/organizacijas/{org['id']}/kontakti").json() == []
    assert klients.delete(f"/kontakti/{k['id']}").status_code == 404


@pytest.mark.parametrize("dati", [{}, {"vards": " "}, {"vards": "X", "epasts": "nav-epasts"}, {"vards": "X", "talrunis": "abc"}])
def test_f2_validacija(klients, dati):
    pieslegt(klients, "anna@example.com")
    org = organizacija(klients)
    assert klients.post(f"/organizacijas/{org['id']}/kontakti", json=dati).status_code == 422


def test_f2_forma_prg_un_kludas(klients):
    pieslegt(klients, "anna@example.com")
    org = organizacija(klients)
    atbilde = klients.post(f"/organizacijas/{org['id']}/kontakti", data={"vards": ""}, headers=HTML)
    assert atbilde.status_code == 422 and 'role="alert"' in atbilde.text
    atbilde = klients.post(f"/organizacijas/{org['id']}/kontakti", data={"vards": "Jānis"}, follow_redirects=False)
    assert atbilde.status_code == 303 and atbilde.headers["location"] == f"/organizacijas/{org['id']}"
    _strukturas_parbaude(klients.get(f"/organizacijas/{org['id']}/kontakti/jauns", headers=HTML).text)


def test_f2_svesas_organizacijas_kontaktus_mainit_nevar(divi, jauns_klients):
    org = organizacija(divi["anna"])
    k = kontakts(divi["anna"], org["id"])
    assert divi["juris"].post(f"/organizacijas/{org['id']}/kontakti", json={"vards": "X"}).status_code == 403
    assert divi["juris"].put(f"/kontakti/{k['id']}", json={"vards": "X"}).status_code == 403
    assert divi["juris"].delete(f"/kontakti/{k['id']}").status_code == 403
    assert "Pievienot kontaktpersonu" not in divi["juris"].get(f"/organizacijas/{org['id']}", headers=HTML).text
    vaditajs = jauns_klients()
    pieslegt_vaditaju(vaditajs)
    assert vaditajs.delete(f"/kontakti/{k['id']}").status_code == 204


def test_f2_neeksistejosa_organizacija_404(klients):
    pieslegt(klients, "anna@example.com")
    assert klients.post("/organizacijas/999/kontakti", json={"vards": "X"}).status_code == 404
    assert klients.get("/organizacijas/999/kontakti").status_code == 404


# --- F5: atgādinājumi ---

def test_f5_atgadinajums_paneli(klients):
    pieslegt(klients, "anna@example.com")
    termins = (SODIEN + timedelta(days=5)).isoformat()
    klients.post("/uzdevumi", json={"nosaukums": "Atgādini-šodien", "termins": termins, "atgadinat": SODIEN.isoformat()})
    klients.post("/uzdevumi", json={"nosaukums": "Atgādini-rīt", "termins": termins,
                                    "atgadinat": (SODIEN + timedelta(days=1)).isoformat()})
    dati = klients.get("/api/panelis").json()
    assert [u["nosaukums"] for u in dati["atgadinajumi"]] == ["Atgādini-šodien"]
    assert dati["atgadinajumi"][0]["atgadinajums_aktivs"] is True
    lapa = klients.get("/panelis", headers=HTML).text
    assert "Atgādini-šodien" in lapa and "Atgādini-rīt" not in lapa
    klients.post(f"/uzdevumi/{dati['atgadinajumi'][0]['id']}/izpildits")
    assert klients.get("/api/panelis").json()["atgadinajumi"] == []


def test_f5_atgadinajums_pec_termina_422(klients):
    pieslegt(klients, "anna@example.com")
    atbilde = klients.post("/uzdevumi", json={"nosaukums": "X", "termins": "2026-10-14", "atgadinat": "2026-10-15"})
    assert atbilde.status_code == 422
    assert atbilde.json()["error"]["details"][0]["field"] == "atgadinat"


def test_f5_cita_atgadinajumi_neredz(divi):
    divi["anna"].post("/uzdevumi", json={"nosaukums": "Annas", "termins": "2026-10-20", "atgadinat": "2026-10-14"})
    assert divi["juris"].get("/api/panelis").json()["atgadinajumi"] == []


# --- F6: meklēšana ---

def test_f6_mekle_visos_ierakstos_bez_garumzimem(divi):
    anna = divi["anna"]
    org = organizacija(anna, "SIA Ziemeļu Būve")
    kontakts(anna, org["id"], vards="Pēteris Zariņš")
    anna.post("/mijiedarbibas", json={"datums": "2026-10-13", "veids": "zvans", "organizacija_id": org["id"],
                                      "kopsavilkums": "Runājām par ziemeļu projektu"})
    anna.post("/pieprasijumi", json={"organizacija_id": org["id"], "apraksts": "Ziemeļu ceļš", "termins": "2026-10-20"})
    anna.post("/uzdevumi", json={"nosaukums": "Zvanīt Zariņam", "termins": "2026-10-20"})
    r = anna.get("/meklet", params={"q": "ziemelu"}).json()
    assert len(r["organizacijas"]) == 1 and len(r["mijiedarbibas"]) == 1 and len(r["pieprasijumi"]) == 1
    assert [k["vards"] for k in anna.get("/meklet", params={"q": "ZARINS"}).json()["kontaktpersonas"]] == ["Pēteris Zariņš"]
    assert len(anna.get("/meklet", params={"q": "zarin"}).json()["uzdevumi"]) == 1
    # N3: Juris redz organizāciju un kontaktu, bet ne Annas mijiedarbības, pieprasījumus un uzdevumus
    rj = divi["juris"].get("/meklet", params={"q": "ziemelu"}).json()
    assert len(rj["organizacijas"]) == 1 and rj["mijiedarbibas"] == [] and rj["pieprasijumi"] == []


def test_f6_iss_vaicajums_un_html(klients):
    pieslegt(klients, "anna@example.com")
    organizacija(klients)
    r = klients.get("/meklet", params={"q": "e"}).json()
    assert r["organizacijas"] == []
    lapa = klients.get("/meklet?q=e", headers=HTML).text
    assert "Ievadiet vismaz 2 rakstzīmes" in lapa
    lapa = klients.get("/meklet?q=koks", headers=HTML).text
    assert "SIA Ezermalas Koks" in lapa and 'role="search"' in lapa
    _strukturas_parbaude(lapa)


def test_f6_bez_pieslegsanas_401(klients):
    assert klients.get("/meklet?q=ab").status_code == 401


# --- F7: pārskats vadītājam ---

def test_f7_parskats_vaditajam(divi, jauns_klients):
    org = organizacija(divi["anna"])
    divi["anna"].post("/mijiedarbibas", json={"datums": "2026-10-10", "veids": "tikšanās", "organizacija_id": org["id"]})
    divi["anna"].post("/mijiedarbibas", json={"datums": "2026-08-01", "veids": "zvans", "organizacija_id": org["id"]})
    divi["anna"].post("/pieprasijumi", json={"organizacija_id": org["id"], "apraksts": "X", "termins": "2026-10-01"})
    divi["anna"].post("/uzdevumi", json={"nosaukums": "Y", "termins": "2026-10-01"})
    vaditajs = jauns_klients()
    pieslegt_vaditaju(vaditajs)
    p = vaditajs.get("/parskats?dienas=30").json()
    anna = next(d for d in p["darbinieki"] if d["vards"] == "Anna")
    assert (anna["tiksanas"], anna["zvani"], anna["mijiedarbibas"]) == (1, 0, 1)
    assert (anna["kaveti_pieprasijumi"], anna["kaveti_uzdevumi"]) == (1, 1)
    assert p["kopa"]["mijiedarbibas"] == 1
    assert vaditajs.get("/parskats?dienas=90").json()["kopa"]["mijiedarbibas"] == 2
    lapa = vaditajs.get("/parskats", headers=HTML).text
    assert "Pārskats vadītājam" in lapa and "Kavēts" in lapa
    _strukturas_parbaude(lapa)


def test_f7_darbiniekam_403_un_nederigs_periods(divi, jauns_klients):
    assert divi["anna"].get("/parskats").status_code == 403
    vaditajs = jauns_klients()
    pieslegt_vaditaju(vaditajs)
    assert vaditajs.get("/parskats?dienas=0").status_code == 422


# --- F8: piekļūstamības paziņojums ---

def test_f8_pazinojums_publisks_un_saite_kaje(klients):
    lapa = klients.get("/pieejamiba", headers=HTML)
    assert lapa.status_code == 200
    assert "Piekļūstamības paziņojums" in lapa.text and "daļēji atbilst" in lapa.text and "mailto:" in lapa.text
    _strukturas_parbaude(lapa.text)
    assert 'href="/pieejamiba"' in klients.get("/auth/login", headers=HTML).text


# --- MI-1: kopsavilkums un nākamais solis ---

@pytest.fixture
def mijiedarbiba(divi):
    org = organizacija(divi["anna"])
    m = divi["anna"].post("/mijiedarbibas", json={"datums": "2026-10-13", "veids": "zvans", "organizacija_id": org["id"],
                                                  "kopsavilkums": "Gaida piedāvājumu līdz piektdienai."}).json()
    return m


def test_mi1_generacija_prasa_apstiprinajumu(divi, mijiedarbiba, monkeypatch):
    nosutits = {}

    def viltots(veids, teksts):
        nosutits.update(veids=veids, teksts=teksts)
        return mi.MiIeteikums(kopsavilkums="Klients gaida piedāvājumu.", nakamais_solis="Nosūtīt piedāvājumu ceturtdien.")

    monkeypatch.setattr(mi, "generet", viltots)
    anna = divi["anna"]
    lapa = anna.post(f"/mijiedarbibas/{mijiedarbiba['id']}/mi/generet", headers=HTML).text
    assert "Ģenerēts ar MI" in lapa and "Nosūtīt piedāvājumu ceturtdien." in lapa
    assert nosutits == {"veids": "zvans", "teksts": "Gaida piedāvājumu līdz piektdienai."}  # N2: bez organizācijas
    kartite = f"/organizacijas/{mijiedarbiba['organizacija_id']}"
    assert "Nosūtīt piedāvājumu ceturtdien." not in anna.get(kartite, headers=HTML).text  # vēl nav apstiprināts
    atbilde = anna.post(f"/mijiedarbibas/{mijiedarbiba['id']}/mi/apstiprinat",
                        data={"kopsavilkums": "Klients gaida piedāvājumu.", "nakamais_solis": "Labots solis."},
                        follow_redirects=False)
    assert atbilde.status_code == 303
    lapa = anna.get(kartite, headers=HTML).text
    assert "Labots solis." in lapa and "Ģenerēts ar MI" in lapa
    assert "Labots solis." not in anna.get("/api/panelis").text  # panelī MI teksta nav


def test_mi1_nav_konfigurets_503(divi, mijiedarbiba, monkeypatch):
    def kluda(*_):
        raise mi.MiNavPieejams("nav konfigurēts")

    monkeypatch.setattr(mi, "generet", kluda)
    atbilde = divi["anna"].post(f"/mijiedarbibas/{mijiedarbiba['id']}/mi/generet", headers=HTML)
    assert atbilde.status_code == 503 and "MI ieteikums nav pieejams" in atbilde.text


def test_mi1_cits_darbinieks_403(divi, mijiedarbiba):
    assert divi["juris"].post(f"/mijiedarbibas/{mijiedarbiba['id']}/mi/generet").status_code == 403
    assert divi["juris"].get(f"/mijiedarbibas/{mijiedarbiba['id']}/mi").status_code == 403
    assert divi["anna"].get("/mijiedarbibas/999/mi").status_code == 404


def test_mi1_atbildes_parsesana():
    ieteikums = mi._parset("KOPSAVILKUMS: A.\nNĀKAMAIS SOLIS: B.")
    assert (ieteikums.kopsavilkums, ieteikums.nakamais_solis) == ("A.", "B.")
    with pytest.raises(mi.MiNavPieejams):
        mi._parset("brīvs teksts")


# --- MI-2: prioritizācija ---

def test_mi2_punkti_ar_pamatojumu_un_redzamiba(divi, jauns_klients):
    anna = divi["anna"]
    aktiva = organizacija(anna, "Aktīvā")
    organizacija(anna, "Klusā")
    anna.post("/mijiedarbibas", json={"datums": "2026-10-10", "veids": "tikšanās", "organizacija_id": aktiva["id"]})
    anna.post("/pieprasijumi", json={"organizacija_id": aktiva["id"], "apraksts": "X", "termins": "2026-10-20"})
    saraksts = anna.get("/prioritates").json()
    assert [p["nosaukums"] for p in saraksts] == ["Aktīvā", "Klusā"]
    assert saraksts[0]["punkti"] == 2 + 3 + 4 + 5 and len(saraksts[0]["pamatojums"]) == 4
    assert saraksts[1]["punkti"] == 0
    assert divi["juris"].get("/prioritates").json() == []  # N3: tikai savas organizācijas
    vaditajs = jauns_klients()
    pieslegt_vaditaju(vaditajs)
    assert len(vaditajs.get("/prioritates").json()) == 2
    lapa = anna.get("/prioritates", headers=HTML).text
    assert "ieteikums darba secībai, nevis lēmums" in lapa
    _strukturas_parbaude(lapa)


# --- N2: piekļuves žurnāls ---

def test_n2_kartites_skatisana_tiek_zurnaleta(divi, jauns_klients):
    org = organizacija(divi["anna"])
    divi["juris"].get(f"/organizacijas/{org['id']}", headers=HTML)
    divi["anna"].get("/panelis", headers=HTML)  # paneļa atvēršana netiek žurnālēta
    vaditajs = jauns_klients()
    pieslegt_vaditaju(vaditajs)
    ieraksti = vaditajs.get("/piekluves-zurnals").json()
    assert [(z["lietotaja_vards"], z["organizacija_id"]) for z in ieraksti] == [("Juris", org["id"])]
    assert divi["anna"].get("/piekluves-zurnals").status_code == 403
    _strukturas_parbaude(vaditajs.get("/piekluves-zurnals", headers=HTML).text)


def test_n2_panelis_bez_kontaktu_datiem(klients):
    pieslegt(klients, "anna@example.com")
    org = organizacija(klients)
    kontakts(klients, org["id"], epasts="slepens@example.com", talrunis="+371 29999999")
    klients.post("/mijiedarbibas", json={"datums": "2026-10-13", "veids": "zvans", "organizacija_id": org["id"]})
    lapa = klients.get("/panelis", headers=HTML).text
    assert "slepens@example.com" not in lapa and "29999999" not in lapa


# --- N4: ātrums ar sākumdatiem ---

def test_n4_galvenas_lapas_atrakas_par_1_s(lietotne, klients, monkeypatch):
    monkeypatch.setenv("CRM_SAKUMDATU_PAROLE", "droša-parole-123")
    assert sakumdati.main() == 0
    klients.post("/auth/login", json={"epasts": "vaditajs@example.com", "parole": "droša-parole-123"})
    for adrese in ("/panelis", "/organizacijas/1", "/meklet?q=sia", "/parskats", "/prioritates"):
        sakums = time.perf_counter()
        atbilde = klients.get(adrese, headers=HTML)
        assert atbilde.status_code == 200, adrese
        assert time.perf_counter() - sakums < 1.0, adrese
