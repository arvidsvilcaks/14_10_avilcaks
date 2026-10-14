"""Vadības panelis. CR-4 tikai sākumlapa pēc pieslēgšanās; saturu pievieno CR-10."""

from fastapi import APIRouter, Request
from fastapi.responses import Response

from crm.auth import Pieslegts
from crm.sabloni import veidne

router = APIRouter()


@router.get("/panelis", name="panelis", include_in_schema=False)
def panelis(request: Request, lietotajs: Pieslegts) -> Response:
    return veidne(request, "panelis.html")
