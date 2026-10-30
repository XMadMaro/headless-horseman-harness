#!/usr/bin/env bash
# Test akceptacyjny: uprząż nie została rozbrojona.
# Jeśli ktoś (agent) zmienił bramkę bez review, harness.lock przestaje się zgadzać.
set -uo pipefail
[[ -f harness.lock ]] || { echo "brak harness.lock"; exit 1; }
bash scripts/gate-lock.sh --check
