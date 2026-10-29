#!/usr/bin/env bash
# check-gate-integrity.sh — weryfikuje że harness nie został osłabiony
set -euo pipefail
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

AGENTS="AGENTS.md"
if [[ ! -f "$AGENTS" ]]; then
  # fallback dla template w podfolderze
  [[ -f "harness-template/AGENTS.md" ]] && AGENTS="harness-template/AGENTS.md"
fi

echo "🔒 Gate Integrity Check"
echo "======================================================"

RULES_COUNT=$(grep -c "^\*\*Reguła [0-9]" "$AGENTS" 2>/dev/null || true)
if [[ -z "$RULES_COUNT" || "$RULES_COUNT" == "0" ]]; then
  RULES_COUNT=$(grep -c "^## 7\." "$AGENTS" 2>/dev/null || true)
fi
RULES_COUNT=$(echo "$RULES_COUNT" | tr -d '[:space:]')
[[ -z "$RULES_COUNT" ]] && RULES_COUNT=0
echo "Reguły w $AGENTS: $RULES_COUNT"

# wykryj osłabienia
WEAKENED=0
if grep -q "skip ci\|skip-ci\|--no-verify" .git/COMMIT_EDITMSG 2>/dev/null; then
  echo -e "${RED}🚩 RULES-WEAKENED: COMMIT_EDITMSG zawiera skip-ci/no-verify${NC}"; WEAKENED=1
fi
if git log -1 --pretty=%B 2>/dev/null | grep -qi "skip ci\|no-verify"; then
  echo -e "${YELLOW}⚠️  Ostatni commit zawiera skip ci${NC}"
fi
if [[ ! -f "scripts/adversarial-review.sh" && ! -f "harness-template/scripts/adversarial-review.sh" ]]; then
  echo -e "${RED}🚩 Brak adversarial-review.sh${NC}"; WEAKENED=1
fi
if [[ ! -f "scripts/docs-provenance.py" && ! -f "harness-template/scripts/docs-provenance.py" ]]; then
  echo -e "${YELLOW}⚠️  Brak docs-provenance.py${NC}"
fi

# sprawdź czy AGENTS.md nie został odchudzony vs origin/main
if git rev-parse --verify origin/main >/dev/null 2>&1; then
  MAIN_COUNT=$(git show origin/main:AGENTS.md 2>/dev/null | grep -c "^\*\*Reguła " 2>/dev/null || true)
  MAIN_COUNT=$(echo "$MAIN_COUNT" | tr -d '[:space:]'); [[ -z "$MAIN_COUNT" ]] && MAIN_COUNT=0
  if [[ "$MAIN_COUNT" -gt "$RULES_COUNT" ]]; then
    echo -e "${RED}🚩 RULES-WEAKENED: AGENTS.md ma mniej reguł niż origin/main ($RULES_COUNT < $MAIN_COUNT)${NC}"
    WEAKENED=1
  fi
fi

if [[ $WEAKENED -eq 1 ]]; then
  echo -e "${RED}❌ GATE INTEGRITY FAILED${NC}"
  exit 1
else
  echo -e "${GREEN}✅ GATE INTEGRITY PASSED (reguły: $RULES_COUNT)${NC}"
  exit 0
fi
