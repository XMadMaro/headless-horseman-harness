#!/usr/bin/env bash
# check-gate-integrity.sh — czy uprząż nie została osłabiona.
#
# Poprawki po audycie (P0-3):
#   * integralność oparta na sha256 (harness.lock), nie na liczbie nagłówków
#   * usunięcie pliku bramki jest BŁĘDEM (wcześniej tylko żółte ostrzeżenie)
#   * porównywane są ZBIORY ID reguł, nie licznik (18 zaślepek nie przejdzie)
#   * usunięty martwy blok porównania z origin/main (szukał nieistniejącego wzorca)
#   * kod wyjścia: 0 = PASS, 1 = osłabienie, 2 = błąd użycia
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo "🔒 Gate Integrity Check"
echo "======================================================"

if [[ ! -f AGENTS.md ]]; then
  echo -e "${RED}❌ BRAK AGENTS.md — nie ma czego chronić (fail-closed)${NC}"
  exit 1
fi

WEAKENED=0

# 1) integralność treści bramek (hash-pin)
if bash scripts/gate-lock.sh --check; then
  echo -e "${GREEN}✅ Integralność plików bramek: zgodna z harness.lock${NC}"
else
  echo -e "${RED}🚩 RULES-WEAKENED: pliki bramek nie zgadzają się z harness.lock${NC}"
  WEAKENED=1
fi

# 2) wymagane bramki istnieją
for f in scripts/adversarial-review.sh scripts/docs-provenance.py scripts/epistemic-gate.py scripts/preflight-gate.py; do
  if [[ ! -f "$f" ]]; then
    echo -e "${RED}🚩 BRAK BRAMKI: $f${NC}"
    WEAKENED=1
  fi
done

# 3) wykrywanie OBEJŚCIA hooka (strukturalnie, nie po treści wiadomości)
#    Uczciwie: `git commit --no-verify` NIE zostawia śladu w commicie — lokalnie jest
#    niewykrywalne. Wykrywalny jest SKUTEK: commit dotykający kodu bez artefaktu preflight.
#    Pełna ochrona = wymagane status checks w CI (branch protection), nie hook lokalny.
#    Oceniamy tylko przypadek, gdy bramka JUŻ istniała w poprzednim commicie
#    (inaczej zgłaszalibyśmy historyczny import repo jako obejście).
preflight_was_present=0
if git rev-parse -q --verify HEAD~1 >/dev/null 2>&1; then
  if git ls-tree -r --name-only HEAD~1 2>/dev/null | grep -q '^docs/preflight/'; then
    preflight_was_present=1
  fi
fi
if [[ -d docs/preflight && $preflight_was_present -eq 1 ]]; then
  changed_code="$(git show --name-only --pretty=format: HEAD 2>/dev/null \
    | grep -E '\.(ts|tsx|js|jsx|py|go|rs|vue|svelte)$' || true)"
  if [[ -n "$changed_code" ]]; then
    if ! git show --name-only --pretty=format: HEAD 2>/dev/null | grep -qE '^docs/preflight/.*\.json$'; then
      echo -e "${RED}🚩 MOŻLIWE OBEJŚCIE HOOKA: ostatni commit zmienia kod, ale nie wnosi artefaktu preflight${NC}"
      echo "   (to typowy skutek commit --no-verify; ochrona docelowa: required checks w CI)"
      WEAKENED=1
    fi
  fi
fi
if grep -qE "skip[ -]ci|--no-verify|\[skip ci\]" .git/COMMIT_EDITMSG 2>/dev/null; then
  echo -e "${YELLOW}⚠️  wiadomość commita zawiera skip-ci/--no-verify (sygnał, nie dowód)${NC}"
fi

# 4) hooki istnieją i nie są puste (martwy hook = brak ochrony)
if [[ -d .git/hooks ]]; then
  for h in pre-commit pre-push; do
    if [[ ! -s ".git/hooks/$h" ]]; then
      echo -e "${YELLOW}⚠️  brak aktywnego hooka .git/hooks/$h — uruchom: bash install.sh${NC}"
    fi
  done
fi

# 5) raport liczby reguł (informacyjnie — NIE jest kryterium)
echo "Reguły w AGENTS.md: $(grep -cE '^## 7\.[0-9]+' AGENTS.md)"

if [[ $WEAKENED -eq 1 ]]; then
  echo -e "${RED}❌ GATE INTEGRITY FAILED${NC}"
  echo "   Jeśli zmiana bramki jest zamierzona: bash scripts/gate-lock.sh --update + review w PR."
  exit 1
fi

echo -e "${GREEN}✅ GATE INTEGRITY PASSED${NC}"
exit 0
