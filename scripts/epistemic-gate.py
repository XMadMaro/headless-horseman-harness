#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
epistemic-gate.py — bramka epistemologiczna dla artefaktów agenta.

Model: nie oceniamy "krytycznego myślenia" (niewidoczne), oceniamy CENĘ TWIERDZENIA.
Każde twierdzenie musi mieć komendę, oczekiwany wynik i zaobserwowany wynik.
`confidence: high` wymaga DOWODU WYKONANEGO (--execute), nie zadeklarowanego.

Reguły blokujące: E1-E10 (E10: allowlista narzędzi + zakaz maskowania). Doradcze: A1-A3. Szczegóły: docs/architecture/CRITICAL-THINKING-ENFORCEMENT.md
Zasada: fail-closed — brak pliku / zły JSON / brak klucza => exit 1 (nie "pomiń").
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
NC = "\033[0m"

REQUIRED_TOP = ["ticket", "code_changed", "claims", "confidence", "tests"]
CONFIDENCE_LEVELS = {"high", "medium", "low"}
MIN_FALSIFIER_LEN = 9  # "test pass" (9) jest za krótkie i zbyt ogólne

# E10: dowód musi pochodzić z NARZĘDZIA, nie z dowolnego shella.
ALLOWED_CMD_PREFIXES = (
    "nx ", "pnpm ", "npm ", "npx ", "yarn ", "node ", "python3 ", "python ",
    "pytest", "tsc ", "eslint ", "ruff ", "mypy ", "pyright ", "semgrep", "gitleaks",
    "git diff", "git show", "git log", "sha256sum", "cargo ", "go test", "make ",
    "bash scripts/", "sh scripts/", "bash ./scripts/",
)
MASKING_PATTERNS = (r"\|\|\s*true", r"\|\|\s*echo", r";\s*true\b", r";\s*exit\s+0", r"&&\s*true\b")
SELF_CONFIRMING = ("echo ", "printf ")


def norm(text: str) -> str:
    """Normalizacja do porównań: bez whitespace-owych różnic, bez wielkości liter."""
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def fail(msg: str) -> int:
    print(f"{RED}✖ EPISTEMIC-GATE: {msg}{NC}")
    return 1


class Report:
    def __init__(self) -> None:
        self.blocking: list[tuple[str, str]] = []
        self.advisory: list[tuple[str, str]] = []
        self.executed = 0

    def block(self, rule: str, msg: str) -> None:
        self.blocking.append((rule, msg))

    def warn(self, rule: str, msg: str) -> None:
        self.advisory.append((rule, msg))

    def print(self) -> None:
        print()
        print("─" * 78)
        print(f"| {'Poziom':8s} | {'Reguła':6s} | Opis")
        print("─" * 78)
        if not self.blocking and not self.advisory:
            print(f"| {'PASS':8s} | {'-':6s} | Zero naruszeń: twierdzenia mają wykonane dowody.")
        for rule, msg in self.advisory:
            print(f"| {YELLOW}{'WARN':8s}{NC} | {rule:6s} | {msg}")
        for rule, msg in self.blocking:
            print(f"| {RED}{'BLOCKING':8s}{NC} | {rule:6s} | {msg}")
        print("─" * 78)
        print(f"Podsumowanie: BLOCKING={len(self.blocking)}, ADVISORY={len(self.advisory)}, wykonane_dowody={self.executed}")


def claim_problem(claim: dict, idx: int) -> str | None:
    """E2: zweryfikowane twierdzenie musi mieć komendę, oczekiwanie i obserwację."""
    for key in ("id", "text", "kind"):
        if not str(claim.get(key, "")).strip():
            return f"claim[{idx}] brak pola '{key}'"
    if claim.get("verified") is not True:
        return None
    for key in ("cmd", "expected", "observed"):
        if not str(claim.get(key, "")).strip():
            return f"claim {claim.get('id')} ma verified=true, ale brak '{key}' (konfabulacja)"
    return None


def check_claim_observed(claim: dict) -> str | None:
    """E3: observed musi zawierać expected (dosłownie, po normalizacji)."""
    exp, obs = norm(claim.get("expected", "")), norm(claim.get("observed", ""))
    if exp and exp not in obs:
        return (
            f"claim {claim.get('id')}: expected '{claim.get('expected')}' "
            f"nie występuje w observed '{claim.get('observed')}'"
        )
    return None


def check_cmd_policy(claim: dict, extra_prefixes: tuple[str, ...] = ()) -> str | None:
    """
    E10: komenda dowodowa musi:
      * pochodzić z allowlisty narzędzi (test runner, linter, kompilator),
      * nie maskować porażki (|| true, || echo, ; exit 0),
      * nie być autorskim potwierdzeniem (echo/printf).
    """
    cmd = str(claim.get("cmd", "")).strip()
    if not cmd:
        return None
    prefixes = tuple(extra_prefixes) + ALLOWED_CMD_PREFIXES
    cid = claim.get("id")
    low = cmd.lower()
    for pat in MASKING_PATTERNS:
        if re.search(pat, low):
            return f"claim {cid}: komenda maskuje porażkę ('{pat}') — dowód, który nie może zawieść, nie jest dowodem"
    if low.startswith(SELF_CONFIRMING):
        return f"claim {cid}: komenda to echo/printf — agent wypisuje własne potwierdzenie, nie uruchamia narzędzia"
    if not any(low.startswith(p) for p in prefixes):
        return (
            f"claim {cid}: komenda '{cmd[:60]}' spoza allowlisty narzędzi "
            f"(dozwolone m.in. {', '.join(p.strip() for p in ALLOWED_CMD_PREFIXES[:6])}...)"
        )
    return None


def check_self_fulfilling(claim: dict) -> str | None:
    """
    E9: dowód nie może być autorski. Jeśli oczekiwany wynik jest wpisany w samą komendę
    (np. `echo '3 passed'`), agent po prostu pisze własne potwierdzenie.
    Dowód ma pochodzić z narzędzia (test runner, linter, kompilator), nie z `echo`.
    """
    cmd, expected = norm(claim.get("cmd", "")), norm(claim.get("expected", ""))
    if expected and cmd and expected in cmd:
        return (
            f"claim {claim.get('id')}: oczekiwany wynik '{claim.get('expected')}' jest wpisany "
            f"w komendę — to potwierdzenie samego siebie, nie dowód"
        )
    return None


def execute_claim(claim: dict, report: Report, timeout: int) -> str | None:
    """Uruchamia cmd i sprawdza, czy wynik zawiera expected. Zwraca komunikat błędu albo None."""
    cmd = str(claim.get("cmd", "")).strip()
    expected = str(claim.get("expected", "")).strip()
    if not cmd or not expected:
        return None
    try:
        proc = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return f"claim {claim.get('id')}: dowód TIMEOUT po {timeout}s ({cmd})"
    except Exception as exc:  # noqa: BLE001 - celowo: każdy błąd wykonania = brak dowodu
        return f"claim {claim.get('id')}: nie można wykonać dowodu ({exc})"
    out = norm(proc.stdout + "\n" + proc.stderr)
    if norm(expected) not in out:
        return (
            f"claim {claim.get('id')}: expected '{expected}' NIE wystąpił w realnym wyniku "
            f"'{cmd}' (exit={proc.returncode}) — deklaracja nie zgadza się z rzeczywistością"
        )
    claim["executed"] = True
    claim["real_exit"] = proc.returncode
    report.executed += 1
    return None


def check_document(doc: dict, report: Report, execute: bool, timeout: int, extra_prefixes: tuple[str, ...] = ()) -> None:
    claims = doc.get("claims") or []
    hypotheses = doc.get("hypotheses") or []
    tests = doc.get("tests") or {}
    code_changed = bool(doc.get("code_changed"))
    confidence = str(doc.get("confidence", "")).strip().lower()

    # --- claims: E1, E2, E3 ---
    verified = [c for c in claims if c.get("verified") is True]
    for idx, claim in enumerate(claims):
        problem = claim_problem(claim, idx)
        if problem:
            report.block("E2", problem)
            continue
        if claim.get("verified") is True:
            mismatch = check_claim_observed(claim)
            if mismatch:
                report.block("E3", mismatch)
            autorski = check_self_fulfilling(claim)
            if autorski:
                report.block("E9", autorski)
            policy = check_cmd_policy(claim, tuple(extra_prefixes))
            if policy:
                report.block("E10", policy)

    if execute:
        for claim in claims:
            if claim.get("verified") is not True:
                continue
            err = execute_claim(claim, report, timeout)
            if err:
                report.block("E3", err)

    if not verified:
        report.block("E1", "brak jakiegokolwiek zweryfikowanego twierdzenia (deklaracja bez dowodu)")

    # --- E4: overconfidence ---
    if confidence not in CONFIDENCE_LEVELS:
        report.block("E4", f"confidence '{confidence}' spoza {sorted(CONFIDENCE_LEVELS)}")
    elif confidence == "high" and report.executed == 0:
        report.block(
            "E4",
            "confidence=high bez WYKONANEGO dowodu — użyj --execute albo obniż confidence",
        )

    # --- E5/E6: higiena testów ---
    added, removed = int(tests.get("added", 0)), int(tests.get("removed", 0))
    if code_changed and removed > 0:
        report.block("E5", f"usunięto {removed} test(ów) przy zmianie kodu — osłabianie weryfikacji")
    if code_changed and added == 0:
        report.block("E6", "zmiana kodu bez ani jednego nowego testu (brak dowodu RED-first)")

    # --- E7: falsyfikowalność hipotez ---
    for hyp in hypotheses:
        predicted = norm(hyp.get("predicted", ""))
        if_wrong = norm(hyp.get("predicted_if_wrong", ""))
        hid = hyp.get("id", "?")
        if len(predicted) < MIN_FALSIFIER_LEN or len(if_wrong) < MIN_FALSIFIER_LEN:
            report.block("E7", f"hipoteza {hid}: przewidywania puste lub zbyt ogólne (min {MIN_FALSIFIER_LEN} znaków)")
        elif predicted == if_wrong:
            report.block("E7", f"hipoteza {hid}: brak falsyfikatora (przewidywanie == przewidywanie przeciwne)")

    # --- E8: dowód zachowania, nie tylko statyki ---
    if code_changed:
        behavior = [c for c in verified if norm(c.get("kind", "")) == "behavior"]
        if not behavior:
            report.block("E8", "zmiana kodu bez dowodu zachowania (kind=behavior) — tylko statyka")

    # --- doradcze A1-A3 ---
    if confidence == "high" and not (doc.get("unknowns") or []):
        report.warn("A1", "confidence=high przy pustych unknowns — sprawdź, czy to prawda, czy brak refleksji")
    if not (doc.get("alternatives_rejected") or []):
        report.warn("A2", "brak odrzuconych alternatyw (sycophancy: przyjęto założenie bez opozycji)")
    mutations = doc.get("mutations") or {}
    killed, survived = int(mutations.get("killed", 0)), int(mutations.get("survived", 0))
    if killed + survived > 0:
        score = killed / (killed + survived)
        if score < 0.8:
            report.warn("A3", f"mutation score {score:.2f} < 0.80 ({killed} zabitych / {survived} przeżyłych)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bramka epistemologiczna: dowód wykonywalny zamiast deklaracji."
    )
    parser.add_argument("--file", required=False, help="ścieżka do JSON z artefaktem epistemicznym")
    parser.add_argument("--ticket", help="ID biletu (skrót: docs/epistemic/<TICKET>.json)")
    parser.add_argument("--execute", action="store_true", help="wykonaj komendy dowodowe i porównaj wynik")
    parser.add_argument("--timeout", type=int, default=120, help="timeout jednego dowodu w sekundach")
    parser.add_argument(
        "--allow-cmd-prefix", action="append", default=[],
        help="dodatkowy dozwolony prefiks komendy dowodowej (np. 'uv run')",
    )
    args = parser.parse_args()

    if not args.file and not args.ticket:
        return fail("brak --file/--ticket (fail-closed: bramka nie zgaduje)")

    path = Path(args.file) if args.file else Path("docs/epistemic") / f"{args.ticket}.json"
    if not path.is_file():
        return fail(f"pliku nie ma: {path} (fail-closed)")

    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return fail(f"niepoprawny JSON w {path}: {exc}")
    if not isinstance(doc, dict):
        return fail(f"{path}: artefakt musi być obiektem JSON")

    missing = [k for k in REQUIRED_TOP if k not in doc]
    if missing:
        return fail(f"{path}: brak wymaganych kluczy: {', '.join(missing)} (fail-closed)")

    print(f"{BLUE}🔎 Epistemic Gate — {doc.get('ticket')} @ {doc.get('commit', 'bez commita')}{NC}")
    print(f"   tryb: {'WYKONUJĄCY (--execute)' if args.execute else 'statyczny'}")

    report = Report()
    check_document(doc, report, args.execute, args.timeout, tuple(args.allow_cmd_prefix or ()))
    report.print()

    if report.blocking:
        print(f"{RED}❌ EPISTEMIC GATE FAILED: {len(report.blocking)} naruszeń blokujących. To nie jest 'gotowe'.{NC}")
        return 1
    print(f"{GREEN}✅ EPISTEMIC GATE PASSED: twierdzenia poparte dowodami.{NC}")
    if report.advisory:
        print(f"{YELLOW}   (uwagi doradcze nie blokują — patrz trend, nie pojedynczy przebieg){NC}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
