"""F7: pārskats vadītājam — darbinieku aktivitāte un slodze izvēlētajā periodā."""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel

from crm import laiks
from crm.auth import Vaditajs
from crm.db import savienojums
from crm.kludas import gaida_html
from crm.mijiedarbibas import VEIDU_NOSAUKUMI
from crm.sabloni import veidne

router = APIRouter()

PERIODI = (7, 30, 90)


class DarbiniekaRaditaji(BaseModel):
    darbinieks_id: int
    vards: str
    zvani: int
    epasti: int
    tiksanas: int
    mijiedarbibas: int
    atverti_pieprasijumi: int
    kaveti_pieprasijumi: int
    neizpilditi_uzdevumi: int
    kaveti_uzdevumi: int


class Parskats(BaseModel):
    no: date
    lidz: date
    dienas: int
    darbinieki: list[DarbiniekaRaditaji]
    kopa: DarbiniekaRaditaji


def parskats(dienas: int) -> Parskats:
    lidz = laiks.sodien()
    no = lidz - timedelta(days=dienas - 1)
    sodien = lidz.isoformat()
    with savienojums() as conn:
        rindas = conn.execute(
            """
            SELECT l.id AS darbinieks_id, l.vards,
                (SELECT COUNT(*) FROM mijiedarbibas m WHERE m.darbinieks_id = l.id AND m.datums BETWEEN ? AND ? AND m.veids = 'zvans') AS zvani,
                (SELECT COUNT(*) FROM mijiedarbibas m WHERE m.darbinieks_id = l.id AND m.datums BETWEEN ? AND ? AND m.veids = 'e-pasts') AS epasti,
                (SELECT COUNT(*) FROM mijiedarbibas m WHERE m.darbinieks_id = l.id AND m.datums BETWEEN ? AND ? AND m.veids = 'tikšanās') AS tiksanas,
                (SELECT COUNT(*) FROM pieprasijumi p WHERE p.atbildigais_id = l.id AND p.statuss != 'Atbildēts') AS atverti_pieprasijumi,
                (SELECT COUNT(*) FROM pieprasijumi p WHERE p.atbildigais_id = l.id AND p.statuss != 'Atbildēts' AND p.termins < ?) AS kaveti_pieprasijumi,
                (SELECT COUNT(*) FROM uzdevumi u WHERE u.atbildigais_id = l.id AND u.izpildits = 0) AS neizpilditi_uzdevumi,
                (SELECT COUNT(*) FROM uzdevumi u WHERE u.atbildigais_id = l.id AND u.izpildits = 0 AND u.termins < ?) AS kaveti_uzdevumi
            FROM lietotaji l ORDER BY l.vards
            """,
            (no.isoformat(), sodien) * 3 + (sodien, sodien),
        ).fetchall()
    darbinieki = [DarbiniekaRaditaji(**dict(r), mijiedarbibas=r["zvani"] + r["epasti"] + r["tiksanas"]) for r in rindas]
    summas = {
        lauks: sum(getattr(d, lauks) for d in darbinieki)
        for lauks in DarbiniekaRaditaji.model_fields
        if lauks not in ("darbinieks_id", "vards")
    }
    kopa = DarbiniekaRaditaji(darbinieks_id=0, vards="Kopā", **summas)
    return Parskats(no=no, lidz=lidz, dienas=dienas, darbinieki=darbinieki, kopa=kopa)


@router.get("/parskats")
def parskata_lapa(
    request: Request, vaditajs: Vaditajs, dienas: Annotated[int, Query(ge=1, le=366)] = 30
) -> Response:
    dati = parskats(dienas)
    if gaida_html(request):
        return veidne(request, "parskats/parskats.html", {"p": dati, "periodi": PERIODI, "veidi": VEIDU_NOSAUKUMI})
    return Response(dati.model_dump_json(), media_type="application/json")
