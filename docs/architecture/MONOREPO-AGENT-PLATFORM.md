# Platforma monorepo dla agentów: Nx + MCP + pamięć RAG + skille + bramki

**Status:** propozycja architektury (do decyzji: ADR)
**Data:** 2026-10-29
**Kontekst:** kontynuacja `AUDYT-KRYTYCZNY.md` — tam padły bramki deklaratywne, tu jest odpowiedź systemowa
**Zakres:** monorepo 20–200 projektów, TS + Python, 2–20 inżynierów + agenci AI

---

## 0. TL;DR — siedem decyzji, które robią 90% roboty

1. **Nx — tak, ale nie „bo Nx”.** Nx daje cztery rzeczy, których nic innego nie daje razem: **graf projektu, `affected`, cache lokalny/zdalny, granice modułów**. To nie jest wybór religijny — to wybór *jednego grafu zadań*. Bez zunifikowanego grafu agenci będą zgadywać, co uruchomić, i to jest źródło nr 1 przepalania tokenów.
2. **Kod nie idzie do RAG.** Źródło kodu indeksujesz **symbolami** (LSP/tree-sitter), nie embeddingami chunków. RAG trzyma **decyzje** (ADR, post-mortemy, glosariusz, „dlaczego”), bo to wiedza mała, gęsta i trwała.
3. **MCP nie udostępnia plików — udostępnia zapytania.** `find_symbol`, `who_imports`, `blast_radius`, `owners`, `decisions_for`. Każda odpowiedź ma budżet tokenów i provenance (`plik:linia @ SHA`).
4. **Kontekst jest kompilowany, nie zbierany.** Target Nx `agent:context` generuje manifest kontekstu dla zadania, cache'owany po hashu (commit + zadanie). Agent nie „chodzi po repo”, agent dostaje wyliczony pakiet.
5. **Stan żyje na dysku, nie w rozmowie.** Spec → bilety (DAG z krawędziami blokad) → **świeży subagent na bilet** → merge. Rozmowa jest pamięcią krótkotrwałą i to ona przepala tokeny; bilet jest pamięcią trwałą.
6. **Mniej bramek, ale prawdziwych.** Osiem bramek, które mają pokrycie, hash-pin i kod wyjścia — zamiast osiemnastu reguł prozą. Wyjątki tylko z terminem ważności i właścicielem.
7. **Nie da się „zmusić” promptem — można tylko uniemożliwić kłamstwo i ograniczyć pętlę.** DoD wykonywalne, blast radius ograniczony, dwie próby na hipotezę, potem eskalacja do człowieka.

Zasada nadrzędna, warta zapamiętania:

> **Agent nie musi być mądry. Musi być niezdolny do skłamania i niezdolny do zapętlenia.**

---

## 1. Diagnoza: dlaczego wielkie monorepo umiera — i co dokładają agenci

Cztery mechanizmy rozkładu (żaden nie jest „brakiem dyscypliny”, wszystkie są strukturalne):

| Mechanizm | Objaw | Co go realnie leczy |
|---|---|---|
| **Sprzężenie** | zmiana w `shared/utils` wywala 14 aplikacji, nikt nie wie które | granice modułów + `affected` + zakaz deep importów |
| **Czas feedbacku** | pełne CI 35 min → ludzie pushują „na wiarę” | cache + testy przyrostowe + podział suite (`unit < 10 s`) |
| **Rozproszona wiedza** | „dlaczego ten endpoint zwraca 403?” wie jedna osoba | ADR + glosariusz + pamięć decyzyjna z provenance |
| **Brak granic** | każdy pakiet zależy od każdego, testy unit mockują pół systemu | **deep modules** (mały interfejs, głęboka implementacja) + testy na szwie |

Agenci dokładają trzy własne tryby awarii:

- **Halucynacja struktury** — zgaduje, gdzie jest funkcja, zamiast zapytać indeks (koszt: tokeny + zły edit).
- **Dryf kontekstu** — po 40 krokach „pamięta” wymaganie inaczej niż na starcie (koszt: rework).
- **Pozorna produktywność** — generuje 600 linii, z czego 400 to nowy dług; wygląda szybko, bo **nie płaci za weryfikację** w tym samym kroku.

Wniosek projektowy: nie walcz z agentem o uwagę. **Odbierz mu swobodę wyboru miejsca pracy i sposób raportowania wyniku.**

---

## 2. Czy Nx? Macierz decyzyjna bez marketingu

| Wymóg | Nx | Turborepo | Bazel/Pants | pnpm workspaces + skrypty |
|---|---|---|---|---|
| Graf projektu i `affected` | ✅ natywnie | ⚠️ tylko po pakietach | ✅ (najlepszy) | ❌ ręcznie |
| Cache lokalny + zdalny | ✅ (Nx Cloud / self-hosted) | ✅ | ✅ (najlepszy) | ❌ |
| **Granice modułów egzekwowane** | ✅ `enforce-module-boundaries` + tagi | ❌ | ⚠️ (własne reguły) | ❌ |
| Poliglota (TS+Python+Go) | ⚠️ działa, graf grubszy | ⚠️ | ✅ | ⚠️ |
| Krzywa wejścia | średnia | niska | bardzo wysoka | niska |
| Generatory (spójne rusztowanie) | ✅ | ❌ | ⚠️ | ❌ |

**Wybór domyślny: Nx.** Uzasadnienie nie brzmi „Nx jest najlepszy”, tylko: *jeden graf zadań z cache i egzekwowanymi granicami jest warunkiem koniecznym, żeby agent w ogóle mógł działać przyrostowo i tanio.*

**Kiedy NIE Nx:**
- < 15 projektów / < 50k LOC → konfiguracja droższa niż problem.
- Ciężka poliglota z kompilacją natywną (C++/Rust/Java) w jednym grafie → Bazel/Pants; Nx będzie udawał graf.
- Zespół bez przyzwolenia na konwencję → Nx karze za improwizację, a nie pilnuje jej automatycznie.

**Czego Nx NIE rozwiąże** (i dlatego jest tylko warstwą 0): nie poprawi interfejsów modułów, nie napisze ADR, nie powstrzyma agenta przed obejściem bramki. To robią warstwy 2–6.

---

## 3. Architektura docelowa — sześć płaszczyzn

```
            ┌──────────────────────────────────────────────────────┐
            │  CZŁOWIEK  (intencja, akceptacja, podpis DONE)        │
            └───────────────────────────┬──────────────────────────┘
                                        │
   ┌────────────────────────────────────▼─────────────────────────────────┐
   │ 6. DOWODY      artefakt per bilet: stdout bramek, koszt tokenów,      │
   │                attempt-ledger, czas, blast radius                     │
   ├──────────────────────────────────────────────────────────────────────┤
   │ 5. BRAMKI      typecheck · lint · granice · testy affected ·          │
   │                semgrep(domena) · gitleaks · migracje · a11y/perf      │
   │                hash-pin · fail-closed · wyjątki z terminem            │
   ├──────────────────────────────────────────────────────────────────────┤
   │ 4. SKILLE      routing: mp-* / ub-* / hhh-*  (max 1+1 aktywnych)      │
   │                precedencja jawna, konflikt nazw rozstrzygnięty        │
   ├──────────────────────────────────────────────────────────────────────┤
   │ 3. PAMIĘĆ     RAG po DECYZJACH: ADR, post-mortem, glosariusz,         │
   │                "dlaczego". Append-only, provenance, wygasanie.        │
   ├──────────────────────────────────────────────────────────────────────┤
   │ 2. KONTEKST   MCP: symbol/e, importy, blast radius, owners, decyzje   │
   │                budżet odpowiedzi, provenance @SHA                     │
   ├──────────────────────────────────────────────────────────────────────┤
   │ 1. GRANICE    tagi Nx + zakaz deep importu + deep modules             │
   ├──────────────────────────────────────────────────────────────────────┤
   │ 0. SUBSTRAT   Nx: graf · affected · cache · generatory · release      │
   └──────────────────────────────────────────────────────────────────────┘
```

Kluczowa własność: **warstwy 0–3 są deterministyczne** (te same dane wejściowe → ten sam wynik, brak LLM). Warstwa 4 to jedyne miejsce z „osądem” modelu. Warstwa 5 nie ufa warstwie 4. Warstwa 6 nie ufa nikomu.

---

## 4. Płaszczyzna kontekstu: MCP jako kompilator, nie wyszukiwarka

### 4.1. Dlaczego nie „agent czyta pliki”

Typowy bilet: agent czyta 14 plików (≈38k tokenów), znajduje 3 istotne, pisze 40 linii. Przy 30 biletach to ~1,1 mln tokenów na projekt, z czego 90% to szum. Ten sam bilet przy zapytaniach symbolicznych: 3 zapytania × ~600 tokenów = 1,8k.

### 4.2. Kontrakt narzędzi (10 narzędzi, koniec)

| Narzędzie | Wejście | Wyjście (budżet) | Po co |
|---|---|---|---|
| `find_symbol` | nazwa / wzorzec | ≤ 8 trafień: `plik:linia`, sygnatura, 3 linie kontekstu | zamiast grepa po całym repo |
| `read_symbol` | `id symbolu` | treść funkcji **bez** reszty pliku (≤ 120 linii) | zamiast czytania pliku |
| `who_imports` | `id symbolu` | lista projektów + 5 przykładów | blast radius |
| `affected_by` | lista plików | `nx show projects --affected --json` | zakres testów |
| `test_for` | `id symbolu` | ścieżki testów + ostatni wynik | RED-first bez szukania |
| `owners` | ścieżka | CODEOWNERS + ostatni autor | eskalacja |
| `decisions_for` | obszar / symbol | ADR-y i post-mortemy z provenance | wiedza „dlaczego” |
| `conventions` | projekt | reguły lokalne (lint, styl, granice) | brak zgadywania stylu |
| `graph_slice` | projekt | zależności wej/wyj (≤ 2 poziomy) | planowanie |
| `evidence` | `bilet` | dotychczasowe próby + ich wynik-hash | **anty-pętla** |

Reguły twarde (egzekwowane w serwerze MCP, nie w prompcie):

1. Każda odpowiedź ≤ **4k znaków**, każdy wynik ma `file:line @ commit_sha`.
2. Zero odpowiedzi bez provenance — jeśli serwer nie zna lokalizacji, **zwraca błąd**, nie domysł (lekcja z audytu: zmyślone `apps/admin/src/app/test.tsx:3`).
3. Serwer **nie** udostępnia „przeczytaj plik” — tylko `read_symbol` z limitem linii.
4. Odpowiedzi cache'owane po `(query, commit_sha)`; merge unieważnia.

### 4.3. Kompilacja kontekstu jako target Nx

```jsonc
// packages/tools/agent/project.json
{
  "name": "agent",
  "targets": {
    "context": {
      "executor": "nx:run-commands",
      "cache": true,
      "inputs": ["{projectRoot}/**/*", "{workspaceRoot}/docs/adr/**/*.md", "{workspaceRoot}/.agent/tasks/{args.ticket}.md"],
      "outputs": ["{workspaceRoot}/.agent/context/{args.ticket}.json"],
      "options": { "command": "node tools/agent/compile-context.mjs --ticket={args.ticket}" }
    }
  }
}
```

```bash
nx run agent:context --ticket=CP-142   # ~200 ms, cache po hashu
```

Wynik (manifest, nie proza):

```jsonc
{
  "ticket": "CP-142",
  "commit": "7644e54",
  "blast_radius": ["apps/admin", "packages/shared"],
  "symbols": [{ "id": "packages/shared/domain/user#canAccess", "file": "packages/shared/domain/user.ts", "lines": "44-61" }],
  "tests": ["packages/shared/domain/user.spec.ts"],
  "decisions": [{ "adr": "ADR-0043", "title": "Single Gateway", "why": "…", "supersedes": null }],
  "conventions": { "boundaries": ["admin ↛ worker"], "lint": "eslint:strict" },
  "budget": { "max_tokens": 40000, "max_files": 15, "max_loc": 400 }
}
```

Ten plik jest **kontraktem zakresu**: agent nie edytuje plików spoza `blast_radius` bez jawnego kroku „rozszerz zakres” (który jest osobną decyzją, widoczną w PR).

---

## 5. Płaszczyzna pamięci: co w RAG, a czego tam nie wkładać

### 5.1. Rozstrzygnięcie podstawowe

| Treść | Mechanizm | Uzasadnienie |
|---|---|---|
| Kod źródłowy | **indeks symboli** (LSP, tree-sitter, graf z Nx) | kod zmienia się co commit; embeddingi chunków psują granice funkcji i mają niską precyzję |
| Decyzje (ADR), post-mortemy, glosariusz, „dlaczego” | **RAG wektorowy + BM25 (hybrid)** | mała, gęsta, stabilna; dokładnie to, czego brakuje w monorepo |
| Konwencje, checklisty | plik w repo, ładowany wprost | RAG niepotrzebny |
| Historia commitów | `git log --follow` / `blame` przez MCP | deterministyczne, zero kosztu indeksu |

### 5.2. Rekord pamięci — schemat, który chroni przed „memory poisoning”

```jsonc
{
  "id": "ADR-0043",
  "type": "decision",                  // decision | postmortem | glossary
  "title": "Single Gateway dla integracji zewnętrznych",
  "claim": "Wszystkie integracje przechodzą przez packages/integrations/gateway.",
  "why": "Trzy równoległe klienty HTTP dały rozjazd timeoutów i retry.",
  "scope": ["packages/integrations/**", "apps/*/server/**"],
  "provenance": { "files": ["packages/integrations/gateway.ts:1-40"], "commit": "7644e54" },
  "status": "active",                  // active | superseded | expired
  "supersedes": null,
  "owner": "@team-platform",
  "approved_by": "human:2026-10-20",
  "expires_at": null,
  "confidence": "high"
}
```

Reguły:
1. **Agent nie zapisuje pamięci bezpośrednio.** Zapisuje *propozycję* (`status: proposed`) do kolejki; zatwierdza człowiek lub GATEKEEPER.
2. **Append-only + `supersedes`.** Nie edytujemy historii decyzji — dodajemy nową, oznaczając starą. Inaczej pamięć kłamie o przeszłości.
3. **Wygasanie.** Decyzja bez potwierdzenia przez N miesięcy → `expired` i wypada z retrievalu (inaczej „zamrożone” reguły blokują projekt).
4. **Retrieval zawsze cytuje `id` + `provenance`.** Agent musi powołać się na ID; bez cytatu nie wolno mu twierdzić „tak mówi architektura”.
5. **Indeks per commit**; po merge reindeks inkrementalny po zmienionych plikach ADR.

### 5.3. Koszt i pułapki

- Reindeks ADR-ów: sekundy, nie minuty — bo to dziesiątki małych dokumentów, nie 200k plików kodu.
- Pułapka #1: **RAG po kodzie** — kosztOWNY indeks, szybko nieaktualny, niska precyzja. Odrzucone świadomie.
- Pułapka #2: **pamięć zatruta** — agent zapisał błędne „ustalenie”, kolejne 20 sesji je dziedziczy. Dlatego approval + wygasanie + `supersedes`.
- Pułapka #3: **chunkowanie po liniach** — tnie tabele i definicje. Chunkuj po nagłówkach/encjach, nie po 512 tokenach.

---

## 6. Płaszczyzna skilli: jak połączyć Matta + dwóch „Uncle Bobów” bez chaosu

### 6.1. Fakty, które trzeba rozstrzygnąć przed instalacją (zweryfikowane 2026-10-29)

| Fakt | Znaczenie |
|---|---|
| `mattpocock/skills`: ~39 skilli w bucketach `engineering` / `productivity`, wiele z `disable-model-invocation: true` | część skilli jest **tylko na jawne wywołanie** — to dobre: drogie fazy nie odpalają się przypadkiem |
| `unclebob/ub-mode`: 4,6k ★, **brak pliku LICENSE** | nie vendoruj kodu; streszczaj z podaniem commita (HHH robi to poprawnie) |
| `robert-hoffmann/uncle-bob`: **MIT**, 11 skilli (`ub-quality`, `ub-workflow`, `ub-governance`, `ub-authoring`, `ub-python/ts/vue/nuxt/css/tailwind`) | **to inny projekt niż `unclebob/ub-mode`** — ta sama marka, inny autor systemu skilli |
| HHH dostarcza `grill-me`, `code-review`, `domain-modeling`, `tdd` — **te same id co u Matta** | bez namespace'ów agent wybierze losowo; to nie „duplikat”, to **konflikt routingu** |

To ostatnie to najczęstsza realna przyczyna „przepalania tokenów” przy instalacji trzech katalogów skilli: dwa skille opisują tę samą fazę odmiennie, model ładuje oba albo wybiera gorszy, a Ty płacisz za oba i za sprzeczność.

### 6.2. Rozstrzygnięcie: namespace + jedna tabela routingu

- `mp-*` — Matt Pocock (implementacja, TS, spec/tickets, diagnoza)
- `ub-*` — robert-hoffmann/uncle-bob (jakość, workflow, governance) oraz `ubm-*` dla `unclebob/ub-mode` (żeby nie mylić)
- `hhh-*` — lokalne skille repozytorium (bramki, podpisy, protokoły)

Pełna tabela w `skills/ROUTING.md`. Zasada: **max 1 skill governance + 1 skill implementacyjny aktywny jednocześnie**; reszta przez progressive disclosure (referencje ładowane tylko, gdy faza ich wymaga).

### 6.3. Kto wygrywa spór — precedencja (bezwzględna)

```
1. Prawda repozytorium      (kod, testy, ADR, kontrakty)   ← zawsze
2. Bramki deterministyczne  (exit code, hash-pin)          ← nie do negocjacji
3. Governance (ub-governance / hhh-protokół)               ← decyduje o dowodach
4. Workflow (ub-workflow / mp-wayfinder / mp-to-tickets)   ← decyduje o podziale pracy
5. Specjalista stacku (mp-*, ub-ts, ub-ts-deep-modules)    ← decyduje o stylu w obrębie zadania
6. Preferencje użytkownika („zrób szybciej”)               ← tylko gdy 1–5 milczą
```

Zapis w `AGENTS.md`: **skill nigdy nie unieważnia bramki**. Jeśli skill każe pominąć test, a bramka wymaga testu — wygrywa bramka, a konflikt idzie do ADR.

### 6.4. Mapowanie na fazy (to jest odpowiedź „jak to połączyć”)

| Faza | Skill | Artefakt wyjściowy | Budżet |
|---|---|---|---|
| 1. Wywiad | `mp-grill-me` / `hhh-grill-me` (jeden!) | `## Decyzje z wywiadu` (źródło, błąd, Must NOT) | 2–4 pytania, ≤ 2k tokenów |
| 2. Duży plan (>1 sesja) | `mp-wayfinder` | mapa biletów-decyzji na trackerze | ≤ 1 sesja, potem **stop** |
| 3. Spec | `mp-to-spec` | spec z kryteriami akceptacji i non-goals | ≤ 6k tokenów |
| 4. Dekompozycja | `mp-to-tickets` | bilety **tracer bullet** z krawędziami blokad (DAG) | ≤ 4k tokenów |
| 5. Projekt modułu | `mp-codebase-design` + `ub-quality` | interfejs (deep module), seam, plan testów | ≤ 3k tokenów |
| 6. Implementacja biletu | `mp-tdd` + `ub-ts`/`ub-python` + `hhh-ub-mode` | kod + test RED→GREEN | ≤ 40k tokenów |
| 7. Diagnoza trudnego buga | `mp-diagnosing-bugs` | hipoteza → eksperyment → wniosek (pętla zamknięta) | ≤ 20k, 2 hipotezy |
| 8. Przegląd | `mp-code-review` + `ub-governance` | lista zarzutów z dowodami (file:line) | ≤ 5k |
| 9. Domknięcie | `mp-pr` + `hhh-protokół` | PR + dowody bramek + podpis człowieka | ≤ 2k |
| 10. Refleksja | `mp-retro`, `ub-authoring` | poprawka **skilla/bramki**, nie tylko kodu | ≤ 5k |

Uwaga na `mp-implement-spec`: jego model (świeży subagent na bilet, merger na merge, równoległość po „ready frontier”) jest **dokładnie** odpowiedzią na „nie przepalać tokenów i dowozić duże projekty”. Nie wymyślaj własnego — włącz go i dostosuj tracker.

### 6.5. Skille trzeba testować jak kod (inaczej to cargo cult)

Minimalny harness ewaluacyjny:

```yaml
# tools/skills-eval/cases/ts-boundary-01.yaml
ticket: "dodać endpoint /health w apps/api"
fixture: fixtures/monorepo-min
expect:
  must_call: [mp-grill-me]            # wywiad przed kodem
  must_not_touch: ["apps/admin/**"]    # blast radius
  gate_exit: {typecheck: 0, lint: 0, boundaries: 0, test: 0}
  max_tokens: 45000
  max_retries_per_hypothesis: 2
```

20–30 takich przypadków + uruchamianie przy każdej zmianie skilla daje **liczby**: skuteczność pierwszej próby, koszt tokenów, wskaźnik obejść. Bez tego „skille są wybitne” jest opinią, nie pomiarem (dokładnie ten błąd wykryłem w HHH).

---

## 7. Płaszczyzna bramek: 8, które mają pokrycie

| # | Bramka | Narzędzie | Blokuje |
|---|---|---|---|
| 1 | Typy | `tsc --noEmit` / `pyright` | `as any`, `@ts-ignore`, niekompletne kontrakty |
| 2 | Lint | `eslint` + `ruff` (reguły, nie grep) | `catch {}` (`no-empty`), `except: pass` (`E722`,`S110`,`BLE001`) |
| 3 | **Granice** | `@nx/enforce-module-boundaries` + `dependency-cruiser` | deep importy, cykle, zależność w złym kierunku |
| 4 | Testy affected | `nx affected -t test --base=origin/main` | regresje w zasięgu zmiany |
| 5 | Reguły domenowe | `semgrep` (taint mode) | tenant/IDOR (`req.body.citySlug`), brak walidacji na granicy |
| 6 | Sekrety | `gitleaks` | `sk-`, `ghp_`, `AKIA…`, klucze prywatne, entropia |
| 7 | Migracje | reguła `APPROVED_DESTRUCTIVE` + dry-run na kopii | `DROP` bez zatwierdzenia |
| 8 | Budżety | rozmiar bundla, czas p95, a11y (`axe`) | degradacja bez wiedzy |

Czego **nie robić** (wnioski z audytu HHH): nie pisz własnych regexów na diff, jeśli istnieje linter z pokryciem; nie karz za *usuwanie* grzechu (skanuj tylko linie `+`); nie raportuj lokalizacji, której nie policzyłeś; nie licz nagłówków zamiast treści.

### 7.1. Wyjątki ograniczone (mechanizm, którego HHH nie ma)

```ts
// APPROVED(boundary): legacy-admin imports worker types — owner:@team-admin expires:2027-01-31 ticket:CP-311
```

- Każdy wyjątek ma **właściciela, ticket i datę wygaśnięcia**; po terminie bramka znów czerwona.
- Wyjątki są **liczone**: > 20 aktywnych lub > 5 wygasłych → CI czerwone (dług staje się widoczny).
- Wyjątek nie może wyłączyć bramki globalnie — tylko pojedyncze naruszenie w miejscu.

### 7.2. Integralność samych bramek

```bash
sha256sum -c .harness/gates.lock     # podmiana skryptu = czerwono
```

Reguły w `scripts/**` i `.github/**` są **zawsze** STANDARD (nie „docs”), a zmiana wymaga CODEOWNERS. Inaczej agent edytuje własne ograniczenia — patrz `AUDYT-KRYTYCZNY.md` §2.4.

---

## 8. Pętla dostawcza: jak „jeździec bez głowy” dowozi duży projekt

```
Intencja (człowiek)
   ↓  mp-grill-me                → decyzje: źródło, błąd, Must NOT
Wayfinder (mapa decyzji)         → STOP: zatwierdzenie mapy przez człowieka
   ↓  mp-to-spec
Spec (kryteria + non-goals)      → Definition of Ready
   ↓  mp-to-tickets
DAG biletów (tracer bullets)     → krawędzie blokad = kolejność, nie zgadywanie
   ↓  mp-implement-spec: ŚWIEŻY kontekst na bilet
Bilet → RED → GREEN → bramki     → artefakt dowodowy
   ↓  mp-code-review + ub-governance
PR → merge queue → main zielone   → reindeks pamięci, retro
```

### Definition of Ready (bilet nie wchodzi bez tego)

- [ ] 1 kryterium akceptacji, obserwowalne (nie „poprawić moduł X”)
- [ ] jawny non-goal (czego nie ruszamy)
- [ ] `blast_radius` policzony przez `affected_by`
- [ ] plan testu RED (nazwa testu + oczekiwany powód porażki)
- [ ] plan rollbacku (flaga / revert / migracja odwracalna)
- [ ] szacunek ≤ 400 LOC / ≤ 15 plików (inaczej: rozbij bilet)

### Definition of Done (wykonywalne, nie checklista prozą)

```bash
nx affected -t typecheck lint boundaries test --base=origin/main
semgrep --config .semgrep/ --error
gitleaks detect --no-git -v
nx run agent:evidence --ticket=$TICKET   # zbiera stdout + koszt + ledger
```

Zielone = dowód. Czerwone = brak dowodu. Człowiek podpisuje `DONE` **po** przeczytaniu artefaktu, nie po przeczytaniu streszczenia agenta.

### Równoległość

Tylko po **niezależnych** węzłach DAG (brak krawędzi blokady). Dwa agenty na tym samym obszarze to gwarantowany konflikt merge'a i podwójny koszt tokenów. Limit: `min(4, liczba niezależnych węzłów)`.

---

## 9. Anty-pętla: jak nie debugować w nieskończoność

### 9.1. Dlaczego agenci debugują w nieskończoność

Nie z głupoty — z braku **falsyfikowalnej hipotezy** i **stanu między próbami**. Trzy próby „na wszelki wypadek” to nie diagnoza, to losowanie. Do tego brak pamięci porażek: próba 4 powtarza próbę 2.

### 9.2. Protokół DOMKNIĘTEJ pętli (6 kroków, obowiązkowy przy każdym bugu)

1. **Reprodukcja** — najmniejszy test/komenda, która zawodzi deterministycznie. Brak repro = `FLAG:UNVERIFIED_RUNTIME`, nie „poprawiam na oko”.
2. **Hipoteza** — jedno zdanie + **przewidywany wynik eksperymentu** („jeśli to X, to log pokaże Y”).
3. **Eksperyment** — jedno polecenie, wynik zapisany w ledgerze.
4. **Wniosek** — hipoteza potwierdzona/odrzucona. Odrzucona **nie może wrócić** (hash w ledgerze).
5. **Dwie próby na hipotezę, dwie hipotezy na bug** → **premise review**: zapisz założenie, podważ je, zmień plan (HHH 7.17 robi to dobrze — zachowaj).
6. **Timebox 45 min** → eskalacja: `git bisect run`, `git log --follow`, `owners`, pytanie do człowieka. Po 2 eskalacjach: **quarantine** (flaga, test `skip` z ticketem, kod nietknięty).

### 9.3. Detektor braku postępu (mechanizm, nie dobra wola)

```bash
# tools/agent/no-progress.sh — po każdym kroku
SIG=$( (nx affected -t test --base=origin/main 2>&1 | grep -E "^(FAIL|✕)" | sort -u; git diff --stat) \
       | sha256sum | cut -c1-16 )
[ "$SIG" = "$(cat .agent/state/last.sig 2>/dev/null)" ] && STALLS=$((STALLS+1)) || STALLS=0
echo "$SIG" > .agent/state/last.sig
[ "$STALLS" -ge 2 ] && echo "🚩 BRAK POSTĘPU: ten sam zbiór porażek i ten sam diff. STOP." && exit 3
```

To jest tania, deterministyczna bramka przed najdroższym błędem agenta: **kręceniem się w miejscu za pieniądze**. Wystarczy hash zamiast opinii.

### 9.4. Ledger prób (anty-powtórki)

```jsonc
// .agent/tasks/CP-142/ledger.jsonl — append-only
{"n":1,"hypothesis":"timeout wynika z retry w gateway","cmd":"nx test integrations --t=gateway","result":"PASS","sig":"a1b2"}
{"n":2,"hypothesis":"brak propagacji AbortSignal","cmd":"nx test api --t=client","result":"FAIL","error_hash":"9f31","sig":"c7d4"}
```

`evidence` w MCP czyta ten plik — agent **na starcie** wie, co już odrzucono. To najtańsza oszczędność tokenów w całym systemie.

---

## 10. Anty-przepalanie tokenów: budżety i mechanika

### 10.1. Budżety startowe (kalibruj po 2 tygodniach)

| Poziom | Budżet | Egzekwowanie |
|---|---|---|
| Krok (jedna akcja agenta) | **8k** tokenów wejścia | MCP twardo ogranicza rozmiar odpowiedzi |
| Bilet | **40k** | manifest `budget` + alert przy 80% |
| Spec / duży plan | **120k** | po przekroczeniu → `mp-handoff` i nowa sesja |
| Odpowiedź narzędzia | **4k znaków** | limiter w serwerze MCP |
| Log błędu | **60 linii** + unikalne ramki stosu | filtr `errors-only` |
| Pliki czytane na krok | **3** | `read_symbol`, nie `cat` |
| Próby na hipotezę | **2** | ledger + detektor |
| Skille aktywne | **2** (1 governance + 1 impl.) | routing |

### 10.2. Cztery mechanizmy, które realnie tną koszt

1. **Cache Nx** — agent nie uruchamia drugi raz tego, co już przeszło. Cel: > 70% trafień w CI, > 90% lokalnie. To oszczędza **czas**, a czas agenta = tokeny.
2. **Świeży kontekst na bilet** (`mp-implement-spec`) — płacisz za bilet, nie za historię projektu. Kontekst rośnie liniowo z liczbą kroków; reset jest tańszy niż dryf.
3. **`mp-handoff`** — przy 70% budżetu sesji: kompresja do dokumentu (stan, decyzje, następny krok) i nowa sesja. Tańsze niż „dociąganie” do końca okna.
4. **Structured failure** — zamiast 800 linii logu: `test name + assertion + top frame + plik:linia`. Reszta na żądanie.

### 10.3. „Context receipt” — audyt kosztu

Każda sesja zapisuje, **co** weszło do kontekstu:

```json
{"ticket":"CP-142","tokens_in":38420,"tokens_out":6120,"tool_calls":14,
 "top_sources":[{"tool":"read_symbol","tokens":9200},{"tool":"decisions_for","tokens":2100}],
 "wasted":{"full_file_reads":2,"retries":1}}
```

Po tygodniu widzisz, gdzie wycieka budżet — i to jest jedyna sensowna podstawa do optymalizacji. Bez tego „oszczędzanie tokenów” to zgadywanie.

---

## 11. Metryki i kryteria zabicia (kill criteria)

| Metryka | Cel | Jeśli nie — co robisz |
|---|---|---|
| Skuteczność pierwszej próby (bilet przechodzi bramki bez poprawek) | > 60% | zmniejsz bilety, popraw DoR |
| Tokeny na zmergowany bilet | malejąco, porównuj tydzień/tydzień | sprawdź `context receipt` |
| Czas do pierwszego zielonego | < 15 min | to problem platformy (feedback), nie agenta |
| Wskaźnik reworku (linie zmienione w 14 dni) | < 15% | za duże bilety, za słaby wywiad |
| Escape rate (bug na 100 biletów) | malejący | bramki mają lukę, nie „agent jest zły” |
| Fałszywe alarmy bramek | **< 5%** | **uprość bramkę** (nie wyłączaj!) |
| Obejścia (`--no-verify`, wyjątki) | ~0 | bramka za droga → ludzie i agenci uciekną |
| Cache hit CI | > 70% | graf zadań źle skonfigurowany |

**Kryteria zabicia eksperymentu** (uczciwie zapisane z góry): jeśli po 8 tygodniach skuteczność pierwszej próby < 30% **i** koszt tokenów na bilet nie spada — architektura nie działa i trzeba wrócić do mniejszych, węższych bramek zamiast dokładać warstw. To jest zabezpieczenie przed tym, co spotkało HHH: rozbudowa deklaracji zamiast naprawy fundamentu.

---

## 12. Roadmapa 30 / 60 / 90 dni

**0–30 dni — fundament, bez którego reszta jest teatrem**
1. Nx: graf, `affected`, cache lokalny + zdalny; tagi projektów; `enforce-module-boundaries` w trybie `error`.
2. Jedna bramka dowodowa: `nx affected -t typecheck lint boundaries test` + `sha256sum -c gates.lock`.
3. `AGENTS.md` skrócony do ≤ 120 linii: precedencja, budżety, DoR/DoD, linki do skilli. (Długi `AGENTS.md` to stały podatek kontekstowy w każdej sesji.)
4. Routing skilli (`skills/ROUTING.md`) + **odinstalowanie duplikatów** (`grill-me`, `tdd`, `code-review`, `domain-modeling` — jeden dostawca na fazę).
5. Ledger + detektor braku postępu.

**30–60 dni — kontekst i pamięć**
6. Serwer MCP z 10 narzędziami i twardymi budżetami; `find_symbol`/`read_symbol`/`affected_by` w pierwszej kolejności (80% wartości).
7. `agent:context` jako target Nx z cache; manifest zakresu obowiązkowy w bilecie.
8. Pamięć: 30–50 ADR-ów wstecz (także „dlaczego odrzucono”), hybrid retrieval, proposal-approve, wygasanie.
9. `semgrep` reguły domenowe (tenant/IDOR) + `gitleaks` (zastąp własne regexy).

**60–90 dni — dostawa i pomiar**
10. `to-spec` → `to-tickets` → `implement-spec` (świeży subagent na bilet) + merge queue.
11. Harness ewaluacji skilli (20–30 przypadków) uruchamiany w CI przy zmianie skilli.
12. Dashboard metryk z §11 + przegląd tygodniowy; pierwsza decyzja o uproszczeniu lub rozszerzeniu.

---

## 13. Co świadomie odrzucamy (i dlaczego)

| Pomysł | Dlaczego nie |
|---|---|
| RAG po całym kodzie źródłowym | drogi indeks, szybka dezaktualizacja, niska precyzja; symbole wygrywają |
| Własne regexy na `git diff` jako bramki | brak pokrycia, fałszywe alarmy na usuwaniu, zmyślone lokalizacje (dowód: audyt HHH) |
| Instalacja 3 katalogów skilli „na wszelki wypadek” | konflikt routingu, sprzeczne instrukcje, podwójny koszt tokenów |
| Agent zapisujący pamięć projektu samodzielnie | memory poisoning; potrzebny człowiek w pętli |
| Gigantyczny `AGENTS.md` z 18 regułami | stały podatek kontekstowy; 18 zasad bez egzekwowania = 0 zasad |
| Równoległe agenty na tym samym obszarze | konflikty merge i podwójny koszt; tylko niezależne węzły DAG |
| Bramka „na wszelki wypadek” bez pokrycia | fałszywe alarmy → `--no-verify` → utrata zaufania do wszystkich bramek |
| „Zmuśmy model promptem” | prompt nie egzekwuje; egzekwuje kod wyjścia i brak alternatywy |

---

## 14. Załącznik A — konfiguracje startowe

### A.1 `nx.json` (fragment)

```jsonc
{
  "targetDefaults": {
    "typecheck": { "cache": true, "inputs": ["production", "^production"] },
    "lint":      { "cache": true, "inputs": ["default", "{workspaceRoot}/.eslintrc.json"] },
    "test":      { "cache": true, "inputs": ["default", "^production"],
                   "outputs": ["{projectRoot}/coverage"] },
    "boundaries":{ "cache": true },
    "agent:context": { "cache": true }
  },
  "defaultBase": "origin/main",
  "namedInputs": {
    "production": ["default", "!{projectRoot}/**/*.spec.ts", "!{projectRoot}/**/*.test.ts"],
    "default": ["{projectRoot}/**/*", "sharedGlobals"]
  }
}
```

### A.2 Tagi i granice (ESLint)

```jsonc
{
  "overrides": [{
    "files": ["*.ts", "*.tsx"],
    "rules": {
      "@nx/enforce-module-boundaries": ["error", {
        "depConstraints": [
          { "sourceTag": "scope:admin",  "onlyDependOnLibsWithTags": ["scope:shared", "scope:domain"] },
          { "sourceTag": "scope:worker", "onlyDependOnLibsWithTags": ["scope:shared", "scope:domain"] },
          { "sourceTag": "scope:domain", "onlyDependOnLibsWithTags": ["scope:domain"] },
          { "sourceTag": "type:app",     "onlyDependOnLibsWithTags": ["type:lib", "type:domain"] }
        ]
      }]
    }
  }]
}
```

### A.3 Deep module — kontrakt interfejsu (przykład)

```ts
// packages/domain/user/index.ts — JEDYNY punkt wejścia modułu
export type AccessDecision = { allowed: boolean; reason: "ok" | "no-role" | "suspended" };

/** Głęboki moduł: 4 publiczne symbole, 900 linii implementacji ukrytej. */
export function canAccess(input: { userId: string; resource: string }): AccessDecision;
export function listRoles(userId: string): readonly string[];
export function grantRole(input: { userId: string; role: string; by: string }): void;
export function revokeRole(input: { userId: string; role: string; by: string }): void;
```

Reguła: **żaden plik poza modułem nie importuje ścieżki głębszej niż `index.ts`** (egzekwowane przez granice + `dependency-cruiser`). To jest różnica między monorepo, po którym agent nawiguje, a monorepo, po którym agent błądzi.

### A.4 Kontrakt narzędzia MCP (szkic)

```ts
// tools/mcp-codebase/src/tools.ts
export const findSymbol = defineTool({
  name: "find_symbol",
  input: { query: z.string().max(120), limit: z.number().max(8).default(5) },
  output: z.array(z.object({
    id: z.string(), file: z.string(), line: z.number(),
    signature: z.string(), commit: z.string()   // provenance OBOWIĄZKOWE
  })),
  budget: { maxChars: 4000 },
  cacheKey: (i, ctx) => `${i.query}|${ctx.commit}`,
});
```

---

## 15. Załącznik B — jak to się ma do HHH (spięcie z audytem)

| Ustalenie z audytu | Konsekwencja w tej architekturze |
|---|---|
| Bramka Inception nie odpalała na własnym formacie | bramki testujemy **na artefaktach z repo**, nie na wymyślonych fixture'ach (§6.5) |
| `Gate Integrity` liczyła nagłówki | integralność = `sha256sum -c`, nie licznik; `scripts/**` i `.github/**` w STANDARD (§7.2) |
| Skaner zwracał 1 przy PASS → `--no-verify` | bramki używają istniejących narzędzi z poprawną semantyką exit code; każda bramka ma test „PASS ⇒ 0” |
| Karanie za Subtract | bramki patrzą na stan (linter/typ), nie na kierunek diffu — usunięcie grzechu jest zawsze legalne (§7) |
| Zmyślone lokalizacje w raporcie | MCP i bramki raportują tylko policzone `file:line @ SHA` (§4.2) |
| Brak wyjątków → ucieczka w obejścia | wyjątki z właścicielem i terminem, liczone (§7.1) |
| Reguły prozą bez egzekwowania | 12 z 18 reguł HHH to umowa społeczna → tu zostaje 8 bramek + DoR/DoD wykonywalne (§7, §8) |
| Skille bez ewaluacji | harness ewaluacyjny z 20–30 przypadkami jako warunek zmiany skilla (§6.5) |

**Rekomendacja porządkowa:** HHH nie powinien być „systemem operacyjnym agenta” (to rola `AGENTS.md` + skilli), tylko **warstwą bramek i dowodów** (płaszczyzny 5–6). Trzy katalogi skilli + HHH jako czwarty zestaw reguł to ta sama klasa błędu, którą audyt wykrył w kodzie: **wiele deklaracji, jedno egzekwowanie**.

---

## 16. Jedno zdanie na koniec

**Nx daje graf i granice, MCP daje precyzyjny kontekst, RAG daje pamięć decyzji, skille dają procedurę, bramki dają prawdę — a „jeźdźca bez głowy” nie zmusza się promptem, tylko odbiera mu możliwość kłamania (dowody), błądzenia (blast radius) i zapętlenia (ledger + detektor braku postępu).**
