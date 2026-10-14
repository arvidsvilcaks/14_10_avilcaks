"""Kļūdu atbildes pēc līguma kopīgās `Error` shēmas un HTML kļūdu lapas."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import ValidationError
from starlette.exceptions import HTTPException

KODI = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
}

ISSUE = {
    "missing": "REQUIRED",
    "string_too_short": "TOO_SHORT",
    "string_too_long": "TOO_LONG",
    "literal_error": "INVALID_VALUE",
    "enum": "INVALID_VALUE",
    "int_parsing": "INVALID_FORMAT",
    "int_type": "INVALID_FORMAT",
    "date_parsing": "INVALID_FORMAT",
    "date_from_datetime_parsing": "INVALID_FORMAT",
    "date_type": "INVALID_FORMAT",
    "bool_parsing": "INVALID_FORMAT",
    "string_type": "INVALID_FORMAT",
}


def _zinojums(kluda: dict[str, Any]) -> str:
    tips = kluda["type"]
    ctx = kluda.get("ctx") or {}
    if tips == "missing":
        return "Lauks ir obligāts."
    if tips == "string_too_short":
        if ctx.get("min_length", 1) <= 1:
            return "Lauks nedrīkst būt tukšs."
        return f"Jābūt vismaz {ctx['min_length']} rakstzīmēm."
    if tips == "string_too_long":
        return f"Ne vairāk kā {ctx.get('max_length')} rakstzīmes."
    if tips in ("literal_error", "enum"):
        return "Izvēlieties vienu no piedāvātajām vērtībām."
    if tips in ("int_parsing", "int_type"):
        return "Jānorāda vesels skaitlis."
    if tips.startswith("date"):
        return "Datums jānorāda formātā GGGG-MM-DD."
    return kluda["msg"]


class Validacija(Exception):
    """Ievades kļūda. `forma` norāda, vai ievade nāca no HTML formas."""

    def __init__(self, kludas: list[dict[str, str]], forma: bool = False, ievade: dict | None = None):
        self.kludas = kludas
        self.forma = forma
        self.ievade = ievade or {}

    @classmethod
    def no_pydantic(cls, exc: ValidationError, forma: bool, ievade: dict) -> "Validacija":
        kludas = []
        for kluda in exc.errors():
            lauks = ".".join(str(p) for p in kluda["loc"]) or "body"
            issue = ISSUE.get(kluda["type"], kluda["type"].upper())
            kludas.append({"field": lauks, "issue": issue, "message": _zinojums(kluda)})
        return cls(kludas, forma, ievade)

    @classmethod
    def lauks(cls, lauks: str, issue: str, zinojums: str, forma: bool = False, ievade: dict | None = None) -> "Validacija":
        return cls([{"field": lauks, "issue": issue, "message": zinojums}], forma, ievade)

    def lauku_kludas(self) -> dict[str, str]:
        rezultats: dict[str, str] = {}
        for kluda in self.kludas:
            rezultats.setdefault(kluda["field"], kluda["message"])
        return rezultats


class NavPieslegts(Exception):
    pass


def gaida_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "")


def kludas_atbilde(status: int, zinojums: str, details: list[dict] | None = None) -> JSONResponse:
    kluda: dict[str, Any] = {"code": KODI.get(status, "ERROR"), "message": zinojums}
    if details is not None:
        kluda["details"] = details
    return JSONResponse({"error": kluda}, status_code=status)


def registret(app: FastAPI) -> None:
    from crm.sabloni import veidne

    @app.exception_handler(HTTPException)
    async def http_kluda(request: Request, exc: HTTPException) -> Response:
        if gaida_html(request):
            return veidne(request, "kluda.html", {"status": exc.status_code, "zinojums": exc.detail}, exc.status_code)
        return kludas_atbilde(exc.status_code, str(exc.detail))

    @app.exception_handler(Validacija)
    async def validacijas_kluda(request: Request, exc: Validacija) -> Response:
        details = [{"field": k["field"], "issue": k["issue"]} for k in exc.kludas]
        return kludas_atbilde(422, "Ievades dati nav derīgi", details)

    @app.exception_handler(RequestValidationError)
    async def pieprasijuma_kluda(request: Request, exc: RequestValidationError) -> Response:
        details = [
            {"field": ".".join(str(p) for p in k["loc"]), "issue": ISSUE.get(k["type"], k["type"].upper())}
            for k in exc.errors()
        ]
        return kludas_atbilde(422, "Ievades dati nav derīgi", details)

    @app.exception_handler(NavPieslegts)
    async def nav_pieslegts(request: Request, exc: NavPieslegts) -> Response:
        if gaida_html(request):
            return RedirectResponse("/auth/login", status_code=303)
        return kludas_atbilde(401, "Nepieciešama pieslēgšanās")
