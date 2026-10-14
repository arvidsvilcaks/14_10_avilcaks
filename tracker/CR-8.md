---
id: CR-8
type: change-request
title: "Pieprasījumi no organizācijām (F4)"
status: READY
priority: medium
reporter: "Prasību analītiķis"
owner: "@<github-lietotājvārds>"
contract: "docs/openapi.yaml · POST /pieprasijumi, GET /pieprasijumi, PATCH /pieprasijumi/{id}"
depends_on: [CR-6]
exported: "2026-10-14 · Ezermalas pieteikumu sistēma (simulācija)"
data_check: "Nav personas datu, piekļuves datu, iekšējo adrešu vai pielikumu. Atbildētāji norādīti ar lomu."
---

# CR-8 · Pieprasījumi no organizācijām (F4)

> Noteikumi vienkāršoti mācību vajadzībām.

## Apraksts (description)

Organizācijas iesūta pieprasījumus, uz kuriem jāatbild līdz termiņam. Katram pieprasījumam ir atbildīgais darbinieks un statuss. Sistēma atpazīst kavētos pieprasījumus, un F9 tos izceļ.

Lauki: organizācija, apraksts, termiņš, statuss („Jauns”, „Darbā”, „Atbildēts”), atbildīgais darbinieks.

**Kavēts:** termiņš ir pirms šodienas (Europe/Riga) un statuss nav „Atbildēts” (F9.7).

## Pieņemšanas kritēriji (acceptance criteria)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 1 | Izveido pieprasījumu ar derīgiem laukiem | Atbilde 201; statuss „Jauns” |
| 2 | Bez termiņa vai ar nederīgu datumu | Atbilde 422 |
| 3 | Statusa vērtība nav no saraksta | Atbilde 422 |
| 4 | Termiņš vakar, statuss „Darbā” | Pieprasījums ir kavēts; sarakstā marķēts ar vārdu „Kavēts” |
| 5 | Termiņš šodien, statuss „Jauns” | Nav kavēts |
| 6 | Termiņš vakar, statuss „Atbildēts” | Nav kavēts |
| 7 | Saraksts ar filtru `statuss=Darbā` vai `kavets=true` | Tikai atbilstošie ieraksti (mērķis F9.5 kartītēm) |
| 8 | Darbinieks pieprasa sarakstu vai maina citam piešķirtu pieprasījumu | Redz tikai savus; maiņai atbilde 403 |
| 9 | Vadītājs pieprasa sarakstu | Redz visus, ar atbildīgā darbinieka vārdu |

## Precizējumi (clarifications)

| Jautājums | Atbilde | Kas atbildēja, kad |
|---|---|---|
| Tehnoloģija: FastAPI vai Flask (sk. CR-4)? | FastAPI | Produkta īpašnieks, 2026-10-14 |
| Vai termiņu nosaka automātiski (piem., +N darba dienas) vai ievada ar roku? | Ievada ar roku; obligāts lauks | Produkta īpašnieks (deleģēts MI aģentam), 2026-10-14 |
| Vai statuss var atgriezties no „Atbildēts” uz „Darbā”? | Jā | Produkta īpašnieks (deleģēts MI aģentam), 2026-10-14 |
| Kurš drīkst mainīt atbildīgo darbinieku? | Tikai vadītājs; darbiniekam — 403 | Produkta īpašnieks (deleģēts MI aģentam), 2026-10-14 |

## Ārpus apjoma (out of scope)

- Pieprasījumu saņemšana pa e-pastu vai no ārējas formas
- Paziņojumi par tuvojošos termiņu

## Komentāri (comments)

- 
