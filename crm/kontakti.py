"""F2: kontaktpersonas pie organizācijas.

Pievienot, labot un dzēst var organizācijas atbildīgais darbinieks vai vadītājs
(tāpat kā labot organizāciju, F1). Dzēšana ir neatgriezeniska (N2).
"""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import AfterValidator, BaseModel, StringConstraints

from crm import piekluve
from crm.auth import Lietotajs, Pieslegts, _epasts
from crm.db import savienojums
from crm.ievade import nolasit
from crm.kludas import Validacija
from crm.organizacijas import KARTITES_PAPILDINAJUMI, Organizacija, atrast_organizaciju, var_labot
from crm.sabloni import veidne

router = APIRouter()

Vards = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Amats = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Epasts = Annotated[str, StringConstraints(max_length=254), AfterValidator(_epasts)]
Talrunis = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30, pattern=r"^\+?[0-9 ()-]+$")]


class KontaktpersonaIevade(BaseModel):
    vards: Vards
    amats: Amats | None = None
    epasts: Epasts | None = None
    talrunis: Talrunis | None = None


class Kontaktpersona(BaseModel):
    id: int
    organizacija_id: int
    vards: str
    amats: str | None
    epasts: str | None
    talrunis: str | None


def _no_rindas(rinda: sqlite3.Row) -> Kontaktpersona:
    return Kontaktpersona(**{k: rinda[k] for k in Kontaktpersona.model_fields})


def atlasit(organizacija_id: int) -> list[Kontaktpersona]:
    with savienojums() as conn:
        rindas = conn.execute(
            "SELECT * FROM kontaktpersonas WHERE organizacija_id = ? ORDER BY vards, id", (organizacija_id,)
        ).fetchall()
    return [_no_rindas(r) for r in rindas]


def visas() -> list[Kontaktpersona]:
    with savienojums() as conn:
        return [_no_rindas(r) for r in conn.execute("SELECT * FROM kontaktpersonas ORDER BY vards, id").fetchall()]


def kontakts_pec_id(kontakta_id: int) -> Kontaktpersona | None:
    with savienojums() as conn:
        rinda = conn.execute("SELECT * FROM kontaktpersonas WHERE id = ?", (kontakta_id,)).fetchone()
    return _no_rindas(rinda) if rinda else None


def _atrast(kontakta_id: int) -> Kontaktpersona:
    kontakts = kontakts_pec_id(kontakta_id)
    if kontakts is None:
        raise HTTPException(404, "Kontaktpersona nav atrasta")
    return kontakts


def _parbaudit_tiesibas(lietotajs: Lietotajs, organizacija: Organizacija) -> None:
    if not var_labot(lietotajs, organizacija):
        raise HTTPException(403, "Kontaktpersonas maina tikai atbildīgais darbinieks vai vadītājs")


def _forma(request: Request, organizacija: Organizacija, kontakts: Kontaktpersona | None = None) -> Response:
    konteksts = {"organizacija": organizacija, "kontakts": kontakts, "ievade": kontakts.model_dump() if kontakts else {}}
    return veidne(request, "kontakti/forma.html", konteksts)


@router.get("/organizacijas/{organizacijas_id}/kontakti")
def saraksts(organizacijas_id: int, lietotajs: Pieslegts) -> Response:
    atrast_organizaciju(organizacijas_id)
    piekluve.ierakstit(lietotajs.id, organizacijas_id)
    return JSONResponse([k.model_dump() for k in atlasit(organizacijas_id)])


@router.get("/organizacijas/{organizacijas_id}/kontakti/jauns", include_in_schema=False)
def jauna_forma(request: Request, organizacijas_id: int, lietotajs: Pieslegts) -> Response:
    organizacija = atrast_organizaciju(organizacijas_id)
    _parbaudit_tiesibas(lietotajs, organizacija)
    return _forma(request, organizacija)


@router.post("/organizacijas/{organizacijas_id}/kontakti", status_code=201)
async def pievienot(request: Request, organizacijas_id: int, lietotajs: Pieslegts) -> Response:
    organizacija = atrast_organizaciju(organizacijas_id)
    _parbaudit_tiesibas(lietotajs, organizacija)
    try:
        dati, forma = await nolasit(request, KontaktpersonaIevade)
    except Validacija as exc:
        if exc.forma:
            konteksts = {"organizacija": organizacija, "kontakts": None, "kludas": exc.lauku_kludas(), "ievade": exc.ievade}
            return veidne(request, "kontakti/forma.html", konteksts, 422)
        raise
    with savienojums() as conn:
        jauns_id = conn.execute(
            "INSERT INTO kontaktpersonas (organizacija_id, vards, amats, epasts, talrunis) VALUES (?, ?, ?, ?, ?)",
            (organizacija.id, dati.vards, dati.amats, dati.epasts, dati.talrunis),
        ).lastrowid
    if forma:
        return RedirectResponse(f"/organizacijas/{organizacija.id}", status_code=303)
    return JSONResponse(kontakts_pec_id(jauns_id).model_dump(), status_code=201)


def _saglabat(kontakts: Kontaktpersona, dati: KontaktpersonaIevade) -> Kontaktpersona:
    with savienojums() as conn:
        conn.execute(
            "UPDATE kontaktpersonas SET vards = ?, amats = ?, epasts = ?, talrunis = ? WHERE id = ?",
            (dati.vards, dati.amats, dati.epasts, dati.talrunis, kontakts.id),
        )
    return kontakts_pec_id(kontakts.id)


@router.put("/kontakti/{kontakta_id}")
async def labot(request: Request, kontakta_id: int, lietotajs: Pieslegts) -> Response:
    """Aizstāj visus laukus; nenorādītie neobligātie lauki tiek notīrīti."""
    kontakts = _atrast(kontakta_id)
    _parbaudit_tiesibas(lietotajs, atrast_organizaciju(kontakts.organizacija_id))
    dati, _ = await nolasit(request, KontaktpersonaIevade)
    return JSONResponse(_saglabat(kontakts, dati).model_dump())


@router.get("/kontakti/{kontakta_id}/labot", include_in_schema=False)
def labosanas_forma(request: Request, kontakta_id: int, lietotajs: Pieslegts) -> Response:
    kontakts = _atrast(kontakta_id)
    organizacija = atrast_organizaciju(kontakts.organizacija_id)
    _parbaudit_tiesibas(lietotajs, organizacija)
    return _forma(request, organizacija, kontakts)


@router.post("/kontakti/{kontakta_id}/labot", include_in_schema=False)
async def labot_forma(request: Request, kontakta_id: int, lietotajs: Pieslegts) -> Response:
    kontakts = _atrast(kontakta_id)
    organizacija = atrast_organizaciju(kontakts.organizacija_id)
    _parbaudit_tiesibas(lietotajs, organizacija)
    try:
        dati, _ = await nolasit(request, KontaktpersonaIevade)
    except Validacija as exc:
        konteksts = {"organizacija": organizacija, "kontakts": kontakts, "kludas": exc.lauku_kludas(), "ievade": exc.ievade}
        return veidne(request, "kontakti/forma.html", konteksts, 422)
    _saglabat(kontakts, dati)
    return RedirectResponse(f"/organizacijas/{organizacija.id}", status_code=303)


def _dzest(kontakts: Kontaktpersona, lietotajs: Lietotajs) -> None:
    _parbaudit_tiesibas(lietotajs, atrast_organizaciju(kontakts.organizacija_id))
    with savienojums() as conn:
        conn.execute("DELETE FROM kontaktpersonas WHERE id = ?", (kontakts.id,))


@router.delete("/kontakti/{kontakta_id}", status_code=204)
def dzest(kontakta_id: int, lietotajs: Pieslegts) -> Response:
    _dzest(_atrast(kontakta_id), lietotajs)
    return Response(status_code=204)


@router.post("/kontakti/{kontakta_id}/dzest", include_in_schema=False)
def dzest_forma(kontakta_id: int, lietotajs: Pieslegts) -> Response:
    kontakts = _atrast(kontakta_id)
    _dzest(kontakts, lietotajs)
    return RedirectResponse(f"/organizacijas/{kontakts.organizacija_id}?pazinojums=kontakts-dzests", status_code=303)


def _kartites_bloks(organizacija: Organizacija, lietotajs: Lietotajs) -> dict:
    return {
        "bloks": "kontakti/kartites_bloks.html",
        "kontakti": atlasit(organizacija.id),
        "var_labot_kontaktus": var_labot(lietotajs, organizacija),
    }


# Kontaktpersonas kartītē rāda pirms mijiedarbībām un pieprasījumiem.
KARTITES_PAPILDINAJUMI.insert(0, _kartites_bloks)
