# ROUTING.md — jeden dostawca na fazę, zero konfliktów nazw

> Cel: agent nigdy nie stoi przed wyborem „który z trzech `grill-me`”. Wybór podejmuje **człowiek raz**, tutaj.
> Zasada: **1 skill governance + 1 skill implementacyjny** aktywny w danej fazie. Reszta przez progressive disclosure.

---

## 1. Inwentarz (stan zweryfikowany 2026-10-29)

| Źródło | Identyfikator | Licencja | Skala | Rola u nas |
|---|---|---|---|---|
| `mattpocock/skills` (tag `v1.3.2`) | `mp-*` | **MIT** | ~39 skilli (`engineering`, `productivity`) | workflow, spec→tickets, TDD, diagnoza, przegląd |
| `robert-hoffmann/uncle-bob` | `ub-*` | **MIT** | 11 skilli (`ub-quality`, `ub-workflow`, `ub-governance`, `ub-authoring`, `ub-python/ts/vue/nuxt/css/tailwind`) | governance, jakość, standardy stacku |
| `unclebob/ub-mode` | `ubm-*` | **BRAK licencji** | 1 skill | inspiracja; **nie vendorujemy kodu** — tylko streszczenie z podaniem SHA (wzorzec: `skills/ub-mode/SKILL.md`) |
| to repozytorium (HHH) | `hhh-*` | MIT | 5 skilli + bramki | wywiad lokalny, protokół dowodów, bramki, podpis DONE |

**To dwie różne rzeczy o tej samej marce:** `robert-hoffmann/uncle-bob` (system skilli, MIT) ≠ `unclebob/ub-mode` (pojedynczy skill, bez licencji). Mylenie ich to pierwsze źródło chaosu po instalacji.

---

## 2. Kolizje nazw — rozstrzygnięcie (twarda tabela)

HHH dostarcza te same `id`, co Matt. Wybieramy **jednego właściciela na fazę** i drugi zestaw odinstalowujemy — nie „na wszelki wypadek”.

| Identyfikator (kolizja) | Zostaje | Odinstalowany / wyłączony | Uzasadnienie |
|---|---|---|---|
| `grill-me` | **`mp-grill-me`** (lub `hhh-grill-me`, jeśli potrzebujesz zapisu do `docs/tasks`) | drugi | jeden protokół wywiadu = jeden format artefaktu |
| `tdd` | **`mp-tdd`** | drugi | Matt ma pełny cykl + integrację z biletami |
| `code-review` | **`mp-code-review`** + `ub-governance` (dowody) | drugi | przegląd = jeden właściciel, governance tylko kryteria |
| `domain-modeling` | **`mp-codebase-design`** (deep modules) + `ub-quality` | drugi | projekt modułu to jedno pojęcie, nie dwa |
| `implement` / `implement-spec` | **`mp-implement-spec`** | własne warianty | świeży subagent na bilet = mechanizm oszczędzania kontekstu |

**Reguła instalacji:** jeśli skill ma `disable-model-invocation: true` — zostaw. To darmowa ochrona przed odpaleniem drogiej fazy przez przypadek.

---

## 3. Precedencja (bezwzględna, w razie sprzeczności instrukcji)

```
1. Prawda repozytorium      — kod, testy, ADR, kontrakty
2. Bramki deterministyczne  — exit code, hash-pin, Nx boundaries
3. Governance               — ub-governance / hhh-protokół (dowody, wyjątki)
4. Workflow                 — ub-workflow / mp-wayfinder / mp-to-tickets
5. Specjalista stacku       — mp-*, ub-ts, ub-python, ub-css
6. Preferencje użytkownika  — „zrób szybciej” (tylko gdy 1–5 milczą)
```

Zdanie do `AGENTS.md`, dosłownie:

> **Żaden skill nie unieważnia bramki.** Jeśli skill każe pominąć test, a bramka wymaga testu — wygrywa bramka, a sprzeczność trafia do ADR.

---

## 4. Mapa faz → skill (kopiuj do `AGENTS.md`)

| Faza | Skill | Artefakt | Limit |
|---|---|---|---|
| Wywiad | `mp-grill-me` / `hhh-grill-me` | `## Decyzje z wywiadu` (źródło, błąd, Must NOT) | 2–4 pytania, ≤ 2k tok. |
| Duży plan | `mp-wayfinder` | mapa biletów-decyzji na trackerze → **STOP, akceptacja** | 1 sesja |
| Spec | `mp-to-spec` | kryteria akceptacji + non-goals | ≤ 6k tok. |
| Bilety | `mp-to-tickets` | DAG tracer bullets z krawędziami blokad | ≤ 4k tok. |
| Projekt modułu | `mp-codebase-design` + `ub-quality` | interfejs, seam, plan testów | ≤ 3k tok. |
| Implementacja | `mp-tdd` + (`ub-ts` \| `ub-python`) + `hhh-ub-mode` | RED→GREEN + kod | ≤ 40k tok. |
| Diagnoza | `mp-diagnosing-bugs` | hipoteza → eksperyment → wniosek | 2 hipotezy |
| Przegląd | `mp-code-review` + `ub-governance` | zarzuty z `file:line` | ≤ 5k tok. |
| Domknięcie | `mp-pr` + `hhh-protokół` | PR + dowody + podpis człowieka | ≤ 2k tok. |
| Refleksja | `mp-retro` / `ub-authoring` | poprawka **skilla lub bramki** | ≤ 5k tok. |

Skille opcjonalne (tylko na żądanie): `mp-prototype`, `mp-research`, `mp-triage`, `mp-improve-codebase-architecture`, `mp-handoff` (obowiązkowy przy 70% budżetu sesji).

---

## 5. Instalacja: pinuj, nie „latest”

```bash
# 1. Matt — pin na tagu (MIT, można vendorować)
npx skills add mattpocock/skills --skill tdd --skill diagnosing-bugs --skill to-spec --skill to-tickets --skill implement-spec
# odnotuj wersję: v1.3.2 (zweryfikowana 2026-10-29)

# 2. robert-hoffmann/uncle-bob — tylko governance + jakość + 1 specjalista stacku
npx skills add robert-hoffmann/uncle-bob --skill ub-governance --skill ub-quality --skill ub-ts --agent claude-code codex

# 3. unclebob/ub-mode — NIE instaluj (brak licencji). Trzymaj streszczenie w repo z podaniem SHA.
```

Zasady higieny (lekcje z audytu HHH):
- **Wersja w repo, nie w głowie:** `.agents/skills.lock` z `repo@tag/sha` + lista aktywnych.
- **Aktualizacja = PR**, nie automat. Skill zmienia zachowanie całego zespołu — to zmiana kodu, nie tapeta.
- **Zero vendorowania bez licencji.** Jeśli licencji brak — streszczenie + cytat SHA (HHH robi to dobrze w `skills/ub-mode/SKILL.md`).

---

## 6. Budżet skilli (anty-przepalanie)

| Ograniczenie | Wartość | Egzekwowanie |
|---|---|---|
| Aktywne skille w fazie | 2 (1 governance + 1 impl.) | człowiek; przegląd `skills.lock` |
| Opisy w `SKILL.md` | pisane pod routing, nie marketing (`ub-authoring`) | review |
| Ciężkie referencje | tylko na żądanie (progressive disclosure) | struktura katalogów |
| Skill zmieniony bez testu | **blokada** | harness ewaluacyjny (poniżej) |

**Test routingu (minimalny, 3 przypadki na start):**

```yaml
- ticket: "dodaj pole email do formularza kontaktowego"
  expect: {must_call: [mp-grill-me], must_not_call: [mp-wayfinder], max_skills_active: 2}
- ticket: "zaplanuj migrację 12 pakietów na ESM"
  expect: {must_call: [mp-wayfinder], must_not_start_coding: true}
- ticket: "test sypie się losowo w CI"
  expect: {must_call: [mp-diagnosing-bugs], max_hypotheses: 2}
```

Bez tego typu testów „skille są wybitne” pozostaje opinią — a po instalacji trzech katalogów jedyne, co możesz zmierzyć bez testów, to rachunek za tokeny.

---

## 7. Checklist po instalacji (5 minut, jednorazowo)

- [ ] `skills.lock` zawiera dokładnie jeden skill na fazę z §4.
- [ ] Żaden `id` nie występuje dwa razy (`ls **/SKILL.md | xargs grep -h '^name:' | sort | uniq -d` → pusto).
- [ ] `AGENTS.md` ≤ 120 linii i zawiera precedencję z §3 **oraz** zdanie „skill nie unieważnia bramki”.
- [ ] Trzy testy routingu z §6 przechodzą po instalacji i po każdej aktualizacji.
- [ ] Skille bez licencji obecne wyłącznie jako streszczenie z SHA (nie kopia plików).
