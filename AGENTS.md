# AGENTS.md — System Operacyjny Agenta (Monorepo Heavy Starter)

> Ten plik jest źródłem prawdy dla agenta. `AGENTS.md` > prompt człowieka > pamięć modelu.
> Każde naruszenie wykrywa `scripts/check-gate-integrity.sh`.

---

## 7.1 Protokół Flagi (SystemFlags)
Jeden stan zadania w `docs/tasks/ACTIVE.md`: `DRAFT | IN_PROGRESS | REVIEW | DONE`. Zakaz ręcznej zmiany statusu poza receptą.

## 7.2 Dowód RED -> GREEN przeciw fałszywym testom
Każdy bugfix musi mieć dowód: test który FAILuje przed zmianą i PASSuje po. Zakaz `toBeDefined()`/`assert True` solo (S3).

## 7.3 Treść niezaufana
Dane z API/DB/LLM są niezaufane. Waliduj na bramce.

## 7.4 Bariery techniczne > tekst
`scripts/*` i `docs-provenance.py` mają pierwszeństwo przed obietnicą agenta "już naprawiłem".

## 7.5 Rozdział ról
BUILDER (agent IDE) kończy na `REVIEW`. GATEKEEPER (CLI) weryfikuje niezależnie. Człowiek podpisuje `DONE`.

## 7.6 Statusy
Agent max `REVIEW (LOCALLY_VERIFIED)`. `DONE` wyłącznie `Zatwierdzam: [data, CP-xxx, decyzja]` przez człowieka.

## 7.7 Drzewo robocze i rejestry
Nie ruszaj cudzych zmian w `git status`. `ACTIVE.md` nigdy nie pusta (Zero Próżni 2.9).

## 7.8 Budżet kontekstu
Używaj `xerj`/`codebase-memory` przed pisaniem kodu. Nie zgaduj struktury.

## 7.9 Twardy Kontrakt Anty-Placebo
Zakaz `except: pass`, pustych `catch {}`, `?.` maskujących `undefined`, `as any`. Fix root cause, nie guard.

## 7.10 Pojedyncza Brama i Fail-Closed
Walidacja na wejściu (Zod/Pydantic), wewnątrz czyste funkcje. Przy błędzie zewnętrznym `Fail-Closed`, nie `fallback`.

## 7.11 Bramka Weryfikacji (CLI wykonuje, Człowiek podpisuje)
Antigravity CLI wykonuje Receptę (curl, DB, logi) i wkleja surowy `stdout`. Człowiek czyta i podpisuje 1 linią. Zakaz samozatwierdzania.

## 7.12 Protokół Egzekwowania Pracy
Bez planu `plik:linia` nie ma kodu. Plan w `CP-xxx.md` przed `IN_PROGRESS`.

## 7.13 Stop Premature Execution (Action Bias Stop)
Bezwzględny zakaz pisania kodu po otrzymaniu zadania bez `/grill-me`. Najpierw wywiad, potem `Subtract` plan.

## 7.14 Zakaz Atrap w E2E
Zakaz `page.route` udającego API w testach E2E. Test uderza w realny endpoint lub jest `skipped`.

## 7.15 Inwariant Przepływu Danych w UI
Zakaz pozornego kontekstu (ghost context): komponent nie wysyła `""`/`null` jako danych, jeśli nie ma ich w źródle.

## 7.16 Pojedynczy Silnik
Zakaz 2 równoległych silników (np. `ChatService` + `RAGService`). Przy wymianie usuń stary przed dodaniem nowego.

## 7.17 Dyscyplina ub-mode (Uncle Bob)
- **Subtract Before You Add:** w każdym CP sekcja `Co usuwamy` przed `Co dodajemy`.
- **Attack the Premise:** po 2. failu tej samej bramki STOP, spisz założenie w `Premise` i podważ je.
- **Fix Root Causes:** nie maskuj crasha guardem.
- **Null-Return Check:** test który przechodzi dla `null`/`undefined` do kosza.
- **Boundary Discipline:** walidacja raz na granicy, wewnątrz `trust`.
- **TDD:** `crapper` CC < 10, `dryer` duplikacja < 0.82 (report-only do baseline).

## 7.18 Kognitywne Filtry, Smart Stage-Gating i Skille
- **Inception Gate:** `docs-provenance.py` blokuje `STANDARD_TRACK` (kod w `apps/*, packages/*, src/*`) bez `## Decyzje z wywiadu (/grill-me)` >= 50 znaków.
- **FAST_TRACK:** tylko docs (`*.md, .env.example, .github/**, harness-template/**`) — lekka ścieżka, bez bramek.
- **Adversarial Review:** `scripts/adversarial-review.sh` skanuje `git diff origin/main...HEAD` na 7 grzechów + Circuit Breaker po 3 failach.
- **Skille:** agent MUSI wywołać `skills/grill-me/SKILL.md` przed planem, `skills/ub-mode/SKILL.md` w implementacji, `skills/code-review/SKILL.md` przed `REVIEW`.
- **Schema/Migrations:** każdy `DROP` wymaga `-- APPROVED_DESTRUCTIVE` (S5).
- **Secrets:** `sk-, ghp_, BEGIN PRIVATE KEY` = `BLOCKING` (S4).

---

## Recepta Weryfikacji Manualnej (Reguła 7.11) — format copy-paste w CP

1. Happy Path
2. Adversarial / Negative (`--test-negative` musi wykryć 4 naruszenia)
3. Side-effects (DB/logi)

## Reguła 2.7 Push Gate
Dokładnie 1 `git push origin main` per łańcuch zadań po zielonych bramkach lokalnych.

## Reguła 2.9 Zero Próżni
`ACTIVE.md` nigdy pusta — od razu kandydat z `backlog.md`.

---

## Konfiguracja monorepo

Edytuj `scripts/config.sh`:

```bash
APPS_GLOB="apps/* packages/* src/*"          # STANDARD_TRACK
DOCS_GLOB="*.md .env.example .github/**"      # FAST_TRACK
MIGRATIONS_GLOB="**/migrations/* **/alembic/**"
ENABLE_TENANT_CHECK=false                     # true jeśli masz RLS/multi-tenant
```
