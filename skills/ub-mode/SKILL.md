---
name: ub-mode
description: >
  Dyscyplina inżynierska wg Uncle Boba (unclebob/ub-mode) dostosowana do CityPulse.
  Używaj przy każdej zmianie kodu: First Make it Work → Then Make it Right → Practice.
  Wywołanie: /ub-mode lub gdy zadanie dotyczy poprawki, refaktoru albo nowej funkcji.
---

# ub-mode (adaptacja CityPulse)

Źródło: https://github.com/unclebob/ub-mode @ `57a8bdd28e45ed41900ace0bafa2ff76dd9ed70f`.
Upstream nie ma pliku LICENSE, więc tu jest własne streszczenie zasad z odnośnikami do reguł repo, nie kopia.

**Pierwszeństwo:** `AGENTS.md` > ten skill. „First Make it Work” NIE znosi Reguły 7.13 (diagnoza → plan → akceptacja przed kodem) ani 7.11 (dowody CLI + podpis człowieka).

## 1. First Make it Work

- **Leniwość:** jedna decyzja żyje w jednym miejscu. Najmniejsza zmiana, która rozwiązuje problem (limit 3.1: ≤15 plików).
- **Najpierw kształt danych**, potem logika. Współbieżny zapis = nie współdziel stanu.
- **TDD:** test oblewa z oczekiwanego powodu (RED), minimalna zmiana daje GREEN (Reguła 7.2). Jeśli uczciwy test jest niepraktyczny, nie pisz złego. Zgłoś `🚩 [FLAG:UNVERIFIED_RUNTIME]`.
- **Redesign od podstaw:** nie doklejaj wymagania do starego projektu. Zapytaj, co zbudowałbyś od zera, i dostarcz to w kawałkach (CP-143 jako przykład).
- **Attack the Premise (7.17):** dwie poprawki z tym samym założeniem oblały tę samą bramkę → STOP, zapisz założenie jednym zdaniem w sekcji `Premise` w CP, usuń je przed trzecią próbą.
- **Subtract Before You Add (7.17, 7.16):** najpierw usuń złożoność (martwy kod, duplikaty, zastąpione silniki), potem dodawaj. Sekcja `Subtract` w CP.
- **Cel sprawdzalny:** celuj w stan końcowy, który da się zweryfikować komendą. Przerwa w połowie dozwolona, gdy jest zaplanowana i odwracalna.
- **Zbuduj dźwignię:** praca nieoczywista na pierwszy rzut oka → najpierw jedna jednostka ręcznie, potem narzędzie.

### Architektura
- **Domena:** nielegalne stany niemożliwe do zapisania w typach (`packages/shared/domain`). Glosariusz domeny nie istnieje jeszcze jako plik — kandydat w `docs/backlog.md`.
- **Granice (7.10):** parsuj dane zewnętrzne raz na wejściu (Zod), wewnątrz ufaj. Logika biznesowa w czystych funkcjach. Single Gateway (ADR-0043).
- **Typy:** nie wyciszaj kompilatora (`@ts-ignore`, `as any` zakazane).
- **Idempotencja:** dwa uruchomienia albo crash w połowie kończą się tym samym stanem (outbox, BullMQ retry).
- **Wspólny stan:** jeśli nie muszą dzielić mutowalnego stanu, daj każdemu własny. Jeśli muszą, jeden pisarz wymuszony strukturą (RLS, `withTenantSession`).

## 2. Then Make it Right

- **Przyczyna, nie objaw (7.9, 7.17):** odtwórz, napraw przyczynę. Strażnik ukrywający crash nie jest poprawką. Cichy fallback zakazany (7.16).
- **Małe weryfikowalne jednostki:** skończ i sprawdź jedną, dopiero wtedy następna (commit lokalny per jednostka, Reguła 2.7).
- **Test zachowania, nie implementacji:** test woła kod tak jak użytkownik i sprawdza to, co użytkownik zobaczy. **Null-Return Check:** jeśli test przeszedłby przy każdej funkcji zwracającej `null` / `undefined` / `[]`, wyrzuć go albo przepisz (7.2, 7.14).
- **Metryki (raport):** `bash scripts/ub-metrics.sh [pliki...]` uruchamia crapper (CRAP / złożoność) i dryer (duplikacja ≥ 0.82) dla plików TS zmienionych względem `origin/main`. Funkcja > 10 złożoności albo nowa para duplikatów wymaga uzasadnienia w CP.
- **Mutacja (na żądanie GATEKEEPERA, security/tenant):** `unclebob/mutator`. Pokryj niepokryte, zabij ocalałe mutanty, usuń martwy kod.
- **Refaktor:** przypnij zachowanie testem → zmień strukturę → udowodnij brak zmiany zachowania.

## 3. Practice

- **Log:** zapisuj każdą akcję i powód. Raport końcowy = log + surowy stdout + tabela PASS/FAIL (4.2).
- **Kontekst:** główny wątek mały, ciężar do subagentów/plików, w wątku zostaje streszczenie (7.8).
- **Worktree:** usuwaj tylko to, co potwierdzenie pokazało jako nieużywane. Niezacommitowana cudza praca czeka na decyzję człowieka (`🚩 [FLAG:DIRTY_WORKTREE_CONFLICT]`).
- **Commity:** małe, uporządkowane. Każdy mówi: dlaczego, co, jak udowodniono. Push do `origin/main` raz na CP, po zielonych bramkach i podpisie człowieka (2.7, 7.11).
