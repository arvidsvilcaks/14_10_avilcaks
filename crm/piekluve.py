"""N2: piekļuves žurnāls — kurš un kad skatīja organizācijas kartīti ar kontaktpersonu datiem.

Ieraksti tiek glabāti `db.ZURNALA_GLABASANAS_DIENAS` dienas; žurnālu redz tikai vadītājs.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from crm.auth import Vaditajs
from crm.db import savienojums
from crm.kludas import gaida_html
from crm.sabloni import veidne

router = APIRouter()

ZURNALA_LIMITS = 200


def ierakstit(lietotajs_id: int, organizacija_id: int) -> None:
    with savienojums() as conn:
        conn.execute(
            "INSERT INTO piekluves_zurnals (lietotajs_id, organizacija_id) VALUES (?, ?)", (lietotajs_id, organizacija_id)
        )


def pedejie(limits: int = ZURNALA_LIMITS) -> list[dict]:
    with savienojums() as conn:
        rindas = conn.execute(
            """
            SELECT z.id, z.laiks, z.lietotajs_id, l.vards AS lietotaja_vards, z.organizacija_id, o.nosaukums AS organizacijas_nosaukums
            FROM piekluves_zurnals z
            JOIN lietotaji l ON l.id = z.lietotajs_id
            JOIN organizacijas o ON o.id = z.organizacija_id
            ORDER BY z.id DESC LIMIT ?
            """,
            (limits,),
        ).fetchall()
    return [dict(r) for r in rindas]


@router.get("/piekluves-zurnals", include_in_schema=False)
def zurnals(request: Request, vaditajs: Vaditajs) -> Response:
    ieraksti = pedejie()
    if gaida_html(request):
        return veidne(request, "piekluves_zurnals.html", {"ieraksti": ieraksti, "limits": ZURNALA_LIMITS})
    return JSONResponse(ieraksti)
