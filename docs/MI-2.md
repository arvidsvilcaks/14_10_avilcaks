# MI-2 — Organizāciju prioritizācija „pēc sadarbības potenciāla”: prasības apraksts

Oct 14, 2026 · @Arvīds Vilčaks

## Pamatinformācija

Darbiniekam jāredz, ar kurām organizācijām sadarbībai šobrīd ir lielākais potenciāls, lai plānotu darba secību.

| Lauks | Vērtība |
| --- | --- |
| ID | MI-2 |
| Nosaukums | Organizāciju prioritizācija «pēc sadarbības potenciāla» |
| Veids | MI prasība |
| Statuss | Izpildīts (bez CR, 2026-10-14), kā caurskatāms noteikumu aprēķins |
| Atkarīga no | F1, F3, F4, N3 |
| Jāatbilst | N1, N2, N4 |

## Lēmums „būvēt vai nē” (F9 to atstāja atvērtu)

**Lēmums: būvēt, bet nevis kā apmācītu vai valodas modeli, bet kā izskaidrojamu punktu aprēķinu.**

| Apsvērums | Secinājums |
| --- | --- |
| Datu apjoms | Desmiti organizāciju — nepietiek modeļa apmācībai |
| Caurskatāmība | Katram rezultātam jābūt saprotamam pamatojumam; noteikumi to dod pilnībā |
| VDAR 22. pants / ES MI akts | Rezultāts ir tikai ieteikums darba secībai; sistēma nepieņem lēmumus par organizācijām vai personām |
| Personas dati | Aprēķinā izmanto tikai darbības datus, ne kontaktpersonu datus |
| Paplašināšana | Svarus var mainīt `crm/prioritates.py` konstantē `SVARI` |

## Aprēķins

| Rādītājs | Punkti |
| --- | --- |
| Mijiedarbība pēdējās 90 dienās | 2 par katru |
| Tikšanās pēdējās 90 dienās | papildus 3 par katru |
| Atvērts pieprasījums | 4 par katru |
| Atbildēts pieprasījums | 1 par katru |
| Pēdējā mijiedarbība ≤ 14 dienas / ≤ 30 dienas | 5 / 2 |

## Detalizētās apakšprasības

| ID | Apakšprasība |
| --- | --- |
| MI-2.1 | Lapa `/prioritates` (HTML un JSON) sakārto organizācijas pēc punktiem dilstoši, vienādiem — pēc nosaukuma |
| MI-2.2 | Katrai organizācijai redzams pamatojums: katra rādītāja ieguldījums punktos |
| MI-2.3 | Lapā ir aprēķina noteikumu apraksts un teksts „ieteikums darba secībai, nevis lēmums” |
| MI-2.4 | Darbinieks redz tikai organizācijas, kurām ir atbildīgais; vadītājs — visas ar atbildīgā kolonnu |
| MI-2.5 | Panelī (F9) prioritātes nerāda; tām ir sava lapa navigācijā |

## Pieņemšanas kritēriji

| # | Gadījums | Gaidāmais rezultāts |
| --- | --- | --- |
| 1 | Organizācija ar tikšanos vakar un atvērtu pieprasījumu | 2+3+4+5 = 14 punkti, 4 pamatojuma rindas |
| 2 | Organizācija bez aktivitātes | 0 punkti, „Nav aktivitātes” |
| 3 | Citam darbiniekam | Neredz svešas organizācijas |

## Tehniskā realizācija (N4)

`crm/prioritates.py` (viens SQL vaicājums), `templates/prioritates.html`; līgumā `GET /prioritates`, shēma `Prioritate`. Testi: `test_mi2_*`.
