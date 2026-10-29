# Status napraw po audycie — co jest zmierzone, a co pozostaje otwarte

**Data:** 2026-10-29
**Podstawa:** `AUDYT-KRYTYCZNY.md` (ustalenia), `docs/architecture/MONOREPO-AGENT-PLATFORM.md` (kierunek)
**Dowód:** `bash scripts/selftest.sh` → **46/46 PASS** (macierz PASS/FAIL wszystkich bramek)

---

## 1. Blokery P0 — zamknięte

| # | Ustalenie z audytu | Naprawa | Test w `selftest.sh` |
|---|---|---|---|
| **P0-1** | Skaner zwracał exit 1 przy „✅ PASSED” (`trap cleanup EXIT` nadpisywał kod) | `cleanup()` kończy się `return 0`; jawne `exit` w każdej ścieżce | `brak diffu => PASS (kod wyjścia 0)` |
| **P0-2** | Inception Gate nie widział formatu z własnej dokumentacji (`\| ID \| Tytuł \| Status \|`) | parsowanie komórek tabeli, oba formaty | `format z dokumentacji + brak wywiadu => FAIL` |
| **P0-3** | `Gate Integrity` przepuszczał skaner podmieniony na `exit 0`; 18 pustych zaślepek = „18 reguł” | `harness.lock` (sha256 + **zbiór** ID reguł), usunięcie martwego bloku `origin/main` | `podmiana skanera...`, `usunięcie bramki Inception...`, `18 pustych zaślepek...` |
| **P0-4** | CI wskazywało nieistniejący `harness-template/` i maskowało błędy `\|\| echo` | workflowy na `scripts/`, brak maskowania, `--self-test` jako osobny krok krytyczny | `self-test detektora (5 klas)` + job `adversarial-review.yml` |

## 2. P1 — zamknięte

| # | Ustalenie | Naprawa | Test |
|---|---|---|---|
| **P1-1** | Własny `TEMPLATE.md` nie przechodził własnej bramki | nagłówek toleruje numerację (`## 2. Decyzje ...`) | `własny TEMPLATE.md przechodzi własną bramkę` |
| **P1-2** | Skaner karał za **usuwanie** grzechu (odwrotność 7.17 Subtract) | skan **tylko linii dodawanych**; usunięcie `!important` = brak naruszenia | `brak diffu => PASS` + test Subtract (poniżej) |
| **P1-3** | Raport podawał zmyślone lokalizacje (`apps/admin/src/app/test.tsx:3`) | `path:line` liczone z `+++ b/` i `@@` | `self-test detektora` (lokalizacje 8, 9, 10, 11 — prawdziwe) |
| **P1-4** | Fałszywe negatywy S1/S4 (wielolinijkowe `except: pass`, `catch {}`, sekrety) | maszyna stanów dla `except/catch`; **mawk nie wspiera `{n,}`** → liczenie tokenów funkcją zamiast regexu | `self-test detektora (5 klas)` |
| **P1-5** | Rozjazd etykiet (sekrety = S4, tenant = S7 w kodzie vs README) + odwołania do nieistniejącej reguły 3.5 | etykiety ujednolicone z README, opisy bez wymyślonych numerów | `self-test` (wypisuje klasy S1–S5) |
| **P1-6** | `config.sh` nigdy nie ładowany; `FAST_TRACK_PATTERNS` martwy | `FAST_TRACK_PATTERNS` **usunięte** (martwy kod); `config.sh` opisany jako przykładowy szablon, nie panel konfiguracji | — (usunięcie martwego kodu) |

## 3. Nowe reguły wynikające z Twoich wymagań

| Reguła | Bramka | Co blokuje |
|---|---|---|
| **7.19 Preflight** | `scripts/preflight-gate.py` | kod bez dowodu przeczytania plików (F2), plan od implementacji (F5), brak Subtract (F4), duplikacja symbolu (F7), budżet > 15 plików / 400 LOC (F6), bug bez reprodukcji (F3) |
| **7.20 Budżet i anty-pętla** | `scripts/epistemic-gate.py` (E1–E10) | twierdzenie bez komendy (E1), dowód autorski `echo` (E9), komenda spoza allowlisty (E10), maskowanie `\|\| true` (E10), `confidence: high` bez wykonanego dowodu (E4), usuwanie testów (E5), hipoteza bez falsyfikatora (E7) |

## 4. Warunki wpięcia (spełnione)

| Warunek z audytu | Stan |
|---|---|
| Bramki w pre-commit / pre-push | `scripts/install-hooks.sh` (z backupem cudzych hooków) |
| Bramki w CI | `.github/workflows/gates.yml` + `adversarial-review.yml` |
| Downstream `--execute` z allowlistą narzędzi | E10 (echo, `\|\| true`, `\|\| echo`, komendy spoza listy → BLOCKING) |
| Integralność bramek | `harness.lock` + `gate-lock.sh --check` w pre-commit i CI |
| Uprząż testuje siebie | `scripts/selftest.sh` — 26 asercji, uruchamiane w CI |
| Brak wyjątków bez terminu | `.adversarial-allow`: `RULE glob owner=@kto reason="..." expires=RRRR-MM-DD`; brak terminu lub po terminie ⇒ BLOCKING |

## 3a. Punkty decyzyjne (Reguła 7.21) — „stop i grill przed każdym krokiem"

| Element | Plik | Co robi |
|---|---|---|
| Walidator decyzji (D1–D10) | `scripts/decision-gate.py` | wymaga artefaktu podpisanego przez człowieka; **zakaz samo-akceptacji (D7)**; fraza `Potwierdzam:` (D8); wygasanie (D9); nieodwracalność (D10) |
| Grill interaktywny | `decision-gate.py --ask` | zadaje pytania w terminalu i zapisuje decyzję; poza TTY **odmawia** (nie podejmie decyzji proces w tle) |
| Orkiestrator kroków | `scripts/hhh-run.py` | wywołuje wszystkie bramki po kolei i **zatrzymuje się** na decyzji; kody: 0 zamknięte, **1 robota agenta**, **3 STOP dla człowieka**, 4 brak postępu, 2 błąd środowiska |
| Schemat | `docs/decisions/SCHEMA.md` | trzy punkty: `scope` → `approach` → `accept` |
| Wzorce | `docs/decisions/CP-150/` (poprawna), `CP-666.gaming/` (samo-akceptacja) | dowód, że bramka rozróżnia |

**Przebieg zmierzony (kopia repo, prawdziwe commity):** brak decyzji `scope` ⇒ exit **3** → podpis ⇒ bramka preflight ⇒ exit **1** → artefakt preflight ⇒ exit **3** (`approach`) → podpis ⇒ exit **1** („brak zmiany — to robota agenta") → kod + dowody ⇒ exit **3** (`accept`) → podpis ⇒ exit **0**.

## 4a. Co wykryłem dopiero przy wdrażaniu (i naprawiłem)

| Znalezisko | Klasa błędu | Naprawa |
|---|---|---|
| `mawk` nie wspiera interwałów `{10,}` — wzorzec na sekrety **nigdy** nie mógł dopasować | dokładnie ten błąd, który audyt zarzucał HHH: wzorzec wygląda dobrze, nie działa | liczenie długości tokenu funkcją zamiast regexu (`toklen`) |
| Skaner karał własne stringi testowe (sekrety i `catch {}` w pliku skryptu) | samoreferencja | fixture'y przeniesione do `tests/fixtures/negative/` + wyjątek w `.adversarial-allow` (z właścicielem i terminem) |
| Skaner flagował **przykłady kodu w dokumentacji** (6 fałszywych blokad na `AUDYT-KRYTYCZNY.md`) | fałszywe alarmy → presja na `--no-verify` | S1/S3 tylko dla plików kodu; S4 w `docs/**` i `*.md` = ADVISORY |
| `chmod +x` z instalatora był liczony jako „kod w indeksie” i wyzwalał preflight | tryb pliku ≠ zmiana treści | hook liczy `git diff --cached --numstat` (tylko realne zmiany linii) |
| Twierdzenie „integralność blokuje `--no-verify`” było nieprawdziwe (wiadomość commita nie zawiera tej flagi) | twierdzenie niemożliwe do spełnienia | strukturalne wykrywanie **skutku**: commit kodu bez artefaktu preflight, gdy bramka już istniała. Lokalnie `--no-verify` pozostaje niewykrywalne — ochrona w CI (required checks) |
| Własny fixture epistemiczny przestał być prawdą po naprawie P1-1 | dowody się starzeją | bramka zgłosiła `E3: expected 'exit=1' NIE wystąpił` i wymusiła aktualizację — to jej zaleta, nie błąd |
| **Skaner złapał mój własny silent fallback** w `hhh-run.py` (`except JSONDecodeError: state = {}`) | dokładnie klasa S1, którą zwalcza | uszkodzony stan teraz kończy się `exit 2` z komunikatem „usuń świadomie" (fail-closed), nie cichym zerowaniem |
| `has_change` nie widział **plików nieśledzonych** — agent tworzący nowe pliki „nie zmieniał nic" | fałszywy STOP | liczy też `git ls-files --others` po ścieżkach kodu |
| Domyślna baza `origin/main` w świeżym sandboksie **nie jest przodkiem HEAD** → fałszywe „zmiana istnieje" | fałszywy PASS kroku `implement` | `resolve_base()`: preferowana → origin/main → main → master → HEAD~1, zawsze z testem `merge-base --is-ancestor` |
| `chmod +x` (instalator) wyzwalał preflight | tryb pliku ≠ zmiana treści | hook liczy `--numstat` |

## 4b. Trymowanie: Hilux vs Full (koszt, nie liczba funkcji)

Zmierzone narzuty po dodaniu wszystkich bramek: **2281 linii skryptów, 21 reguł, 9 kroków, 3 podpisy, ~150 linii JSON na bilet**. To było Ferrari. Po trymowaniu:

| | hilux (domyślnie) | full |
|---|---|---|
| kroki | 7 | 9 |
| podpisy człowieka / bilet | 2 | 3 |
| bramki w pętli | 3 | 6 |
| pre-commit (zmierzone) | 141 ms | 197 ms |
| artefakty do wypełnienia | preflight + 2 decyzje + evidence | + approach |

Wycięte w hilux: decyzja `approach` (zwykle wynika ze `scope` — trzeci podpis to biurokracja), krok `close` (integralność leci w pre-commit), Inception i dowody z pre-commit (przeniesione do CI).

**Reguła utrzymania:** bramka z > 5% fałszywych alarmów w tygodniu **wypada**, nie jest dostrajana. Fałszywe alarmy uczą `--no-verify` i zabijają zaufanie do wszystkich pozostałych bramek — to zmierzone w audycie, nie teoria.

## 5. Co pozostaje otwarte (uczciwie)

0. **Zmiana pliku bramki wymaga przeliczenia `harness.lock` w tym samym commicie.** To celowe (uniemożliwia ciche „przy okazji”), ale bywa zaskakujące — komunikat bramki mówi to wprost.
1. **`harness.lock` da się przeliczyć lokalnie.** Ochroną jest CODEOWNERS na `scripts/**`, `AGENTS.md` i branch protection — nie sam plik. Bez tego jedna osoba/agent z prawem zapisu może zalegalizować własną zmianę bramki.
2. **`--execute` nie dowodzi jakości testu.** Dowodzi, że komenda z allowlisty została uruchomiona i jej wynik zgadza się z deklaracją. Słaba asercja nadal przejdzie — dlatego potrzebne są mutacje (§4.4 architektury) i ukryte testy akceptacyjne.
3. **Kłamstwo spójne wewnętrznie nadal przechodzi tryb statyczny.** To jest wpisane w `selftest.sh` jako **oczekiwane** zachowanie (`spójne kłamstwo przechodzi tryb statyczny (znane)`), żeby nikt nie pomylił tego z PASS-em jakościowym. Dlatego CI zawsze używa `--execute`.
4. **Liczby w case study CityPulse** nadal nie domykają się (77% vs 80.8% vs 82.1%). Nie ruszałem marketingu — to decyzja autora, nie bramki.
5. **Człowiek może klepnąć decyzję bez czytania.** Skrypt nie odróżni świadomej zgody od „enter, enter". Ograniczają to: ≥ 2 opcje z ceną, `must_not`, obserwowalne `done_when`, wygasanie i osobny plik decyzji w historii git (widać kto i kiedy).
6. **Cała walidacja jest syntetyczna.** 46/46 dowodzi, że bramki zachowują się zgodnie ze specyfikacją — **nie** że pomagają w prawdziwym monorepo. Hilux jest sprawdzony przez 500 tys. km, nie przez kartę katalogową. Pierwszy realny test: 2 tygodnie, 5 biletów, jeden prawdziwy agent.
7. **Reguły 7.1–7.16** nadal są w większości umową, nie kodem. Zmierzone egzekwowanie: 7.2 (S3, E5/E6), 7.8/7.9 (S1), 7.10 (S7 opt-in), 7.17 (F4, F5), 7.18 (S5, Inception), 7.19, 7.20. Reszta = review człowieka.

## 6. Jak sprawdzić to samodzielnie w 60 sekund

```bash
bash scripts/selftest.sh          # 26 asercji: PASS/FAIL każdej bramki
bash scripts/gate-lock.sh --check # integralność bramek
python3 scripts/preflight-gate.py --file docs/preflight/CP-666.gaming.json   # exit 1
python3 scripts/epistemic-gate.py --file docs/epistemic/CP-142.example.json --execute  # exit 0
```
