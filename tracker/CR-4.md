---
id: CR-4
type: change-request
title: "Pieslēgšanās, reģistrēšanās un atteikšanās (F0)"
status: READY
priority: high
reporter: "Prasību analītiķis"
owner: "@<github-lietotājvārds>"
contract: "docs/openapi.yaml · POST /auth/register, POST /auth/login, POST /auth/logout"
depends_on: []
exported: "2026-10-14 · Ezermalas pieteikumu sistēma (simulācija)"
data_check: "Nav personas datu, piekļuves datu, iekšējo adrešu vai pielikumu. Atbildētāji norādīti ar lomu."
---

# CR-4 · Pieslēgšanās, reģistrēšanās un atteikšanās (F0)

> Noteikumi vienkāršoti mācību vajadzībām.

## Apraksts (description)

CRM lietotājam jāvar izveidot kontu, pieslēgties un atslēgties. Bez pieslēgšanās sistēmas dati nav pieejami. Pēc pieslēgšanās lietotājs nonāk savā vadības panelī (F9). Prasība ir priekšnoteikums lomām (N3) un visām pārējām funkcijām.

## Pieņemšanas kritēriji (acceptance criteria)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 1 | Reģistrācija ar vārdu, derīgu e-pastu un paroli, kas atbilst garuma prasībai | Konts izveidots; atbilde 201; parole netiek atgriezta |
| 2 | Reģistrācija ar jau reģistrētu e-pastu (arī ar citiem lielajiem/mazajiem burtiem) | Atbilde 409; otrs konts netiek izveidots |
| 3 | Reģistrācija ar nederīgu e-pastu vai tukšu vārdu | Atbilde 422 ar lauka nosaukumu |
| 4 | Reģistrācija ar par īsu paroli | Atbilde 422 |
| 5 | Pieslēgšanās ar pareizu e-pastu un paroli | Izveidota sesija; lietotājs tiek novirzīts uz `/panelis` (F9.1) |
| 6 | Pieslēgšanās ar nepareizu paroli vai nezināmu e-pastu | Atbilde 401; abos gadījumos vienāds ziņojums |
| 7 | Atteikšanās | Sesija dzēsta; nākamais pieprasījums uz aizsargātu lapu novirza uz pieslēgšanās lapu |
| 8 | Nepieslēgts lietotājs atver aizsargātu lapu (piem., `/panelis`) | Novirza uz pieslēgšanās lapu (F9.2) |
| 9 | Pārbauda datubāzi un žurnālus pēc reģistrācijas | Parole glabāta tikai kā sāļota jaucējvērtība; žurnālos paroles nav |
| 10 | Pieslēgts lietotājs atver `/` | Novirza uz `/panelis` |

## Precizējumi (clarifications)

| Jautājums | Atbilde | Kas atbildēja, kad |
|---|---|---|
| Tehnoloģija: FastAPI (kā līgums un `Makefile`) vai Flask + Jinja2 (kā `docs/F9.md` N4)? | FastAPI; HTML lapas ar Jinja2 šabloniem | Produkta īpašnieks, 2026-10-14 |
| Vai reģistrēties var jebkurš, vai kontus izveido vadītājs? | Jebkurš; jauns konts vienmēr saņem lomu „Darbinieks” (CR-5) | Produkta īpašnieks (deleģēts MI aģentam), 2026-10-14 |
| Minimālais paroles garums (ieteikums: 12 simboli)? | 12 simboli | Produkta īpašnieks (deleģēts MI aģentam), 2026-10-14 |
| Sesijas derīguma laiks? | 8 stundas; parakstīta sīkdatne `HttpOnly`, `SameSite=Lax`; sesijā glabā tikai lietotāja ID, lomu nolasa no datubāzes katrā pieprasījumā | Produkta īpašnieks (deleģēts MI aģentam), 2026-10-14 |
| Vai `experiments/auth/` kodu drīkst izmantot par pamatu? | Jā, bez `users.db`; eksperimenta mapi pēc pārnešanas dzēš | Produkta īpašnieks (deleģēts MI aģentam), 2026-10-14 |

## Ārpus apjoma (out of scope)

- Paroles atjaunošana un e-pasta apstiprināšana
- Divfaktoru autentifikācija, SSO
- Lomu piešķiršana un maiņa (CR-5)
- Vadības paneļa saturs (CR-10)

## Komentāri (comments)

- Esošais eksperiments `experiments/auth/` satur `users.db` ar testa lietotājiem — to nedrīkst iekļaut repozitorijā.
