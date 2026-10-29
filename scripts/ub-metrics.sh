#!/usr/bin/env bash
# CP-144 / AGENTS.md Reguła 7.17: raport crapper (CRAP / złożoność) + dryer (duplikacja) dla plików TS.
# REPORT-ONLY: nie blokuje pusha. Progi blokujące = osobny CP po baseline (Reguła 7.4).
# Awaria narzędzia (clone, niezgodny SHA, crash) = exit != 0. Brak cichego sukcesu.
#
# Użycie:
#   bash scripts/ub-metrics.sh                 # pliki TS zmienione względem origin/main (HEAD, bez brudnego worktree)
#   bash scripts/ub-metrics.sh plik.ts dir/    # wskazane ścieżki
#   UB_COVERAGE=1 bash scripts/ub-metrics.sh   # crapper z pokryciem (uruchamia vitest --coverage; wolne)
set -euo pipefail

CRAPPER_SHA="${CRAPPER_SHA:-6fd92c4c9bcc56efb64a2f8743d5a2993bcfd42d}"
DRYER_SHA="${DRYER_SHA:-66ff6d21a42c04afcad89c78a80066176d1294b0}"
TOOLS_DIR="${UB_TOOLS_DIR:-$HOME/.cache/citypulse-ub-tools}"
BASE_REF="${BASE_REF:-origin/main}"

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

fetch_tool() {
  local name="$1" sha="$2" dir="$TOOLS_DIR/$1"
  if [ ! -d "$dir/.git" ]; then
    mkdir -p "$TOOLS_DIR"
    git clone --quiet "https://github.com/unclebob/${name}.git" "$dir"
  fi
  if ! git -C "$dir" cat-file -e "${sha}^{commit}" 2>/dev/null; then
    git -C "$dir" fetch --quiet origin
  fi
  if ! git -C "$dir" checkout --quiet --detach "$sha" 2>/dev/null; then
    echo "UB-METRICS-ERROR: nie można przełączyć ${name} na przypięty SHA ${sha}" >&2
    return 3
  fi
  local actual
  actual="$(git -C "$dir" rev-parse HEAD)"
  if [ "$actual" != "$sha" ]; then
    echo "UB-METRICS-ERROR: ${name} HEAD=${actual} != przypięty SHA ${sha}" >&2
    return 3
  fi
}

targets=()
if [ "$#" -gt 0 ]; then
  targets=("$@")
else
  while IFS= read -r f; do
    [ -n "$f" ] && [ -f "$f" ] && targets+=("$f")
  done < <(git diff --name-only --diff-filter=AM "${BASE_REF}...HEAD" -- 'apps/**/*.ts' 'apps/**/*.tsx' 'packages/**/*.ts' 'packages/**/*.tsx' \
    | grep -vE '\.(spec|test|e2e)\.tsx?$' || true)
fi

if [ "${#targets[@]}" -eq 0 ]; then
  echo "UB-METRICS: brak zmienionych plików TS względem ${BASE_REF} — nic do zmierzenia."
  exit 0
fi

fetch_tool crapper "$CRAPPER_SHA"
fetch_tool dryer "$DRYER_SHA"

crapper_args=(--no-coverage)
[ "${UB_COVERAGE:-0}" = "1" ] && crapper_args=()

echo "=== UB-METRICS crapper@${CRAPPER_SHA:0:8} dryer@${DRYER_SHA:0:8} | pliki: ${#targets[@]}"
echo "=== crapper ${crapper_args[*]:-(z pokryciem)}"
"$TOOLS_DIR/crapper/crapper" "${crapper_args[@]}" "${targets[@]}"
echo "=== dryer (threshold 0.82)"
"$TOOLS_DIR/dryer/dryer" "${targets[@]}"
echo "=== UB-METRICS: raport zakończony (report-only, bez progów blokujących)"
