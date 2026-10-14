"""CR-6: organizācijas — izveidot, rediģēt, meklēt (F1)."""

import sqlite3
import unicodedata
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, StringConstraints

from crm.auth import Lietotajs, Pieslegts, lietotajs_pec_id, visi_lietotaji
from crm.db import savienojums
from crm.ievade import nolasit
from crm.kludas import Validacija, gaida_html
from crm.sabloni import veidne

router = APIRouter()

Nosaukums = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
RegNr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]


class OrganizacijaIevade(BaseModel):
    nosaukums: Nosaukums
    reg_nr: RegNr | None = None


class OrganizacijasLabojums(BaseModel):
    nosaukums: Nosaukums | None = None
    reg_nr: RegNr | None = None
    atbildigais_id: int | None = None


class Organizacija(BaseModel):
    id: int
    nosaukums: str
    reg_nr: str | None
    atbildigais_id: int
    atbildigais_vards: str


def normalizet(teksts: str) -> str:
    """Meklēšanas forma: bez garumzīmēm un mīkstinājuma zīmēm, mazajiem burtiem."""
    sadalits = unicodedata.normalize("NFKD", teksts)
    return "".join(z for z in sadalits if not unicodedata.combining(z)).casefold()


_VAICAJUMS = """
    SELECT o.*, l.vards AS atbildigais_vards
    FROM organizacijas o JOIN lietotaji l ON l.id = o.atbildigais_id
"""


def _no_rindas(rinda: sqlite3.Row) -> Organizacija:
    return Organizacija(
        id=rinda["id"],
        nosaukums=rinda["nosaukums"],
        reg_nr=rinda["reg_nr"],
        atbildigais_id=rinda["atbildigais_id"],
        atbildigais_vards=rinda["atbildigais_vards"],
    )


def organizacija_pec_id(organizacijas_id: int) -> Organizacija | None:
    with savienojums() as conn:
        rinda = conn.execute(_VAICAJUMS + " WHERE o.id = ?", (organizacijas_id,)).fetchone()
    return _no_rindas(rinda) if rinda else None


def atrast_organizaciju(organizacijas_id: int) -> Organizacija:
    organizacija = organizacija_pec_id(organizacijas_id)
    if organizacija is None:
        raise HTTPException(404, "Organizācija nav atrasta")
    return organizacija


def meklet(teksts: str | None = None) -> list[Organizacija]:
    vaicajums, parametri = _VAICAJUMS, []
    if teksts and teksts.strip():
        aizsargats = normalizet(teksts.strip()).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        vaicajums += " WHERE o.nosaukums_meklesanai LIKE ? ESCAPE '\\'"
        parametri.append(f"%{aizsargats}%")
    with savienojums() as conn:
        rindas = conn.execute(vaicajums + " ORDER BY o.nosaukums_meklesanai, o.id", parametri).fetchall()
    return [_no_rindas(r) for r in rindas]


def var_labot(lietotajs: Lietotajs, organizacija: Organizacija) -> bool:
    return lietotajs.ir_vaditajs or organizacija.atbildigais_id == lietotajs.id


def _reg_nr_konflikts() -> HTTPException:
    return HTTPException(409, "Organizācija ar šo reģistrācijas numuru jau ir")


def _formas_konteksts(lietotajs: Lietotajs, **papildus) -> dict:
    konteksts = {"lietotaji": visi_lietotaji() if lietotajs.ir_vaditajs else []}
    konteksts.update(papildus)
    return konteksts


@router.get("/organizacijas")
def saraksts(request: Request, lietotajs: Pieslegts, q: str | None = None) -> Response:
    organizacijas = meklet(q)
    if gaida_html(request):
        return veidne(request, "organizacijas/saraksts.html", {"organizacijas": organizacijas, "q": q or ""})
    return JSONResponse([o.model_dump() for o in organizacijas])


@router.get("/organizacijas/jauna", include_in_schema=False)
def jauna_forma(request: Request, lietotajs: Pieslegts) -> Response:
    return veidne(request, "organizacijas/forma.html", _formas_konteksts(lietotajs))


@router.post("/organizacijas", status_code=201)
async def izveidot(request: Request, lietotajs: Pieslegts) -> Response:
    try:
        dati, forma = await nolasit(request, OrganizacijaIevade)
    except Validacija as exc:
        if exc.forma:
            konteksts = _formas_konteksts(lietotajs, kludas=exc.lauku_kludas(), ievade=exc.ievade)
            return veidne(request, "organizacijas/forma.html", konteksts, 422)
        raise
    try:
        with savienojums() as conn:
            jauns_id = conn.execute(
                "INSERT INTO organizacijas (nosaukums, nosaukums_meklesanai, reg_nr, atbildigais_id) VALUES (?, ?, ?, ?)",
                (dati.nosaukums, normalizet(dati.nosaukums), dati.reg_nr, lietotajs.id),
            ).lastrowid
    except sqlite3.IntegrityError:
        if forma:
            konteksts = _formas_konteksts(
                lietotajs, kludas={"reg_nr": "Organizācija ar šo reģistrācijas numuru jau ir."}, ievade=dati.model_dump()
            )
            return veidne(request, "organizacijas/forma.html", konteksts, 409)
        raise _reg_nr_konflikts() from None
    if forma:
        return RedirectResponse(f"/organizacijas/{jauns_id}", status_code=303)
    return JSONResponse(organizacija_pec_id(jauns_id).model_dump(), status_code=201)


@router.get("/organizacijas/{organizacijas_id}")
def kartite(request: Request, organizacijas_id: int, lietotajs: Pieslegts) -> Response:
    organizacija = atrast_organizaciju(organizacijas_id)
    if gaida_html(request):
        konteksts = {"organizacija": organizacija, "var_labot": var_labot(lietotajs, organizacija)}
        konteksts["kartites_bloki"] = []
        for papildinajums in KARTITES_PAPILDINAJUMI:
            dati = papildinajums(organizacija, lietotajs)
            konteksts["kartites_bloki"].append(dati.pop("bloks"))
            konteksts.update(dati)
        return veidne(request, "organizacijas/kartite.html", konteksts)
    return JSONResponse(organizacija.model_dump())


# Citu moduļu (F3, F4) bloki organizācijas kartītē: funkcija(organizacija, lietotajs) atgriež
# konteksta datus un atslēgā "bloks" — iekļaujamā šablona nosaukumu.
KARTITES_PAPILDINAJUMI: list[Callable[[Organizacija, Lietotajs], dict]] = []


def _saglabat(organizacija: Organizacija, lietotajs: Lietotajs, dati: OrganizacijasLabojums) -> Organizacija:
    """Pārbauda tiesības un saglabā tikai norādītos laukus."""
    if not var_labot(lietotajs, organizacija):
        raise HTTPException(403, "Rediģēt var tikai atbildīgais darbinieks vai vadītājs")
    lauki = dati.model_dump(include=dati.model_fields_set)
    if "atbildigais_id" in lauki:
        if not lietotajs.ir_vaditajs:
            raise HTTPException(403, "Atbildīgo darbinieku maina tikai vadītājs")
        if lauki["atbildigais_id"] is None or lietotajs_pec_id(lauki["atbildigais_id"]) is None:
            raise Validacija.lauks("atbildigais_id", "NOT_FOUND", "Lietotājs nav atrasts.")
    if "nosaukums" in lauki:
        if lauki["nosaukums"] is None:
            raise Validacija.lauks("nosaukums", "REQUIRED", "Lauks ir obligāts.")
        lauki["nosaukums_meklesanai"] = normalizet(lauki["nosaukums"])
    if lauki:
        izteiksme = ", ".join(f"{k} = ?" for k in lauki)
        try:
            with savienojums() as conn:
                conn.execute(f"UPDATE organizacijas SET {izteiksme} WHERE id = ?", (*lauki.values(), organizacija.id))
        except sqlite3.IntegrityError:
            raise _reg_nr_konflikts() from None
    return organizacija_pec_id(organizacija.id)


@router.patch("/organizacijas/{organizacijas_id}")
async def labot(request: Request, organizacijas_id: int, lietotajs: Pieslegts) -> Response:
    organizacija = atrast_organizaciju(organizacijas_id)
    dati, _ = await nolasit(request, OrganizacijasLabojums)
    return JSONResponse(_saglabat(organizacija, lietotajs, dati).model_dump())


@router.get("/organizacijas/{organizacijas_id}/labot", include_in_schema=False)
def labosanas_forma(request: Request, organizacijas_id: int, lietotajs: Pieslegts) -> Response:
    organizacija = atrast_organizaciju(organizacijas_id)
    if not var_labot(lietotajs, organizacija):
        raise HTTPException(403, "Rediģēt var tikai atbildīgais darbinieks vai vadītājs")
    konteksts = _formas_konteksts(lietotajs, organizacija=organizacija, ievade=organizacija.model_dump())
    return veidne(request, "organizacijas/forma.html", konteksts)


@router.post("/organizacijas/{organizacijas_id}/labot", include_in_schema=False)
async def labot_forma(request: Request, organizacijas_id: int, lietotajs: Pieslegts) -> Response:
    """HTML forma nevar sūtīt PATCH; tukšs reģistrācijas numurs nozīmē „nav”."""
    organizacija = atrast_organizaciju(organizacijas_id)
    ievade = dict(await request.form())
    try:
        dati, _ = await nolasit(request, OrganizacijasLabojums)
        if "nosaukums" not in dati.model_fields_set:
            raise Validacija.lauks("nosaukums", "REQUIRED", "Lauks ir obligāts.")
        dati.reg_nr = dati.reg_nr  # piešķiršana iekļauj lauku model_fields_set arī tad, ja tas bija tukšs
        _saglabat(organizacija, lietotajs, dati)
    except Validacija as exc:
        konteksts = _formas_konteksts(lietotajs, organizacija=organizacija, kludas=exc.lauku_kludas(), ievade=ievade)
        return veidne(request, "organizacijas/forma.html", konteksts, 422)
    except HTTPException as exc:
        if exc.status_code != 409:
            raise
        konteksts = _formas_konteksts(
            lietotajs, organizacija=organizacija, kludas={"reg_nr": exc.detail + "."}, ievade=ievade
        )
        return veidne(request, "organizacijas/forma.html", konteksts, 409)
    return RedirectResponse(f"/organizacijas/{organizacija.id}", status_code=303)
