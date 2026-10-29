#!/usr/bin/env bash
# install.sh — Instalator Headless Horseman Harness (HHH)
set -euo pipefail

echo "🐎 Headless Horseman Harness (HHH) — Installer"
echo "==============================================="

# Nadaj uprawnienia wykonywania skryptom
chmod +x scripts/*.sh 2>/dev/null || true
chmod +x scripts/*.py 2>/dev/null || true

# Sprawdź obecność Gita
if [[ ! -d ".git" ]]; then
  echo "⚠️  Katalog .git nie istnieje. Zainicjuj repozytorium (git init) przed instalacją hooków."
  exit 0
fi

# Zainstaluj pre-commit i pre-push hooki
mkdir -p .git/hooks

cat > .git/hooks/pre-commit << 'EOF'
#!/usr/bin/env bash
set -e
echo "🐎 [HHH] Gate Integrity & Provenance Check..."
python3 scripts/docs-provenance.py --check
bash scripts/check-gate-integrity.sh
EOF

chmod +x .git/hooks/pre-commit

cat > .git/hooks/pre-push << 'EOF'
#!/usr/bin/env bash
set -e
echo "🐎 [HHH] Adversarial Code Review Check..."
bash scripts/adversarial-review.sh origin/main
EOF

chmod +x .git/hooks/pre-push

echo "✅ Hooki Git (.git/hooks/pre-commit, pre-push) zainstalowane pomyślnie."
echo "🚀 HHH jest aktywny i chroni Twoje repozytorium przed halucynacjami agentów."
