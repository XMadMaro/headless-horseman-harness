<img width="2020" height="1228" alt="Headless Horseman Harness" src="https://github.com/user-attachments/assets/5306b6c3-e2a4-4fd9-a5f7-90a0ca766686" />

# 🐎 Headless Horseman Harness (HHH)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Battle Tested](https://img.shields.io/badge/Battle--Tested-CityPulse%20(GovTech)-success)](https://github.com/XMadMaro/CityPulseV2)
[![Zero LLM Gates](https://img.shields.io/badge/Gates-Deterministic%20(Zero%20LLM)-orange)](#-5-warstw-ochrony--co-dostajesz-w-pudełku)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#)

> **„Nie przyspiesza pisania kodu. Kasuje 90% czasu refaktoru.”**  
> **Ścina głowy halucynującym agentom, zanim ich kod trafi do gałęzi `main`.**

Template dyscypliny architektonicznej dla dużych projektów monorepo (TS + Python, Nx/Turborepo/pnpm/uv), w których zjawisko **`agent rot`** (degradacja kodu przez AI) zazwyczaj paraliżuje rozwój po 2–3 tygodniach.

Zamiast kolejnego szablonu z gotowym frameworkiem (Next.js + Prisma) dostajesz **deterministyczną uprząż inżynierską**: 5 mechanicznych warstw kontroli, które fizycznie uniemożliwiają agentom zgadywanie wymagań, mockowanie testów i maskowanie błędów produkcyjnych.

---

## 🎯 Dla kogo / nie dla kogo

### ❌ **NIE używaj jeśli:**
- Budujesz jednorazowy prototyp na weekend, hackathon lub prosty landing page.
- Kod ma < 5 000 linii, 1–2 proste encje i brak izolacji uprawnień (RLS / multi-tenant).
- Projekt ma żyć krócej niż 3 miesiące.

### ✅ **UŻYJ jeśli:**
- Prowadzisz monorepo `apps/*` + `packages/*` (Frontend + API + Worker).
- Błąd na produkcji oznacza realną stratę danych, pieniędzy lub reputacji (Gov-Tech, FinTech, B2B SaaS).
- Baza kodu przekracza 10 000 LOC, w projekcie pracuje 2+ programistów lub autonomiczny agent AI na co dzień dotyka logiki biznesowej.

---

## 🏆 Battle-Tested Evidence: Case Study CityPulse

Uprząż została wyjęta bezpośrednio z żywego projektu produkcyjnego **[CityPulse](https://github.com/XMadMaro/CityPulseV2)** (Gov-Tech monorepo, 30k+ LOC, obsługa gmin i urzędów):

| Metryka | Przed uprzężą (CP-142) | Po wdrożeniu HHH (CP-145) | Zmiana |
|---|---|---|---|
| **Czas pisania kodu** | 1.0 h | 1.5 h (TDD w ub-mode) | +30 min (dyscyplina TDD) |
| **Wywiad wstępny (/grill-me)** | 0 min (zgadywanie) | 20 min (Inception Gate) | Wymuszony kontrakt |
| **Czas usuwania regresji i refaktoru** | **12.0 h** | **30 min** (Adversarial Review) | **-95% straty czasu** |
| **Łączny czas wdrożenia zadania** | **13.0 h** | **2.5 h** | **77% redukcji długu i czasu** |

> Wcześniej model pisał kod w 20 minut, po czym przez 2 dni programiści łatali ciche `catch {}`, rozjechany layout przez `!important` i fałszywe testy z `toBeDefined()`. Po wdrożeniu HHH agent nie ma fizycznej możliwości zgłoszenia zadania bez twardych dowodów.

---

## 🛡️ 5 Warstw Ochrony — co dostajesz w pudełku

```
            [ Prompt Użytkownika ]
                      │
                      ▼
 ┌──────────────────────────────────────────┐
 │ 1. Inception Gate (/grill-me)            │ ──► Blokuje brakujące założenia i zgadywanie
 └────────────────────┬─────────────────────┘
                      ▼
 ┌──────────────────────────────────────────┐
 │ 2. ub-mode (Uncle Bob Discipline)        │ ──► Wymusza Subtract Before Add & Zero Placebo
 └────────────────────┬─────────────────────┘
                      ▼
 ┌──────────────────────────────────────────┐
 │ 3. Adversarial Code Review (Zero LLM)    │ ──► Skanuje git diff na 7 grzechów głównych
 └────────────────────┬─────────────────────┘
                      ▼
 ┌──────────────────────────────────────────┐
 │ 4. Visual Regression Gate                │ ──► Wykrywa zgnieciony layout na 1440px i 1024px
 └────────────────────┬─────────────────────┘
                      ▼
 ┌──────────────────────────────────────────┐
 │ 5. Gate Integrity Sentinel               │ ──► Blokuje próby osłabienia reguł w git hooks
 └────────────────────┬─────────────────────┘
                      ▼
         [ Bezpieczny Commit do Main ]
```

| # | Warstwa | Narzędzie | Co dokładnie blokuje? |
|---|---|---|---|
| **1** | **Inception Gate** | `scripts/docs-provenance.py` + `docs/tasks/TEMPLATE.md` | Agent nie wejdzie w stan `IN_PROGRESS` bez udokumentowanego wywiadu `## Decyzje z wywiadu (/grill-me)` (min. 50 znaków, źródło danych, obsługa błędu, granice Must NOT). |
| **2** | **ub-mode** | `AGENTS.md` (Reguła 7.17) + `scripts/ub-metrics.sh` | Wymusza *Subtract Before You Add* (wycięcie martwego kodu przed dodaniem nowego), *Attack the Premise*, *Null-Return Check* oraz raport złożoności cyklomatycznej (`crapper`) i duplikacji (`dryer`). |
| **3** | **Adversarial Review** | `scripts/adversarial-review.sh` | Bezwzględny skaner `git diff origin/main...HEAD` wykrywający 7 grzechów głównych kodu bez użycia LLM (czysty, deterministyczny ripgrep/bash). |
| **4** | **Visual Regression** | `e2e/visual-regression.spec.ts` | Testy Playwright na ekranach `1440x900` oraz `1024x768` (13-calowe laptopy) z wyłączonymi animacjami — chroni formularze przed zgnieceniem przez nawigację boczną. |
| **5** | **Gate Integrity** | `scripts/check-gate-integrity.sh` | Pilnuje nienaruszalności uprzęży: sprawdza liczbę aktywnych reguł, blokuje flagi `--no-verify`, `skip-ci` oraz próby usuwania skryptów sprawdzających. |

---

## ⚡ Quick Start (3 minuty)

### Sposób 1: Klonowanie do nowego projektu
```bash
npx degit XMadMaro/headless-horseman-harness ./moj-projekt
cd ./moj-projekt
bash install.sh
```

### Sposób 2: Instalacja w istniejącym repozytorium
```bash
# 1. Pobierz pliki uprzęży
curl -sSL https://raw.githubusercontent.com/XMadMaro/headless-horseman-harness/main/install.sh | bash

# 2. Uruchom weryfikację lokalną
bash scripts/check-gate-integrity.sh
bash scripts/adversarial-review.sh origin/main
python3 scripts/docs-provenance.py --check
```

---

## ⚔️ Skaner 7 Grzechów Głównych (Zero LLM, czysty determinizm)

Skaner `scripts/adversarial-review.sh` bada diff zmian linia po linii. Ten sam diff daje **zawsze identyczny werdykt**:

| ID | Grzech | Wzorzec w diffie | Dlaczego jest ścinany? |
|---|---|---|---|
| **S1** | **Silent Fallback** | `except: pass`, `catch {}`, `catch { return null; }` | Maskuje awarię bazy lub modelu; uniemożliwia monitoring i debugowanie. |
| **S2** | **Destructive CSS** | `!important` w plikach `.css` / `.tsx` | Niszczy kaskadę styli i responsywność na małych ekranach. |
| **S3** | **Fake Assertion** | `toBeDefined()`, `assert True`, `toBeTruthy()` solo | Test przechodzi nawet wtedy, gdy testowana funkcja zwraca pusty obiekt. |
| **S4** | **Secret Leak** | `sk-`, `ghp_`, `BEGIN PRIVATE KEY`, `password=` | Zapobiega przypadkowemu commitowaniu kluczy API i tokenów. |
| **S5** | **Destructive Migration** | `DROP TABLE`, `DROP COLUMN` bez `-- APPROVED_DESTRUCTIVE` | Chroni produkcyjne bazy danych przed nieodwracalną utratą danych. |
| **S6** | **Dependency Bloat** | Zmiana w `package.json` / `pyproject.toml` bez uzasadnienia | Zapobiega puchnięciu monorepo o zbędne biblioteki wprowadzane ad-hoc. |
| **S7** | **Tenant Leak (IDOR)** | Parametr tenanta czytany z payloadu zamiast z sesji tokena | Chroni architekturę multi-tenant przed dostępem do cudzych danych. |

---

## 🐍 Dlaczego `docs-provenance.py` w Pythonie?

W projektach z TypeScriptem naturalnym odruchem bywa pisanie wszystkiego w Vitest. W HHH `docs-provenance.py` celowo napisano w czystym **Pythonie 3.8+**:
1. **Zero zależności (Zero Dependency)** — korzysta wyłącznie z biblioteki standardowej (`re`, `sys`, `pathlib`, `argparse`).
2. **Błyskawiczne uruchomienie (15ms)** — działa natychmiast w hookach `pre-commit` i lekkich kontenerach CI, bez czekania na `pnpm install` czy pobieranie gigabajtów `node_modules`.
3. **Prawdziwy poliglota** — sprawdza zadania w monorepo łączącym TypeScript, Python, Go czy Rust bez narzucania środowiska Node.

---

## 🤖 Integracja z narzędziami AI

HHH jest natywnie dostosowany do wiodących asystentów programistycznych:

### 1. Claude Code
Plik `AGENTS.md` oraz katalog `skills/` są automatycznie wykrywane. Claude traktuje `AGENTS.md` jako nadrzędną instrukcję systemową repozytorium.

### 2. Antigravity IDE / CLI
Uprząż posiada wbudowany podział ról wg Reguły 7.5:
- **Antigravity IDE (`BUILDER`)** implementuje kod i testy.
- **Antigravity CLI (`GATEKEEPER`)** wykonuje automatyczną Receptę Weryfikacji Manualnej (Reguła 7.11) i przygotowuje surowy stdout dla człowieka.

### 3. Cursor
Dodaj dowiązanie symboliczne do reguł Cursora:
```bash
ln -s AGENTS.md .cursorrules
```

---

## 📁 Zawartość Repozytorium

```
headless-horseman-harness/
├── AGENTS.md                 # System operacyjny agenta (Reguły 7.1 - 7.18)
├── KNOWN_LIMITATIONS.md      # Co uprząż rozwiązuje, a czego NIE zastąpi
├── README.md                 # Główna dokumentacja projektu
├── install.sh                # Skrypt instalacyjny hooków gita
├── docs/tasks/
│   ├── TEMPLATE.md           # Szablon zadania z sekcjami Inception Gate i Subtract
│   └── ACTIVE.md             # Rejestr WIP=1 i protokół Zero Próżni (Reguła 2.9)
├── scripts/
│   ├── adversarial-review.sh # Deterministyczny skaner 7 grzechów głównych
│   ├── check-gate-integrity.sh # Weryfikacja nienaruszalności uprzęży
│   ├── docs-provenance.py    # Zero-dependency Inception Gate checker
│   ├── ub-metrics.sh         # Pomiary złożoności cyklomatycznej i duplikacji
│   └── config.sh             # Konfiguracja ścieżek i flag monorepo
├── skills/                   # Skille inżynierskie
│   ├── grill-me/             # Protokół wywiadu przed przystąpieniem do kodu
│   ├── ub-mode/              # Reguły inżynierskie Uncle Boba
│   ├── code-review/          # Przegląd kodu pod kątem czystej architektury
│   ├── domain-modeling/      # Modelowanie encji i pojęć dziedzinowych
│   └── tdd/                  # Ścisły cykl Red-Green-Refactor
├── e2e/
│   └── visual-regression.spec.ts # Wzorzec testów Playwright dla dwóch viewportów
└── .github/workflows/
    ├── provenance-check.yml  # Bramka CI sprawdzająca Inception Gate
    └── adversarial-review.yml # Bramka CI skanująca pull requesty
```

---

## 📄 Licencja

Projekt objęty licencją **MIT**. Kod wolny do użytku komercyjnego i prywatnego. Zero ukrytej telemetrii, zero połączeń zewnętrznych.
