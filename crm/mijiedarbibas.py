"""CR-7: mijiedarbību žurnāls (F3)."""

import sqlite3
from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import AfterValidator, BaseModel, StringConstraints
from pydantic_core import PydanticCustomError

from crm import laiks
from crm.auth import Lietotajs, Pieslegts
from crm.db import savienojums
from crm.ievade import nolasit
from crm.kludas import Validacija, gaida_html
from crm.organizacijas import KARTITES_PAPILDINAJUMI, Organizacija, atrast_organizaciju, meklet, organizacija_pec_id
from crm.sabloni import veidne

router = APIRouter()

Veids = Literal["zvans", "e-pasts", "tikšanās"]
VEIDU_NOSAUKUMI = {"zvans": "Zvans", "e-pasts": "E-pasts", "tikšanās": "Tikšanās"}
KOPSAVILKUMA_MAX = 2000


def _ne_nakotne(datums: date) -> date:
    if datums > laiks.sodien():
        raise PydanticCustomError("FUTURE_DATE", "Datums nedrīkst būt nākotnē.")
    return datums


class MijiedarbibaIevade(BaseModel):
    datums: Annotated[date, AfterValidator(_ne_nakotne)]
    veids: Veids
    organizacija_id: int
    kopsavilkums: Annotated[str, StringConstraints(strip_whitespace=True, max_length=KOPSAVILKUMA_MAX)] = ""


class Mijiedarbiba(BaseModel):
    id: int
    datums: date
    veids: Veids
    organizacija_id: int
    organizacijas_nosaukums: str
    darbinieks_id: int
    darbinieka_vards: str
    kopsavilkums: str
    mi_kopsavilkums: str | None = None  # MI-1, tikai pēc darbinieka apstiprinājuma
    mi_nakamais_solis: str | None = None


_VAICAJUMS = """
    SELECT m.*, o.nosaukums AS organizacijas_nosaukums, l.vards AS darbinieka_vards
    FROM mijiedarbibas m
    JOIN organizacijas o ON o.id = m.organizacija_id
    JOIN lietotaji l ON l.id = m.darbinieks_id
"""
_SECIBA = " ORDER BY m.datums DESC, m.id DESC"


def _no_rindas(rinda: sqlite3.Row) -> Mijiedarbiba:
    return Mijiedarbiba(**{k: rinda[k] for k in Mijiedarbiba.model_fields})


def atlasit(
    darbinieks_id: int | None = None,
    no: date | None = None,
    lidz: date | None = None,
    organizacija_id: int | None = None,
    limits: int | None = None,
) -> list[Mijiedarbiba]:
    """Mijiedarbības no jaunākās. `darbinieks_id=None` — visu darbinieku."""
    nosacijumi, parametri = [], []
    if darbinieks_id is not None:
        nosacijumi.append("m.darbinieks_id = ?")
        parametri.append(darbinieks_id)
    if organizacija_id is not None:
        nosacijumi.append("m.organizacija_id = ?")
        parametri.append(organizacija_id)
    if no is not None:
        nosacijumi.append("m.datums >= ?")
        parametri.append(no.isoformat())
    if lidz is not None:
        nosacijumi.append("m.datums <= ?")
        parametri.append(lidz.isoformat())
    vaicajums = _VAICAJUMS + (" WHERE " + " AND ".join(nosacijumi) if nosacijumi else "") + _SECIBA
    if limits is not None:
        vaicajums += " LIMIT ?"
        parametri.append(limits)
    with savienojums() as conn:
        return [_no_rindas(r) for r in conn.execute(vaicajums, parametri).fetchall()]


def mijiedarbiba_pec_id(mijiedarbibas_id: int) -> Mijiedarbiba | None:
    with savienojums() as conn:
        rinda = conn.execute(_VAICAJUMS + " WHERE m.id = ?", (mijiedarbibas_id,)).fetchone()
    return _no_rindas(rinda) if rinda else None


def sonedel() -> tuple[date, date]:
    sakums = laiks.nedelas_sakums(laiks.sodien())
    return sakums, sakums + timedelta(days=6)


def redzamais_darbinieks(lietotajs: Lietotajs) -> int | None:
    """Darbinieks redz tikai savus ierakstus, vadītājs — visus (N3)."""
    return None if lietotajs.ir_vaditajs else lietotajs.id


def _formas_konteksts(**papildus) -> dict:
    return {"organizacijas": meklet(), "veidi": VEIDU_NOSAUKUMI, "sodien": laiks.sodien()} | papildus


@router.get("/mijiedarbibas")
def saraksts(request: Request, lietotajs: Pieslegts, periods: Literal["sonedel"] | None = None) -> Response:
    no, lidz = sonedel() if periods == "sonedel" else (None, None)
    mijiedarbibas = atlasit(redzamais_darbinieks(lietotajs), no, lidz)
    if gaida_html(request):
        konteksts = {"mijiedarbibas": mijiedarbibas, "periods": periods, "veidi": VEIDU_NOSAUKUMI}
        return veidne(request, "mijiedarbibas/saraksts.html", konteksts)
    return JSONResponse([m.model_dump(mode="json") for m in mijiedarbibas])


@router.get("/mijiedarbibas/jauna", include_in_schema=False)
def jauna_forma(request: Request, lietotajs: Pieslegts, organizacija_id: int | None = None) -> Response:
    ievade = {"datums": laiks.sodien().isoformat(), "organizacija_id": organizacija_id}
    return veidne(request, "mijiedarbibas/forma.html", _formas_konteksts(ievade=ievade))


@router.post("/mijiedarbibas", status_code=201)
async def pievienot(request: Request, lietotajs: Pieslegts) -> Response:
    try:
        dati, forma = await nolasit(request, MijiedarbibaIevade)
        if organizacija_pec_id(dati.organizacija_id) is None:
            ievade = dict(await request.form()) if forma else {}
            raise Validacija.lauks("organizacija_id", "NOT_FOUND", "Organizācija nav atrasta.", forma, ievade)
    except Validacija as exc:
        if exc.forma:
            konteksts = _formas_konteksts(kludas=exc.lauku_kludas(), ievade=exc.ievade)
            return veidne(request, "mijiedarbibas/forma.html", konteksts, 422)
        raise
    with savienojums() as conn:
        jauns_id = conn.execute(
            "INSERT INTO mijiedarbibas (datums, veids, organizacija_id, darbinieks_id, kopsavilkums) VALUES (?, ?, ?, ?, ?)",
            (dati.datums.isoformat(), dati.veids, dati.organizacija_id, lietotajs.id, dati.kopsavilkums),
        ).lastrowid
        rinda = conn.execute(_VAICAJUMS + " WHERE m.id = ?", (jauns_id,)).fetchone()
    if forma:
        return RedirectResponse(f"/organizacijas/{dati.organizacija_id}", status_code=303)
    return JSONResponse(_no_rindas(rinda).model_dump(mode="json"), status_code=201)


@router.get("/organizacijas/{organizacijas_id}/mijiedarbibas")
def organizacijas_mijiedarbibas(organizacijas_id: int, lietotajs: Pieslegts) -> Response:
    atrast_organizaciju(organizacijas_id)
    return JSONResponse([m.model_dump(mode="json") for m in atlasit(organizacija_id=organizacijas_id)])


def _kartites_bloks(organizacija: Organizacija, lietotajs: Lietotajs) -> dict:
    return {
        "bloks": "mijiedarbibas/kartites_bloks.html",
        "mijiedarbibas": atlasit(organizacija_id=organizacija.id),
        "veidi": VEIDU_NOSAUKUMI,
        "ar_mi": True,
    }


KARTITES_PAPILDINAJUMI.append(_kartites_bloks)
