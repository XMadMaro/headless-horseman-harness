# heavy-starter — Deterministyczny Harness dla Monorepo

> **Nie przyspiesza pisania kodu. Kasuje 90% czasu refaktoru.**

Template dla dużych projektów monorepo (TS + Python, Nx/Turborepo/pnpm/uv), gdzie `agent rot` zabija projekt po 2 tygodniach.

Zamiast kolejnego boilerplate (Next.js + Prisma) dostajesz **architekturę dyscypliny agenta**: 5 warstw bramek które fizycznie blokują halucynacje.

---

## Dla kogo / nie dla kogo

**NIE używaj jeśli:**
- Prototyp < 1 tydzień, hackathon, landing page
- < 5k LOC, 1-2 encje, brak RLS/tenantów
- Żyjesz < 3 miesiące

**UŻYJ jeśli:**
- Monorepo `apps/*` + `packages/*` (Web + API + Worker)
- Błąd = strata danych / kasy / reputacji
- > 10k LOC, 2+ devów lub agent AI na produkcji > 1 miesiąc

---

## 5 warstw — co dostajesz w pudełku

| # | Warstwa | Plik | Co blokuje |
|---|---|---|---|
| 1 | **Inception Gate** | `scripts/docs-provenance.py` + `docs/tasks/TEMPLATE.md` | Zadanie nie wejdzie w `IN_PROGRESS` bez `## Decyzje z wywiadu (/grill-me)` >= 50 znaków. Zakaz zgadywania wymagań. |
| 2 | **ub-mode** | `AGENTS.md` 7.17 | `Subtract Before Add`, `Attack Premise`, `Fix Root Causes`, `Zero Placebo` |
| 3 | **Adversarial Review** | `scripts/adversarial-review.sh` | Skan `git diff origin/main...HEAD` na 7 grzechów, deterministyczny `grep` (0 LLM) |
| 4 | **Visual Diffs** | `e2e/visual-regression.spec.ts` (wzorzec) | Snapshoty `1440x900` + `1024x768` z `animations:disabled` |
| 5 | **Gate Integrity** | `scripts/check-gate-integrity.sh` | Liczy reguły w `AGENTS.md`, wykrywa `--no-verify`, `skip-ci` |

---

## Quick Start (5 min)

```bash
# 1. Skopiuj template do swojego monorepo
npx degit XMadMaro/CBA-RAG/harness-template ./

# lub ręcznie:
cp -r harness-template/scripts ./scripts
cp -r harness-template/.github ./
cp harness-template/AGENTS.md ./AGENTS.md

# 2. Dodaj bramki do CI (GitHub Actions już w .github/workflows/)
# 3. Uruchom lokalnie:
bash scripts/check-gate-integrity.sh
bash scripts/adversarial-review.sh origin/main
python scripts/docs-provenance.py --check
```

---

## 7 grzechów (deterministyczne, grep — nie LLM)

| ID | Nazwa | Wzorzec | Przykład |
|---|---|---|---|
| S1 | Silent Fallback | `except: pass`, `catch {}` pusty, `catch { return null }` | Ukrywa crash |
| S2 | Destructive CSS | `!important` w `*.css/*.tsx` | Rozwala layout |
| S3 | Fake Assertion | `toBeDefined()`, `assert True` bez pól, `expect(...).toBeTruthy()` solo | Test przechodzi dla `undefined` |
| S4 | Secret Leak | `sk-`, `ghp_`, `password=`, `BEGIN PRIVATE KEY` | Wyciek sekretu |
| S5 | Destructive Migration | `DROP TABLE`, `DROP COLUMN` bez `-- APPROVED_DESTRUCTIVE` | Usuwa dane |
| S6 | Dependency Hygiene | `package.json/pyproject.toml` +1 dep bez sekcji `Uzasadnienie` w CP | Rozrost deps |
| S7 | Tenant Leak* | `req.body.citySlug` zamiast `session` | IDOR — opcjonalnie dla multi-tenant |

*S7 włączasz flagą `--enable-tenant-check` jeśli masz RLS.

Wszystkie oparte na `grep -rn`, `AST` nie LLM. Ten sam diff = ten sam werdykt.

---

## Workflow: jak agent pracuje

```
Prompt -> /grill-me (3 pytania) -> TEMPLATE.md z Subtract/Must NOT -> Human Accept
  -> TDD Red->Green (ub-mode) -> adversarial-review.sh -> check-gate-integrity.sh
  -> Recepta CLI (curl/logs) -> Human podpis: Zatwierdzam: [data, CP-xxx, DONE] -> git push (Reguła 2.7: 1 push per łańcuch)
     ^-- po 3 failach: [FLAG:CIRCUIT_BREAKER] -> wróć do /grill-me
```

---

## Struktura template

```
harness-template/
├── AGENTS.md                 # System operacyjny agenta (7.1-7.18)
├── docs/tasks/TEMPLATE.md    # Szablon zadania z Inception Gate
├── docs/tasks/ACTIVE.md      # Rejestr Zero Próżni (Reguła 2.9)
├── scripts/
│   ├── adversarial-review.sh     # 7 grzechów, tryby scan/report/test-negative
│   ├── check-gate-integrity.sh   # 53 reguły, wykrywa osłabienia
│   └── docs-provenance.py        # Inception Gate checker
├── skills/grill-me/SKILL.md      # Protokół wywiadu
└── .github/workflows/
    ├── provenance-check.yml
    ├── adversarial-review.yml
    └── visual-regression.yml
```

---

## Monorepo-agnostic

Działa z:
- **JS/TS:** pnpm + Turborepo/Nx, `apps/*`, `packages/*`
- **Python:** uv + `src/*`, `pyproject.toml`, `alembic migrations`
- **Mieszane:** front TS + api Python — bramki obsługują oba stosy

Konfigurujesz `scripts/config.sh`: `MONOREPO_ROOT`, `APPS_GLOB`, `MIGRATIONS_GLOB`.

---

## Znane ograniczenia

Zobacz `KNOWN_LIMITATIONS.md`: harness gwarantuje **higienę wykonania, nie słuszność kierunku**. Nie zastąpi `CODEOWNERS`, `Sentry`, `required_status_checks`.

---

## Licencja

MIT — wyciągnięte z battle-tested CityPulse (GovTech) + CBA-RAG. Zero telemetry, zero phone-home.
