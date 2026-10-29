#!/usr/bin/env bash
# gate-lock.sh — generuje/weryfikuje harness.lock (integralność bramek).
#
# Po co: poprzednia wersja liczyła nagłówki w AGENTS.md, więc 18 pustych zaślepek
# przechodziło jako "18 reguł", a podmiana skanera na `exit 0` nie była widoczna.
#
# Użycie:
#   bash scripts/gate-lock.sh --check     # 0 = lock zgodny, 1 = rozjazd/nośnik zmieniony
#   bash scripts/gate-lock.sh --update    # przelicz lock (wymaga review w PR!)
#
# OGRANICZENIE (uczciwie): ktoś z prawem zapisu może przeliczyć lock lokalnie.
# Ochroną jest CI + CODEOWNERS na scripts/** i AGENTS.md, nie ten plik.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
LOCK="harness.lock"

PROTECTED=(
  "AGENTS.md"
  "skills/ROUTING.md"
  "scripts/adversarial-review.sh"
  "scripts/docs-provenance.py"
  "scripts/check-gate-integrity.sh"
  "scripts/preflight-gate.py"
  "scripts/epistemic-gate.py"
  "scripts/gate-lock.sh"
  "scripts/install-hooks.sh"
  "scripts/selftest.sh"
  "scripts/decision-gate.py"
  "scripts/hhh-run.py"
  "install.sh"
  ".adversarial-allow"
  "scripts/acceptance-gate.py"
  "hidden/manifest.json"
  "hidden/acceptance/01_lock_intact.sh"
  "hidden/acceptance/02_fixtures_validate.sh"
  "tests/fixtures/negative/test.tsx"
  "tests/fixtures/negative/0099_test.sql"
)

# ID reguł, które MUSZĄ istnieć w AGENTS.md (zbiór, nie licznik)
RULES_EXPECTED="7.1 7.2 7.3 7.4 7.5 7.6 7.7 7.8 7.9 7.10 7.11 7.12 7.13 7.14 7.15 7.16 7.17 7.18 7.19 7.20 7.21"

hash_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$1"
  fi
}

rule_ids() {
  # wyciąga ID z nagłówków typu "## 7.17 ..." — zbiór posortowany
  grep -oE '^## (7\.[0-9]+)' "$1" 2>/dev/null | awk '{print $2}' | sort -V | tr '\n' ' ' | sed 's/ $//' || true
}

cmd_update() {
  {
    echo "# harness.lock — wygenerowany przez scripts/gate-lock.sh. NIE edytuj ręcznie."
    echo "# Zmiana wymaga review (CODEOWNERS na scripts/** i AGENTS.md)."
    echo "format=1"
    echo "rules=$(rule_ids AGENTS.md)"
    for f in "${PROTECTED[@]}"; do
      if [[ -f "$f" ]]; then
        echo "sha256 $(hash_file "$f")  $f"
      else
        echo "missing -  $f"
      fi
    done
  } > "$LOCK"
  echo "✅ zapisano $LOCK"
}

cmd_check() {
  if [[ ! -f "$LOCK" ]]; then
    echo "❌ BRAK $LOCK — integralność niezweryfikowana (fail-closed). Uruchom: bash scripts/gate-lock.sh --update"
    return 1
  fi
  local rc=0 declared_rules actual_rules path want got
  declared_rules="$(grep -oE '^rules=.*' "$LOCK" | cut -d= -f2- || true)"
  actual_rules="$(rule_ids AGENTS.md)"
  if [[ "$declared_rules" != "$actual_rules" ]]; then
    echo "🚩 ZBIÓR REGUŁ ZMIENIONY"
    echo "   lock:     ${declared_rules:-<pusto>}"
    echo "   AGENTS.md:${actual_rules:-<pusto>}"
    rc=1
  fi
  # każda reguła oczekiwana musi istnieć
  local r
  for r in $RULES_EXPECTED; do
    if ! grep -qE "^## ${r}([ .]|$)" AGENTS.md 2>/dev/null; then
      echo "🚩 BRAK REGUŁY ${r} w AGENTS.md"
      rc=1
    fi
  done
  while read -r _ hash path; do
    [[ -z "${path:-}" || "$path" == "#"* ]] && continue
    if [[ "$hash" == "-" ]]; then
      echo "🚩 PLIK BRAMKI USUNIĘTY: $path"
      rc=1
      continue
    fi
    if [[ ! -f "$path" ]]; then
      echo "🚩 PLIK BRAMKI USUNIĘTY: $path"
      rc=1
      continue
    fi
    got="$(hash_file "$path")"
    if [[ "$got" != "$hash" ]]; then
      echo "🚩 ZMIENIONA TREŚĆ BRAMKI: $path"
      echo "   lock=$hash"
      echo "   plik=$got"
      rc=1
    fi
  done < <(grep -E '^sha256 ' "$LOCK")
  return $rc
}

case "${1:---check}" in
  --check) cmd_check ;;
  --update) cmd_update ;;
  *) echo "Użycie: bash scripts/gate-lock.sh [--check|--update]"; exit 2 ;;
esac
