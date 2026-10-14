---
id: CR-9
type: change-request
title: "Uzdevumi (F5, bez atgādinājumiem)"
status: READY
priority: medium
reporter: "Prasību analītiķis"
owner: "@<github-lietotājvārds>"
contract: "docs/openapi.yaml · POST /uzdevumi, GET /uzdevumi, POST /uzdevumi/{id}/izpildits"
depends_on: [CR-5]
exported: "2026-10-14 · Ezermalas pieteikumu sistēma (simulācija)"
data_check: "Nav personas datu, piekļuves datu, iekšējo adrešu vai pielikumu. Atbildētāji norādīti ar lomu."
---

# CR-9 · Uzdevumi (F5, bez atgādinājumiem)

> Noteikumi vienkāršoti mācību vajadzībām.

## Apraksts (description)

Darbinieks plāno darbu ar uzdevumiem, kuriem ir termiņš. Uzdevumu var atzīmēt kā izpildītu. F9 rāda neizpildītos uzdevumus ar termiņu šodien vai agrāk un ļauj tos atzīmēt tieši no paneļa (F9.6).

Lauki: nosaukums, termiņš, izpildīts (jā/nē), atbildīgais darbinieks, organizācija (nav obligāta).

## Pieņemšanas kritēriji (acceptance criteria)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 1 | Izveido uzdevumu ar nosaukumu un termiņu | Atbilde 201; atbildīgais ir izveidotājs; nav izpildīts |
| 2 | Bez nosaukuma vai termiņa | Atbilde 422 |
| 3 | Atbildīgais atzīmē savu uzdevumu kā izpildītu | Uzdevums izpildīts; novirza atpakaļ (POST–redirect–GET) |
| 4 | Darbinieks atzīmē citam piešķirtu uzdevumu | Atbilde 403; uzdevums nemainās |
| 5 | Atzīmē neeksistējošu uzdevumu | Atbilde 404 |
| 6 | Atzīmē jau izpildītu uzdevumu | Bez kļūdas; stāvoklis nemainās |
| 7 | Saraksts ar filtru „līdz šodienai, neizpildītie” (Europe/Riga) | Tikai neizpildītie ar termiņu šodien vai agrāk |
| 8 | Darbinieks pieprasa sarakstu | Redz tikai savus uzdevumus |

## Precizējumi (clarifications)

| Jautājums | Atbilde | Kas atbildēja, kad |
|---|---|---|
| Tehnoloģija: FastAPI vai Flask (sk. CR-4)? | FastAPI | Produkta īpašnieks, 2026-10-14 |
| Vai vadītājs var piešķirt uzdevumu darbiniekam? | Jā; darbinieks var izveidot uzdevumu tikai sev | Produkta īpašnieks (deleģēts MI aģentam), 2026-10-14 |
| Vai izpildītu uzdevumu var atkal atvērt? | Nē, šajā pieteikumā ne (ārpus apjoma) | Produkta īpašnieks (deleģēts MI aģentam), 2026-10-14 |

## Ārpus apjoma (out of scope)

- Atgādinājumi (F5 otrā daļa) — atsevišķs pieteikums
- Atkārtoti uzdevumi

## Komentāri (comments)

- 
