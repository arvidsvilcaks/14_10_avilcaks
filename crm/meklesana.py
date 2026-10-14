"""F6: meklēšana pa visiem ierakstiem.

Meklē bez reģistra un garumzīmēm (kā F1). Redzamība kā sadaļu sarakstos (N3):
organizācijas un kontaktpersonas redz visi; mijiedarbības, pieprasījumus un
uzdevumus darbinieks redz tikai savus, vadītājs — visus.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from crm import kontakti, mijiedarbibas, organizacijas, pieprasijumi, uzdevumi
from crm.auth import Lietotajs, Pieslegts
from crm.kludas import gaida_html
from crm.kontakti import Kontaktpersona
from crm.mijiedarbibas import Mijiedarbiba
from crm.organizacijas import Organizacija, normalizet
from crm.pieprasijumi import Pieprasijums
from crm.sabloni import veidne
from crm.uzdevumi import Uzdevums

router = APIRouter()

MIN_GARUMS = 2


class MeklesanasRezultati(BaseModel):
    q: str
    organizacijas: list[Organizacija]
    kontaktpersonas: list[Kontaktpersona]
    mijiedarbibas: list[Mijiedarbiba]
    pieprasijumi: list[Pieprasijums]
    uzdevumi: list[Uzdevums]


def _atbilst(teksts: str, *lauki: str | None) -> bool:
    return any(teksts in normalizet(lauks) for lauks in lauki if lauks)


def meklet(lietotajs: Lietotajs, q: str) -> MeklesanasRezultati:
    teksts = normalizet(q.strip())
    filtrs = None if lietotajs.ir_vaditajs else lietotajs.id
    if len(teksts) < MIN_GARUMS:
        return MeklesanasRezultati(q=q, organizacijas=[], kontaktpersonas=[], mijiedarbibas=[], pieprasijumi=[], uzdevumi=[])
    return MeklesanasRezultati(
        q=q,
        organizacijas=[o for o in organizacijas.meklet() if _atbilst(teksts, o.nosaukums, o.reg_nr)],
        kontaktpersonas=[k for k in kontakti.visas() if _atbilst(teksts, k.vards, k.amats, k.epasts, k.talrunis)],
        mijiedarbibas=[
            m for m in mijiedarbibas.atlasit(filtrs) if _atbilst(teksts, m.kopsavilkums, m.organizacijas_nosaukums)
        ],
        pieprasijumi=[p for p in pieprasijumi.atlasit(filtrs) if _atbilst(teksts, p.apraksts, p.organizacijas_nosaukums)],
        uzdevumi=[u for u in uzdevumi.atlasit(filtrs) if _atbilst(teksts, u.nosaukums, u.organizacijas_nosaukums)],
    )


@router.get("/meklet")
def meklesana(request: Request, lietotajs: Pieslegts, q: str = "") -> Response:
    rezultati = meklet(lietotajs, q)
    if gaida_html(request):
        organizaciju_nosaukumi = {o.id: o.nosaukums for o in organizacijas.meklet()}
        konteksts = {
            "r": rezultati,
            "par_isu": 0 < len(q.strip()) < MIN_GARUMS,
            "min_garums": MIN_GARUMS,
            "veidi": mijiedarbibas.VEIDU_NOSAUKUMI,
            "organizaciju_nosaukumi": organizaciju_nosaukumi,
        }
        return veidne(request, "meklesana/rezultati.html", konteksts)
    return JSONResponse(rezultati.model_dump(mode="json"))
