"""CR-5: lomas „Darbinieks” un „Vadītājs” (N3)."""

import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import BaseModel

from crm.auth import Loma, Pieslegts, Vaditajs, lietotajs_pec_id
from crm.db import savienojums
from crm.ievade import nolasit

router = APIRouter()


class LomasMaina(BaseModel):
    loma: Loma


def macibu_rezims() -> bool:
    return os.environ.get("CRM_MACIBU_REZIMS") == "1"


@router.patch("/lietotaji/{lietotaja_id}/loma")
async def mainit_lomu(request: Request, lietotaja_id: int, vaditajs: Vaditajs) -> Response:
    dati, _ = await nolasit(request, LomasMaina)
    merkis = lietotajs_pec_id(lietotaja_id)
    if merkis is None:
        raise HTTPException(404, "Lietotājs nav atrasts")
    with savienojums() as conn:
        if merkis.ir_vaditajs and dati.loma != "vaditajs":
            vaditaji = conn.execute("SELECT COUNT(*) FROM lietotaji WHERE loma = 'vaditajs'").fetchone()[0]
            if vaditaji <= 1:
                raise HTTPException(409, "Sistēmā jāpaliek vismaz vienam vadītājam")
        conn.execute("UPDATE lietotaji SET loma = ? WHERE id = ?", (dati.loma, lietotaja_id))
    return JSONResponse(lietotajs_pec_id(lietotaja_id).model_dump())


@router.post("/macibu-rezims/loma")
async def parslegt_lomu(request: Request, lietotajs: Pieslegts) -> Response:
    if not macibu_rezims():
        raise HTTPException(403, "Lomu var pārslēgt tikai mācību režīmā")
    dati, forma = await nolasit(request, LomasMaina)
    with savienojums() as conn:
        conn.execute("UPDATE lietotaji SET loma = ? WHERE id = ?", (dati.loma, lietotajs.id))
    if forma:
        return RedirectResponse("/panelis", status_code=303)
    return JSONResponse(lietotajs_pec_id(lietotajs.id).model_dump())
