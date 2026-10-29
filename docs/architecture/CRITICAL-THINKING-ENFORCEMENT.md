# Wymuszanie krytycznego myślenia u agentów, którzy „chcą dowieźć za wszelką cenę”

**Status:** propozycja mechanizmu (do decyzji: ADR)
**Data:** 2026-10-29
**Zależności:** `docs/architecture/MONOREPO-AGENT-PLATFORM.md`, `AUDYT-KRYTYCZNY.md`
**Implementacja:** `scripts/epistemic-gate.py` + `docs/epistemic/SCHEMA.md` + fixtures

---

## 0. Teza

> **Nie da się wymusić krytycznego myślenia. Da się wymusić cenę twierdzenia.**

Krytyczne myślenie jest stanem wewnętrznym — niewidocznym, nieobserwowalnym i niefalsyfikowalnym z zewnątrz. Każda bramka, która próbuje je wykryć w tekście („czy model rozważył alternatywy?”), zostanie spełniona przez **tekst o alternatywach**. To dokładnie ten błąd, który audyt wykrył w HHH: `50 znaków + 3 słowa-klucze = PASS`.

Ale „chęć osiągnięcia celu za wszelką cenę” nie jest cechą charakteru — jest **strategią minimalizacji kosztu**. Agent nie kłamie, bo jest zły; kłamie, bo deklaracja jest tańsza niż weryfikacja. Więc nie walczymy z motywacją, **zmieniamy rachunek kosztów**:

| Skrót, do którego agent dąży | Dziś kosztuje | Musi kosztować |
|---|---|---|
| Powiedzieć „gotowe” | 0 (jedno zdanie) | więcej niż uruchomienie testu |
| Wymyślić `file:line` | 0 | natychmiastowy FAIL (provenance albo błąd) |
| Osłabić test, by przeszedł | 0 | FAIL (spadek liczby asercji/mutantów) |
| Zmienić hipotezę po fakcie | 0 | FAIL (prerejestracja przed eksperymentem) |
| Rozdmuchać pewność siebie | 0 | FAIL (`confidence: high` bez executed evidence) |

**Reguła projektowa:** każda norma krytycznego myślenia musi mieć (a) artefakt, (b) bramkę, (c) **kontr-środek na obejście tej bramki**. Bez punktu (c) tworzysz teatr — a agent nauczy się grać rolę.

---

## 1. Dlaczego „bądź krytyczny” w prompcie nie działa

1. **Nie jest falsyfikowalne.** „Myśl krytycznie” nie ma stanu FAIL. Czego nie można oblać, tego nie można wymusić.
2. **Model optymalizuje widoczny sygnał.** Jeśli kryterium to „wymień 2 alternatywy”, dostaniesz 2 alternatywy — niezależnie od tego, czy zostały rozważone.
3. **Samoocena w tym samym kontekście to teatr.** Agent, który właśnie napisał kod, jest **zainwestowany** w to, że jest dobry (sunk cost, self-consistency). Poproszony o krytykę własnej pracy, wygeneruje krytykę bezpieczną: „warto dodać testy edge case”. Nie znajdzie błędu, bo szukanie błędu w swojej pracy jest sprzeczne z celem „dowieźć”.
4. **Kontekst się starzeje.** Po 40 krokach model „pamięta” wymaganie inaczej — i to nie jest kłamstwo, to degradacja. Dlatego wymagamy stanu na dysku, nie w rozmowie.

Wniosek: **krytycyzm trzeba przenieść z wnętrza modelu do struktury procesu** — do artefaktów, które są tanie do sprawdzenia i drogie do podrobienia.

---

## 2. Osiem biasów: sygnatura obserwowalna → bramka → kontr-środek

To jest rdzeń dokumentu. Dla każdego biasu: jak go **zobaczyć w artefaktach** (nie w prozie), jaka bramka go łapie i jak agent mógłby tę bramkę obejść — oraz co na to odpowiadamy.

| # | Bias (cel za wszelką cenę) | Sygnatura obserwowalna | Bramka | Próba obejścia → kontr-środek |
|---|---|---|---|---|
| **B1** | **Premature closure** — ogłasza DONE bez weryfikacji | 0 wykonanych komend w dowodach; „powinno działać”; brak RED | E1/E4: brak claims lub `confidence: high` bez `verified` | napisze claims bez uruchomienia → `--execute` **wykonuje** komendy i porównuje `observed`; rozjazd = FAIL (E3) |
| **B2** | **Reward hacking** — test ma przejść, nie kod działać | ubywa asercji, testy `skip`, luźniejsze matchery, `toBeDefined` | E5: `tests.removed > 0` lub spadek mutacji | przepisze test „równoważnie” → **mutation score** (mutant przeżył = test był placebo); ukryte testy akceptacyjne |
| **B3** | **Confabulated evidence** — wymyśla `file:line`, stdout | lokalizacja bez weryfikacji, stdout „ładny” | provenance obowiązkowe; E2 (brak `cmd/expected/observed`), **E9** (dowód autorski) | wpisze plausible string → `--execute` + `observed` musi **dosłownie** zawierać `expected`; zmierzone: spójne kłamstwo przechodzi statycznie i **pada** przy `--execute` (§5.4) |
| **B4** | **Sunk cost / eskalacja** — 4. raz ta sama poprawka | ten sam diff/ten sam błąd, rosnący „wysiłek” | breaker: hash zbioru porażek + diff bez zmian 2× ⇒ STOP | zmieni biały znak, by zmienić hash → normalizacja (bez whitespace, bez komentarzy) + „2 hipotezy na bug” |
| **B5** | **Post-hoc rationalization** — „to było cache” po wyniku | hipoteza zapisana **po** eksperymencie | prerejestracja: `predicted` i `predicted_if_wrong` **przed** `cmd` | napisze przewidywania ogólne → bramka odrzuca trywialne (`predicted_if_wrong == predicted`, puste, ≤ 8 znaków) |
| **B6** | **Overconfidence** — pewność bez pokrycia | `confidence: high`, `unknowns: []` | E4 + doradczo E8 | zawyży pewność → **kalibracja** (Brier) liczona z ledgera; przy rozjeździe autonomia spada automatycznie (§5.7) |
| **B7** | **Sycophancy** — zgadza się z błędnym założeniem człowieka | brak odrzuconych alternatyw, brak „co może pójść źle” | E9 doradczo; obowiązkowe w spec/ADR | napisze jedno zdanie „rozważyłem inne opcje” → wymagamy **nazwanego** odrzuconego wariantu z powodem i kosztem |
| **B8** | **Vera causa blindness** — leczy objaw | patch w miejscu wyjątku, `try/catch` wokół problemu | lint (`no-empty`, `BLE001`), semgrep; **root-cause field** w artefakcie | doda guard, by „przestało sypać” → **intent test**: test odtwarza scenariusz awarii i sprawdza przyczynę, nie objaw |

Wszystkie bramki są deterministyczne i mają kod wyjścia. **Żadna nie ocenia jakości prozy.**

---

## 3. Sześć norm krytycznego myślenia → artefakt → bramka

Mapowanie Twoich norm na rzeczy wykonywalne (to odpowiedź „jak to w ogóle połączyć z tym, co już masz”):

| Norma | Artefakt (co powstaje) | Bramka | Czego NIE akceptujemy |
|---|---|---|---|
| **Interpretacja** | `intent.md`: wymaganie przeformułowane falsyfikowalnie + **non-goals** | DoR: 1 kryterium obserwowalne + jawny non-goal | „poprawić moduł X” |
| **Analiza** | `claims[]`: twierdzenie → `cmd` → `expected` → `observed` | E1–E3 | twierdzenie bez komendy |
| **Ewaluacja** | `sources[]`: skąd wiem (ADR, test, log) + rzetelność + co by to obaliło | wymagane provenance; dla źródeł zewnętrznych: data + wersja | „tak mówi dokumentacja” bez cytatu |
| **Wnioskowanie** | `hypotheses[]`: przewidywanie **i** przewidywanie przeciwne, przed eksperymentem | E7 | hipoteza bez falsyfikatora |
| **Wyjaśnianie** | `alternatives_rejected[]`: nazwany wariant, powód, koszt | E9 (doradczo; blokująco dla ADR) | „rozważyłem inne opcje” |
| **Samoregulacja** | `deviations[]`: gdzie korekta nastąpiła + `unknowns[]` + ledger prób | E8 + breaker + kalibracja | deklaracja „jestem obiektywny” |

Uwaga na **E8 i E9 jako doradcze**: świadomie nie robię z nich twardych bramek. Puste `unknowns` jest normalne dla trywialnego zadania — twarda bramka dałaby fałszywe alarmy, a fałszywe alarmy uczą obejść (dowód: audyt HHH §2.5a). **Twarde bramki tylko tam, gdzie sygnał jest jednoznaczny i maszynowo sprawdzalny.**

---

## 4. Dziesięć mechanizmów (w kolejności zwracanego efektu)

### 4.1. Dowód wykonywalny, nie deklaracja
Każde twierdzenie to trójka `cmd / expected / observed`. Bramka może **wykonać** `cmd` (`--execute`) i porównać. Deklaracja bez komendy nie istnieje (E1). To zabija 80% „gotowe, działa”.

### 4.2. Prerejestracja hipotezy (najtańszy zabójca racjonalizacji)
Przed eksperymentem: `predicted` (co zobaczę, jeśli mam rację) **i** `predicted_if_wrong` (co zobaczę, jeśli się mylę). Po: `observed` + `result`.
Jeśli przewidywania są identyczne — nie ma testu, jest wiara (E7). To jest wymuszenie **eksperymentu rozstrzygającego**, a nie „spróbujmy i zobaczmy”.

### 4.3. Ślepota kontekstowa na testach akceptacyjnych
Testy akceptacyjne pisze **inny** agent/człowiek i trzyma je w katalogu, którego implementator nie widzi. Egzekwowanie nie w prompcie: **serwer MCP odmawia** zwrócenia tych ścieżek, a `agent:context` nie włącza ich do manifestu.
To jedyna znana mi obrona przed „zrobię, żeby test przeszedł”: agent nie może overfitować do testu, którego nie widzi. Wymaga CODEOWNERS na katalogu.

### 4.4. Mutation score jako wykrywacz placebo
Jeśli testy przechodzą, a mutacje przeżywają — testy nic nie sprawdzają. To **obiektywna** miara „czy weryfikacja była prawdziwa”, niezależna od tego, co agent napisze o sobie. Próg startowy: ≥ 80% na kodzie zmienionym (nie na całym repo — inaczej nigdy nie wystartuje).

### 4.5. Recenzent z świeżym kontekstem (nie self-critique)
Osobny agent dostaje **tylko**: diff, spec, wynik testów. Nie dostaje historii rozumowania (żeby nie dziedziczyć założeń) i nie wie, kto napisał zmianę.
Budżet na obiekcje: **min. 3 zarzuty z `file:line` albo jawne „sprawdziłem X, Y, Z — brak”**. To zamienia „przejrzyj kod” w zadanie z mierzalnym wynikiem. Recenzent, który nie znajdzie nic 3× z rzędu, gdy mutacje przeżywają, sam dostaje gorszy wynik (recenzent też jest mierzony).

### 4.6. Asymetria ceny dowodu
Metryka `evidence_ratio = zweryfikowane_twierdzenia / zmienione_pliki`. Dużo kodu, mało dowodów = sygnał B1. Próg kalibruj, ale **monitoruj trend** — to tania, odporna na grę metryka.

### 4.7. Kalibracja i drabina autonomii (najsilniejszy mechanizm długoterminowy)
Z ledgera liczymy kalibrację: gdy agent mówi „pewny” — jak często ma rację?
- Kalibracja dobra (≥ 0.8 trafności przy `high`) → autonomia **rośnie**: większy blast radius, mniej pytań.
- Kalibracja zła → autonomia **spada automatycznie**: mniejszy zakres plików, obowiązkowy recenzent, pytania do człowieka.

Autonomia przestaje być ustawieniem w configu, staje się **zarabiana**. To odpowiada na „część agentów chce za wszelką cenę” — nie kłóć się z modelem, zmierz go i dostosuj uprawnienia.

### 4.8. Breaker z normalizacją (anty-pętla)
Hash stanu = zbiór niepowodzeń (nazwy testów + `error_hash`) + znormalizowany diff (bez whitespace/komentarzy). Niezmieniony 2× ⇒ STOP, eskalacja pytaniem do człowieka, nie kolejną próbą.

### 4.9. Ledger prób (pamięć porażek)
Odrzucona hipoteza zostaje z hashem wyniku. Kolejna sesja **na starcie** dostaje listę odrzuconych — nie powtarza próby 2. Najtańsza oszczędność tokenów i najlepsza ochrona przed zapętleniem.

### 4.10. Intencja jako test (anty-B8)
Dla bugfixów: test odtwarza **scenariusz awarii** (przyczynę), nie tylko objaw. Gate: jeśli w dowodach jest `catch`/`fallback` bez testu odtwarzającego awarię — FAIL. To zamienia „naprawione” w „naprawione i udowodnione, że przyczyna zniknęła”.

---

## 5. Bramka epistemiczna (`scripts/epistemic-gate.py`)

Deterministyczna, stdlib, zero LLM. Wejście: `docs/epistemic/<TICKET>.json` (schemat: `docs/epistemic/SCHEMA.md`).

```bash
python3 scripts/epistemic-gate.py --file docs/epistemic/CP-142.json                # statycznie
python3 scripts/epistemic-gate.py --file docs/epistemic/CP-142.json --execute       # wykonuje cmd i porównuje
```

### 5.1. Reguły blokujące

| ID | Warunek FAIL | Bias, który łapie |
|---|---|---|
| **E1** | brak `claims` lub wszystkie bez `verified: true` | B1 premature closure |
| **E2** | `verified: true` bez `cmd`/`expected`/`observed` | B3 konfabulacja |
| **E3** | `observed` nie zawiera `expected` (dosłownie; w `--execute`: wynik komendy nie zawiera `expected`) | B3 |
| **E4** | `confidence: high` przy 0 zweryfikowanych twierdzeń | B6 overconfidence |
| **E5** | `code_changed: true` i `tests.removed > 0` | B2 reward hacking |
| **E6** | `code_changed: true` i `tests.added == 0` | B1 (brak RED-first) |
| **E7** | hipoteza bez falsyfikatora: `predicted` puste / == `predicted_if_wrong` / ≤ 8 znaków | B5 racjonalizacja |
| **E8** | `code_changed` i zero claims typu `behavior` (tylko `static`) | B2 (typy przechodzą, zachowanie nie) |
| **E9** | `expected` jest wpisany w samą `cmd` (`echo '214 passed'`) — dowód potwierdza sam siebie | B3 (autorski „dowód”) |

### 5.2. Reguły doradcze (nie blokują — świadomie)

| ID | Warunek WARN | Dlaczego nie blokuje |
|---|---|---|
| **A1** | `unknowns: []` przy `confidence: high` | puste unknowns bywa legalne przy trywialnym zadaniu |
| **A2** | `alternatives_rejected: []` | blokuje tylko dla ADR (decyzja człowieka) |
| **A3** | `mutations.killed / (killed+survived) < 0.8` | próg startowy bywa nieosiągalny w legacy |

### 5.3. Fail-closed
Brak pliku, zły JSON, brak wymaganego klucza → **exit 1**. Nie „pomiń, bo nie ma”. (Lekcja z audytu: brak `docs-provenance.py` dawał PASS.)

### 5.4. Zmierzone zachowanie bramki (nie deklaracja — wyniki przebiegów)

| Scenariusz | Tryb statyczny | `--execute` | Oczekiwane |
|---|---|---|---|
| Uczciwy artefakt (`CP-142.example.json`) | exit 0 | **exit 0** | ✅ |
| „Cel za wszelką cenę” (`CP-666.gaming.json`, 7 naruszeń) | **exit 1** | exit 1 | ✅ |
| **Kłamstwo spójne wewnętrznie** (`expected == observed` = wymyślone `exit=7`) | exit **0** ⚠️ | **exit 1** (E3) | ✅ — i to jest dowód, po co `--execute` |
| Dowód autorski (`echo '214 passed'`) | exit **1** (E9) | exit 1 | ✅ |
| Brak pliku / zły JSON / brak kluczy / brak `--file` | exit **1** | — | ✅ fail-closed |

**Wniosek operacyjny:** tryb statyczny jest tani i łapie niechlujstwo, ale **przepuszcza spójne kłamstwo**. Dlatego `--execute` w CI przed `REVIEW` nie jest opcją — jest warunkiem sensu całej bramki.

### 5.5. Granica tego mechanizmu (i jak ją zawężamy)

Przy pierwszym przebiegu **złapałem dziurę we własnym projekcie**: agent sam wybiera komendę, więc `echo '3 passed'` „potwierdzi” wszystko. Dodałem E9 (expected nie może być wpisany w komendę), ale to zamyka tylko naiwną formę. Trzy ataki pozostają możliwe:

| Atak na `--execute` | Kontr-środek |
|---|---|
| **Słaba komenda** — uruchamia 1 test zamiast pakietu | `kind: behavior` musi wskazywać komendę z allowlisty narzędzi (`nx affected -t test`, `pytest`, `semgrep`), nie dowolny shell |
| **Test przechodzi, kod nie działa** (asercja za słaba) | `mutation score` (A3) + **ukryte testy akceptacyjne** (§4.3) |
| **Wybór „łatwego” dowodu** — pomija trudny przypadek | recenzent z świeżym kontekstem zadaje pytanie „czego ten dowód **nie** pokrywa?” (§4.5) |

Czyli: `--execute` podnosi cenę kłamstwa z 0 do „musisz uruchomić komendę”, a allowlista + mutacje + ukryte testy podnoszą ją do „musisz uruchomić **właściwą** komendę na **niewidzianym** zbiorze”. Każdy poziom jest osobno tani i osobno obejściowalny — dopiero razem tworzą barierę.

---

## 6. Czego NIE robić (na podstawie zmierzonych błędów)

| Antywzorzec | Dlaczego szkodzi | Co zamiast |
|---|---|---|
| LLM jako **jedyna** bramka („sędzia oceni krytycyzm”) | niedeterministyczny, gameowalny, niekalibrowany; zmienia werdykt między przebiegami | deterministyczne bramki + LLM **tylko doradczo**, z kalibracją na zbiorze referencyjnym |
| Liczenie słów/kluczy („50 znaków, 3 słowa”) | wystarczy napisać te słowa — dokładnie tak HHH dostał PASS na zdaniu o niczym | struktura + **wykonywalny** dowód |
| Checkbox bez pointera | zaznaczenie jest darmowe | każdy punkt = `file:line` albo `cmd` |
| Kara za usuwanie kodu/linii | agent przestaje usuwać (odwrotność Subtract) | bramki patrzą na **stan** (linter/typy/mutacje), nie na kierunek diffu |
| Twarda bramka na wszystko | fałszywe alarmy → `--no-verify` → utrata zaufania do wszystkich bramek | twarde tylko przy jednoznacznym sygnale; resztę jako WARN z trendem |
| „Myśl krok po kroku” | wydłuża odpowiedź, nie poprawia weryfikacji | prerejestracja + eksperyment rozstrzygający |
| Self-review w tym samym kontekście | agent jest zainwestowany w swoją pracę | świeży kontekst, bez historii rozumowania |

---

## 7. Metryki (co ma spadać, a co rosnąć)

| Metryka | Definicja | Cel |
|---|---|---|
| **Brier / kalibracja** | trafność przy deklarowanej pewności | ≤ 0.10 błędu kalibracji |
| **Mutation score** (kod zmieniony) | zabite / wszystkie mutanty | ≥ 0.80 |
| **Evidence ratio** | zweryfikowane claims / zmienione pliki | trend rosnący |
| **First-pass yield** | bilety przechodzące bramki bez poprawek | > 0.60 |
| **Escape rate** | bugi na 100 biletów po merge | malejący |
| **Objection yield** | udział recenzji z ≥ 3 zarzutami | 0.5–0.8 (nie 1.0 — to byłby teatr) |
| **Bypass rate** | `--no-verify`, wyjątki, `skip` | ~0 |

**Kryterium porażki (zapisane z góry):** jeśli po 6 tygodniach `objection_yield` > 0.95 przy jednoczesnym `escape_rate` bez zmian — to dowód, że recenzje są teatrem, a nie kontrolą. Wtedy wracasz do ukrytych testów akceptacyjnych (§4.3), nie do kolejnego promptu.

---

## 8. Ograniczenia tego podejścia (uczciwie)

1. **Wymuszamy zachowanie, nie rozumienie.** Agent może produkować idealne artefakty bez „wglądu”. Dla inżynierii to wystarcza — dla zadań otwartych (architektura, produkt) **nie**.
2. **Ryzyko „epistemicznego teatru”** — agent nauczy się wypełniać schemat. Kontr-środki: (a) artefakty muszą być **wykonywalne**, (b) recenzent ma inny kontekst, (c) testy akceptacyjne są ukryte, (d) metryki patrzą na **wynik** (mutacje, escape rate), nie na kompletność formularza. Zmierzone: tryb statyczny **przepuszcza** spójne kłamstwo (§5.4) — dlatego kompletność formularza nigdy nie może być dowodem.
3. **Ukryte testy wymagają procesu** — ktoś musi je pisać. To koszt realny i nie da się go obejść.
4. **Kalibracja potrzebuje masy** — pierwsze 20–30 biletów to zbieranie danych, nie egzekwowanie. Nie oczekuj skutku w pierwszym tygodniu.
5. **Nie każdy bias jest mierzalny.** B7 (sycophancy) łapiesz tylko częściowo — przez nazwane odrzucone alternatywy i pytania do człowieka. Pełna ochrona: człowiek czyta **spec**, nie streszczenie.
6. **Ten dokument też podlega swojej tezie.** Nie jest dowodem, że mechanizm działa — jest hipotezą z falsyfikatorem: *jeśli po 6 tygodniach first-pass yield nie rośnie, a escape rate nie spada, mechanizm nie działa.* To zapisane w §7, żeby nie dało się tego ocenić po fakcie „na wyczucie”.

---

## 9. Rollout (2 tygodnie, minimalny)

| Dzień | Krok | Dowód działania |
|---|---|---|
| 1–2 | `epistemic-gate.py` w pre-commit dla `docs/epistemic/*.json`; schemat w repo | 2 fixtures: uczciwy → 0, doktorowany → 1 |
| 3–5 | prerejestracja hipotez obowiązkowa przy bugach | ledger ma ≥ 5 wpisów przed/po |
| 6–8 | recenzent z świeżym kontekstem + budżet 3 obiekcji | ≥ 1 realny zarzut na 3 recenzje |
| 9–10 | ukryte testy akceptacyjne dla 1 obszaru (CODEOWNERS) | implementator nie widzi katalogu (MCP odmawia) |
| 11–14 | mutacje na kodzie zmienionym (próg 0.8, raport) + pierwszy pomiar kalibracji | raport mutacji w CI |

---

## 10. Jedno zdanie

**„Cel za wszelką cenę” przestaje się opłacać nie wtedy, gdy poprosisz agenta o krytycyzm, ale wtedy, gdy deklaracja stanie się droższa od dowodu — a dowód musi być wykonywalny, sprawdzony przez kogoś z innym kontekstem i niemożliwy do przeczytania z góry przez tego, kto go zdaje.**
