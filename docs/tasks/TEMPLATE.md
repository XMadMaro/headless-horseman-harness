# CP-XXX: Tytuł zadania

> Status: DRAFT | IN_PROGRESS | REVIEW | DONE
> Track: STANDARD_TRACK | FAST_TRACK
> Data: YYYY-MM-DD

---

## 1. Cel i kontekst

Jedno zdanie: co dowozi i dlaczego teraz. Link do `backlog.md` / issue.

## 2. Decyzje z wywiadu (/grill-me) — WYMAGANE dla STANDARD_TRACK

> Bramka `docs-provenance.py` blokuje przejście do IN_PROGRESS jeśli ta sekcja < 50 znaków.

**Pytania zadane (ask_question / /grill-me):**

1. **Skąd pochodzą dane?** `props / sesja / endpoint / RLS / Qdrant` — konkretne źródło prawdy + plik:linia
2. **Co przy braku danych / błędzie 403/404?** `Fail-Closed / redirect / skeleton / toast` — zachowanie + edge case
3. **Czego celowo NIE robimy? (Must NOT)** — jawna lista granic, np. `Nie ruszamy auth, nie dodajemy migracji, nie zmieniamy schema`

**Wypełnia Człowiek:**

- [ ] Źródło danych:
- [ ] Obsługa błędu / braku danych:
- [ ] Must NOT:

**Podpis wywiadu:** `Potwierdzam: [data, osoba]`

---

## 3. Plan Ograniczeń: Must / Must NOT

| Must (dowieźć) | Must NOT (zakaz) |
|---|---|
| 1. ... | 1. ... |
| 2. ... | 2. ... |

## 4. Co usuwamy przed dodaniem (Subtract Before You Add) — Reguła 7.17

> Agent najpierw kasuje legacy, potem dodaje nowe. Wymień pliki/funkcje do usunięcia.

- [ ] Usuwane: `plik:linia` — dlaczego martwe/zastąpione
- [ ] Usuwane: `plik:linia`

Jeśli nic do usunięcia: napisz `Brak — greenfield, uzasadnienie: ...`

## 5. Premise (Attack the Premise) — wypełniane po 2. failu

> Jeśli 2x ta sama bramka FAIL, zatrzymaj się i wpisz błędne założenie.

- Założenie: `...`
- Podważenie: `...`
- Nowy plan:

## 6. Implementacja (TDD + ub-mode)

- [ ] Test RED (fail przed kodem)
- [ ] Kod GREEN
- [ ] Refactor (crapper < 10, dryer < 0.82)

Pliki dotykane: `apps/...`, `packages/...`, `src/...`

## 7. Dowody bramek (wkleja CLI, nie agent)

```bash
bash scripts/check-gate-integrity.sh
# -> exit 0, 18 reguł PASS

bash scripts/adversarial-review.sh origin/main
# -> BLOCKING=0, ADVISORY=0

python scripts/docs-provenance.py --check
# -> 1 passed | 0 failed

bash scripts/adversarial-review.sh --test-negative || echo "exit: $?"
# -> BLOCKING=4, exit 1 (poprawnie zablokowano S1,S2,S5,S6)
```

Wklej surowy stdout poniżej:

```
...
```

## 8. Recepta Weryfikacji Manualnej (Reguła 7.11)

### Krok 1 — Happy Path
Komenda + oczekiwany wynik + rzeczywisty stdout

### Krok 2 — Adversarial / Negative
`--test-negative` + stdout

### Krok 3 — Side-effects
DB/logi po zmianie + stdout

## 9. Evidence i podpis

### Raport CLI

```
...
```

### Podpis człowieka (jedyna droga do DONE)

```
Zatwierdzam: [YYYY-MM-DD, CP-XXX, decyzja: DONE]
```

---

## Checklist Definition of Done

- [ ] Inception Gate zielony (Decyzje z wywiadu >= 50 znaków)
- [ ] Subtract wypełnione
- [ ] Test RED->GREEN dowód
- [ ] `adversarial-review.sh` PASS (BLOCKING=0)
- [ ] `check-gate-integrity.sh` PASS
- [ ] Recepta 3-krokowa wykonana przez CLI, stdout wklejony
- [ ] Podpis człowieka 1 linią

### Circuit Breaker

Jeśli 3x z rzędu `adversarial-review.sh` FAIL na tym samym CP: dodaj `🚩 [FLAG:CIRCUIT_BREAKER]` do nagłówka, wróć do `/grill-me`, nie rób 4. fix-rush.
