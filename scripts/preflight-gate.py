#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preflight-gate.py — "pomyśl, zanim napiszesz linijkę".

Problem, który rozwiązuje: agent zaczyna od kodu, potem dokleja, duplikuje i robi
frankensteina. Ta bramka wymaga artefaktu, który można PODWAŻYĆ mechanicznie:

  F2 (dive)      każde dotykane pliki muszą mieć CYCTAT istniejący w pliku w podanej linii
                 -> żeby to spełnić, agent MUSI otworzyć plik (nie zgadnie)
  F4 (subtract)  najpierw usuń; greenfield tylko z uzasadnieniem
  F5 (order)     plan zaczyna się od 'subtract' lub 'diagnose', nie od 'implement'
  F7 (dup)       nowy symbol, który już istnieje w repo, wymaga reuse lub uzasadnienia
  F6 (budget)    limit plików i linii -> blokada frankensteina

Fail-closed: brak pliku / złego JSON / brak klucza => exit 1.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

RED = "\033[0;31m"; GREEN = "\033[0;32m"; YELLOW = "\033[1;33m"; BLUE = "\033[0;34m"; NC = "\033[0m"

REQUIRED = ["ticket", "kind", "intent", "files_touched", "plan", "budget"]
DEFAULT_LIMITS = {"max_files": 15, "max_loc": 400}
SCAN_EXT = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".py", ".go", ".rs", ".vue", ".svelte", ".sh")
SHELL_DEF_RE = re.compile(r"^\s*(?:function\s+)?([A-Za-z_][A-Za-z0-9_]{2,})\s*\(\)\s*\{", re.M)
DEF_RE = re.compile(
    r"(?:^|\s)(?:export\s+)?(?:async\s+)?(?:function|def|class|const|let|interface|type)\s+([A-Za-z_][A-Za-z0-9_]{2,})",
    re.M,
)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def fail(msg: str) -> int:
    print(f"{RED}✖ PREFLIGHT-GATE: {msg}{NC}")
    return 1


class Report:
    def __init__(self) -> None:
        self.blocking: list[tuple[str, str]] = []
        self.advisory: list[tuple[str, str]] = []

    def block(self, rule: str, msg: str) -> None:
        self.blocking.append((rule, msg))

    def warn(self, rule: str, msg: str) -> None:
        self.advisory.append((rule, msg))

    def render(self) -> None:
        print()
        print("─" * 78)
        print(f"| {'Poziom':8s} | {'Reguła':6s} | Opis")
        print("─" * 78)
        if not self.blocking and not self.advisory:
            print(f"| {'PASS':8s} | {'-':6s} | Preflight kompletny: pliki przeczytane, plan od sprzątania.")
        for rule, msg in self.advisory:
            print(f"| {YELLOW}{'WARN':8s}{NC} | {rule:6s} | {msg}")
        for rule, msg in self.blocking:
            print(f"| {RED}{'BLOCKING':8s}{NC} | {rule:6s} | {msg}")
        print("─" * 78)
        print(f"Podsumowanie: BLOCKING={len(self.blocking)}, ADVISORY={len(self.advisory)}")


def verify_quote(entry: dict, area: int = 10) -> str | None:
    """F2: cytat musi istnieć w pliku w okolicy podanej linii. To dowód, że plik został otwarty."""
    path_raw = entry.get("path", "")
    quote = norm(entry.get("quote", ""))
    path = Path(path_raw)
    if not path_raw:
        return "wpis bez 'path'"
    if not path.is_file():
        return f"{path_raw}: plik nie istnieje (nie można zadeklarować zmiany w pliku-widmie)"
    if len(quote) < 12:
        return f"{path_raw}: cytat za krótki ({len(quote)} < 12) — nie dowodzi lektury"
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    line_no = entry.get("line")
    if isinstance(line_no, int) and line_no > 0:
        lo = max(0, line_no - 1 - area)
        hi = min(len(lines), line_no + area)
        window = norm(" ".join(lines[lo:hi]))
        if quote in window:
            return None
        # fallback: cytat może być wielolinijkowy i spaść poza okno
    whole = norm(" ".join(lines))
    if quote in whole:
        return None
    return f"{path_raw}:{line_no if line_no else '?'}: CYTAT NIE WYSTĘPUJE w pliku — to znaczy, że plik nie został przeczytany"


def _repo_source_files(limit: int = 20000) -> list[str]:
    """
    Pliki źródłowe = śledzone + nieśledzone (preflight działa przed commitem,
    więc `git grep` po samym indeksie gubiłby nowe pliki).
    """
    try:
        tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True, timeout=30).stdout.split()
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True, timeout=30
        ).stdout.split()
    except Exception:
        return []
    seen, out = set(), []
    for f in tracked + untracked:
        if f in seen or not f.endswith(SCAN_EXT):
            continue
        seen.add(f)
        out.append(f)
        if len(out) >= limit:
            break
    return out


def existing_definition(name: str, exclude: list[str]) -> str | None:
    """F7: szuka istniejącej definicji o tej samej nazwie (normalizowanej) w repo."""
    key = re.sub(r"[^a-z0-9]", "", name.lower())
    token_re = re.compile(rf"\b{re.escape(name)}\b")
    exclude_norm = [e.rstrip("*") for e in exclude if e]
    for f in _repo_source_files():
        if any(f.startswith(e) for e in exclude_norm):
            continue
        try:
            txt = Path(f).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not token_re.search(txt):
            continue
        for regex in (DEF_RE, SHELL_DEF_RE):
            for m in regex.finditer(txt):
                if re.sub(r"[^a-z0-9]", "", m.group(1).lower()) == key:
                    return f
    return None


def check_document(doc: dict, report: Report) -> None:
    intent = doc.get("intent") or {}
    files = doc.get("files_touched") or []
    plan = doc.get("plan") or []
    budget = doc.get("budget") or {}
    kind = str(doc.get("kind", "")).strip().lower()
    subtract = doc.get("subtract") or []
    greenfield = norm(doc.get("greenfield_justification", ""))
    reuse = doc.get("reuse") or []

    # F1: intencja falsyfikowalna + non-goals
    if len(norm(intent.get("falsifiable", ""))) < 20:
        report.block("F1", "intent.falsifiable < 20 znaków — nie da się sprawdzić, czy zadanie jest zrobione")
    if not (intent.get("non_goals") or []):
        report.block("F1", "intent.non_goals puste — brak granic zakresu (prawo do rozrastania się)")

    # F2: zanurkowanie w pliki
    if not files:
        report.block("F2", "files_touched puste — deklarujesz zmianę bez przeczytania czegokolwiek")
    for entry in files:
        problem = verify_quote(entry)
        if problem:
            report.block("F2", problem)
        if not norm(entry.get("why", "")):
            report.advisory.append(("F2", f"{entry.get('path')}: brak 'why' (po co dotykamy tego pliku)"))

    # F3: bugfix musi mieć reprodukcję
    if kind == "bug":
        repro = doc.get("repro") or {}
        if not norm(repro.get("cmd", "")):
            report.block("F3", "kind=bug bez repro.cmd — debugowanie na wyczucie przepala tokeny")
        if len(norm(repro.get("observed_failure", ""))) < 10:
            report.block("F3", "kind=bug bez repro.observed_failure — brak dowodu, że awaria istnieje")

    # F4: najpierw Subtract
    if not subtract and len(greenfield) < 40:
        report.block("F4", "brak sekcji 'subtract' i brak greenfield_justification >= 40 znaków")
    for item in subtract:
        action = norm(item.get("action", "remove")).lower()
        if action == "none-greenfield":
            continue
        if not item.get("path"):
            report.block("F4", "subtract bez 'path'")
        elif not Path(item["path"]).exists():
            report.block("F4", f"subtract wskazuje nieistniejący plik: {item['path']}")
        if not norm(item.get("what", "")):
            report.block("F4", f"subtract dla {item.get('path')}: brak 'what' (co konkretnie usuwamy)")

    # F5: kolejność planu
    if not plan:
        report.block("F5", "plan pusty")
    else:
        first = norm(plan[0]).lower()
        allowed = ("subtract", "diagnose", "repro")
        if not first.startswith(allowed):
            report.block(
                "F5",
                f"plan zaczyna się od '{plan[0]}' — musi zaczynać się od sprzątania/diagnozy "
                f"({', '.join(allowed)}), a nie od implementacji",
            )
        if "verify" not in [norm(p).lower() for p in plan]:
            report.advisory.append(("F5", "plan bez kroku 'verify' — jak udowodnisz, że działa?"))

    # F6: budżet (anty-frankenstein)
    max_files = int(budget.get("max_files", DEFAULT_LIMITS["max_files"]))
    max_loc = int(budget.get("max_loc", DEFAULT_LIMITS["max_loc"]))
    if max_files > DEFAULT_LIMITS["max_files"]:
        report.block("F6", f"max_files={max_files} > {DEFAULT_LIMITS['max_files']} — rozbij zadanie")
    if max_loc > DEFAULT_LIMITS["max_loc"]:
        report.block("F6", f"max_loc={max_loc} > {DEFAULT_LIMITS['max_loc']} — to już nie zmiana, to przebudowa")
    if files and max_files < len(files):
        report.block("F6", f"deklarujesz {len(files)} plików, a budżet to {max_files}")

    # F7: anty-duplikacja
    touched = [e.get("path", "") for e in files]
    for item in reuse:
        name = norm(item.get("new", ""))
        if len(name) < 3:
            # krótka nazwa (np. stała 'x') jest legalna — nie da się dla niej sprawdzić duplikacji
            report.warn("F7", f"nazwa '{name}' zbyt krótka, by sprawdzić duplikację — sprawdź ręcznie")
            continue
        justification = norm(item.get("justification", ""))
        if item.get("reuse_of"):
            target = norm(item["reuse_of"])
            if not existing_definition(target, touched):
                report.block("F7", f"reuse_of '{target}' nie istnieje w repo — nie można 'użyć' czegoś, czego nie ma")
            continue
        dup = existing_definition(name, touched)
        if dup and len(justification) < 20:
            report.block(
                "F7",
                f"'{name}' już istnieje w {dup} — to jest duplikacja. Użyj reuse_of albo uzasadnij (>= 20 znaków)",
            )


def main() -> int:
    ap = argparse.ArgumentParser(description="Preflight Gate: pomyśl i posprzątaj przed kodem.")
    ap.add_argument("--file", required=False, help="docs/preflight/<TICKET>.json")
    ap.add_argument("--ticket", help="ID biletu (skrót: szuka docs/preflight/<TICKET>.json)")
    args = ap.parse_args()

    path = Path(args.file) if args.file else (Path("docs/preflight") / f"{args.ticket}.json" if args.ticket else None)
    if path is None:
        return fail("podaj --file albo --ticket (fail-closed: bramka nie zgaduje)")
    if not path.is_file():
        return fail(f"brak artefaktu preflight: {path} — najpierw zanurkuj w pliki, potem kod")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return fail(f"niepoprawny JSON w {path}: {exc}")
    if not isinstance(doc, dict):
        return fail(f"{path}: artefakt musi być obiektem JSON")
    missing = [k for k in REQUIRED if k not in doc]
    if missing:
        return fail(f"{path}: brak kluczy: {', '.join(missing)} (fail-closed)")

    print(f"{BLUE}🔍 Preflight Gate — {doc.get('ticket')} ({doc.get('kind')}){NC}")
    report = Report()
    check_document(doc, report)
    report.render()

    if report.blocking:
        print(f"{RED}❌ PREFLIGHT FAILED: {len(report.blocking)} blokad. Nie pisz jeszcze kodu.{NC}")
        return 1
    print(f"{GREEN}✅ PREFLIGHT PASSED: pliki przeczytane, plan od sprzątania, budżet w normie.{NC}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
