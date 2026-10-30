# Skill: grill-me — Inception Gate Protocol

> Ładuj ten skill ZAWSZE przed planem. Zakaz pisania kodu bez wywiadu (Reguła 7.21).

## Kiedy
- Nowy UX / nowa encja / niejednoznaczne wymagania / prompt użytkownika < 20 słów
- `STANDARD_TRACK` (dotyka `apps/*, packages/*, src/*`)

## Jak
1. Zadaj 2-4 pytania z opcjami (ask_question modal):
   1. `Skąd dane?` [props / sesja+RLS / endpoint GET / Qdrant / DB]
   2. `Co przy braku danych / 403 / 404?` [Fail-Closed + toast / redirect / skeleton / BRAK_DANYCH]
   3. `Czego NIE robimy w tym kroku? (Must NOT)` [np. nie ruszamy auth, nie dodajemy migracji]
   4. (opcjonalnie) `Gdzie walidacja?` [Zod na granicy / Pydantic / brak]
2. Zapisz odpowiedzi w `docs/tasks/CP-xxx.md` w `## Decyzje z wywiadu (/grill-me)` (>=50 znaków, 3 filary)
3. Dopiero po `Potwierdzam: [data, osoba]` przejdź do `TEMPLATE.md` Sekcja 3/4

## Bramka
`python scripts/docs-provenance.py --check` musi dać `PASS`. Inaczej `IN_PROGRESS` zablokowane.

## Antywzorzec
Agent który zgaduje `citySlug` z `props` zamiast `session` tworzy `ghost context` (Reguła 7.9) — blokuje `adversarial-review.sh` S4.
