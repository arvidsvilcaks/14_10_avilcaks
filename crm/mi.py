"""MI-1: mijiedarbības kopsavilkums un nākamā soļa ieteikums.

MI ieteikumu ģenerē Claude (Anthropic API). Tas netiek saglabāts, kamēr darbinieks
to nav pārskatījis un apstiprinājis; saglabātais ieteikums vienmēr ir marķēts
„Ģenerēts ar MI”. Modelim nosūta tikai mijiedarbības veidu un kopsavilkuma tekstu —
ne organizācijas nosaukumu, ne kontaktpersonu datus (N2).

Konfigurācija: `ANTHROPIC_API_KEY` (vai cits Anthropic SDK akreditācijas avots) un
pakotne `anthropic`. Bez tām funkcija paziņo, ka MI nav pieejams.
"""

import os
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, StringConstraints

from crm.auth import Lietotajs, Pieslegts
from crm.db import savienojums
from crm.ievade import nolasit
from crm.kludas import Validacija
from crm.mijiedarbibas import VEIDU_NOSAUKUMI, Mijiedarbiba, mijiedarbiba_pec_id
from crm.sabloni import veidne

router = APIRouter()

MODELIS = os.environ.get("CRM_MI_MODELIS", "claude-opus-5-5")
SISTEMA = (
    "Tu palīdzi pašvaldības darbiniekam CRM sistēmā. No mijiedarbības apraksta uzraksti latviski: "
    "1) kopsavilkumu ne garāku par 2 teikumiem; 2) vienu konkrētu nākamo soli. "
    "Neizdomā faktus, kuru nav aprakstā. Atbildi tieši divās rindās formātā:\n"
    "KOPSAVILKUMS: ...\nNĀKAMAIS SOLIS: ..."
)


class MiNavPieejams(Exception):
    pass


class MiIeteikums(BaseModel):
    kopsavilkums: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    nakamais_solis: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


def _parset(teksts: str) -> MiIeteikums:
    lauki = {"kopsavilkums": "", "nakamais_solis": ""}
    for rinda in teksts.splitlines():
        galva, _, vertiba = rinda.partition(":")
        galva = galva.strip().upper()
        if galva == "KOPSAVILKUMS":
            lauki["kopsavilkums"] = vertiba.strip()
        elif galva in ("NĀKAMAIS SOLIS", "NAKAMAIS SOLIS"):
            lauki["nakamais_solis"] = vertiba.strip()
    if not lauki["kopsavilkums"] or not lauki["nakamais_solis"]:
        raise MiNavPieejams("MI atbilde nav gaidītajā formātā")
    return MiIeteikums(**lauki)


def generet(veids: str, kopsavilkums: str) -> MiIeteikums:
    """Izsauc Claude. Testos šo funkciju aizstāj."""
    try:
        import anthropic
    except ImportError:
        raise MiNavPieejams("Pakotne anthropic nav instalēta") from None
    try:
        klients = anthropic.Anthropic()
        atbilde = klients.messages.create(
            model=MODELIS,
            max_tokens=1024,
            system=SISTEMA,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": f"Veids: {VEIDU_NOSAUKUMI[veids]}\nApraksts: {kopsavilkums}"}],
        )
    except anthropic.APIStatusError as exc:
        raise MiNavPieejams(f"MI pakalpojuma kļūda ({exc.status_code})") from None
    except (anthropic.APIConnectionError, anthropic.AnthropicError):
        raise MiNavPieejams("MI pakalpojums nav sasniedzams vai nav konfigurēts") from None
    if atbilde.stop_reason == "refusal":
        raise MiNavPieejams("MI atteicās sagatavot ieteikumu")
    teksts = "".join(b.text for b in atbilde.content if b.type == "text")
    return _parset(teksts)


def var_lietot(lietotajs: Lietotajs, mijiedarbiba: Mijiedarbiba) -> bool:
    return lietotajs.ir_vaditajs or mijiedarbiba.darbinieks_id == lietotajs.id


def _atrast(mijiedarbibas_id: int, lietotajs: Lietotajs) -> Mijiedarbiba:
    mijiedarbiba = mijiedarbiba_pec_id(mijiedarbibas_id)
    if mijiedarbiba is None:
        raise HTTPException(404, "Mijiedarbība nav atrasta")
    if not var_lietot(lietotajs, mijiedarbiba):
        raise HTTPException(403, "MI ieteikumu var veidot mijiedarbības autors vai vadītājs")
    return mijiedarbiba


def _lapa(request: Request, mijiedarbiba: Mijiedarbiba, status_code: int = 200, **papildus) -> Response:
    konteksts = {"m": mijiedarbiba, "veidi": VEIDU_NOSAUKUMI} | papildus
    return veidne(request, "mi/ieteikums.html", konteksts, status_code)


@router.get("/mijiedarbibas/{mijiedarbibas_id}/mi", include_in_schema=False)
def ieteikuma_lapa(request: Request, mijiedarbibas_id: int, lietotajs: Pieslegts) -> Response:
    return _lapa(request, _atrast(mijiedarbibas_id, lietotajs))


@router.post("/mijiedarbibas/{mijiedarbibas_id}/mi/generet", include_in_schema=False)
def generet_ieteikumu(request: Request, mijiedarbibas_id: int, lietotajs: Pieslegts) -> Response:
    mijiedarbiba = _atrast(mijiedarbibas_id, lietotajs)
    if not mijiedarbiba.kopsavilkums:
        return _lapa(request, mijiedarbiba, 422, kluda="Mijiedarbībai nav kopsavilkuma teksta, no kā veidot ieteikumu.")
    try:
        ieteikums = generet(mijiedarbiba.veids, mijiedarbiba.kopsavilkums)
    except MiNavPieejams as exc:
        return _lapa(request, mijiedarbiba, 503, kluda=f"MI ieteikums nav pieejams: {exc}.")
    return _lapa(request, mijiedarbiba, melnraksts=ieteikums.model_dump())


@router.post("/mijiedarbibas/{mijiedarbibas_id}/mi/apstiprinat", include_in_schema=False)
async def apstiprinat(request: Request, mijiedarbibas_id: int, lietotajs: Pieslegts) -> Response:
    """Saglabā darbinieka pārskatīto (un, ja vajag, laboto) MI ieteikumu."""
    mijiedarbiba = _atrast(mijiedarbibas_id, lietotajs)
    try:
        dati, _ = await nolasit(request, MiIeteikums)
    except Validacija as exc:
        return _lapa(request, mijiedarbiba, 422, melnraksts=exc.ievade, kludas=exc.lauku_kludas())
    with savienojums() as conn:
        conn.execute(
            "UPDATE mijiedarbibas SET mi_kopsavilkums = ?, mi_nakamais_solis = ?, mi_apstiprinaja_id = ? WHERE id = ?",
            (dati.kopsavilkums, dati.nakamais_solis, lietotajs.id, mijiedarbiba.id),
        )
    return RedirectResponse(f"/organizacijas/{mijiedarbiba.organizacija_id}", status_code=303)


@router.post("/mijiedarbibas/{mijiedarbibas_id}/mi/dzest", include_in_schema=False)
def dzest(mijiedarbibas_id: int, lietotajs: Pieslegts) -> Response:
    mijiedarbiba = _atrast(mijiedarbibas_id, lietotajs)
    with savienojums() as conn:
        conn.execute(
            "UPDATE mijiedarbibas SET mi_kopsavilkums = NULL, mi_nakamais_solis = NULL, mi_apstiprinaja_id = NULL WHERE id = ?",
            (mijiedarbiba.id,),
        )
    return RedirectResponse(f"/organizacijas/{mijiedarbiba.organizacija_id}", status_code=303)
