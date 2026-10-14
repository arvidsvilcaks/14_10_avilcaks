"""F8: piekļūstamības paziņojums (publiski pieejams, bez pieslēgšanās)."""

from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import Response

from crm.sabloni import veidne

router = APIRouter()

SAGATAVOTS = date(2026, 10, 14)
PARSKATITS = date(2026, 10, 14)


@router.get("/pieejamiba", include_in_schema=False)
def pazinojums(request: Request) -> Response:
    return veidne(request, "pieejamiba.html", {"sagatavots": SAGATAVOTS, "parskatits": PARSKATITS})
