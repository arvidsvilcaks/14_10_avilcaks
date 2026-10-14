---
id: CR-7
type: change-request
title: "Mijiedarbību žurnāls (F3)"
status: READY
priority: medium
reporter: "Prasību analītiķis"
owner: "@<github-lietotājvārds>"
contract: "docs/openapi.yaml · POST /mijiedarbibas, GET /mijiedarbibas, GET /organizacijas/{id}/mijiedarbibas"
depends_on: [CR-6]
exported: "2026-10-14 · Ezermalas pieteikumu sistēma (simulācija)"
data_check: "Nav personas datu, piekļuves datu, iekšējo adrešu vai pielikumu. Atbildētāji norādīti ar lomu."
---

# CR-7 · Mijiedarbību žurnāls (F3)

> Noteikumi vienkāršoti mācību vajadzībām.

## Apraksts (description)

Darbinieks pieraksta katru saziņu ar organizāciju: zvanu, e-pastu vai tikšanos. Žurnāls parāda sadarbības vēsturi organizācijas kartītē, un F9 rāda pēdējās mijiedarbības un to skaitu šonedēļ.

Lauki: datums, veids, organizācija, darbinieks (pieslēgtais lietotājs), kopsavilkums.

## Pieņemšanas kritēriji (acceptance criteria)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 1 | Darbinieks pievieno mijiedarbību ar derīgiem laukiem | Atbilde 201; darbinieks ir pieslēgtais lietotājs |
| 2 | Veids nav „zvans”, „e-pasts” vai „tikšanās” | Atbilde 422 |
| 3 | Neeksistējoša organizācija | Atbilde 422 (vai 404) |
| 4 | Datums nākotnē | Atbilde 422 |
| 5 | Pieprasījumā norādīts cits darbinieks | Tiek ignorēts; saglabā pieslēgto lietotāju |
| 6 | Atver organizācijas kartīti | Mijiedarbības sakārtotas no jaunākās |
| 7 | Darbinieks pieprasa sarakstu | Redz tikai savas mijiedarbības; vadītājs redz visas |
| 8 | Saraksta filtrs „šonedēļ” (Europe/Riga, pirmdiena–svētdiena) | Tikai šīs nedēļas ieraksti |
| 9 | Sākumdati | 30 mijiedarbības, arī pēdējo 7 dienu laikā |

## Precizējumi (clarifications)

| Jautājums | Atbilde | Kas atbildēja, kad |
|---|---|---|
| Tehnoloģija: FastAPI vai Flask (sk. CR-4)? | FastAPI | Produkta īpašnieks, 2026-10-14 |
| Vai mijiedarbību var labot vai dzēst pēc pievienošanas? | Nē, šajā pieteikumā ne (ārpus apjoma) | Produkta īpašnieks (deleģēts MI aģentam), 2026-10-14 |
| Vai darbinieks drīkst pievienot mijiedarbību citam darbiniekam piešķirtai organizācijai? | Jā; mijiedarbība pieder tās autoram | Produkta īpašnieks (deleģēts MI aģentam), 2026-10-14 |
| Kopsavilkuma maksimālais garums? | 2000 simboli; garākam — 422 | Produkta īpašnieks (deleģēts MI aģentam), 2026-10-14 |

## Ārpus apjoma (out of scope)

- MI kopsavilkums un nākamā soļa ieteikums (MI-1)
- Saistība ar kontaktpersonu (F2)

## Komentāri (comments)

- 
