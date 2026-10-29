# AGENTS.md — System Operacyjny Agenta (Monorepo Heavy Starter)

> Ten plik jest źródłem prawdy dla agenta. `AGENTS.md` > prompt człowieka > pamięć modelu.
> Zmiany TREŚCI bramek wykrywa `scripts/gate-lock.sh --check` (hash-pin). Naruszenia PROCESU wykrywają bramki 7.18–7.20.
>
> **Precedencja:** prawda repozytorium > bramki deterministyczne > governance > workflow > specjalista stacku > preferencje człowieka.
> **Żaden skill nie unieważnia bramki.** Jeśli skill każe pominąć test, a bramka go wymaga — wygrywa bramka.

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

## 7.19 Preflight: myśl, zanim napiszesz linijkę
Zakaz tworzenia/edycji kodu bez artefaktu `docs/preflight/CP-xxx.json` (bramka: `scripts/preflight-gate.py`).

**Zanim kod — zanurkuj i posprzątaj:**
- **F2 Dive:** dla każdego pliku, który zamierzasz tknąć, wpisz `path` + **cytat istniejący w pliku** (±10 linii od `line`). Cytat niepasujący = plik nie został przeczytany. Nie zgaduj struktury.
- **F5 Order:** `plan` zaczyna się od `subtract` / `diagnose` / `repro`. Implementacja jest **trzecim** krokiem, nie pierwszym.
- **F4 Subtract:** sekcja `subtract` wskazuje realne pliki/symbole do usunięcia albo `greenfield_justification` ≥ 40 znaków. Paragraf 7.17 egzekwowany mechanicznie.
- **F7 Duplication:** każdy nowy symbol ma `reuse_of` (istniejący!) albo uzasadnienie ≥ 20 znaków. Nazwa już istniejąca w repo bez `reuse_of` = duplikacja = blokada. **Frankenstein powstaje z duplikacji, nie z braku talentu.**
- **F6 Budget:** ≤ 15 plików i ≤ 400 LOC na bilet. Więcej = rozbij, nie doklejaj.
- **F3 Reprodukcja:** przy `kind=bug` wymagany `repro.cmd` + `observed_failure` ≥ 10 znaków. Brak repro = debugowanie na wyczucie.

## 7.20 Budżet, anty-pętla, koniec przepalania tokenów
- **Budżety:** krok ≤ 8k tokenów, bilet ≤ 40k, sesja: przy 70% → handoff i nowa sesja (nie „dociąganie”).
- **Hipotezy:** 2 hipotezy na bug, 2 próby na hipotezę. Odrzucona hipoteza trafia do `.agent/state/ledger.jsonl` i **nie wraca**.
- **Breaker:** hash zbioru niepowodzeń + znormalizowany diff bez zmian 2× ⇒ STOP (exit 3), pytanie do człowieka. Kręcenie się w miejscu to najdroższy błąd agenta.
- **Dowody:** twierdzenie bez komendy nie istnieje (`scripts/epistemic-gate.py`, tryb `--execute` w CI).
- **Eskalacja:** po 2 breakerach — `git bisect`, `owners`, pytanie do człowieka. Nie trzecia próba.

## 7.21 Punkty decyzyjne: STOP i grill przed każdym krokiem
Zakaz przejścia kroku bez **artefaktu decyzji** podpisanego przez człowieka (`docs/decisions/CP-xxx/<krok>.json`, bramka `scripts/decision-gate.py`).

**Trzy punkty zatrzymania (i żadne inne):**
- `scope` — co dowozimy (definicja ukończenia) i czego **NIE** robimy,
- `approach` — który wariant i dlaczego (z ceną alternatyw),
- `accept` — czy dowody wystarczają (podpis `DONE`).

**Zakaz samo-akceptacji (D7):** `confirmed_by` ≠ `asked_by` i nie jest tożsamością agenta (`HHH_AGENT_IDENTITIES`). Agent nie może zatwierdzić własnej decyzji, nawet jeśli nazwie się jak człowiek.

**Wymogi decyzji:** ≥ 2 opcje z ceną/ryzykiem, uzasadnienie ≥ 20 znaków, `must_not` niepuste, `done_when` obserwowalne komendą, fraza `Potwierdzam: RRRR-MM-DD, CP-xxx, krok=WYBÓR`, termin ważności. Decyzja nieodwracalna wymaga `acknowledged_irreversible` + `blast_radius`.

**Sterowanie:** `python3 scripts/hhh-run.py --ticket CP-xxx --run`. Kody: 0 = zamknięte, **1 = błąd do naprawy przez agenta**, **3 = STOP, potrzebna decyzja człowieka**, 4 = brak postępu (breaker), 2 = błąd środowiska. Agent, który dostanie 3, **nie zgaduje** — woła `decision-gate.py --ask`.

**Zakaz obchodzenia:** decyzja nie może być dopisana po fakcie. `asked_at` < `confirmed_at` < moment implementacji (kolejność commitów), a `--ask` działa tylko w terminalu (`isatty`) — nie w CI ani w pętli agenta.

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
