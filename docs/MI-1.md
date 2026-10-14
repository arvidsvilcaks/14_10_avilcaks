# MI-1 — Mijiedarbības kopsavilkums un nākamā soļa ieteikums: prasības apraksts

Oct 14, 2026 · @Arvīds Vilčaks

## Pamatinformācija

Pēc mijiedarbības (F3) darbinieks var lūgt MI sagatavot īsu kopsavilkumu un ieteikt vienu nākamo soli. MI dod tikai ieteikumu; saglabā un izmanto to darbinieks.

| Lauks | Vērtība |
| --- | --- |
| ID | MI-1 |
| Nosaukums | Mijiedarbības kopsavilkums un nākamā soļa ieteikums |
| Veids | MI prasība |
| Statuss | Izpildīts (bez CR, 2026-10-14) |
| Atkarīga no | F3 (mijiedarbības), N3 (lomas) |
| Jāatbilst | N1, N2, N4; F9 sadaļa „Mākslīgais intelekts” |

## Lēmumi

| Jautājums | Lēmums | Pamatojums |
| --- | --- | --- |
| Kurš modelis? | Anthropic Claude, `claude-opus-5-5` (maināms ar `CRM_MI_MODELIS`), `effort: low` | Pašreizējais noklusējuma modelis; īss uzdevums — zema piepūle |
| Kā izsauc? | Oficiālais `anthropic` Python SDK; akreditācija no `ANTHROPIC_API_KEY` vai SDK profila | Nav jāglabā atslēga kodā |
| Ja MI nav konfigurēts? | Lapa paziņo „MI ieteikums nav pieejams” (503); pārējā sistēma strādā | MI ir papildfunkcija, ne obligāta |
| Ko sūta modelim? | Tikai mijiedarbības veidu un kopsavilkuma tekstu | Datu minimizēšana (N2): bez organizācijas nosaukuma, darbinieka un kontaktpersonām |
| Kad saglabā? | Tikai pēc darbinieka apstiprinājuma; pirms tam tekstu var labot vai noraidīt | Cilvēks paliek atbildīgs; nav automatizētu lēmumu |
| Kā marķē? | Visur, kur rāda ieteikumu, — atzīme „Ģenerēts ar MI” | Caurskatāmība (ES MI akts, 50. pants) |
| Kurš drīkst? | Mijiedarbības autors vai vadītājs | Atbilst F3 redzamībai |
| Panelī? | Nerāda — panelī mijiedarbību bloks ir bez teksta (N2) | F9 N2 prasība |

## Detalizētās apakšprasības

| ID | Apakšprasība |
| --- | --- |
| MI-1.1 | Organizācijas kartītes mijiedarbību tabulā ir kolonna „MI ieteikums” ar saiti „Sagatavot” vai „Skatīt” |
| MI-1.2 | Lapa `/mijiedarbibas/{id}/mi` rāda mijiedarbību, brīdinājumu par datu nosūtīšanu un pogu „Ģenerēt ieteikumu” |
| MI-1.3 | Pēc ģenerēšanas rāda melnrakstu ar atzīmi „Ģenerēts ar MI” rediģējamos laukos; „Apstiprināt un saglabāt” vai „Noraidīt” |
| MI-1.4 | Neapstiprināts ieteikums netiek saglabāts un nav redzams kartītē |
| MI-1.5 | Apstiprinātais ieteikums redzams kartītē ar atzīmi; to var dzēst |
| MI-1.6 | Mijiedarbībai bez kopsavilkuma teksta ģenerēšana nav iespējama (422) |
| MI-1.7 | Modeļa atteikums (`stop_reason: refusal`), API kļūda vai nederīgs atbildes formāts → paziņojums, nevis kļūda |

## Pieņemšanas kritēriji

| # | Gadījums | Gaidāmais rezultāts |
| --- | --- | --- |
| 1 | Autors ģenerē un apstiprina (ar labojumu) | Kartītē redzams labotais solis ar „Ģenerēts ar MI” |
| 2 | Ģenerē, bet neapstiprina | Kartītē nekas nemainās |
| 3 | MI nav konfigurēts | 503 lapa ar skaidrojumu |
| 4 | Cits darbinieks | 403 |
| 5 | Neeksistējoša mijiedarbība | 404 |
| 6 | Modelim nosūtītais teksts | Tikai veids un kopsavilkums |

## Tehniskā realizācija (N4)

- `crm/mi.py`, `templates/mi/ieteikums.html`; kolonnas `mijiedarbibas.mi_kopsavilkums`, `mi_nakamais_solis`, `mi_apstiprinaja_id` (migrācija).
- `Mijiedarbiba` JSON shēmā lauki `mi_kopsavilkums`, `mi_nakamais_solis`.
- Pakotne `anthropic` nav obligāta (`pip install anthropic`); bez tās funkcija paziņo, ka MI nav pieejams.
- Testi: `test_mi1_*` (MI izsaukums aizstāts ar viltotu funkciju — testi neizmanto tīklu).
