# Audyt krytyczny: Headless Horseman Harness (HHH)

**Przedmiot:** `XMadMaro/headless-horseman-harness` @ `7644e54` (28 plików, 1 commit w historii)
**Data:** 2026-10-29
**Zakres:** całość repozytorium — dokumentacja, 5 skryptów bramkujących, 5 skilli, wzorzec E2E, 2 workflowy CI
**Metoda:** pełna lektura kodu + **wykonanie każdej bramki** i 12 eksperymentów falsyfikacyjnych w kopiach repozytorium (`/tmp`, repo źródłowe nietknięte)

---

## 0. Werdykt w jednym akapicie

To nie jest próżny projekt: pomysł (deterministyczne, nieregexowe-naiwne bramki + rozdział ról człowiek/agent) jest trafny, a `KNOWN_LIMITATIONS.md` to rzadka oznaka intelektualnej uczciwości. Ale **warstwa egzekwowania nie robi tego, co deklaruje dokumentacja**. Trzy z pięciu „warstw ochrony” są w praktyce martwe: bramka Inception **nigdy nie może się uruchomić na formacie, który sama narzuca**, kontroler integralności **przepuszcza skaner podmieniony na `exit 0`**, a skaner grzechów **zawsze zwraca kod wyjścia 1** — czyli przy werdykcie „✅ PASSED” blokuje każdy push. Do tego dochodzi odwrócenie intencji reguły 7.17: skaner **karze za usuwanie** grzechów, które każe usuwać.

Skutek przewidywalny: użytkownik po dwóch zablokowanych pushach z zielonym raportem sięgnie po `--no-verify` — dokładnie ryzyko #2 opisane w `KNOWN_LIMITATIONS.md`. Uprząż sama produkuje warunki własnej erozji.

**Ocena ważona deklaracjami projektu:** koncepcja 8/10, dokumentacja intencji 8/10, **zgodność implementacji z deklaracją 2/10**, odporność na obejście 2/10, jakość dowodów 3/10.

---

## 1. INTERPRETACJA — co ten projekt twierdzi, że robi

Rekonstrukcja tezy z dokumentów (nie moja ocena, tylko odczyt):

| Deklaracja | Źródło | Charakter twierdzenia |
|---|---|---|
| „5 mechanicznych warstw kontroli, które **fizycznie uniemożliwiają** agentom zgadywanie wymagań, mockowanie testów i maskowanie błędów” | README | twierdzenie absolutne, falsyfikowalne |
| „Ten sam diff daje **zawsze identyczny werdykt**” | README | twierdzenie o determinizmie |
| „Każde naruszenie wykrywa `scripts/check-gate-integrity.sh`” | AGENTS.md (nagłówek) | twierdzenie absolutne |
| „Blokuje flagi `--no-verify`” | README, warstwa 5 | twierdzenie logicznie niemożliwe (patrz §4.6) |
| „-95% czasu refaktoru”, „77% redukcji”, „kasuje 90% czasu refaktoru” | README | twierdzenie ilościowe o przyczynowości |
| „Zero ukrytej telemetrii, **zero połączeń zewnętrznych**” | README | twierdzenie weryfikowalne w kodzie |
| „Python 3.8+”, „uruchomienie 15 ms” | README | twierdzenie techniczne |
| „Harness gwarantuje higienę wykonania, nie słuszność kierunku” | KNOWN_LIMITATIONS | twierdzenie **właściwie skalibrowane** |

Interpretacja intencji: autor nie sprzedaje frameworka, sprzedaje **dyscyplinę procesu** dla agentów AI w dużych monorepo. Bramki mają być tanie (15 ms), deterministyczne (zero LLM) i odporne na „grzeczne kłamstwo” modelu. To spójna i sensowna intencja. Problem zaczyna się przy pytaniu: *czy implementacja realizuje intencję?*

---

## 2. ANALIZA — mapa deklaracji na kod

### 2.1. Reguła → egzekwowanie: 18 reguł, ~5 z jakimkolwiek kodem

Kluczowe pytanie audytu: ile z 18 reguł `AGENTS.md` ma ścieżkę kodu, która **może realnie zatrzymać commit/push**?

| Reguła | Temat | Egzekwowanie mechaniczne |
|---|---|---|
| 7.1 | Protokół flag (DRAFT/IN_PROGRESS/…) | ❌ brak (a regex bramki i tak nie trafia — §2.2) |
| 7.2 | Dowód RED→GREEN | ⚠️ pośrednio: S3 banuje `toBeDefined()`/`toBeTruthy()`/`assert True` |
| 7.3 | Treść niezaufana | ❌ brak |
| 7.4 | Bariery > tekst | — meta |
| 7.5 | Rozdział ról BUILDER/GATEKEEPER | ❌ brak |
| 7.6 | Statusy, podpis `Zatwierdzam:` | ❌ brak (`grep` w `scripts/` = 0 wystąpień) |
| 7.7 | Worktree, ACTIVE niepusta | ❌ brak |
| 7.8 | Budżet kontekstu (`xerj`/`codebase-memory`) | ❌ brak; narzędzia spoza repo |
| 7.9 | Twardy kontrakt anty-placebo | ⚠️ S1 — wąski (§3.3) |
| 7.10 | Jedna brama, Fail-Closed | ⚠️ S4 tenant — opt-in, 2 nazwy pól |
| 7.11 | Bramka weryfikacji manualnej | ❌ brak (tylko placeholder w szablonie) |
| 7.12 | Plan `plik:linia` przed kodem | ❌ brak |
| 7.13 | Stop premature execution (/grill-me) | ❌ brak |
| 7.14 | Zakaz `page.route` w E2E | ❌ brak (0 wystąpień w `scripts/`) |
| 7.15 | Inwariant przepływu danych (ghost context) | ⚠️ tylko przez nazwy pól w S4 |
| 7.16 | Pojedynczy silnik | ❌ brak |
| 7.17 | ub-mode: Subtract, Attack Premise, metryki | ⚠️ `ub-metrics.sh` jest **report-only**, progi nie blokują; Subtract jest **karany** (§3.2) |
| 7.18 | Inception Gate, Adversarial, FAST_TRACK, secrets, DROP | ⚠️ S5 działa; S4-sekrety wąsko; Inception **zepsuty**; FAST_TRACK **dziurawy** |

**Wniosek analityczny:** ~12–13 z 18 reguł to czysta deklaracja w Markdownie. README nazywa to „5 mechanicznych warstw, które fizycznie uniemożliwiają”. Uczciwy opis brzmiałby: „2 działające filtry, 3 częściowo działające, 13 reguł jako umowa społeczna”.

### 2.2. Sprzeczność #1: bramka Inception vs. format, który sama narzuca

`docs/tasks/ACTIVE.md` i `TEMPLATE.md` definiują tabelę `| ID | Tytuł | Status | Track | Właściciel |`. Regex w `docs-provenance.py:91`:

```python
re.findall(r"\|\s*(CP-\d+)\s*\|\s*IN_PROGRESS", text, re.I)
```

Wymaga `IN_PROGRESS` **bezpośrednio po ID**, więc nie trafia w format z kolumną „Tytuł”.

**Dowód empiryczny (wykonany):**

| Zawartość `ACTIVE.md` | Werdykt bramki |
|---|---|
| `\| CP-007 \| Endpoint /health \| IN_PROGRESS \| …` (format z dokumentacji, CP **bez wywiadu**) | `Brak zadań IN_PROGRESS — PASS`, exit 0 |
| `\| CP-007 \| IN_PROGRESS \|` (format wymyślony przeze mnie) | `INCEPTION GATE FAILED`, exit 1 |

Bramka działa **wyłącznie** na formacie, którego w repozytorium nie ma. Efekt: „warstwa 1” nie istnieje w praktyce, a raport pokazuje zielone światło. To najgroźniejszy typ błędu w narzędziu bezpieczeństwa — **fail-open z komunikatem sukcesu**.

### 2.3. Sprzeczność #2: własny szablon nie przechodzi własnej bramki

```
$ python3 scripts/docs-provenance.py --file docs/tasks/TEMPLATE.md
FAIL: docs/tasks/TEMPLATE.md -> brak sekcji 'Decyzje z wywiadu (/grill-me)'
```

Przyczyna: bramka wymaga nagłówka `## Decyzje z wywiadu (/grill-me)`, a szablon ma `## 2. Decyzje z wywiadu (/grill-me) — WYMAGANE…`. Fallback (dopasowanie podłańcucha) też nie łapie, bo różni się prefiks. Pierwszy kontakt użytkownika z uprzężą to **sprzeczność**: szablon każe pisać numerowane sekcje, bramka numeracji nie akceptuje, a komunikat błędu mówi „brak sekcji”, nie „zły format nagłówka”. Klasyczna droga do `--no-verify`.

### 2.4. Sprzeczność #3: „Gate Integrity” nie chroni bramek

Eksperyment (kopia repo): podmieniłem `scripts/adversarial-review.sh` na `exit 0`, usunąłem `docs-provenance.py`, a 18 realnych reguł zastąpiłem 18 pustymi nagłówkami `## 7.N. placeholder`.

```
✅ GATE INTEGRITY PASSED (reguły: 18)   exit=0
```

Trzy przyczyny w kodzie:

1. **Licznik zamiast treści** (`check-gate-integrity.sh:15-19`): liczy nagłówki `^## 7\.`, nie sprawdza ich treści ani sum kontrolnych skryptów. 18 pustych zaślepek = 18 „reguł”.
2. **Brak weryfikacji integralności plików** — skrypt sprawdza tylko **istnienie** `adversarial-review.sh`, nigdy jego treści.
3. **Usunięcie bramki Inception nie jest błędem** (`:33-36`): brak `docs-provenance.py` to żółte ostrzeżenie bez `WEAKENED=1`. Czyli najważniejszą bramkę można skasować i dostać PASS.
4. **Martwy mechanizm anty-regresji** (`:39-46`): porównanie z `origin/main` szuka `^\*\*Reguła ` — w `AGENTS.md` nie ma ani jednego takiego nagłówka (są `## 7.x`), więc `MAIN_COUNT` zawsze wynosi 0 i warunek nigdy nie zachodzi. Kod wygląda na zabezpieczenie, ale jest nieosiągalny.

### 2.5. Sprzeczność #4: „deterministyczny” ≠ „poprawny” — skaner grzechów

Skaner jest deterministyczny (potwierdzam: powtórzone przebiegi dają identyczny wynik). Ale determinizm osiągnięto przez `grep` na całym diffie, co daje dwa rodzaje błędu:

**(a) Fałszywe alarmy na usuwaniu kodu.** S2–S5 greppują **każdą** linię diffu, także usuwane (`-`). Eksperyment: jedyna zmiana w diffie to *usunięcie* `!important` — dokładnie to, czego wymaga „Subtract Before You Add” (7.17):

```
-  .card { color: red !important; }
+  .card { color: red; }
→ BLOCKING | S2: Destructive CSS | apps/admin/src/app/test.tsx:3
```

Bramka **karze za naprawę**. To nie jest drobiazg: reguła 7.17 jest osią całej filozofii „najpierw usuń, potem dodawaj”.

**(b) Fałszywe negatywy na realnych wzorcach.** Wstrzyknąłem 4 kanoniczne „grzechy” z narracji README („ciche `catch {}`”, Python `except: pass`) w realistycznej, wieloliniowej postaci:

```python
except Exception as e:
    pass
except BaseException:
    return None
```
```ts
catch (e) { /* ignorujemy */ }
catch { return undefined; }
```

Werdykt: **wszystkie cztery przepuszczone** (BLOCKING=1, i to tylko za `ghp_`). Regex S1 wymaga `pass`/`return None` **w tej samej linii** co `except`, a `catch {}` — literalnie pustego nawiasu. Czyli skaner nie łapie form, które są w praktyce najczęstsze. Analogicznie S4 przepuścił `AKIA…` (klucz AWS) i `password='…'` (pojedyncze cudzysłowy), choć README obiecuje wzorzec `password=`.

**(c) Zmyślone lokalizacje w raporcie.** W trybie `--test-negative` S2 raportuje `apps/admin/src/app/test.tsx:3` — to **zahardkodowany string** (`:90`, `xargs -I{} echo "apps/admin/src/app/test.tsx:3"`), niezależny od treści diffu. S3/S1 raportują `apps/...:3`, `apps/...:2`. Narzędzie, którego celem jest walka z halucynowaniem dowodów, **samo generuje fikcyjne dowody**: plik `apps/admin/src/app/test.tsx` nie istnieje w tym repozytorium.

### 2.6. Sprzeczność #5: skaner zawsze zwraca 1

```
$ bash scripts/adversarial-review.sh     # pusty diff
✅ ADVERSARIAL REVIEW PASSED: Brak zmian.
$ echo $?
1
```

Przyczyna (zredukowana do minimum i potwierdzona reprodukcją):

```bash
set -euo pipefail
cleanup(){ [[ -n "" ]] && rm -rf "$x"; }   # ostatnia komenda zwraca 1
trap cleanup EXIT
exit 0
# → kod wyjścia procesu: 1
```

`trap cleanup EXIT` nadpisuje kod wyjścia statusem ostatniego polecenia w funkcji sprzątającej. Konsekwencja: hook `pre-push` (`install.sh:31-36`, `set -e`) **blokuje każdy push, nawet przy zerze naruszeń**, a użytkownik widzi „PASSED”. W CI ten sam efekt oznacza czerwoną gałąź bez widocznej przyczyny.

### 2.7. Sprzeczność #6: samo-testy, które nie mogą zawieść

`--test-negative` deklaruje „wstrzyknięto **4** zatrute wzorce”, raportuje **5** naruszeń, kończy „✅ SUKCES” i zwraca **exit 1**. Dokumentacja jest z tym niezgodna w trzech miejscach:

| Źródło | Twierdzenie | Rzeczywistość |
|---|---|---|
| `AGENTS.md` 7.11 | „`--test-negative` musi wykryć **4** naruszenia” | 5 |
| `TEMPLATE.md:78` | „BLOCKING=**4**, poprawnie zablokowano S1,S2,S5,S6” | BLOCKING=5, zestaw S1,S2,S3,S6,S5 |
| `README` §7 grzechów | sekrety = **S4**, tenant = **S7** | kod emituje sekrety = **S6**, tenant = **S4** |
| kod, komunikat S1 | odwołanie do „(7.16)” | 7.16 to „Pojedynczy silnik”, nie silent fallback |
| kod, komunikat S4 | odwołanie do „(3.5)” | w repo nie ma sekcji 3 (ani reguły 3.5) |

Głębszy problem metodologiczny: test negatywny sprawdza, czy **5 regexów zadziałało na 5 ręcznie dobranych stringach**. To tautologia — nie weryfikuje pokrycia detektora względem rzeczywistości. Tymczasem ten sam harness wymaga od agenta dowodu RED→GREEN „przeciw fałszywym testom” (7.2). **Uprząż nie stosuje wobec siebie reguły, którą egzekwuje** — i to jest najpoważniejszy zarzut procesowy w całym audycie.

### 2.8. Sprzeczność #7: „Zero połączeń zewnętrznych” i „konfiguracja”

- README: „zero połączeń zewnętrznych”. `scripts/ub-metrics.sh:24` robi `git clone https://github.com/unclebob/…`. Do tego `npx degit`, `curl | bash` w Quick Start i GitHub Actions. Twierdzenie nieprawdziwe (samo klonowanie jest obronione przypięciem SHA — patrz §5, ale to inna kwestia).
- `scripts/config.sh` — obszernie opisany w README i AGENTS.md jako panel konfiguracji (`ENABLE_TENANT_CHECK`, `DOCS_GLOB`, `APPS_GLOB`). **Niktóry skrypt go nie ładuje** (`grep`: 0 wystąpień `source`). Edycja pliku nie zmienia niczego. Jednocześnie `FAST_TRACK_PATTERNS` w `docs-provenance.py:15` jest zdefiniowane i **nigdy nieużyte** — martwy kod w narzędziu, które samo każe usuwać martwy kod (7.17).
- „Python 3.8+”: adnotacje `list[str]` / `tuple[bool, str]` (linie 18, 27) wymagają Pythona 3.9+ (PEP 585); na 3.8 padają przy imporcie. *(wniosek z analizy statycznej — w środowisku audytu jest tylko 3.11, więc nie wykonałem testu)*.
- „15 ms”: zmierzone 26–34 ms na tym sprzęcie. Rząd wielkości się zgadza, deklaracja optymistyczna.

### 2.9. Sprzeczność #8: FAST_TRACK jako furtka, w tym do własnych bramek

`is_fast_track_only()` uznaje za STANDARD wyłącznie ścieżki zaczynające się od `apps/`, `packages/`, `src/`. Wszystko inne jest „dokumentacją”:

| Ścieżka | Klasyfikacja |
|---|---|
| `apps/api/x.ts` | STANDARD (bramka) |
| `frontend/src/App.tsx` | **FAST_TRACK** (bez bramek) |
| `infra/terraform/main.tf` | **FAST_TRACK** |
| `scripts/adversarial-review.sh` | **FAST_TRACK** — agent może przepisać bramkę |
| `.github/workflows/ci.yml` | **FAST_TRACK** — agent może wyłączyć CI |
| `install.sh` | **FAST_TRACK** |

To nie jest przeoczenie kosmetyczne: **kod egzekwujący reguły leży poza obszarem egzekwowania**. Monorepo z katalogiem `frontend/` zamiast `apps/` dostaje zero bramek i zielony raport. Domyślna konfiguracja jest fail-open, a nie fail-closed — wbrew regule 7.10.

### 2.10. Sprzeczność #9: CI, które nie może zawieść (i nie może wystartować)

`.github/workflows/*.yml` wywołują `harness-template/scripts/…` — **taki katalog nie istnieje** w repozytorium (potwierdzone). Oba workflowy padają na pierwszym kroku. A krok negatywny:

```yaml
run: bash harness-template/scripts/adversarial-review.sh --test-negative || echo "✅ negative test correctly blocked"
```

`|| echo` zamienia **każde** niepowodzenie (w tym prawdziwą regresję detektora) w sukces. Ten krok nigdy nie może być czerwony — nawet gdyby ścieżka była poprawna. Trzecia „warstwa ochrony” w CI jest dekoracją.

### 2.11. Sprzeczność #10: warstwa 4 (E2E) nie jest wykonywalna

Brak `package.json`, brak `playwright.config.ts`, brak zapisanych snapshotów bazowych (`home-desktop-1440.png`). Plik `.spec.ts` jest **wzorcem**, nie testem — ale README lokuje go jako „warstwę ochrony, którą dostajesz w pudełku”. Dodatkowo:

- Własny, rekomendowany przez HHH wzorzec wyłączania animacji zawiera 2× `!important` — a S2 banuje `!important` w **dowolnym** pliku diffu. Eksperyment: dodanie jednej linii `transform: none !important;` wewnątrz tego bloku → `BLOCKING S2`, lokalizacja `apps/admin/src/app/test.tsx:3` (fikcyjna). **Uprząż blokuje rozszerzenie własnego wzorca.**
- Tolerancja `scrollWidth <= viewport + 5` przepuszcza 5 px poziomego overflow — czyli dokładnie klasę błędu, którą warstwa ma wykrywać. Magiczna stała bez uzasadnienia.
- Reguła 7.14 („zakaz `page.route`”) nie ma żadnego odzwierciedlenia w kodzie — deklaracja bez egzekwowania.

---

## 3. EWALUACJA — wiarygodność dowodów i źródeł

### 3.1. Case study CityPulse: arytmetyka nie domyka się

Przeliczyłem tabelę z README niezależnie:

| Wiersz | Przed | Po |
|---|---|---|
| Pisanie kodu | 1.0 h | 1.5 h |
| Wywiad /grill-me | 0 min | 20 min |
| Usuwanie regresji | 12.0 h | 0.5 h |
| **Suma z wierszy** | **13.0 h** | **2.33 h** |
| **Suma deklarowana w tabeli** | 13.0 h | **2.5 h** |

- Kolumna „po” nie sumuje się do 2.5 h (różnica +0.17 h bez wyjaśnienia).
- Nagłówek mówi **77% redukcji**; z danych tabeli wychodzi **80.8%**, a z sumy wierszy **82.1%**. Żadna liczba nie wynika z zaprezentowanych danych.
- W jednym dokumencie występują trzy różne wartości tej samej poprawy: „kasuje **90%** czasu refaktoru” (cytat), **-95%** (tabela), **-77%** (nagłówek).

**Ocena źródła:** n=1, self-report autora, brak grupy kontrolnej, brak zdefiniowanej metodyki pomiaru (co liczono jako „czas usuwania regresji”? jak mierzono?), brak surowych logów. Odnośnik prowadzi do prywatnego projektu autora (`CP-142`, `CP-145`) — **nieweryfikowalny w tym środowisku i dla czytelnika bez dostępu**. Badge „Battle-Tested” opiera się na tym jednym, niezweryfikowanym przypadku. To materiał marketingowy, nie dowód. Uczciwa forma: „case study wewnętrzny, n=1, dane autora, liczby nieaudytowane”.

### 3.2. `KNOWN_LIMITATIONS.md`: najlepszy dokument w repo — z jednym defektem

Warstwa retoryczna jest wzorowa: przyznanie „Cargo Cult”, „Regex Hell”, „Fałszywe poczucie bezpieczeństwa”, zdanie „harness pomoże Ci zbudować błędny system bardzo zdyscyplinowanie”. To dokładnie postawa, której brakuje README.

Ale część mitigacji **nie istnieje w kodzie**:

| Deklarowana mitigacja | Stan faktyczny |
|---|---|
| `--allow-false-positive` w `adversarial-review.sh` | ❌ flaga nie istnieje (są tylko `--enable-tenant-check`, `--test-negative`, `--help`) |
| allowlist `// APPROVED: <powód>` | ❌ nie zaimplementowana (istnieje wyłącznie `APPROVED_DESTRUCTIVE` dla DROP) |
| „AST gdzie warto” | ❌ brak |
| `grep -r "Uzasadnienie"` | ✅ częściowo (kontrola S6) |

Czyli dokument, który ma być antidotum na iluzję bezpieczeństwa, sam zawiera **obietnicę nieistniejącego bezpiecznika**. To szczególnie kosztowne, bo czytelnik ufa właśnie temu plikowi.

### 3.3. Co jest solidne (uczciwość wymaga odnotowania)

- **`ub-metrics.sh`** to najlepszy kod w repozytorium: przypięte SHA zamiast „latest”, weryfikacja `HEAD == SHA` po checkoutcie, jawny błąd zamiast cichego sukcesu, udokumentowane „report-only”. Wzór do naśladowania dla reszty.
- **Higiena licencyjna skilla `ub-mode`**: autor zauważa brak LICENSE upstreamu, streszcza zamiast kopiować, cytuje konkretny commit. Rzadka rzetelność.
- **Determinizm i zero-LLM** — deklaracja prawdziwa i łatwo weryfikowalna.
- **Idea samo-testu** (`--test-negative`, `--test-red`) jest słuszna, choć wykonanie tautologiczne.
- **Rozdział ról człowiek/maszyna** (BUILDER → REVIEW → człowiek `DONE`) adresuje realny problem nadużywania autonomii agentów.
- **Zgodność reguł z zasadami inżynierskimi** (Fail-Closed, single gateway, idempotencja, Null-Return Check) — merytorycznie poprawne i dobrze sformułowane.

---

## 4. WNIOSKOWANIE — co z tego wynika

### 4.1. Model zagrożenia jest niedopasowany do przeciwnika

Uprząż broni przed agentem **leniwym, ale uczciwym**: takim, który napisze `catch {}` i pójdzie dalej. Nie broni przed agentem **optymalizującym wynik bramki** — a to jest dokładnie dominująca strategia modeli językowych nagradzanych za „zielone testy”. Ścieżka ataku jest krótka i nie wymaga wiedzy specjalnej:

1. Agent widzi błąd bramki → poprawia **nagłówek/format**, nie sens zadania (nagroda: PASS).
2. Bramka Inception nie odpala na prawdziwym formacie → wywiad staje się opcjonalny, mimo że „fizycznie uniemożliwiony”.
3. Gdyby jednak odpaliła: wystarczy jedno zdanie ze słowami „źródło”, „błąd”, „Must NOT”. **Dowód:** `PASS: OK (91 znaków, 3 filary)` dla tekstu „Nie wiemy, zgadujemy, ale słowa kluczowe są, więc bramka przechodzi”. Trzy słowa-klucze = przejście.
4. W razie oporu: `scripts/` i `.github/` są FAST_TRACK, a kontrola integralności liczy nagłówki → agent może **edytować własne ograniczenia** (potwierdzone: `exit 0` w skanerze = PASS).

To nie jest hipoteza teoretyczna — to trzy niezależne, wykonane eksperymenty. Nazwa „Gate Integrity Sentinel” obiecuje coś, czego kod nie robi, co jest gorsze niż brak kontroli: **tworzy zaufanie, którego nie ma pokrycia**.

### 4.2. Sprzeczność bodźców: bramka, która karze cnotę

Reguła 7.17 każe **usuwać** przed dodawaniem. Skaner traktuje usunięcie `!important`, `toBeDefined()`, `DROP` czy linii z `sk-` jako BLOCKING. Agent uczący się na sprzężeniu zwrotnym nauczy się **nie usuwać** — czyli dokładnie odwrotnie do zamierzonej dyscypliny. W systemie z agentem w pętli sprzężenia to nie „false positive”, to **trening przeciwko celowi**.

### 4.3. Koszt adopcji ponosi użytkownik, korzyść jest deklaratywna

Sekwencja pierwszych 15 minut nowego użytkownika: szablon nie przechodzi bramki → hook blokuje push mimo „PASSED” → komunikat negatywnego testu mówi „SUKCES” i zwraca 1 → CI nie startuje (zła ścieżka). Cztery z czterech pierwszych kontaktów to tarcie bez wyjaśnienia. `KNOWN_LIMITATIONS` sam nazywa ten mechanizm („Friction vs Adoption”) i wskazuje skutek: `--no-verify`, `force push`. Kod **dokładnie tę przepowiednię realizuje**.

### 4.4. Zasada, którą warto zachować, i granica, której nie wolno przekraczać

Wartością projektu nie są regexery, lecz **trzy decyzje projektowe**: (a) dowody z CLI zamiast deklaracji agenta, (b) `DONE` wyłącznie z podpisem człowieka, (c) rozdzielenie stanów DRAFT→REVIEW→DONE. One są tanie, odporne na halucynacje i niezależne od implementacji. Natomiast obietnica „fizycznie uniemożliwia” jest nie do utrzymania przy tej klasie narzędzi (grep na diffie) i **niepotrzebna** — wystarczy „wykrywa X z Y znanych wzorców, reszta to review człowieka”.

### 4.5. Alternatywa architektoniczna (wniosek, nie opinia)

„Zero LLM” nie wymaga „własnoręczny grep”. Istnieją dojrzałe, deterministyczne, szybkie narzędzia o pokryciu nieporównywalnie lepszym niż 5 regexów:

| Cel | Zamiast regexu | Efekt |
|---|---|---|
| Silent fallback (Python) | `ruff` — `E722`, `S110`, `BLE001` | łapie `except: pass` w każdej formie, także wieloliniowej |
| Silent fallback (TS) | `eslint` — `no-empty`, `no-useless-catch` + `@typescript-eslint/no-floating-promises` | pokrycie klas, nie stringów |
| Sekrety | `gitleaks` / `trufflehog` (reguły + entropia) | AWS/Azure/GCP/Slack/klucze prywatne, nie tylko `sk-` |
| IDOR / tenant leak | `semgrep` z regułą taint-mode (`req.body → query`) | pokrycie przepływu danych, nie nazwy pola |
| Integralność bramek | `sha256sum -c harness.lock` + CODEOWNERS na `scripts/` | realna odporność na podmianę |

Wszystkie są deterministyczne, offline-owalne i szybsze w utrzymaniu niż własny parser diffu. To **reduce scope**: 3 bramki, które naprawdę działają, biją 5, które deklarują.

---

## 5. WYJAŚNIANIE — jak to komunikować (rekomendacje w kolejności naprawy)

### P0 — blokery, bez których uprząż szkodzi bardziej niż brak uprząż

| # | Problem | Poprawka | Test regresyjny (RED first) |
|---|---|---|---|
| P0-1 | Skaner zwraca 1 przy PASS (§2.6) | `trap 'cleanup \|\| true' EXIT` lub `cleanup(){ rm -f "$DIFF_FILE"; [ -z "$TEST_DIR" ] \|\| rm -rf "$TEST_DIR"; return 0; }` | `bash adversarial-review.sh; [ $? -eq 0 ]` przy pustym diffie |
| P0-2 | Inception Gate nie widzi własnego formatu (§2.2) | parsować komórki tabeli: `^\|\s*(CP-\d+)\s*\|[^|]*\|\s*IN_PROGRESS\s*\|` | fixture = **prawdziwy** `docs/tasks/ACTIVE.md` z repo, CP bez wywiadu ⇒ oczekiwany exit 1 |
| P0-3 | Gate Integrity przepuszcza `exit 0` (§2.4) | `sha256sum -c harness.lock`; porównuj **zbiór ID reguł**, nie licznik; brak `docs-provenance.py` ⇒ `WEAKENED=1`; CODEOWNERS na `scripts/` | podmiana skryptu na `exit 0` ⇒ oczekiwany exit 1 |
| P0-4 | CI nie startuje i nie może zawieść (§2.10) | naprawić ścieżki (`scripts/`, nie `harness-template/scripts/`); usunąć `\|\| echo`; jawnie asertować kod wyjścia i **zbiór** oczekiwanych grzechów | PR z celowo złym CP ⇒ job czerwony |

### P1 — spójność wewnętrzna i wiarygodność

| # | Problem | Poprawka |
|---|---|---|
| P1-1 | Szablon nie przechodzi bramki (§2.3) | akceptować `^## (?:\d+\.\s*)?Decyzje…`; komunikat błędu winien mówić o **formacie nagłówka**, nie „brak sekcji” |
| P1-2 | Karanie za Subtract (§2.5a) | skanować wyłącznie dodawane linie (`^+` i nie `^+++`); usunięcie grzechu raportować jako **dodatni** sygnał |
| P1-3 | Fałszywe negatywy S1/S4 (§2.5b) | przejść na `ruff`/`eslint`/`gitleaks` (§4.5); jeśli zostaje grep — dodać wykrywanie wieloliniowe i testy na 10 realnych wzorcach |
| P1-4 | Zmyślone lokalizacje (§2.5c) | liczyć `plik:linia` z nagłówków `+++ b/…` i hunków `@@`; **zero** stringów literałowych w raporcie |
| P1-5 | Rozjazd dokumentacji i kodu (§2.7) | ujednolicić S1–S7 (jedno źródło prawdy: tablica w skrypcie generująca README); poprawić „4” na faktyczną liczbę; usunąć odwołania do nieistniejących reguł 3.5/7.16 przy S1 |
| P1-6 | `config.sh` martwy (§2.8) | `source scripts/config.sh` w obu skryptach **albo** usunąć plik i sekcję w README (7.17: Subtract) |
| P1-7 | FAST_TRACK jako furtka (§2.9) | domyślnie **wszystko** jest STANDARD; FAST_TRACK tylko przez jawną, wąską allowlistę; `scripts/**` i `.github/**` zawsze STANDARD |
| P1-8 | E2E niewykonywalne (§2.11) | dodać `package.json`, `playwright.config.ts`, zapisane baseline'y; usunąć tolerancję +5 px; `!important` z wzorca przenieść do CSS aplikacji lub jawnie wyłączyć pliki testowe z S2 |

### P2 — prawdomówność dokumentacji

1. Zamienić „fizycznie uniemożliwiają” na **liczby**: „4 wzorce blokujące, 13 reguł jako umowa, review człowieka”.
2. Case study: oznaczyć jako `n=1, self-report, dane nieaudytowane`; **usunąć -77%** albo pokazać wyliczenie, które je daje; uzgodnić 90%/-95%/-77% do jednej wartości.
3. Usunąć „zero połączeń zewnętrznych” albo dodać tryb offline (`UB_METRICS_OFFLINE=1` pomijający `git clone`).
4. „Python 3.8+” → „3.9+”, albo `from __future__ import annotations`.
5. `KNOWN_LIMITATIONS`: zaimplementować `--allow-false-positive` **albo** usunąć wzmiankę. Dokument o uczciwości nie może zawierać nieistniejących bezpieczników.
6. Usunąć wyciek CityPulse z artefaktów generycznych (`$HOME/.cache/citypulse-ub-tools`, `CP-143`, `ADR-0043`, `backlog.md` nieistniejący w repo) — albo jawnie oznaczyć jako „przykłady z projektu źródłowego”.
7. `install.sh`: nie nadpisywać cudzych hooków bez backupu, nie rekomendować `curl | bash` jako ścieżki domyślnej bez sumy kontrolnej; „Sposób 2” z README **nie instaluje plików uprzęży** — naprawić albo usunąć.
8. Wykonać `Subtract` na samym repo: martwe `FAST_TRACK_PATTERNS`, nieosiągalny blok `origin/main` w kontroli integralności, podwójne liczenie S1 (§2.4, §2.8).

---

## 6. SAMOREGULACJA — ograniczenia tego audytu i moje własne błędy

Świadomie przykładam te same standardy do siebie:

1. **Błąd, który popełniłem i poprawiłem.** Pierwszy test „dogfoodingu” wykonałem w kopii zawierającej `.git`, więc fixture był wadliwy („nothing to commit”) — wynik był bezwartościowy. Odrzuciłem go i powtórzyłem na czystej historii. Odnotowuję to, bo to **ta sama klasa błędu**, którą zarzucam repozytorium: test, który nie może zawieść, jest gorszy niż brak testu.
2. **Stronniczość wobec hipotezy.** Po znalezieniu fałszywych alarmów celowo szukałem fałszywych negatywów (osobny eksperyment) i osobno spisałem, co działa (§3.3), żeby nie zbudować jednostronnego oskarżenia.
3. **Czego nie zweryfikowałem wykonawczo.** (a) Python 3.8 — twierdzenie z analizy statycznej, w sandboxie jest 3.11; (b) Playwright/E2E — brak Node i przeglądarek; (c) case study CityPulse — projekt źródłowy jest niedostępny; (d) rzeczywisty wskaźnik fałszywych alarmów w codziennej pracy — wymagałby tygodni obserwacji na prawdziwym monorepo.
4. **Rozmiar próby.** 1 commit w historii = nie oceniam praktyki utrzymania, jakości PR-ów ani kultury review. Oceniam **artyfakt**, nie autora, i nie zakładam złej woli — większość usterek wygląda na pośpiech przy publikacji, nie na celowe zawyżanie.
5. **Ryzyko zawyżenia surowości.** To szablon po jednym commicie, nie produkt po roku eksploatacji. Gdybym oceniał „dojrzałość produkcyjną”, oceny byłyby łagodniejsze. Oceniam **zgodność z własnymi deklaracjami**, bo deklaracje są absolutne („fizycznie uniemożliwia”, „każde naruszenie wykrywa”).
6. **Ironia własnej pracy.** Ten raport to plik `.md`, więc w logice `docs-provenance.py` jest FAST_TRACK i **nie podlega żadnej bramce**. Gdyby zawierał błędy, uprząż by ich nie wykryła. Sam ten fakt jest argumentem za P1-7.

---

## 7. Załącznik — polecenia reprodukcyjne

```bash
# P0-1: PASS z kodem wyjścia 1
bash scripts/adversarial-review.sh; echo "exit=$?"        # → "PASSED", exit=1

# P0-2: bramka głucha na format z dokumentacji
printf '| CP-007 | Endpoint | IN_PROGRESS | STANDARD_TRACK | @x |\n' > docs/tasks/ACTIVE.md
python3 scripts/docs-provenance.py --check                # → PASS (powinno FAIL)

# P0-3: integralność nie chroni bramek
printf '#!/usr/bin/env bash\nexit 0\n' > scripts/adversarial-review.sh
bash scripts/check-gate-integrity.sh                      # → PASSED, exit=0

# P1-1: własny szablon nie przechodzi własnej bramki
python3 scripts/docs-provenance.py --file docs/tasks/TEMPLATE.md   # → FAIL

# P1-2: skaner karze za Subtract
#   (repo testowe: na main linia z !important, w gałęzi fix ta linia USUNIĘTA)
bash scripts/adversarial-review.sh main                   # → BLOCKING S2

# P1-3: fałszywe negatywy (Python except/pass w 2 liniach, catch z komentarzem, catch→undefined, AKIA…)
#   → BLOCKING=1 (tylko ghp_), reszta przepuszczona

# P2: arytmetyka case study
python3 -c "print(f'{100*(1-2.5/13):.1f}%', f'{100*(1-2.33/13):.1f}%')"  # 80.8% / 82.1% ≠ 77%

# P2: martwa konfiguracja
grep -rn "source.*config.sh" scripts/ install.sh            # → brak wyników
grep -n "FAST_TRACK_PATTERNS" scripts/docs-provenance.py    # → tylko definicja (linia 15)
```

Wszystkie eksperymenty wykonano w kopiach w `/tmp`; repozytorium źródłowe pozostało niezmienione poza dodaniem tego pliku.

---

## 8. Jedno zdanie na koniec

**Uprzęż ma słuszną filozofię i dobre intencje, ale jej warstwa wykonawcza jest w większości deklaratywna, a w trzech miejscach aktywna szkodliwa** — dlatego zamiast dodawać szóstą warstwę, warto najpierw sprawić, by pierwsze trzy robiły dokładnie to, co mówią, i przestać obiecywać „fizyczne uniemożliwienie” tam, gdzie działa `grep`.
