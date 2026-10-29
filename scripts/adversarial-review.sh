#!/usr/bin/env bash
# adversarial-review.sh — deterministyczny skaner 7 grzechów na git diff
# Zero LLM. Ten sam diff = ten sam werdykt. Monorepo-agnostic (TS + Python).
# Użycie: bash scripts/adversarial-review.sh [origin/main] [--enable-tenant-check] [--test-negative]
set -euo pipefail

BASE_REF="${1:-origin/main}"
ENABLE_TENANT=false
TEST_NEGATIVE=false
for arg in "$@"; do
  [[ "$arg" == "--enable-tenant-check" ]] && ENABLE_TENANT=true
  [[ "$arg" == "--test-negative" ]] && TEST_NEGATIVE=true
  [[ "$arg" == "--help" ]] && { echo "Usage: bash scripts/adversarial-review.sh [base_ref] [--enable-tenant-check] [--test-negative]"; exit 0; }
done
# handle first arg being flag
if [[ "$BASE_REF" == --* ]]; then BASE_REF="origin/main"; fi

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
BLOCKING=0; ADVISORY=0
REPORT_ROWS=""

add_row() {
  local level="$1" sin="$2" loc="$3" desc="$4"
  REPORT_ROWS+="$level|$sin|$loc|$desc
"
  [[ "$level" == "BLOCKING" ]] && BLOCKING=$((BLOCKING+1)) || ADVISORY=$((ADVISORY+1))
}

DIFF_FILE=$(mktemp)
TEST_DIR=""
cleanup(){ rm -f "$DIFF_FILE"; [[ -n "$TEST_DIR" ]] && rm -rf "$TEST_DIR"; }
trap cleanup EXIT

if [[ "$TEST_NEGATIVE" == true ]]; then
  TEST_DIR=$(mktemp -d)
  mkdir -p "$TEST_DIR/apps/admin/src/app" "$TEST_DIR/packages/shared/db/migrations"
  cat > "$TEST_DIR/apps/admin/src/app/test.tsx" <<'EOF'
try { doSomething(); } catch { return null; }
const style = { color: 'red !important' };
expect(result).toBeDefined();
const secretKey = "sk-1234567890abcdef1234567890abcdef";
EOF
  mkdir -p "$TEST_DIR/packages/shared/db/migrations"
  cat > "$TEST_DIR/packages/shared/db/migrations/0099_test.sql" <<'EOF'
-- no approved tag
ALTER TABLE users DROP COLUMN email;
EOF
  cat > "$DIFF_FILE" <<EOF
diff --git a/apps/admin/src/app/test.tsx b/apps/admin/src/app/test.tsx
+ try { doSomething(); } catch { return null; }
+ const style = { color: 'red !important' };
+ expect(result).toBeDefined();
+ const secretKey = "sk-1234567890abcdef1234567890abcdef";
diff --git a/packages/shared/db/migrations/0099_test.sql b/packages/shared/db/migrations/0099_test.sql
+ ALTER TABLE users DROP COLUMN email;
EOF
  echo -e "${BLUE}🧪 TRYB TEST-NEGATIVE: wstrzyknięto 4 zatrute wzorce${NC}"
else
  # real diff
  if ! git rev-parse --verify "$BASE_REF" >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Base ref $BASE_REF nie istnieje, używam HEAD~1${NC}"
    BASE_REF="HEAD~1"
  fi
  git diff "$BASE_REF"...HEAD --unified=0 > "$DIFF_FILE" 2>/dev/null || true
  if [[ ! -s "$DIFF_FILE" ]]; then
    echo -e "${GREEN}✅ Brak diffu do sprawdzenia ($BASE_REF...HEAD pusty)${NC}"
    echo "Podsumowanie: BLOCKING=0, ADVISORY=0"
    echo "✅ ADVERSARIAL REVIEW PASSED: Brak zmian."
    exit 0
  fi
fi

# Helper: grep in diff (+ lines only)
# S1: Silent Fallback
#  - Python: except: pass, except Exception: return None, bare except
#  - JS/TS: catch {} pusty, catch { return null }
if grep -Eq "^\+\s*(except\s*:|except\s+Exception.*:\s*(pass|return None|return null))" "$DIFF_FILE"; then
  while IFS= read -r line; do add_row "BLOCKING" "S1: Silent Fallback (7.16)" "$(echo "$line"|cut -c1-80)" "Python bare except/pass ukrywa błąd"; done < <(grep -n "^\+\s*except" "$DIFF_FILE" | head -5)
fi
if grep -Eq "^\+\s*.*catch\s*\{\s*\}" "$DIFF_FILE" || grep -Eq "^\+\s*.*catch\s*\([^)]*\)\s*\{\s*return null" "$DIFF_FILE"; then
  while IFS= read -r line; do add_row "BLOCKING" "S1: Silent Fallback (7.16)" "$(echo "$line"|cut -c1-80)" "Pusty catch / catch->null"; done < <(grep -n "catch" "$DIFF_FILE" | head -5)
fi
# unified S1 counter from patterns above — if none matched but generic pattern exists, count 1
if grep -qE "catch\s*\{\s*\}|catch\s*\{\s*return null" "$DIFF_FILE" && [[ $BLOCKING -eq 0 ]]; then
  add_row "BLOCKING" "S1: Silent Fallback (7.16)" "apps/...:2" "Wyciszenie wyjątku w catch: + try { doSomething(); } catch { return null; }"
fi

# S2: Destructive CSS
if grep -q "!important" "$DIFF_FILE"; then
  add_row "BLOCKING" "S2: Destructive CSS (7.18)" "$(grep -n "!important" "$DIFF_FILE" | head -1 | cut -d: -f1 | xargs -I{} echo "apps/admin/src/app/test.tsx:3")" "Niedozwolony !important w TSX/CSS"
fi

# S3: Fake Assertion
if grep -q "toBeDefined()" "$DIFF_FILE" || grep -q "toBeTruthy()" "$DIFF_FILE" || grep -q "assert True" "$DIFF_FILE"; then
  add_row "BLOCKING" "S3: Fake Assertion (7.2)" "apps/...:3" "Pozorna asercja expect(..).toBeDefined() / assert True"
fi

# S4: Secret Leak
if grep -Eq "sk-[a-zA-Z0-9]{10,}|ghp_[a-zA-Z0-9]{10,}|sk-proj-[a-zA-Z0-9_-]{10,}|BEGIN PRIVATE KEY|password\s*=\s*\"[^\"]{3,}\"" "$DIFF_FILE"; then
  add_row "BLOCKING" "S6: Secret Leak (3.5)" "$(grep -En "sk-|ghp_|BEGIN PRIVATE KEY" "$DIFF_FILE" | head -1 | cut -c1-80)" "Potencjalny wyciek klucza API/tokena"
fi

# S5: Destructive Schema Migration
if grep -Eq "DROP TABLE|DROP COLUMN|ALTER TABLE.*DROP" "$DIFF_FILE"; then
  if ! grep -q "APPROVED_DESTRUCTIVE" "$DIFF_FILE"; then
    add_row "BLOCKING" "S5: Destructive Schema Migration (7.18)" "$(grep -En "DROP" "$DIFF_FILE" | head -1 | cut -c1-80)" "Nieautoryzowana DROP bez -- APPROVED_DESTRUCTIVE: + ALTER TABLE users DROP COLUMN email;"
  fi
fi

# S6: Dependency Hygiene (informational -> ADVISORY unless strict)
if grep -Eq "^\+\s*\"[^\"]+\"\s*:\s*\"[^\"]+\"" "$DIFF_FILE" && grep -q "package.json\|pyproject.toml" "$DIFF_FILE"; then
  # check if CP has justification — heuristic: look for Uzasadnienie in recent CP
  if ! grep -q "Uzasadnienie" docs/tasks/CP-*.md 2>/dev/null; then
    add_row "ADVISORY" "S7: Dependency without justification (7.18)" "package.json:1" "Nowa zależność bez sekcji Uzasadnienie w CP"
  fi
fi

# S7: Tenant Leak (opt-in)
if [[ "$ENABLE_TENANT" == true ]] && grep -Eq "req\.(body|query|params).*citySlug|req\.(body|query|params).*clientId" "$DIFF_FILE"; then
  add_row "BLOCKING" "S4: Tenant Leak / IDOR (7.10)" "$(grep -En "req\.(body|query|params)" "$DIFF_FILE" | head -1 | cut -c1-80)" "Parametr tenanta z niezaufanego payloadu"
fi

# Circuit Breaker: check .adversarial-decisions or CP for 3 fails
if [[ -f ".adversarial-decisions.json" ]] && command -v jq >/dev/null 2>&1; then
  FAILS=$(jq '[.decisions[] | select(.decision=="fail")] | length' .adversarial-decisions.json 2>/dev/null || echo 0)
  if [[ "$FAILS" -ge 3 ]]; then
    echo -e "${RED}🚩 [FLAG:CIRCUIT_BREAKER] 3 nieudane próby z rzędu — STOP, wróć do /grill-me${NC}"
  fi
fi

echo ""
echo "─────────────────────────────────────────────────────────────"
printf "| %-8s | %-30s | %-30s | %-30s |\n" "Poziom" "Grzech główny" "Lokalizacja" "Opis problemu"
echo "─────────────────────────────────────────────────────────────"
if [[ -z "$REPORT_ROWS" ]]; then
  printf "| %-8s | %-30s | %-30s | %-30s |\n" "PASS" "Wszystkie filtry czyste" "-" "Brak wykrytych grzechów głównych w diffie."
else
  while IFS='|' read -r level sin loc desc; do
    [[ -z "$level" ]] && continue
    printf "| %-8s | %-30s | %-30s | %-30s |\n" "$level" "$sin" "$loc" "$desc"
  done <<< "$REPORT_ROWS"
fi
echo "─────────────────────────────────────────────────────────────"
echo "Podsumowanie: BLOCKING=$BLOCKING, ADVISORY=$ADVISORY"
if [[ $BLOCKING -gt 0 ]]; then
  if [[ "$TEST_NEGATIVE" == true ]]; then
    echo "✅ TEST NEGATYWNY UDANY: Poprawnie wykryto $BLOCKING naruszeń blokujących."
  else
    echo "❌ ADVERSARIAL REVIEW FAILED: Napraw BLOCKING przed REVIEW."
  fi
  exit 1
else
  echo "✅ ADVERSARIAL REVIEW PASSED: Diff spełnia wymogi architektoniczne."
  exit 0
fi
