"""CR-10: kopsavilkuma ekrāns — vadības panelis (F9).

Saturu filtrē serverī pēc pieslēgtā lietotāja un viņa lomas (F9.3); URL un
formas parametri to neietekmē.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import Response
from pydantic import BaseModel

from crm import laiks, mijiedarbibas, pieprasijumi, uzdevumi
from crm.auth import Lietotajs, Pieslegts
from crm.db import savienojums
from crm.mijiedarbibas import Veids
from crm.pieprasijumi import Pieprasijums
from crm.sabloni import veidne
from crm.uzdevumi import IZPILDITS_PAZINOJUMS, Uzdevums

router = APIRouter()

TUVAKO_DIENU_SKAITS = 3
PEDEJO_MIJIEDARBIBU_SKAITS = 5
AKTIVITATES_DIENAS = 7


class Raditaji(BaseModel):
    uzdevumi_sodien: int
    kaveti_pieprasijumi: int
    pieprasijumi_darba: int
    mijiedarbibas_sonedel: int


class PanelaMijiedarbiba(BaseModel):
    """Mijiedarbība panelī — bez kopsavilkuma teksta (N2)."""

    id: int
    datums: date
    veids: Veids
    organizacija_id: int
    organizacijas_nosaukums: str
    darbinieks_id: int
    darbinieka_vards: str


class DarbiniekaAktivitate(BaseModel):
    darbinieks_id: int
    vards: str
    mijiedarbibas: int
    atverti_pieprasijumi: int
    kaveti_pieprasijumi: int


class PanelisAtbilde(BaseModel):
    lietotajs: Lietotajs
    sodien: date
    raditaji: Raditaji
    uzdevumi: list[Uzdevums]
    pieprasijumi: list[Pieprasijums]
    mijiedarbibas: list[PanelaMijiedarbiba]
    aktivitate: list[DarbiniekaAktivitate] | None


def aktivitate_pa_darbiniekiem(dienas: int = AKTIVITATES_DIENAS) -> list[DarbiniekaAktivitate]:
    sodien = laiks.sodien()
    no = (sodien - timedelta(days=dienas - 1)).isoformat()
    with savienojums() as conn:
        rindas = conn.execute(
            """
            SELECT l.id AS darbinieks_id, l.vards,
                (SELECT COUNT(*) FROM mijiedarbibas m
                 WHERE m.darbinieks_id = l.id AND m.datums BETWEEN ? AND ?) AS mijiedarbibas,
                (SELECT COUNT(*) FROM pieprasijumi p
                 WHERE p.atbildigais_id = l.id AND p.statuss != 'Atbildēts') AS atverti_pieprasijumi,
                (SELECT COUNT(*) FROM pieprasijumi p
                 WHERE p.atbildigais_id = l.id AND p.statuss != 'Atbildēts' AND p.termins < ?) AS kaveti_pieprasijumi
            FROM lietotaji l
            ORDER BY l.vards
            """,
            (no, sodien.isoformat(), sodien.isoformat()),
        ).fetchall()
    return [DarbiniekaAktivitate(**dict(r)) for r in rindas]


def panela_dati(lietotajs: Lietotajs) -> PanelisAtbilde:
    filtrs = None if lietotajs.ir_vaditajs else lietotajs.id
    sodien = laiks.sodien()
    no, lidz = mijiedarbibas.sonedel()
    raditaji = Raditaji(
        uzdevumi_sodien=len(uzdevumi.atlasit(filtrs, lidz_sodienai=True)),
        kaveti_pieprasijumi=len(pieprasijumi.atlasit(filtrs, kavets=True)),
        pieprasijumi_darba=len(pieprasijumi.atlasit(filtrs, statuss="Darbā")),
        mijiedarbibas_sonedel=len(mijiedarbibas.atlasit(filtrs, no, lidz)),
    )
    pedejas = mijiedarbibas.atlasit(filtrs, limits=PEDEJO_MIJIEDARBIBU_SKAITS)
    return PanelisAtbilde(
        lietotajs=lietotajs,
        sodien=sodien,
        raditaji=raditaji,
        uzdevumi=uzdevumi.atlasit(lietotajs.id, lidz_sodienai=True),
        pieprasijumi=pieprasijumi.atlasit(
            filtrs, termins_lidz=sodien + timedelta(days=TUVAKO_DIENU_SKAITS), neatbildeti=True
        ),
        mijiedarbibas=[PanelaMijiedarbiba(**m.model_dump(exclude={"kopsavilkums"})) for m in pedejas],
        aktivitate=aktivitate_pa_darbiniekiem() if lietotajs.ir_vaditajs else None,
    )


@router.get("/panelis", name="panelis", include_in_schema=False)
def panelis(request: Request, lietotajs: Pieslegts, pazinojums: str | None = None) -> Response:
    konteksts = {
        "dati": panela_dati(lietotajs),
        "veidi": mijiedarbibas.VEIDU_NOSAUKUMI,
        "izpildits_pazinojums": pazinojums == IZPILDITS_PAZINOJUMS,
    }
    return veidne(request, "panelis.html", konteksts)


@router.get("/api/panelis")
def api_panelis(lietotajs: Pieslegts) -> PanelisAtbilde:
    return panela_dati(lietotajs)
