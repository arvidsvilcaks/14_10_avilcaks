"""Vienots JSON un HTML formu ievades nolasījums."""

from typing import TypeVar

from fastapi import HTTPException, Request
from pydantic import BaseModel, ValidationError

from crm.kludas import Validacija

M = TypeVar("M", bound=BaseModel)

FORMU_TIPI = ("application/x-www-form-urlencoded", "multipart/form-data")


def ir_forma(request: Request) -> bool:
    return request.headers.get("content-type", "").startswith(FORMU_TIPI)


async def nolasit(request: Request, modelis: type[M]) -> tuple[M, bool]:
    """Nolasa un validē ievadi. Atgriež (dati, vai ievade nāca no HTML formas).

    Formas tukšie lauki tiek uzskatīti par nenorādītiem.
    """
    forma = ir_forma(request)
    if forma:
        ievade = {k: v for k, v in (await request.form()).items() if isinstance(v, str) and v.strip() != ""}
    else:
        try:
            ievade = await request.json()
        except ValueError:
            raise HTTPException(400, "Pieprasījuma ķermenis nav derīgs JSON") from None
        if not isinstance(ievade, dict):
            raise HTTPException(400, "Pieprasījuma ķermenim jābūt JSON objektam")
    try:
        return modelis.model_validate(ievade), forma
    except ValidationError as exc:
        raise Validacija.no_pydantic(exc, forma, ievade) from None
