# Schemat artefaktu epistemicznego (`docs/epistemic/<TICKET>.json`)

> Artefakt jest **maszynowy**, nie prozatorski. Człowiek czyta go w 30 sekund, bramka w 30 ms.
> Zasada: **każde twierdzenie ma komendę. Bez komendy twierdzenie nie istnieje.**

## Pola wymagane (fail-closed: brak któregokolwiek ⇒ exit 1)

| Pole | Typ | Znaczenie |
|---|---|---|
| `ticket` | string | ID biletu (`CP-142`) |
| `code_changed` | bool | czy zmieniono kod produkcyjny (włącza E5/E6/E8) |
| `claims` | array | twierdzenia z dowodami (§1) |
| `confidence` | `high`\|`medium`\|`low` | `high` **wymaga** dowodu wykonanego (`--execute`) |
| `tests` | `{added, removed}` | higiena testów (ujemne `removed` = blokada) |

## Pola opcjonalne, ale mierzone

| Pole | Typ | Do czego |
|---|---|---|
| `intent` | `{falsifiable, non_goals[]}` | interpretacja: co da się obalić + czego NIE robimy |
| `hypotheses` | array (§2) | wnioskowanie z falsyfikatorem |
| `unknowns` | array | samoregulacja: co pozostaje niewiadome (puste przy `high` = WARN) |
| `alternatives_rejected` | array `{option, why, cost}` | sycophancy: nazwany wariant, powód, koszt |
| `sources` | array `{ref, reliability, would_change_mind}` | ewaluacja źródeł |
| `mutations` | `{killed, survived}` | czy testy nie są placebo (score < 0.8 = WARN) |
| `commit` | string | provenance artefaktu |

## 1. `claims[]`

```json
{
  "id": "C1",
  "text": "Obcy tenant dostaje 403.",
  "kind": "behavior",
  "cmd": "nx test api --t=tenant",
  "expected": "1 passed",
  "observed": "1 passed",
  "verified": true
}
```

- `kind`: `behavior` (zachowanie — wymagane przy `code_changed`, reguła E8) albo `static` (typy, lint).
- `verified: true` bez `cmd`/`expected`/`observed` = **E2 konfabulacja**.
- `expected` musi wystąpić w `observed` = **E3**.
- `expected` **wpisany w `cmd`** (`echo '3 passed'`) = **E9 potwierdzenie samego siebie**.
- `--execute` uruchamia `cmd` i sprawdza `expected` w **realnym** wyniku. To jedyny tryb, który łapie kłamstwo spójne wewnętrznie (patrz tabela w dokumencie architektury, §5.5).

## 2. `hypotheses[]` — prerejestracja

```json
{
  "id": "H1",
  "text": "Slug czytany z req.body zamiast sesji.",
  "predicted": "Po poprawce obcy slug zwróci 403, log pokaże session_tenant != body_slug.",
  "predicted_if_wrong": "Nadal 200, a w logu brak session_tenant (źródłem jest cache uprawnień).",
  "result": "confirmed"
}
```

- Oba przewidywania **przed** eksperymentem, minimum 9 znaków = **E7**.
- `predicted == predicted_if_wrong` ⇒ to nie eksperyment, to wiara (**E7**).

## 3. Jak uruchomić

```bash
python3 scripts/epistemic-gate.py --file docs/epistemic/CP-142.json             # statycznie (szybko, w pre-commit)
python3 scripts/epistemic-gate.py --file docs/epistemic/CP-142.json --execute   # wykonuje dowody (w CI / przed REVIEW)
```

## 4. Przykłady w repo (i ich status)

| Plik | Przeznaczenie | Wynik |
|---|---|---|
| `CP-142.example.json` | wzorzec poprawny (komendy realne, wykonywalne z root repo) | `--execute` → exit 0 |
| `CP-666.gaming.json` | wzorzec „cel za wszelką cenę” (7 naruszeń) | exit 1 |

> ⚠️ `CP-142.example.json` to **przykład struktury**, nie dowód tego projektu: pola `tests`, `mutations` i `sources` są ilustracyjne. Komendy w `claims` są prawdziwe i wykonują się na tym repozytorium.
