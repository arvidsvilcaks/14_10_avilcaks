"""CR-8: pieprasījumi no organizācijām (F4)."""

import sqlite3
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, StringConstraints

from crm import laiks
from crm.auth import Lietotajs, Pieslegts, lietotajs_pec_id, visi_lietotaji
from crm.db import savienojums
from crm.ievade import ir_forma, nolasit
from crm.kludas import Validacija, gaida_html
from crm.organizacijas import KARTITES_PAPILDINAJUMI, Organizacija, meklet, organizacija_pec_id
from crm.sabloni import veidne

router = APIRouter()

Statuss = Literal["Jauns", "Darbā", "Atbildēts"]
STATUSI: tuple[str, ...] = ("Jauns", "Darbā", "Atbildēts")
Apraksts = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class PieprasijumsIevade(BaseModel):
    organizacija_id: int
    apraksts: Apraksts
    termins: date
    atbildigais_id: int | None = None


class PieprasijumaLabojums(BaseModel):
    apraksts: Apraksts | None = None
    termins: date | None = None
    statuss: Statuss | None = None
    atbildigais_id: int | None = None


class Pieprasijums(BaseModel):
    id: int
    organizacija_id: int
    organizacijas_nosaukums: str
    apraksts: str
    termins: date
    statuss: Statuss
    atbildigais_id: int
    atbildiga_vards: str
    kavets: bool


def ir_kavets(termins: date, statuss: str) -> bool:
    """F9.7: termiņš pirms šodienas (Europe/Riga) un statuss nav „Atbildēts”."""
    return termins < laiks.sodien() and statuss != "Atbildēts"


_VAICAJUMS = """
    SELECT p.*, o.nosaukums AS organizacijas_nosaukums, l.vards AS atbildiga_vards
    FROM pieprasijumi p
    JOIN organizacijas o ON o.id = p.organizacija_id
    JOIN lietotaji l ON l.id = p.atbildigais_id
"""


def _no_rindas(rinda: sqlite3.Row) -> Pieprasijums:
    termins = date.fromisoformat(rinda["termins"])
    lauki = {k: rinda[k] for k in Pieprasijums.model_fields if k not in ("termins", "kavets")}
    return Pieprasijums(**lauki, termins=termins, kavets=ir_kavets(termins, rinda["statuss"]))


def atlasit(
    atbildigais_id: int | None = None,
    statuss: str | None = None,
    kavets: bool | None = None,
    organizacija_id: int | None = None,
    termins_lidz: date | None = None,
    neatbildeti: bool = False,
) -> list[Pieprasijums]:
    """Pieprasījumi pēc termiņa. `atbildigais_id=None` — visu darbinieku."""
    nosacijumi, parametri = [], []
    sodien = laiks.sodien().isoformat()
    if atbildigais_id is not None:
        nosacijumi.append("p.atbildigais_id = ?")
        parametri.append(atbildigais_id)
    if organizacija_id is not None:
        nosacijumi.append("p.organizacija_id = ?")
        parametri.append(organizacija_id)
    if statuss is not None:
        nosacijumi.append("p.statuss = ?")
        parametri.append(statuss)
    if kavets is True:
        nosacijumi.append("p.termins < ? AND p.statuss != 'Atbildēts'")
        parametri.append(sodien)
    elif kavets is False:
        nosacijumi.append("NOT (p.termins < ? AND p.statuss != 'Atbildēts')")
        parametri.append(sodien)
    if termins_lidz is not None:
        nosacijumi.append("p.termins <= ?")
        parametri.append(termins_lidz.isoformat())
    if neatbildeti:
        nosacijumi.append("p.statuss != 'Atbildēts'")
    vaicajums = _VAICAJUMS + (" WHERE " + " AND ".join(nosacijumi) if nosacijumi else "")
    with savienojums() as conn:
        rindas = conn.execute(vaicajums + " ORDER BY p.termins, p.id", parametri).fetchall()
    return [_no_rindas(r) for r in rindas]


def pieprasijums_pec_id(pieprasijuma_id: int) -> Pieprasijums | None:
    with savienojums() as conn:
        rinda = conn.execute(_VAICAJUMS + " WHERE p.id = ?", (pieprasijuma_id,)).fetchone()
    return _no_rindas(rinda) if rinda else None


def var_mainit(lietotajs: Lietotajs, pieprasijums: Pieprasijums) -> bool:
    return lietotajs.ir_vaditajs or pieprasijums.atbildigais_id == lietotajs.id


def _parbaudit_atbildigo(lietotajs: Lietotajs, atbildigais_id: int) -> None:
    if atbildigais_id != lietotajs.id and not lietotajs.ir_vaditajs:
        raise HTTPException(403, "Atbildīgo darbinieku maina tikai vadītājs")
    if lietotajs_pec_id(atbildigais_id) is None:
        raise Validacija.lauks("atbildigais_id", "NOT_FOUND", "Lietotājs nav atrasts.")


def _formas_konteksts(lietotajs: Lietotajs, **papildus) -> dict:
    return {
        "organizacijas": meklet(),
        "lietotaji": visi_lietotaji() if lietotajs.ir_vaditajs else [],
    } | papildus


def _saraksta_virsraksts(statuss: str | None, kavets: bool | None) -> str:
    if kavets:
        return "Kavētie pieprasījumi"
    if statuss:
        return f"Pieprasījumi statusā „{statuss}”"
    return "Pieprasījumi"


@router.get("/pieprasijumi")
def saraksts(
    request: Request, lietotajs: Pieslegts, statuss: Statuss | None = None, kavets: bool | None = None
) -> Response:
    pieprasijumi = atlasit(None if lietotajs.ir_vaditajs else lietotajs.id, statuss, kavets)
    if gaida_html(request):
        konteksts = {
            "pieprasijumi": pieprasijumi,
            "virsraksts": _saraksta_virsraksts(statuss, kavets),
            "statusi": STATUSI,
            "filtrets": statuss is not None or kavets is not None,
        }
        return veidne(request, "pieprasijumi/saraksts.html", konteksts)
    return JSONResponse([p.model_dump(mode="json") for p in pieprasijumi])


@router.get("/pieprasijumi/jauns", include_in_schema=False)
def jauna_forma(request: Request, lietotajs: Pieslegts, organizacija_id: int | None = None) -> Response:
    ievade = {"organizacija_id": organizacija_id, "atbildigais_id": lietotajs.id}
    return veidne(request, "pieprasijumi/forma.html", _formas_konteksts(lietotajs, ievade=ievade))


@router.post("/pieprasijumi", status_code=201)
async def izveidot(request: Request, lietotajs: Pieslegts) -> Response:
    forma = ir_forma(request)
    try:
        dati, _ = await nolasit(request, PieprasijumsIevade)
        atbildigais_id = dati.atbildigais_id if dati.atbildigais_id is not None else lietotajs.id
        _parbaudit_atbildigo(lietotajs, atbildigais_id)
        if organizacija_pec_id(dati.organizacija_id) is None:
            raise Validacija.lauks("organizacija_id", "NOT_FOUND", "Organizācija nav atrasta.")
    except Validacija as exc:
        if forma:
            ievade = dict(await request.form())
            konteksts = _formas_konteksts(lietotajs, kludas=exc.lauku_kludas(), ievade=ievade)
            return veidne(request, "pieprasijumi/forma.html", konteksts, 422)
        raise
    with savienojums() as conn:
        jauns_id = conn.execute(
            "INSERT INTO pieprasijumi (organizacija_id, apraksts, termins, atbildigais_id) VALUES (?, ?, ?, ?)",
            (dati.organizacija_id, dati.apraksts, dati.termins.isoformat(), atbildigais_id),
        ).lastrowid
    if forma:
        return RedirectResponse("/pieprasijumi", status_code=303)
    return JSONResponse(pieprasijums_pec_id(jauns_id).model_dump(mode="json"), status_code=201)


def _saglabat(pieprasijums: Pieprasijums, lietotajs: Lietotajs, dati: PieprasijumaLabojums) -> Pieprasijums:
    if not var_mainit(lietotajs, pieprasijums):
        raise HTTPException(403, "Mainīt var tikai atbildīgais darbinieks vai vadītājs")
    lauki = dati.model_dump(include=dati.model_fields_set)
    for lauks in ("apraksts", "termins", "statuss", "atbildigais_id"):
        if lauks in lauki and lauki[lauks] is None:
            raise Validacija.lauks(lauks, "REQUIRED", "Lauks ir obligāts.")
    if "atbildigais_id" in lauki and lauki["atbildigais_id"] != pieprasijums.atbildigais_id:
        _parbaudit_atbildigo(lietotajs, lauki["atbildigais_id"])
    if "termins" in lauki:
        lauki["termins"] = lauki["termins"].isoformat()
    if lauki:
        izteiksme = ", ".join(f"{k} = ?" for k in lauki)
        with savienojums() as conn:
            conn.execute(f"UPDATE pieprasijumi SET {izteiksme} WHERE id = ?", (*lauki.values(), pieprasijums.id))
    return pieprasijums_pec_id(pieprasijums.id)


def _atrast(pieprasijuma_id: int) -> Pieprasijums:
    pieprasijums = pieprasijums_pec_id(pieprasijuma_id)
    if pieprasijums is None:
        raise HTTPException(404, "Pieprasījums nav atrasts")
    return pieprasijums


@router.patch("/pieprasijumi/{pieprasijuma_id}")
async def labot(request: Request, pieprasijuma_id: int, lietotajs: Pieslegts) -> Response:
    pieprasijums = _atrast(pieprasijuma_id)
    dati, _ = await nolasit(request, PieprasijumaLabojums)
    return JSONResponse(_saglabat(pieprasijums, lietotajs, dati).model_dump(mode="json"))


@router.post("/pieprasijumi/{pieprasijuma_id}/statuss", include_in_schema=False)
async def mainit_statusu_forma(request: Request, pieprasijuma_id: int, lietotajs: Pieslegts) -> Response:
    """HTML forma statusa maiņai sarakstā."""
    pieprasijums = _atrast(pieprasijuma_id)
    dati, _ = await nolasit(request, PieprasijumaLabojums)
    _saglabat(pieprasijums, lietotajs, PieprasijumaLabojums(statuss=dati.statuss))
    atpakal = request.headers.get("referer", "")
    merkis = atpakal if atpakal.startswith(str(request.base_url)) else "/pieprasijumi"
    return RedirectResponse(merkis, status_code=303)


def _kartites_bloks(organizacija: Organizacija, lietotajs: Lietotajs) -> dict:
    return {"bloks": "pieprasijumi/kartites_bloks.html", "pieprasijumi": atlasit(organizacija_id=organizacija.id)}


KARTITES_PAPILDINAJUMI.append(_kartites_bloks)
