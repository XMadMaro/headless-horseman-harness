#!/usr/bin/env bash
# adversarial-review.sh — deterministyczny skaner grzechów głównych na git diff.
# Zero LLM. Ten sam diff = ten sam werdykt.
#
# Zasady (poprawki po audycie):
#   * skanujemy WYŁĄCZNIE linie dodawane (+) — usuwanie grzechu nigdy nie jest karane (Reguła 7.17 Subtract)
#   * lokalizacja w raporcie jest LICZONA z nagłówka @@ (nigdy nie zmyślana)
#   * kod wyjścia odpowiada werdyktowi (0 = PASS, 1 = BLOCKING)
#   * każdy wyjątek ma właściciela, powód i termin ważności (.adversarial-allow)
#
# Użycie:
#   bash scripts/adversarial-review.sh [base_ref] [--enable-tenant-check]
#   bash scripts/adversarial-review.sh --self-test      # test własny: 0 = detektor działa, 1 = regresja
#   bash scripts/adversarial-review.sh --test-negative   # surowy test negatywny (1 = wykryto, jak przy realnym diffie)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

BASE_REF=""
ENABLE_TENANT=false
TEST_NEGATIVE=false
SELF_TEST=false
for arg in "$@"; do
  case "$arg" in
    --enable-tenant-check) ENABLE_TENANT=true ;;
    --test-negative)       TEST_NEGATIVE=true ;;
    --self-test)           SELF_TEST=true ;;
    --help|-h)
      echo "Usage: bash scripts/adversarial-review.sh [base_ref] [--enable-tenant-check] | --test-negative | --self-test"
      exit 0 ;;
    -*) echo "Nieznana flaga: $arg" >&2; exit 2 ;;
    *)  BASE_REF="$arg" ;;
  esac
done
BASE_REF="${BASE_REF:-origin/main}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

DIFF_FILE="$(mktemp)"
FINDINGS_FILE="$(mktemp)"
ALLOW_FILE=".adversarial-allow"

cleanup() {
  rm -f "$DIFF_FILE" "$FINDINGS_FILE" 2>/dev/null || true
  if [[ -n "${TEST_DIR:-}" && -d "${TEST_DIR:-}" ]]; then rm -rf "$TEST_DIR" 2>/dev/null || true; fi
  return 0   # P0-1: trap nie może nadpisać kodu wyjścia bramki
}
trap cleanup EXIT

# ---------------------------------------------------------------- self-test fixtures
make_negative_fixture() {
  # Wzorce trzymamy w tests/fixtures/negative/ (a nie w tym skrypcie), żeby skaner
  # nie flagował własnych stringów testowych. Wyjątek: .adversarial-allow (z terminem).
  local fx="tests/fixtures/negative"
  TEST_DIR="$(mktemp -d)"
  if [[ ! -f "$fx/test.tsx" || ! -f "$fx/0099_test.sql" ]]; then
    echo "❌ Brak fixture'ów w $fx — nie mogę wykonać samotestu." >&2
    return 1
  fi
  {
    echo "diff --git a/apps/admin/src/app/test.tsx b/apps/admin/src/app/test.tsx"
    echo "--- a/apps/admin/src/app/test.tsx"
    echo "+++ b/apps/admin/src/app/test.tsx"
    echo "@@ -7,0 +8,4 @@"
    sed 's/^/+/' "$fx/test.tsx"
    echo "diff --git a/packages/shared/db/migrations/0099_test.sql b/packages/shared/db/migrations/0099_test.sql"
    echo "--- a/packages/shared/db/migrations/0099_test.sql"
    echo "+++ b/packages/shared/db/migrations/0099_test.sql"
    echo "@@ -1,0 +2,1 @@"
    sed 's/^/+/' "$fx/0099_test.sql"
  } > "$DIFF_FILE"
}

if [[ "$TEST_NEGATIVE" == true || "$SELF_TEST" == true ]]; then
  make_negative_fixture
  echo -e "${BLUE}🧪 TRYB SAMOTESTU: wstrzyknięto wzorce z 5 różnych klas grzechów${NC}"
else
  if ! git rev-parse --verify "${BASE_REF}^{commit}" >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Base ref '$BASE_REF' nie istnieje — używam HEAD~1${NC}"
    BASE_REF="HEAD~1"
    git rev-parse --verify "${BASE_REF}^{commit}" >/dev/null 2>&1 || {
      echo -e "${YELLOW}⚠️  Brak historii (HEAD~1 nie istnieje) — nie ma czego skanować.${NC}"
      echo "Podsumowanie: BLOCKING=0, ADVISORY=0, ALLOWED=0"
      echo -e "${GREEN}✅ ADVERSARIAL REVIEW PASSED: brak zmian.${NC}"
      exit 0
    }
  fi
  git diff "$BASE_REF...HEAD" --unified=0 > "$DIFF_FILE" 2>/dev/null || true
  if [[ ! -s "$DIFF_FILE" ]]; then
    echo -e "${GREEN}✅ Brak diffu do sprawdzenia ($BASE_REF...HEAD pusty)${NC}"
    echo "Podsumowanie: BLOCKING=0, ADVISORY=0, ALLOWED=0"
    echo -e "${GREEN}✅ ADVERSARIAL REVIEW PASSED: brak zmian.${NC}"
    exit 0
  fi
fi

# ---------------------------------------------------------------- detekcja (tylko linie dodawane)
# Wyjście: RULE<TAB>LEVEL<TAB>path<TAB>line<TAB>snippet
ENABLE_TENANT_AWK=$([[ "$ENABLE_TENANT" == true ]] && echo 1 || echo 0)

# Uwaga: mawk (domyślny awk w Debianie/Ubuntu) NIE wspiera interwałów {n,}.
# Dlatego sekrety liczymy funkcją toklen(), a nie regexem — inaczej wzorzec nigdy nie dopasuje.
# shellcheck disable=SC2016
awk -v tenant="$ENABLE_TENANT_AWK" '
function emit(rule, level, path, line, snip) {
  gsub(/\t/, " ", snip)
  printf "%s\t%s\t%s\t%s\t%s\n", rule, level, path, line, substr(snip, 1, 110)
}
function is_test_file(p) { return (p ~ /(\.(spec|test|e2e)\.[a-z]+$)|(^e2e\/)/) }
function is_migration(p) { return (p ~ /(^|\/)(migrations|alembic)\//) }
function is_cssish(p) { return (p ~ /\.(css|scss|sass|less|tsx|jsx|vue|svelte)$/) }
function is_code(p) { return (p ~ /\.(ts|tsx|js|jsx|mjs|cjs|py|go|rs|java|kt|rb|cs|php|vue|svelte|sh|sql)$/) }
function is_docs(p) { return (p ~ /\.(md|mdx|txt|rst)$/ || p ~ /(^|\/)docs\//) }

# długość ciągu alfanumerycznego po markerze (bez interwałów)
function toklen(s, marker,   i, rest, n, c) {
  i = index(s, marker); if (i == 0) return 0
  rest = substr(s, i + length(marker)); n = 0
  while (1) {
    c = substr(rest, n + 1, 1)
    if (c == "") break
    if (c !~ /[A-Za-z0-9_-]/) break
    n++
  }
  return n
}
function has_secret(s,   m, v) {
  if (toklen(s, "sk-proj-", 10) >= 10) return 1
  if (toklen(s, "sk-", 10) >= 10) return 1
  if (toklen(s, "ghp_", 10) >= 10) return 1
  if (toklen(s, "gho_", 10) >= 10) return 1
  if (toklen(s, "AKIA", 12) >= 12) return 1
  if (toklen(s, "xoxb-", 10) >= 10) return 1
  if (s ~ /BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY/) return 1
  if (s ~ /(password|passwd|secret|token)[ \t]*[:=][ \t]*["\047]/) {
    if (match(s, /[:=][ \t]*["\047][^"\047]*["\047]/)) {
      v = substr(s, RSTART, RLENGTH)
      gsub(/["\047]/, "", v); gsub(/[:=]/, "", v); gsub(/[ \t]/, "", v)
      if (length(v) >= 6) return 1
    }
  }
  return 0
}

/^diff --git / { path = ""; pending = 0; next }
/^\+\+\+ / { if ($0 ~ /^\+\+\+ b\//) path = substr($0, 7); else path = ""; next }
/^@@ / {
  if (match($0, /\+[0-9]+/)) nl = substr($0, RSTART + 1, RLENGTH - 1) + 0; else nl = 0
  if (nl > 0) nl = nl - 1
  pending = 0
  next
}
/^\+/ && !/^\+\+\+/ {
  line = substr($0, 2); nl++
  if (path == "") next
  approved = (line ~ /APPROVED:/)

  # ---- S1: silent fallback (tylko kod; w dokumentacji to przykład, nie błąd) ----
  if (!approved && is_code(path)) {
    # Python: except ...: pass / return None (także w kolejnej linii)
    if (line ~ /^[ \t]*except[^:]*:[ \t]*(pass|return[ \t]+(None|null))[ \t]*$/) {
      emit("S1", "BLOCKING", path, nl, line); pending = 0
    } else if (line ~ /^[ \t]*except([ \t]+[^:]+)?[ \t]*:[ \t]*$/) {
      pending = nl
    } else if (pending && line ~ /^[ \t]*(pass|return[ \t]+(None|null))[ \t]*$/) {
      emit("S1", "BLOCKING", path, pending, "except ... -> " line); pending = 0
    }
    # JS/TS: pusty catch, catch z samym komentarzem, catch -> null/undefined
    else if (line ~ /catch[ \t]*(\([^)]*\))?[ \t]*\{[ \t]*(\/\*([^*]|\*[^\/])*\*\/[ \t]*)?\}[ \t]*$/) {
      emit("S1", "BLOCKING", path, nl, line); pending = 0
    } else if (line ~ /catch[ \t]*(\([^)]*\))?[ \t]*\{[ \t]*return[ \t]+(null|undefined);?[ \t]*\}[ \t]*$/) {
      emit("S1", "BLOCKING", path, nl, line); pending = 0
    } else if (pending && line ~ /^[ \t]*(return[ \t]+(null|undefined);?)?[ \t]*\}[ \t]*$/) {
      emit("S1", "BLOCKING", path, pending, "catch ... -> " line); pending = 0
    } else if (line ~ /catch[ \t]*(\([^)]*\))?[ \t]*\{[ \t]*$/) {
      pending = nl
    } else if (line !~ /^[ \t]*(\/\/|#|$)/) {
      pending = 0
    }
  }

  # ---- S2: destructive CSS (pliki produkcyjne) ----
  if (!approved && line ~ /!important/ && is_cssish(path) && !is_test_file(path))
    emit("S2", "BLOCKING", path, nl, line)

  # ---- S3: fake assertion ----
  if (!approved && is_code(path) && line ~ /(toBeDefined\(\)|toBeTruthy\(\)|assert[ \t]+True|assertTrue\(True\))/)
    emit("S3", "BLOCKING", path, nl, line)

  # ---- S4: sekrety (w dokumentacji ADVISORY: tam często są przykłady) ----
  if (!approved && has_secret(line))
    emit("S4", (is_docs(path) ? "ADVISORY" : "BLOCKING"), path, nl, line)

  # ---- S5: destructive migration ----
  if (!approved && is_migration(path) && line ~ /(DROP[ \t]+TABLE|DROP[ \t]+COLUMN|ALTER[ \t]+TABLE.*DROP)/)
    emit("S5", "BLOCKING", path, nl, line)

  # ---- S6: dependency bloat (doradczo) ----
  if (!approved && path ~ /(package\.json|pyproject\.toml)$/ && line ~ /^[ \t]*"[^"]+"[ \t]*:[ \t]*"[~^]?[0-9]/)
    emit("S6", "ADVISORY", path, nl, line)

  # ---- S7: tenant leak (opt-in) ----
  if (tenant == 1 && !approved && line ~ /(req|request)\.(body|query|params)\.[A-Za-z0-9_]*(tenant|citySlug|clientId|orgId|workspaceId)/)
    emit("S7", "BLOCKING", path, nl, line)

  next
}
' "$DIFF_FILE" > "$FINDINGS_FILE"

# ---------------------------------------------------------------- allowlist (wyjątki z terminem)
# Format .adversarial-allow:  RULE  glob  owner=@kto  reason="..."  expires=YYYY-MM-DD
is_allowed() {
  local rule="$1" path="$2"
  [[ -f "$ALLOW_FILE" ]] || return 1
  local line r g rest exp today
  today="$(date +%Y-%m-%d)"
  while IFS= read -r line; do
    [[ "$line" =~ ^[[:space:]]*(#|$) ]] && continue
    r="$(awk '{print $1}' <<<"$line")"
    g="$(awk '{print $2}' <<<"$line")"
    [[ "$r" == "$rule" ]] || continue
    # shellcheck disable=SC2053
    [[ "$path" == $g ]] || continue
    exp="$(grep -oE 'expires=[0-9]{4}-[0-9]{2}-[0-9]{2}' <<<"$line" | cut -d= -f2 || true)"
    if [[ -z "$exp" ]]; then
      echo -e "${RED}🚩 WYJĄTEK BEZ TERMINU: $line${NC}" >&2
      return 2
    fi
    if [[ "$exp" < "$today" ]]; then
      echo -e "${RED}🚩 WYJĄTEK WYGASŁ ($exp): $line${NC}" >&2
      return 3
    fi
    return 0
  done < "$ALLOW_FILE"
  return 1
}

BLOCKING=0; ADVISORY=0; ALLOWED=0
ROWS=""
DETECTED_RULES=""

while IFS=$'\t' read -r rule level path line snip; do
  [[ -z "${rule:-}" ]] && continue
  rc=0; is_allowed "$rule" "$path" || rc=$?
  if [[ $rc -eq 0 ]]; then
    ALLOWED=$((ALLOWED+1)); ROWS+="ALLOWED|$rule|$path:$line|$snip"$'\n'; continue
  fi
  if [[ $rc -eq 2 || $rc -eq 3 ]]; then
    ROWS+="BLOCKING|$rule (wyjątek bez terminu/po terminie)|$path:$line|$snip"$'\n'
    BLOCKING=$((BLOCKING+1)); continue
  fi
  if [[ "$level" == "BLOCKING" ]]; then
    BLOCKING=$((BLOCKING+1)); DETECTED_RULES+="$rule "
    ROWS+="BLOCKING|$rule|$path:$line|$snip"$'\n'
  else
    ADVISORY=$((ADVISORY+1)); ROWS+="ADVISORY|$rule|$path:$line|$snip"$'\n'
  fi
done < "$FINDINGS_FILE"

# ---------------------------------------------------------------- raport
echo ""
echo "───────────────────────────────────────────────────────────────────────────────"
printf "| %-8s | %-9s | %-34s | %s\n" "Poziom" "Grzech" "Lokalizacja" "Opis / fragment"
echo "───────────────────────────────────────────────────────────────────────────────"
if [[ -z "$ROWS" ]]; then
  printf "| %-8s | %-9s | %-34s | %s\n" "PASS" "-" "-" "Brak grzechów w liniach dodawanych."
else
  while IFS='|' read -r lvl rl loc snip; do
    [[ -z "${lvl:-}" ]] && continue
    desc="$snip"
    case "$rl" in
      S1) desc="Silent fallback ukrywa błąd (7.9) :: $snip" ;;
      S2) desc="!important niszczy kaskadę (7.10) :: $snip" ;;
      S3) desc="Asercja pozorna, przejdzie dla pustego obiektu (7.2) :: $snip" ;;
      S4) desc="Prawdopodobny sekret w kodzie :: $snip" ;;
      S5) desc="DROP bez -- APPROVED_DESTRUCTIVE (7.18) :: $snip" ;;
      S6) desc="Nowa zależność bez uzasadnienia w CP :: $snip" ;;
      S7) desc="Tenant z niezaufanego payloadu (7.10) :: $snip" ;;
    esac
    printf "| %-8s | %-9s | %-34s | %s\n" "$lvl" "$rl" "$loc" "$desc"
  done <<< "$ROWS"
fi
echo "───────────────────────────────────────────────────────────────────────────────"
UNIQ_RULES="$(tr ' ' '\n' <<< "$DETECTED_RULES" | grep -v '^$' | sort -u | tr '\n' ' ' || true)"
echo "Podsumowanie: BLOCKING=$BLOCKING, ADVISORY=$ADVISORY, ALLOWED=$ALLOWED"
[[ -n "$UNIQ_RULES" ]] && echo "Wykryte klasy: ${UNIQ_RULES% }"

if [[ "$TEST_NEGATIVE" == true ]]; then
  if [[ $BLOCKING -gt 0 ]]; then
    echo -e "${GREEN}✅ TEST NEGATYWNY UDANY: detektor zgłosił $BLOCKING naruszeń w $UNIQ_RULES${NC}"
    echo -e "${YELLOW}   (tryb --test-negative zwraca 1, bo tak zachowuje się na realnym diffie; w CI użyj --self-test)${NC}"
  else
    echo -e "${RED}❌ TEST NEGATYWNY NIEUDANY: detektor nie zgłosił nic${NC}"
  fi
  exit 1
fi

if [[ "$SELF_TEST" == true ]]; then
  classes=$(tr ' ' '\n' <<< "$DETECTED_RULES" | grep -v '^$' | sort -u | wc -l | tr -d ' ')
  if [[ "$classes" -ge 4 && $BLOCKING -ge 4 ]]; then
    echo -e "${GREEN}✅ SELF-TEST PASSED: detektor rozpoznał $classes klas grzechów ($UNIQ_RULES)${NC}"
    exit 0
  fi
  echo -e "${RED}❌ SELF-TEST FAILED: oczekiwano >=4 klas, wykryto $classes ($UNIQ_RULES). To regresja bramki.${NC}"
  exit 1
fi

if [[ $BLOCKING -gt 0 ]]; then
  echo -e "${RED}❌ ADVERSARIAL REVIEW FAILED: napraw BLOCKING przed REVIEW.${NC}"
  echo "   Wyjątek? Dopisz do .adversarial-allow: <RULE> <glob> owner=@kto reason=\"...\" expires=RRRR-MM-DD"
  exit 1
fi
echo -e "${GREEN}✅ ADVERSARIAL REVIEW PASSED: linie dodawane czyste.${NC}"
exit 0
