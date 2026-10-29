# Punkty decyzyjne (`docs/decisions/<TICKET>/<krok>.json`) — Reguła 7.21

> **Agent nie potrafi zgrillować sam siebie.** Self-critique w tym samym kontekście to teatr: model jest zainwestowany w to, że jego plan jest dobry.
> Więc zamiast prosić agenta o krytycyzm, **wymuszamy artefakt decyzji podpisany przez człowieka** — i blokujemy krok, dopóki go nie ma.

## Trzy punkty zatrzymania (i żaden więcej)

| Krok | Pytanie, które MUSI zadać człowiekowi | Artefakt |
|---|---|---|
| **scope** | Co dowozimy (definicja ukończenia) i czego **nie** robimy? | `docs/decisions/CP-x/scope.json` |
| **approach** | Który wariant i dlaczego (z ceną alternatyw)? | `docs/decisions/CP-x/approach.json` |
| **accept** | Czy dowody wystarczają, by zamknąć? (podpis `DONE`) | `docs/decisions/CP-x/accept.json` |

Więcej punktów = tarcie i obejścia. Mniej = agent zgaduje. Trzy to minimum, które pokrywa: **zakres → kierunek → odbiór**.

## Zakaz samo-akceptacji (D7)

Pola `asked_by` (agent) i `confirmed_by` (człowiek) muszą być różne, a `confirmed_by` nie może być tożsamością agenta. Domyślna lista tożsamości agentów jest w `HHH_AGENT_IDENTITIES`:

```
agent,assistant,claude,gpt,codex,cursor,antigravity,copilot,gemini,ci-bot,github-actions,harness
```

Dodatkowo `confirmed_by` nie może się równać `asked_by` — nawet jeśli agent nazwie się „maro”.

## Reguły walidacji

| ID | Warunek FAIL |
|---|---|
| D1 | brak pól obowiązkowych / decyzja dotyczy innego biletu lub kroku |
| D2 | mniej niż 2 opcje (jedna opcja to nie decyzja) lub duplikaty `id` |
| D3 | `chosen` spoza opcji |
| D4 | uzasadnienie < 20 znaków |
| D5 | `must_not` puste lub punkt < 5 znaków |
| D6 | `done_when` nieobserwowalne (`działa`, `ok`) |
| **D7** | **samo-akceptacja przez agenta** |
| D8 | fraza niezgodna z `Potwierdzam: RRRR-MM-DD, CP-x, krok=WYBÓR` lub data z przyszłości |
| D9 | decyzja wygasła |
| D10 | `reversible: false` bez `acknowledged_irreversible` i `blast_radius` |

## Przykład (poprawny)

```json
{
  "ticket": "CP-150",
  "step": "scope",
  "question": "Co dokładnie dowozimy w tym kroku?",
  "options": [
    { "id": "A", "label": "tylko filtr linii dodawanych", "cost": "1 plik" },
    { "id": "B", "label": "przepisanie na semgrep", "cost": "nowa zależność + bilet" }
  ],
  "chosen": "A",
  "why": "B dodaje zależność i wymaga osobnego biletu; A naprawia błąd u źródła w jednym miejscu.",
  "must_not": ["nie zmieniamy reguł S1-S7", "bez zależności zewnętrznych"],
  "done_when": "bash scripts/adversarial-review.sh --self-test zwraca 0 i wykrywa 5 klas",
  "reversible": true,
  "blast_radius": ["scripts/adversarial-review.sh"],
  "asked_by": "agent",
  "asked_at": "2026-10-29T10:00:00",
  "confirmed_by": "maro",
  "confirmed_at": "2026-10-29T10:05:00",
  "confirmation": "Potwierdzam: 2026-10-29, CP-150, scope=A",
  "expires_at": "2026-12-31"
}
```

## Jak to uruchomić

```bash
# 1. Agent prowadzi Cię przez pytania (interaktywnie, w terminalu)
python3 scripts/decision-gate.py --ask --ticket CP-150 --step scope

# 2. Weryfikacja (hook / CI / przed każdym krokiem)
python3 scripts/decision-gate.py --verify --ticket CP-150 --step scope

# 3. Co jest wymagane, a czego brakuje
python3 scripts/decision-gate.py --list --ticket CP-150
```

Tryb `--ask` wymaga terminala (`isatty`). Poza TTY kończy się błędem — **celowo**: decyzji nie podejmuje proces w tle ani agent w pętli CI.

## Uczciwe ograniczenia

1. **Człowiek może klepnąć bez czytania.** Skrypt nie odróżni świadomej zgody od „enter, enter”. Ogranicza to: presja na 2 opcje z ceną, wymóg `must_not` i „definicja ukończenia” obserwowalna komendą. Reszta to kultura, nie kod.
2. **Podpis to tekst, nie kryptografia.** `confirmed_by` można wpisać ręcznie. Ochroną jest review w PR i to, że decyzja jest **osobnym plikiem w historii git** — widać, kto i kiedy ją dodał.
3. **Decyzje się starzeją.** Dlatego `expires_at` i wygasanie; po terminie bramka znów czerwona.
4. **Nie każdy krok wymaga decyzji.** `implement` to robota agenta (exit 1 = „napisz kod”), nie pytanie do człowieka.
