#!/usr/bin/env bash
# install.sh — instalator Headless Horseman Harness (HHH)
#
# Poprawki po audycie:
#   * nie twierdzi, że "pobiera" uprząż — instaluje hooki w istniejącym checkoucie
#   * usuwa martwe odwołania do nieistniejących skryptów
#   * weryfikuje integralność (harness.lock) po instalacji
#   * hooki instaluje scripts/install-hooks.sh (nie nadpisuje cudzych bez backupu)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "🐎 Headless Horseman Harness (HHH) — instalacja w istniejącym repozytorium"
echo "=============================================================="

if [[ ! -d .git ]]; then
  echo "⚠️  Brak .git. Zainicjuj repo (git init), potem uruchom ponownie."
  exit 0
fi

REQUIRED=(scripts/gate-lock.sh scripts/check-gate-integrity.sh scripts/adversarial-review.sh \
          scripts/docs-provenance.py scripts/preflight-gate.py scripts/epistemic-gate.py \
          scripts/install-hooks.sh AGENTS.md harness.lock)
missing=0
for f in "${REQUIRED[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "🚩 Brak pliku uprzęży: $f"
    missing=1
  fi
done
if [[ $missing -eq 1 ]]; then
  echo "   To repozytorium wygląda na niekompletne. Sklonuj całość (npx degit XMadMaro/headless-horseman-harness)."
  exit 1
fi

echo "🔍 Sprawdzanie stosu narzędziowego i rekomendowanego ekosystemu..."
if command -v python3 >/dev/null 2>&1; then
  echo "  ✅ python3: $(python3 --version)"
else
  echo "  ❌ python3: BRAK (Wymagany do bramek preflight, epistemic i provenance)"
  exit 1
fi

if command -v nx >/dev/null 2>&1 || [ -f "node_modules/.bin/nx" ]; then
  echo "  ✅ nx: dostępny"
else
  echo "  ⚠️  nx: BRAK (Zalecane: npm install -g nx lub npm install -D nx dla monorepo)"
fi

if curl -sf http://127.0.0.1:8080/health >/dev/null 2>&1 || command -v xerj >/dev/null 2>&1; then
  echo "  ✅ xerj: aktywny lub zainstalowany (BM25)"
else
  echo "  ⚠️  xerj: NIEWYKRYTY (Zalecane: uruchom xerj.service dla szybkiego wyszukiwania BM25)"
fi

echo "📋 Rekomendowane serwery MCP w konfiguracji agenta/IDE:"
echo "  🔹 codebase-memory-mcp  -> Graf wiedzy AST (search_graph, trace_path)"
echo "  🔹 Hindsight MCP        -> Trwała pamięć architektoniczna (https://hindsight.vectorize.io/)"
echo ""

echo "1/3 uprawnienia"
chmod +x scripts/*.sh 2>/dev/null || true
chmod +x scripts/*.py 2>/dev/null || true

echo "2/3 hooki git"
bash scripts/install-hooks.sh

echo "3/3 weryfikacja integralności"
bash scripts/gate-lock.sh --check
bash scripts/check-gate-integrity.sh

echo
echo "✅ HHH zainstalowany."
echo "   Bramki: gate-lock, docs-provenance (Inception), preflight (7.19), epistemic (7.20), adversarial-review."
echo "   Uwaga: bramki preflight/epistemic włączasz, tworząc katalogi docs/preflight i docs/epistemic."
