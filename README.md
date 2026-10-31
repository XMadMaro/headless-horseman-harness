<img width="2020" height="1228" alt="Headless Horseman Harness" src="https://github.com/user-attachments/assets/5306b6c3-e2a4-4fd9-a5f7-90a0ca766686" />

# 🐎 Headless Horseman Harness (HHH)

**Polski** · [English](README.en.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Battle Tested](https://img.shields.io/badge/Battle--Tested-CityPulse%20(GovTech)-success)](https://github.com/XMadMaro/CityPulseV2)
[![Zero LLM Gates](https://img.shields.io/badge/Gates-Deterministic%20(Zero%20LLM)-orange)](#-5-warstw-ochrony--co-dostajesz-w-pudełku)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#)

> **„Nie przyspiesza pisania kodu. Kasuje 90% czasu refaktoru.”**  
> **Ścina głowy halucynującym agentom, zanim ich kod trafi do gałęzi `main`.**

Template dyscypliny architektonicznej dla dużych projektów monorepo (TS + Python, Nx/Turborepo/pnpm/uv), w których zjawisko **`agent rot`** (degradacja kodu przez AI) zazwyczaj paraliżuje rozwój po 2–3 tygodniach.

Zamiast kolejnego szablonu z gotowym frameworkiem (Next.js + Prisma) dostajesz **deterministyczną uprząż inżynierską**: bramki z kodem wyjścia, hash-pinem i własnym samotestem.

**Uczciwa skala (zmierzona, nie deklarowana):** 7 bramek blokujących (`gate-lock`, Inception, Preflight, Epistemic, Decision, Adversarial, selftest) + 2 reguły procesu (7.19 myśl-przed-kodem, 7.20 budżet/anty-pętla). Nie „fizycznie uniemożliwiają” — **podnoszą cenę kłamstwa i obejścia**. Pozostałe reguły to umowa społeczna, której pilnuje review człowieka.
Pełny stan: `docs/architecture/GATE-FIXES.md`. Dowód: `bash scripts/selftest.sh` → 52/52.

---

## 🛻 Profil: Hilux czy Full (domyślnie Hilux)

Uprząż ma dwa tryby — **nie musisz włączać wszystkiego**. Wybór jest w pliku `hhh.profile`:

| | **hilux** (domyślnie) | **full** |
|---|---|---|
| Kroki w pętli | 7 | 9 |
| Punkty decyzyjne (podpisy człowieka) | **2** (`scope`, `accept`) | 3 (+`approach`) |
| Bramki w pętli | 3 (preflight, skan diffu, dowody) | 6 |
| Pre-commit (zmierzone) | **~140 ms** — pomija Inception i dowody | ~200 ms |
| Dla kogo | 1–5 osób, monorepo bez RLS, chcesz dowozić | multi-tenant/GovTech, długa historia regresji |

```bash
echo "profile=hilux" > hhh.profile   # domyślnie i tak tyle jest
```

**Zasada Hiluxa:** bramka, która w tygodniu daje > 5% fałszywych alarmów, **wypada** — nie jest „dostrajana”. Więcej bramek ≠ większa kontrola; to Ferrari, które stoi w serwisie.

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

## 🧩 Wymagany Stos Narzędziowy (Ecosystem & Prerequisites)

Headless Horseman Harness nie działa w próżni. Aby fizycznie odciąć agentów od halucynacji, amnezji i ślepego zgadywania, uprząż opiera się na 4 filarach ekosystemu:

| Filar / Narzędzie | Rola w uprzęży | Co daje i dlaczego jest wymagane? |
|---|---|---|
| **Nx Monorepo (`nx`)** | *Orkiestracja & Bramki CI* | Weryfikacja pakietów (`nx test <project>`) oraz bramka zmian dotkniętych (`nx affected -t test,lint,typecheck`). Zabezpiecza przed testowaniem tylko pojedynczych plików. |
| **Codebase Memory Graph (`codebase-memory-mcp`)** | *Nawigacja AST (Zero Blind Grep)* | Serwer MCP grafu bazy kodu. Pozwala agentom śledzić wywołania w górę i w dół (`trace_path`), badać symbole (`search_graph`) i pobierać snipety (`get_code_snippet`) bez zaśmiecania okna kontekstu niecelnymi grepami. |
| **Lokalny silnik BM25 (`xerj`)** | *Szybkie wyszukiwanie pełnotekstowe* | Lokalny demon BM25 (`:8080` REST / `:9200` ES-compat). Błyskawicznie przeszukuje kod i dokumentację (`xerj search --prefix cp "<query>"`), oszczędzając tokeny i redukując czas odpowiedzi agenta. |
| **Pamięć Długoterminowa ([Hindsight](https://hindsight.vectorize.io/))** | *Trwała pamięć architektoniczna* | Serwer MCP eliminujący amnezję agentów między sesjami. Przechowuje decyzje projektowe (ADR), ustalenia biznesowe i stan inicjatyw (`hindsight_search_knowledge_pages`), chroniąc przed ponownym negocjowaniem raz podjętych ustaleń. |

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

## 🛡️ 8 Bramek — co realnie blokuje commit

```text
  [ Intencja człowieka ]
        │
        ▼
  Inception Gate .......... wywiad + WIP=1
        │
        ▼
  Preflight (7.19) ........ czy pliki PRZECZYTANE? cytat z każdego
        │                   plan od subtract/diagnose, brak duplikacji
        ▼
  🛑 DECYZJA: scope ....... podpis człowieka
        │
        ▼
  Implementacja (agent) ... kod + test RED→GREEN
        │
        ▼
  Adversarial Review ...... 7 grzechów, tylko linie dodawane, plik:linia
        │
        ▼
  Epistemic (7.20) ........ dowody WYKONANE (--execute), nie zadeklarowane
        │
        ▼
  🛑 DECYZJA: accept ...... podpis człowieka (nic bez odbioru)
        │
        ▼
  Gate Integrity .......... harness.lock: podmiana bramki wykryta
        │
        ▼
      [ Commit do main ]
```

Sterowanie całością: `python3 scripts/hhh-run.py --ticket CP-xxx --run`
(exit 3 = STOP, potrzebna decyzja człowieka · exit 1 = robota agenta)

| # | Bramka | Narzędzie | Co dokładnie blokuje |
|---|---|---|---|
| **1** | **Inception** | `docs-provenance.py` | `IN_PROGRESS` bez udokumentowanego wywiadu (`## Decyzje z wywiadu`, ≥50 znaków, źródło + obsługa błędu + Must NOT) oraz więcej niż jedno zadanie w toku (WIP=1). |
| **2** | **Preflight (7.19)** | `preflight-gate.py` | Kod bez **cytatu z każdego dotykanego pliku** (dowód lektury, ±10 linii). Plan zaczynający się od `subtract`/`diagnose`. Brak sekcji Subtract. Duplikacja istniejącego symbolu. Budżet >15 plików / >400 LOC. |
| **3** | **Decision: scope (7.21)** | `decision-gate.py` | Start bez decyzji podpisanej przez człowieka: ≥2 opcje z ceną, `must_not`, obserwowalne `done_when`, fraza `Potwierdzam:`. **Zakaz samo-akceptacji (D7).** |
| **4** | **Adversarial** | `adversarial-review.sh` | 7 grzechów: silent fallback (`except: pass`, `catch {}`), `!important`, asercje pozorne, sekrety, `DROP` bez zatwierdzenia, zależności bez uzasadnienia, tenant leak (opt-in). **Tylko linie dodawane** — usunięcie grzechu nie jest karane (7.17). |
| **5** | **Epistemic (7.20)** | `epistemic-gate.py` | Twierdzenie bez `cmd`/`expected`/`observed`. Dowód autorski (`echo`), maskowanie (`\|\| true`), komenda spoza allowlisty. `confidence: high` bez **wykonanego** dowodu. Hipoteza bez falsyfikatora. |
| **6** | **Decision: accept (7.21)** | `decision-gate.py` | Zamknięcie bez odbioru przez człowieka. Decyzja nieodwracalna bez `acknowledged_irreversible` + `blast_radius`. Decyzja po terminie ważności. |
| **7** | **Gate Integrity** | `gate-lock.sh` + `check-gate-integrity.sh` | Podmiana bramki (hash w `harness.lock`), usunięcie bramki, 18 pustych zaślepek zamiast reguł, wyjątki bez terminu. |
| **8** | **Self-test** | `selftest.sh` | Regresja samej uprzęży: każda bramka musi **przejść** i **zablokować** to, co deklaruje (52 asercje). |

Poza tą ósemką: `acceptance-gate.py` — testy akceptacyjne, których agent **nie widzi** (`hidden/`, sha256 + lock, podmiana = STOP). To nie jest bramka na deklaracje, tylko na produkt.

**To nie są bramki** (świadomie): `ub-mode` to zestaw zasad w `AGENTS.md` (7.17) plus raport metryk, a `e2e/visual-regression.spec.ts` to **wzorzec** wymagający runnera Playwright — bez `package.json`, `playwright.config.ts` i baseline'ów nie chroni niczego.

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
# 1. Skopiuj pliki uprzęży (install.sh NIE pobiera nic z sieci — instaluje hooki w checkoucie)
npx degit XMadMaro/headless-horseman-harness/. ./_harness && cp -r ./_harness/. . && rm -rf ./_harness

# 2. Zainstaluj hooki (pre-commit: integralność + preflight; pre-push: skaner + decyzje)
bash install.sh

# 2b. Włącz CI — GOTOWE workflowy leżą w docs/ci/ (token bez uprawnień `workflows`
#     nie może zapisywać .github/workflows; bez tego kroku CI nie sprawdza bramek)
cp docs/ci/gates.yml docs/ci/adversarial-review.yml .github/workflows/

# 3. Weryfikacja: każda bramka musi przejść I zablokować to, co ma blokować
bash scripts/selftest.sh                 # 26 asercji, oczekiwane: 26/26
bash scripts/gate-lock.sh --check        # integralność bramek (hash-pin)
bash scripts/adversarial-review.sh origin/main     # skan grzechów (tylko linie dodawane)
python3 scripts/docs-provenance.py --check         # wywiad + WIP=1
python3 scripts/preflight-gate.py --ticket CP-XXX  # myśl i posprzątaj przed kodem
python3 scripts/epistemic-gate.py --ticket CP-XXX --execute  # dowody wykonane

# 4. Prowadzenie krok po kroku (zatrzymuje się na decyzjach człowieka)
python3 scripts/hhh-run.py --ticket CP-XXX --status   # plan kroków
python3 scripts/hhh-run.py --ticket CP-XXX --run      # 0=zamknięte, 1=robota agenta, 3=STOP: decyzja człowieka
python3 scripts/decision-gate.py --ask --ticket CP-XXX --step scope   # grill w terminalu
```

> Włączanie bram opcjonalnych jest jawne: Preflight działa, gdy istnieje katalog `docs/preflight/`, Epistemic — gdy `docs/epistemic/`. To celowe: brak tarcia przy adopcji, ale też brak cichego „pominięto”.

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
Uprząż posiada wbudowany podział ról wg Reguły 7.11:
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
├── AGENTS.md                 # System operacyjny agenta (8 reguł: 7.4-7.21)
├── KNOWN_LIMITATIONS.md      # Co uprząż rozwiązuje, a czego NIE zastąpi
├── README.md                 # Główna dokumentacja projektu
├── install.sh                # Skrypt instalacyjny hooków gita
├── docs/tasks/
│   ├── TEMPLATE.md           # Szablon zadania z sekcjami Inception Gate i Subtract
│   └── ACTIVE.md             # Rejestr WIP=1 i protokół Zero Próżni (Reguła 2.9)
├── harness.lock              # Hash-pin bramek (integralność, nie licznik nagłówków)
├── scripts/
│   ├── adversarial-review.sh # Skaner grzechów: tylko linie dodawane, prawdziwe plik:linia
│   ├── check-gate-integrity.sh # Weryfikacja nienaruszalności uprzęży (woła gate-lock)
│   ├── gate-lock.sh          # Generowanie/weryfikacja harness.lock (sha256 + zbiór reguł)
│   ├── docs-provenance.py    # Inception Gate: wywiad + WIP=1 (fail-closed)
│   ├── preflight-gate.py     # 7.19: dive/subtract/duplikacja/budżet przed kodem
│   ├── epistemic-gate.py     # 7.20: dowody wykonywalne (E1-E10)
│   ├── decision-gate.py      # 7.21: punkty decyzyjne, zakaz samo-akceptacji (D1-D10)
│   ├── hhh-run.py            # orkiestrator: bramki krok po kroku, STOP na decyzji
│   ├── selftest.sh           # Macierz PASS/FAIL wszystkich bramek (52 asercje)
│   ├── acceptance-gate.py    # Testy poza zasięgiem agenta (tamper=STOP, bez oracle)
│   ├── install-hooks.sh      # Hooki git z backupem cudzych
│   ├── ub-metrics.sh         # Pomiary złożoności cyklomatycznej i duplikacji
├── docs/preflight/           # Artefakty 7.19 (schemat + wzorce: uczciwy / frankenstein)
├── docs/epistemic/           # Artefakty 7.20 (schemat + wzorce: uczciwy / gra w bramkę)
├── docs/decisions/           # Artefakty 7.21 (schemat + wzorce: podpisana / samo-akceptacja)
├── docs/architecture/        # Platforma monorepo, wymuszanie krytycyzmu, status napraw
├── docs/research/            # Dowody: jak duże projekty degradują się pod AI (i co działa)
├── hidden/                   # Testy akceptacyjne, których agent NIE widzi (sha256 + lock)
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
