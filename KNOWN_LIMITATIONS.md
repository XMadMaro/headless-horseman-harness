# KNOWN_LIMITATIONS — co ten harness NIE robi

> ⚠️ Harness nie uczyni agenta genialnym. Uczyni go zdyscyplinowanym.
> Jeśli założenia biznesowe są błędne, harness pomoże Ci zbudować błędny system bardzo zdyscyplinowanie.

1. **Fikcja checklisty (Cargo Cult):** `docs-provenance.py` sprawdza obecność `## Decyzje z wywiadu` + 50 znaków + 3 słowa-klucze, nie prawdę. Agent może zmyślić sekcję. Mitigacja: `grep -r "Uzasadnienie"` + review człowieka.
2. **Friction vs Adoption:** Za ostre bramki = `force push`, `--no-verify`. Mitigacja: `FAST_TRACK` dla docs-only, `--allow-false-positive` w `adversarial-review.sh`.
3. **Regex Hell:** `grep` ma false positives (np. `sk-` w teście). Mitigacja: allowlist `// APPROVED: <powód>` + AST gdzie warto.
4. **Context Exhaustion:** Wpinanie wszystkich skilli na raz rozwala okno kontekstu. Mitigacja: modularne ładowanie — tylko `grill-me` na starcie, tylko `code-review` na końcu.
5. **Fałszywe poczucie bezpieczeństwa:** Zielone bramki ≠ dobry produkt. Mitigacja: `AGENTS.md 7.11` — CLI zbiera dowody, człowiek podpisuje `DONE`.

6. **Bramki łapią lenistwo, nie wrogość (zmierzone 2026-10-30).** Przy założeniu, że agent jest
   *aktywnym przeciwnikiem*, dwie bramki padają trywialnie:
   - `decision-gate.py`: `confirmed_by` to **string, nie tożsamość**. Komunikat błędu D8 sam podaje
     dokładną frazę potwierdzenia; przepisanie jej zajmuje agentowi jedną iterację, a bramka
     kończy z `PASSED: decyzja podpisana (Marek (human))` — czyli podpis jest do podrobienia.
   - `gate-lock.sh`: `--update` jest w zasięgu agenta. Zmiana pliku bramki + `--update` daje
     `--check` = 0 i `check-gate-integrity` = 0, a backdoor w bramce staje się niewidoczny.
   - `hidden/`: ukryte **przez zapomnienie, nie przez brak dostępu** — agent czyta cały system plików.
   - `.hhh/events.jsonl`, `.git/hooks/*`, `--no-verify`: wszystko w zasięgu agenta.
   **Wniosek:** to tripwire na pośpiech, nie kontrola bezpieczeństwa. Integralność musi być
   weryfikowana **poza agentem** (CI względem `main`, podpisy GPG/SSH, log append-only, least privilege).

Harness gwarantuje **higienę wykonania, nie słuszność kierunku**.
