"""MI-2: organizāciju prioritizācija „pēc sadarbības potenciāla”.

Lēmums: nevis apmācīts modelis, bet caurskatāms, izskaidrojams punktu aprēķins
pēc CRM datiem. Katram rādītājam redzams ieguldījums punktos. Rezultāts ir tikai
ieteikums darba secībai — sistēma nepieņem automatizētus lēmumus par
organizācijām vai personām, un aprēķinā neizmanto kontaktpersonu datus (N2).
Darbinieks redz savas organizācijas, vadītājs — visas (N3).
"""

from datetime import date, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from crm import laiks
from crm.auth import Pieslegts
from crm.db import savienojums
from crm.kludas import gaida_html
from crm.sabloni import veidne

router = APIRouter()

PERIODA_DIENAS = 90
# (rādītājs, punkti par vienību, paskaidrojums)
SVARI = {
    "mijiedarbibas": (2, "par katru mijiedarbību pēdējās 90 dienās"),
    "tiksanas": (3, "papildus par katru tikšanos pēdējās 90 dienās"),
    "atverti_pieprasijumi": (4, "par katru atvērto pieprasījumu"),
    "atbildeti_pieprasijumi": (1, "par katru atbildēto pieprasījumu"),
}
SVAIGUMA_PUNKTI = ((14, 5), (30, 2))  # pēdējā mijiedarbība ne senāk par N dienām → punkti


class Prioritate(BaseModel):
    organizacija_id: int
    nosaukums: str
    atbildigais_vards: str
    mijiedarbibas: int
    tiksanas: int
    atverti_pieprasijumi: int
    atbildeti_pieprasijumi: int
    pedeja_mijiedarbiba: date | None
    punkti: int
    pamatojums: list[str]


def _svaiguma_punkti(pedeja: date | None, sodien: date) -> int:
    if pedeja is None:
        return 0
    for dienas, punkti in SVAIGUMA_PUNKTI:
        if (sodien - pedeja).days <= dienas:
            return punkti
    return 0


def aprekinat(atbildigais_id: int | None) -> list[Prioritate]:
    sodien = laiks.sodien()
    no = (sodien - timedelta(days=PERIODA_DIENAS - 1)).isoformat()
    vaicajums = """
        SELECT o.id AS organizacija_id, o.nosaukums, l.vards AS atbildigais_vards,
            (SELECT COUNT(*) FROM mijiedarbibas m WHERE m.organizacija_id = o.id AND m.datums >= ?) AS mijiedarbibas,
            (SELECT COUNT(*) FROM mijiedarbibas m WHERE m.organizacija_id = o.id AND m.datums >= ? AND m.veids = 'tikšanās') AS tiksanas,
            (SELECT COUNT(*) FROM pieprasijumi p WHERE p.organizacija_id = o.id AND p.statuss != 'Atbildēts') AS atverti_pieprasijumi,
            (SELECT COUNT(*) FROM pieprasijumi p WHERE p.organizacija_id = o.id AND p.statuss = 'Atbildēts') AS atbildeti_pieprasijumi,
            (SELECT MAX(m.datums) FROM mijiedarbibas m WHERE m.organizacija_id = o.id) AS pedeja_mijiedarbiba
        FROM organizacijas o JOIN lietotaji l ON l.id = o.atbildigais_id
    """
    parametri: list = [no, no]
    if atbildigais_id is not None:
        vaicajums += " WHERE o.atbildigais_id = ?"
        parametri.append(atbildigais_id)
    with savienojums() as conn:
        rindas = conn.execute(vaicajums, parametri).fetchall()
    rezultats = []
    for r in rindas:
        pedeja = date.fromisoformat(r["pedeja_mijiedarbiba"]) if r["pedeja_mijiedarbiba"] else None
        pamatojums, punkti = [], 0
        for raditajs, (svars, apraksts) in SVARI.items():
            if r[raditajs]:
                punkti += r[raditajs] * svars
                pamatojums.append(f"+{r[raditajs] * svars} — {r[raditajs]} × {svars} {apraksts}")
        svaigums = _svaiguma_punkti(pedeja, sodien)
        if svaigums:
            punkti += svaigums
            pamatojums.append(f"+{svaigums} — nesens kontakts ({(sodien - pedeja).days} dienas kopš pēdējās mijiedarbības)")
        rezultats.append(Prioritate(**dict(r) | {"pedeja_mijiedarbiba": pedeja}, punkti=punkti, pamatojums=pamatojums))
    return sorted(rezultats, key=lambda p: (-p.punkti, p.nosaukums))


@router.get("/prioritates")
def prioritates(request: Request, lietotajs: Pieslegts) -> Response:
    saraksts = aprekinat(None if lietotajs.ir_vaditajs else lietotajs.id)
    if gaida_html(request):
        konteksts = {"prioritates": saraksts, "svari": SVARI, "svaigums": SVAIGUMA_PUNKTI, "dienas": PERIODA_DIENAS}
        return veidne(request, "prioritates.html", konteksts)
    return JSONResponse([p.model_dump(mode="json") for p in saraksts])
