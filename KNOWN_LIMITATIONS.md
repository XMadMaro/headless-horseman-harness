# KNOWN_LIMITATIONS — co ten harness NIE robi

> ⚠️ Harness nie uczyni agenta genialnym. Uczyni go zdyscyplinowanym.
> Jeśli założenia biznesowe są błędne, harness pomoże Ci zbudować błędny system bardzo zdyscyplinowanie.

1. **Fikcja checklisty (Cargo Cult):** `docs-provenance.py` sprawdza obecność `## Decyzje z wywiadu` + 50 znaków + 3 słowa-klucze, nie prawdę. Agent może zmyślić sekcję. Mitigacja: `grep -r "Uzasadnienie"` + review człowieka.
2. **Friction vs Adoption:** Za ostre bramki = `force push`, `--no-verify`. Mitigacja: `FAST_TRACK` dla docs-only, `--allow-false-positive` w `adversarial-review.sh`.
3. **Regex Hell:** `grep` ma false positives (np. `sk-` w teście). Mitigacja: allowlist `// APPROVED: <powód>` + AST gdzie warto.
4. **Context Exhaustion:** Wpinanie wszystkich skilli na raz rozwala okno kontekstu. Mitigacja: modularne ładowanie — tylko `grill-me` na starcie, tylko `code-review` na końcu.
5. **Fałszywe poczucie bezpieczeństwa:** Zielone bramki ≠ dobry produkt. Mitigacja: `AGENTS.md 7.11` — CLI zbiera dowody, człowiek podpisuje `DONE`.

Harness gwarantuje **higienę wykonania, nie słuszność kierunku**.
