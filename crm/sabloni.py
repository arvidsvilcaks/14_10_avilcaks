"""Jinja2 šabloni un to palīgfunkcijas."""

from datetime import date
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

from crm.db import SAKNE

veidnes = Jinja2Templates(directory=SAKNE / "templates")


def veidne(request: Request, nosaukums: str, konteksts: dict[str, Any] | None = None, status_code: int = 200) -> Response:
    dati = {"lietotajs": getattr(request.state, "lietotajs", None), "kludas": {}, "ievade": {}}
    dati.update(konteksts or {})
    return veidnes.TemplateResponse(request, nosaukums, dati, status_code=status_code)


def _datums(vertiba: date | str | None) -> str:
    if not vertiba:
        return ""
    if isinstance(vertiba, str):
        vertiba = date.fromisoformat(vertiba[:10])
    return vertiba.strftime("%d.%m.%Y")


veidnes.env.filters["datums"] = _datums
