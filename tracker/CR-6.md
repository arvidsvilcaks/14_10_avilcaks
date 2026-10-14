---
id: CR-6
type: change-request
title: "Organizācijas: izveidot, rediģēt, meklēt (F1)"
status: READY
priority: high
reporter: "Prasību analītiķis"
owner: "@<github-lietotājvārds>"
contract: "docs/openapi.yaml · POST /organizacijas, GET /organizacijas, GET /organizacijas/{id}, PATCH /organizacijas/{id}"
depends_on: [CR-5]
exported: "2026-10-14 · Ezermalas pieteikumu sistēma (simulācija)"
data_check: "Nav personas datu, piekļuves datu, iekšējo adrešu vai pielikumu. Atbildētāji norādīti ar lomu."
---

# CR-6 · Organizācijas: izveidot, rediģēt, meklēt (F1)

> Noteikumi vienkāršoti mācību vajadzībām.

## Apraksts (description)

Organizācija ir CRM pamatieraksts, pie kura piesaista mijiedarbības (F3) un pieprasījumus (F4). Katrai organizācijai ir viens atbildīgais darbinieks. Organizācijas kartīte ir mērķis F9 saitēm (F9.8).

Minimālie lauki: nosaukums, reģistrācijas numurs (nav obligāts), atbildīgais darbinieks.

## Pieņemšanas kritēriji (acceptance criteria)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 1 | Darbinieks izveido organizāciju ar nosaukumu | Atbilde 201; atbildīgais ir izveidotājs |
| 2 | Izveide bez nosaukuma vai ar tikai atstarpēm | Atbilde 422 |
| 3 | Izveide ar jau esošu reģistrācijas numuru | Atbilde 409 |
| 4 | Atbildīgais darbinieks rediģē savu organizāciju | Izmaiņas saglabātas |
| 5 | Darbinieks rediģē organizāciju, kurai atbildīgais ir cits | Atbilde 403 |
| 6 | Vadītājs maina organizācijas atbildīgo darbinieku | Izmaiņas saglabātas |
| 7 | Meklēšana ar nosaukuma daļu, neatkarīgi no lielajiem burtiem un garumzīmēm | Saraksts ar atbilstošajām organizācijām |
| 8 | Meklēšana bez rezultātiem | Tukšs saraksts ar paskaidrojumu, nevis kļūda |
| 9 | Atver `/organizacijas/{id}` neeksistējošam ID | Atbilde 404 |
| 10 | Sākumdati | 10 organizācijas, sadalītas starp vismaz 2 darbiniekiem |

## Precizējumi (clarifications)

| Jautājums | Atbilde | Kas atbildēja, kad |
|---|---|---|
| Tehnoloģija: FastAPI vai Flask (sk. CR-4)? | FastAPI | Produkta īpašnieks, 2026-10-14 |
| Vai darbinieks drīkst skatīt (ne rediģēt) citu darbinieku organizācijas? | Jā, skatīt drīkst; rediģēt tikai savas (vadītājs — visas) | Produkta īpašnieks (deleģēts MI aģentam), 2026-10-14 |
| Vai organizāciju var dzēst? | Nē, šajā pieteikumā ne (ārpus apjoma) | Produkta īpašnieks (deleģēts MI aģentam), 2026-10-14 |
| Vai meklējot jāņem vērā garumzīmes („Rīga” = „Riga”)? | Nē — meklēšana neatkarīga no garumzīmēm un lielajiem burtiem | Produkta īpašnieks (deleģēts MI aģentam), 2026-10-14 |

## Ārpus apjoma (out of scope)

- Kontaktpersonas (F2)
- Vispārējā meklēšana pa visiem ierakstiem (F6)
- Imports no Uzņēmumu reģistra

## Komentāri (comments)

- 
