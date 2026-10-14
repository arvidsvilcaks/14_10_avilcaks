---
id: CR-5
type: change-request
title: "Lomas „Darbinieks” un „Vadītājs” (N3)"
status: READY
priority: high
reporter: "Prasību analītiķis"
owner: "@<github-lietotājvārds>"
contract: "docs/openapi.yaml · PATCH /lietotaji/{id}/loma, POST /macibu-rezims/loma"
depends_on: [CR-4]
exported: "2026-10-14 · Ezermalas pieteikumu sistēma (simulācija)"
data_check: "Nav personas datu, piekļuves datu, iekšējo adrešu vai pielikumu. Atbildētāji norādīti ar lomu."
---

# CR-5 · Lomas „Darbinieks” un „Vadītājs” (N3)

> Noteikumi vienkāršoti mācību vajadzībām.

## Apraksts (description)

Sistēmā ir divas lomas. Darbinieks strādā tikai ar saviem datiem, vadītājs redz visu darbinieku datus. Loma nosaka, ko lietotājs redz un drīkst darīt; to pārbauda serverī katrā pieprasījumā, nevis tikai paslēpj ekrānā (F9.3). Mācību režīmā lietotājs var pārslēgt savu lomu, lai izmēģinātu abus skatus (F9.12).

## Pieņemšanas kritēriji (acceptance criteria)

| # | Ievade | Sagaidāmais rezultāts |
|---|---|---|
| 1 | Jauns lietotājs reģistrējas | Loma ir „Darbinieks” |
| 2 | Vadītājs maina cita lietotāja lomu | Loma mainīta; atbilde 200 |
| 3 | Darbinieks mēģina mainīt savu vai cita lomu | Atbilde 403; loma nemainās |
| 4 | Lomas vērtība nav „darbinieks” vai „vaditajs” | Atbilde 422 |
| 5 | Lietotāja loma datubāzē mainīta, kamēr viņam ir aktīva sesija | Nākamais pieprasījums izmanto jauno lomu |
| 6 | Mācību režīms ieslēgts; lietotājs pārslēdz savu lomu | Nākamajā pieprasījumā redz jaunās lomas saturu |
| 7 | Mācību režīms izslēgts; lietotājs mēģina pārslēgt lomu | Atbilde 403 (vai 404); loma nemainās |
| 8 | Sistēma tiek palaista pirmo reizi | Ir vismaz viens vadītājs (no sākumdatiem vai konfigurācijas) |

## Precizējumi (clarifications)

| Jautājums | Atbilde | Kas atbildēja, kad |
|---|---|---|
| Tehnoloģija: FastAPI vai Flask (sk. CR-4)? | FastAPI | Produkta īpašnieks, 2026-10-14 |
| Kā ieslēdz „mācību režīmu” — vides mainīgais, konfigurācija? | Vides mainīgais `CRM_MACIBU_REZIMS=1`; pēc noklusējuma izslēgts | Produkta īpašnieks (deleģēts MI aģentam), 2026-10-14 |
| Kā tiek izveidots pirmais vadītājs? | Sākumdatu skripts izveido vadītāju; paroli ņem no vides mainīgā `CRM_SAKUMDATU_PAROLE`, repozitorijā paroles nav | Produkta īpašnieks (deleģēts MI aģentam), 2026-10-14 |
| Vai vadītājs var noņemt vadītāja lomu pats sev, ja viņš ir vienīgais? | Nē; atbilde 409 | Produkta īpašnieks (deleģēts MI aģentam), 2026-10-14 |

## Ārpus apjoma (out of scope)

- Vairāk nekā divas lomas, detalizētas tiesības
- Lietotāju administrēšanas lapa (izņemot lomas maiņu)

## Komentāri (comments)

- 
