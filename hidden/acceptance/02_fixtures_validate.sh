#!/usr/bin/env bash
# Test akceptacyjny: dostarczone artefakty-wzorce nadal przechodzą swoje bramki.
# Regresja w bramce albo rozjazd schematu z przykładem = czerwony test.
set -uo pipefail
python3 scripts/preflight-gate.py --file docs/preflight/CP-150.example.json || exit 1
python3 scripts/decision-gate.py --verify --ticket CP-150 --step scope || exit 1
