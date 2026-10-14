"""CR-9: uzdevumi (F5) un atgādinājumi.

Atgādinājums ir datums, no kura neizpildīts uzdevums parādās paneļa blokā
„Atgādinājumi” un uzdevumu sarakstā ar atzīmi „Atgādinājums”.
"""

import sqlite3
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, StringConstraints, ValidationInfo, field_validator
from pydantic_core import PydanticCustomError

from crm import laiks
from crm.auth import Lietotajs, Pieslegts, lietotajs_pec_id, visi_lietotaji
from crm.db import savienojums
from crm.ievade import ir_forma, nolasit
from crm.kludas import Validacija, gaida_html
from crm.organizacijas import meklet, organizacija_pec_id
from crm.sabloni import veidne

router = APIRouter()

IZPILDITS_PAZINOJUMS = "uzdevums-izpildits"


class UzdevumsIevade(BaseModel):
    nosaukums: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    termins: date
    organizacija_id: int | None = None
    atbildigais_id: int | None = None
    atgadinat: date | None = None

    @field_validator("atgadinat")
    @classmethod
    def _atgadinajums_lidz_terminam(cls, vertiba: date | None, info: ValidationInfo) -> date | None:
        termins = info.data.get("termins")
        if vertiba is not None and termins is not None and vertiba > termins:
            raise PydanticCustomError("REMINDER_AFTER_DUE", "Atgādinājums nevar būt pēc termiņa.")
        return vertiba


class Uzdevums(BaseModel):
    id: int
    nosaukums: str
    termins: date
    izpildits: bool
    atbildigais_id: int
    atbildiga_vards: str
    organizacija_id: int | None
    organizacijas_nosaukums: str | None
    atgadinat: date | None = None
    atgadinajums_aktivs: bool = False


_VAICAJUMS = """
    SELECT u.*, l.vards AS atbildiga_vards, o.nosaukums AS organizacijas_nosaukums
    FROM uzdevumi u
    JOIN lietotaji l ON l.id = u.atbildigais_id
    LEFT JOIN organizacijas o ON o.id = u.organizacija_id
"""


def _no_rindas(rinda: sqlite3.Row) -> Uzdevums:
    lauki = {k: rinda[k] for k in Uzdevums.model_fields if k != "atgadinajums_aktivs"}
    aktivs = not rinda["izpildits"] and rinda["atgadinat"] is not None and rinda["atgadinat"] <= laiks.sodien().isoformat()
    return Uzdevums(**lauki, atgadinajums_aktivs=aktivs)


def atlasit(atbildigais_id: int | None = None, lidz_sodienai: bool = False, atgadinajumi: bool = False) -> list[Uzdevums]:
    """Uzdevumi pēc termiņa. `lidz_sodienai` — neizpildītie ar termiņu šodien vai agrāk;
    `atgadinajumi` — neizpildītie, kuru atgādinājuma datums ir pienācis."""
    nosacijumi, parametri = [], []
    if atgadinajumi:
        nosacijumi.append("u.izpildits = 0 AND u.atgadinat IS NOT NULL AND u.atgadinat <= ?")
        parametri.append(laiks.sodien().isoformat())
    if atbildigais_id is not None:
        nosacijumi.append("u.atbildigais_id = ?")
        parametri.append(atbildigais_id)
    if lidz_sodienai:
        nosacijumi.append("u.izpildits = 0 AND u.termins <= ?")
        parametri.append(laiks.sodien().isoformat())
    vaicajums = _VAICAJUMS + (" WHERE " + " AND ".join(nosacijumi) if nosacijumi else "")
    with savienojums() as conn:
        rindas = conn.execute(vaicajums + " ORDER BY u.izpildits, u.termins, u.id", parametri).fetchall()
    return [_no_rindas(r) for r in rindas]


def uzdevums_pec_id(uzdevuma_id: int) -> Uzdevums | None:
    with savienojums() as conn:
        rinda = conn.execute(_VAICAJUMS + " WHERE u.id = ?", (uzdevuma_id,)).fetchone()
    return _no_rindas(rinda) if rinda else None


def drosa_atpakal_adrese(adrese: str | None, noklusejums: str) -> str:
    """Novirza tikai uz šīs lietotnes ceļu, nevis ārēju adresi."""
    if adrese and adrese.startswith("/") and not adrese.startswith("//") and "\\" not in adrese:
        return adrese
    return noklusejums


def _formas_konteksts(lietotajs: Lietotajs, **papildus) -> dict:
    return {"organizacijas": meklet(), "lietotaji": visi_lietotaji() if lietotajs.ir_vaditajs else []} | papildus


@router.get("/uzdevumi")
def saraksts(request: Request, lietotajs: Pieslegts, lidz_sodienai: bool = False, pazinojums: str | None = None) -> Response:
    uzdevumi = atlasit(None if lietotajs.ir_vaditajs else lietotajs.id, lidz_sodienai)
    if gaida_html(request):
        konteksts = {
            "uzdevumi": uzdevumi,
            "lidz_sodienai": lidz_sodienai,
            "izpildits_pazinojums": pazinojums == IZPILDITS_PAZINOJUMS,
        }
        return veidne(request, "uzdevumi/saraksts.html", konteksts)
    return JSONResponse([u.model_dump(mode="json") for u in uzdevumi])


@router.get("/uzdevumi/jauns", include_in_schema=False)
def jauna_forma(request: Request, lietotajs: Pieslegts) -> Response:
    ievade = {"termins": laiks.sodien().isoformat(), "atbildigais_id": lietotajs.id}
    return veidne(request, "uzdevumi/forma.html", _formas_konteksts(lietotajs, ievade=ievade))


@router.post("/uzdevumi", status_code=201)
async def izveidot(request: Request, lietotajs: Pieslegts) -> Response:
    forma = ir_forma(request)
    try:
        dati, _ = await nolasit(request, UzdevumsIevade)
        atbildigais_id = dati.atbildigais_id if dati.atbildigais_id is not None else lietotajs.id
        if atbildigais_id != lietotajs.id:
            if not lietotajs.ir_vaditajs:
                raise HTTPException(403, "Uzdevumu citam darbiniekam var piešķirt tikai vadītājs")
            if lietotajs_pec_id(atbildigais_id) is None:
                raise Validacija.lauks("atbildigais_id", "NOT_FOUND", "Lietotājs nav atrasts.")
        if dati.organizacija_id is not None and organizacija_pec_id(dati.organizacija_id) is None:
            raise Validacija.lauks("organizacija_id", "NOT_FOUND", "Organizācija nav atrasta.")
    except Validacija as exc:
        if forma:
            konteksts = _formas_konteksts(lietotajs, kludas=exc.lauku_kludas(), ievade=dict(await request.form()))
            return veidne(request, "uzdevumi/forma.html", konteksts, 422)
        raise
    with savienojums() as conn:
        jauns_id = conn.execute(
            "INSERT INTO uzdevumi (nosaukums, termins, atbildigais_id, organizacija_id, atgadinat) VALUES (?, ?, ?, ?, ?)",
            (dati.nosaukums, dati.termins.isoformat(), atbildigais_id, dati.organizacija_id,
             dati.atgadinat.isoformat() if dati.atgadinat else None),
        ).lastrowid
    if forma:
        return RedirectResponse("/uzdevumi", status_code=303)
    return JSONResponse(uzdevums_pec_id(jauns_id).model_dump(mode="json"), status_code=201)


@router.post("/uzdevumi/{uzdevuma_id}/izpildits")
async def atzimet_izpilditu(request: Request, uzdevuma_id: int, lietotajs: Pieslegts) -> Response:
    """Atzīmē var tikai uzdevuma atbildīgais. Atkārtota atzīmēšana neko nemaina."""
    uzdevums = uzdevums_pec_id(uzdevuma_id)
    if uzdevums is None:
        raise HTTPException(404, "Uzdevums nav atrasts")
    if uzdevums.atbildigais_id != lietotajs.id:
        raise HTTPException(403, "Atzīmēt var tikai savu uzdevumu")
    with savienojums() as conn:
        conn.execute("UPDATE uzdevumi SET izpildits = 1 WHERE id = ?", (uzdevuma_id,))
    if ir_forma(request):
        atpakal = drosa_atpakal_adrese((await request.form()).get("atpakal"), "/uzdevumi")
        atdalitajs = "&" if "?" in atpakal else "?"
        return RedirectResponse(f"{atpakal}{atdalitajs}pazinojums={IZPILDITS_PAZINOJUMS}", status_code=303)
    return JSONResponse(uzdevums_pec_id(uzdevuma_id).model_dump(mode="json"))
