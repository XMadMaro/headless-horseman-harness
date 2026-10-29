# Schemat preflight (`docs/preflight/<TICKET>.json`) — Reguła 7.19

> **Cel: agent nie pisze linijki kodu, dopóki nie udowodni, że wszedł w pliki, posprzątał i zaplanował.**
> Artefakt jest maszynowy. Wypełnienie go to nie biurokracja — to moment, w którym agent czyta kod zamiast zgadywać.

## Dlaczego to jest mechaniczne, a nie „prośba o myślenie”

| Reguła | Co wymusza | Czego nie da się oszukać |
|---|---|---|
| **F2 Dive** | `path` + **cytat istniejący w pliku** (±10 linii) | cytatu nie da się wymyślić — plik trzeba otworzyć |
| **F4 Subtract** | lista realnych plików/symboli do usunięcia **albo** `greenfield_justification` ≥ 40 znaków | nie da się „przejść dalej” bez decyzji o sprzątaniu |
| **F5 Order** | `plan[0]` ∈ {`subtract`, `diagnose`, `repro`} | implementacja nie może być pierwszym krokiem |
| **F6 Budget** | ≤ 15 plików, ≤ 400 LOC | frankenstein jest z definicji poza budżetem |
| **F7 Duplication** | każdy nowy symbol: `reuse_of` (istniejący) **albo** uzasadnienie ≥ 20 znaków | jeśli symbol już jest w repo — bramka to pokaże |
| **F3 Repro** | `kind=bug` ⇒ `repro.cmd` + `observed_failure` | debugowanie bez reprodukcji = przepalanie tokenów |
| **F1 Intent** | `falsifiable` ≥ 20 znaków + `non_goals` niepuste | brak granic = zadanie rozrasta się samo |

## Minimalny, poprawny artefakt

```json
{
  "ticket": "CP-150",
  "kind": "refactor",
  "intent": {
    "falsifiable": "Po zmianie usunięcie !important nie jest raportowane jako BLOCKING.",
    "non_goals": ["nie zmieniamy zestawu reguł S1-S7"]
  },
  "files_touched": [
    { "path": "scripts/adversarial-review.sh", "line": 6,
      "quote": "skanujemy WYŁĄCZNIE linie dodawane", "why": "tu filtrujemy diff" }
  ],
  "subtract": [
    { "path": "scripts/adversarial-review.sh", "what": "grep po całym diffie (karał usuwanie)", "action": "replace" }
  ],
  "plan": ["subtract", "diagnose", "design", "test", "implement", "verify"],
  "budget": { "max_files": 2, "max_loc": 180 },
  "reuse": [
    { "new": "has_secret", "reuse_of": null,
      "justification": "brak odpowiednika; mawk nie wspiera interwałów, potrzebna funkcja" }
  ]
}
```

Dla `kind: "bug"` dodatkowo:

```json
"repro": { "cmd": "nx test api --t=tenant", "observed_failure": "FAIL: foreign tenant received 200" }
```

## Zakres `kind`

| Wartość | Kiedy | Wymóg dodatkowy |
|---|---|---|
| `feature` | nowa funkcja | brak |
| `bug` | coś nie działa | `repro` (F3) |
| `refactor` | zmiana struktury bez zmiany zachowania | `plan[0]` powinien być `subtract` |

## Reguły oszczędzania (to jest anty-frankenstein)

1. Jedno zadanie = jeden artefakt. Nie dopisuj do zamkniętego ticketu — otwórz nowy.
2. Limit 15 plików / 400 LOC jest **twardy**. Przekroczenie = sygnał, że zadanie nie jest zrozumiane.
3. `reuse_of` jest tańsze niż nowa funkcja — jeśli istnieje odpowiednik, bramka wymusi uzasadnienie duplikacji.
4. `quote` bierz z pliku (skopiuj realną linię), nie z pamięci. Kłamliwy cytat = FAIL.
5. Po preflight kod pisze się **krócej**, bo decyzje już zapadły — to jest mechanizm oszczędzania tokenów, nie biurokracja.

## Uruchomienie

```bash
python3 scripts/preflight-gate.py --file docs/preflight/CP-150.json
python3 scripts/preflight-gate.py --ticket CP-150    # skrót
```

Fail-closed: brak pliku, zły JSON, brak klucza ⇒ exit 1.
