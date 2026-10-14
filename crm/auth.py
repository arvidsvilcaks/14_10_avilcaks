"""CR-4: reģistrēšanās, pieslēgšanās un atteikšanās (F0)."""

import re
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import AfterValidator, BaseModel, StringConstraints
from pydantic_core import PydanticCustomError

from crm import paroles
from crm.db import savienojums
from crm.ievade import ir_forma, nolasit
from crm.kludas import NavPieslegts, Validacija, gaida_html
from crm.sabloni import veidne

router = APIRouter()

PAROLES_MIN_GARUMS = 12
EPASTA_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _epasts(vertiba: str) -> str:
    vertiba = vertiba.strip().lower()
    if not EPASTA_RE.match(vertiba):
        raise PydanticCustomError("INVALID_FORMAT", "Nederīga e-pasta adrese.")
    return vertiba


Epasts = Annotated[str, StringConstraints(max_length=254), AfterValidator(_epasts)]
Vards = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class Lietotajs(BaseModel):
    id: int
    vards: str
    epasts: str


class Registracija(BaseModel):
    vards: Vards
    epasts: Epasts
    parole: Annotated[str, StringConstraints(min_length=PAROLES_MIN_GARUMS, max_length=256)]


class Pieslegsanas(BaseModel):
    epasts: Annotated[str, StringConstraints(min_length=1, max_length=254)]
    parole: Annotated[str, StringConstraints(min_length=1, max_length=256)]


def _no_rindas(rinda: sqlite3.Row) -> Lietotajs:
    return Lietotajs(id=rinda["id"], vards=rinda["vards"], epasts=rinda["epasts"])


def lietotajs_pec_id(lietotaja_id: int) -> Lietotajs | None:
    with savienojums() as conn:
        rinda = conn.execute("SELECT * FROM lietotaji WHERE id = ?", (lietotaja_id,)).fetchone()
    return _no_rindas(rinda) if rinda else None


def pieslegts_lietotajs(request: Request) -> Lietotajs:
    """Atkarība aizsargātiem maršrutiem. Lietotāju nolasa no datubāzes katrā pieprasījumā."""
    lietotaja_id = request.session.get("lietotajs_id")
    lietotajs = lietotajs_pec_id(lietotaja_id) if isinstance(lietotaja_id, int) else None
    if lietotajs is None:
        request.session.clear()
        raise NavPieslegts()
    request.state.lietotajs = lietotajs
    return lietotajs


Pieslegts = Annotated[Lietotajs, Depends(pieslegts_lietotajs)]


@router.get("/", include_in_schema=False)
def sakums(request: Request) -> RedirectResponse:
    merkis = "/panelis" if request.session.get("lietotajs_id") else "/auth/login"
    return RedirectResponse(merkis, status_code=303)


@router.get("/auth/register", include_in_schema=False)
def registracijas_lapa(request: Request) -> Response:
    return veidne(request, "auth/registreties.html")


@router.post("/auth/register", status_code=201)
async def registret(request: Request) -> Response:
    try:
        dati, forma = await nolasit(request, Registracija)
    except Validacija as exc:
        if exc.forma:
            return veidne(request, "auth/registreties.html", {"kludas": exc.lauku_kludas(), "ievade": exc.ievade}, 422)
        raise
    salt, hash_ = paroles.jauna(dati.parole)
    try:
        with savienojums() as conn:
            kursors = conn.execute(
                "INSERT INTO lietotaji (vards, epasts, paroles_salt, paroles_hash) VALUES (?, ?, ?, ?)",
                (dati.vards, dati.epasts, salt, hash_),
            )
            jauns_id = kursors.lastrowid
    except sqlite3.IntegrityError:
        if forma:
            kludas = {"epasts": "Lietotājs ar šo e-pastu jau ir reģistrēts."}
            return veidne(request, "auth/registreties.html", {"kludas": kludas, "ievade": dati.model_dump()}, 409)
        raise HTTPException(409, "Lietotājs ar šo e-pastu jau ir reģistrēts") from None
    if forma:
        return RedirectResponse("/auth/login?registrets=1", status_code=303)
    return JSONResponse(lietotajs_pec_id(jauns_id).model_dump(), status_code=201)


@router.get("/auth/login", include_in_schema=False)
def pieslegsanas_lapa(request: Request, registrets: bool = False) -> Response:
    return veidne(request, "auth/pieslegties.html", {"registrets": registrets})


NEPAREIZI_DATI = "Nepareizs e-pasts vai parole"


@router.post("/auth/login")
async def pieslegties(request: Request) -> Response:
    try:
        dati, forma = await nolasit(request, Pieslegsanas)
    except Validacija as exc:
        if exc.forma:
            return veidne(request, "auth/pieslegties.html", {"kludas": exc.lauku_kludas(), "ievade": exc.ievade}, 422)
        raise
    epasts = dati.epasts.strip().lower()
    with savienojums() as conn:
        rinda = conn.execute("SELECT * FROM lietotaji WHERE epasts = ?", (epasts,)).fetchone()
    if rinda is None:
        paroles.fiktiva_parbaude(dati.parole)
    if rinda is None or not paroles.parbaudit(dati.parole, rinda["paroles_salt"], rinda["paroles_hash"]):
        if forma:
            konteksts = {"kluda": NEPAREIZI_DATI + ".", "ievade": {"epasts": dati.epasts}}
            return veidne(request, "auth/pieslegties.html", konteksts, 401)
        raise HTTPException(401, NEPAREIZI_DATI)
    request.session.clear()
    request.session["lietotajs_id"] = rinda["id"]
    if forma:
        return RedirectResponse("/panelis", status_code=303)
    return JSONResponse({"lietotajs": _no_rindas(rinda).model_dump()})


@router.post("/auth/logout")
async def atslegties(request: Request) -> Response:
    request.session.clear()
    if ir_forma(request) or gaida_html(request):
        return RedirectResponse("/auth/login", status_code=303)
    return Response(status_code=204)
