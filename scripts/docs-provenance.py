#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docs-provenance.py — Inception Gate.

Poprawki po audycie:
  * P0-2: parsuje UDOKUMENTOWANY format tabeli ACTIVE.md (| ID | Tytuł | Status | ...),
          a nie tylko wymyślony (| ID | STATUS |)
  * P1-1: akceptuje numerowane nagłówki (## 2. Decyzje z wywiadu ...), czyli własny szablon repo
  * WIP=1: egzekwuje maksymalnie jedno zadanie IN_PROGRESS (Reguła 7.11 / 2.9)
  * Fail-closed: brak ACTIVE.md przy oczekiwanym STANDARD_TRACK => błąd, nie ciche PASS

Zasada: bramka nie ocenia PRAWDY wywiadu (to robi człowiek), ocenia jego OBECNOŚĆ i strukturę.
"""
import argparse
import re
import sys
from pathlib import Path

TASKS_DIR = Path("docs/tasks")
ACTIVE = TASKS_DIR / "ACTIVE.md"

# nagłówek: "## Decyzje ..." albo "## 2. Decyzje ..." albo "### ..." (tolerancyjnie)
SECTION_RE = re.compile(
    r"^#{2,4}\s*(?:\d+[.)]\s*)?Decyzje z wywiadu\s*\(/grill-me\)(.*?)(?=^#{2,4}\s|\Z)",
    re.S | re.M | re.I,
)

PILLARS = {
    "źródło danych": r"props|sesj|endpoint|źródł|pochodz|RLS|Qdrant|DB\b|tabel|API",
    "obsługa błędu": r"błąd|403|404|brak danych|fail|toast|redirect|skeleton|BRAK_DANYCH",
    "Must NOT": r"Must NOT|nie ruszamy|granice|zakaz|Nie robimy|poza zakresem",
}
FILE_REF_RE = re.compile(r"[\w./-]+\.\w+:\d+|/\w[\w/-]*")
MIN_CHARS = 50


def find_active_tasks(text: str) -> list[str]:
    """
    Znajduje wiersze tabeli z IN_PROGRESS w DWÓCH formatach:
      | CP-007 | Endpoint /health | IN_PROGRESS | STANDARD_TRACK | @x |   <- udokumentowany
      | CP-007 | IN_PROGRESS |                                          <- skrócony
    """
    ids: list[str] = []
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells:
            continue
        m = re.fullmatch(r"(CP-\d+)", cells[0])
        if not m:
            continue
        if any(re.fullmatch(r"IN_PROGRESS", c, re.I) for c in cells[1:]):
            ids.append(m.group(1))
    return ids


def check_cp_file(path: Path) -> tuple[bool, str, list[str]]:
    """Zwraca (ok, komunikat, ostrzeżenia)."""
    if not path.exists():
        return False, "brak pliku CP (fail-closed)", []
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = SECTION_RE.search(text)
    if not match:
        return (
            False,
            "brak sekcji 'Decyzje z wywiadu (/grill-me)' — nagłówek musi brzmieć "
            "'## Decyzje z wywiadu (/grill-me)' (numeracja '## 2.' jest dozwolona)",
            [],
        )
    content = match.group(1).strip()
    if len(content) < MIN_CHARS:
        return False, f"sekcja za krótka: {len(content)} < {MIN_CHARS} znaków", []

    missing = [name for name, rx in PILLARS.items() if not re.search(rx, content, re.I)]
    if missing:
        return False, f"brak filarów: {', '.join(missing)}", []

    warnings = []
    if not FILE_REF_RE.search(content):
        warnings.append(
            "wywiad bez odniesienia do pliku/endpointu — słowa-klucze bez konkretu "
            "(ryzyko cargo cult, KNOWN_LIMITATIONS #1)"
        )
    return True, f"OK ({len(content)} znaków, 3 filary)", warnings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="sprawdź ACTIVE.md vs CP-*.md")
    ap.add_argument("--file", help="sprawdź konkretny plik CP")
    ap.add_argument("--test-red", action="store_true", help="dowód RED: celowo sprawdź plik bez wywiadu")
    ap.add_argument("--allow-multi-wip", action="store_true", help="wyłącz egzekwowanie WIP=1 (niezalecane)")
    args = ap.parse_args()

    if args.file:
        ok, msg, warns = check_cp_file(Path(args.file))
        print(f"{'PASS' if ok else 'FAIL'}: {args.file} -> {msg}")
        for w in warns:
            print(f"WARN: {w}")
        return 0 if ok else 1

    if args.test_red:
        tmp = Path("/tmp/CP-TEST-RED.md")
        tmp.write_text("# CP-TEST\n## Cel\nBrak wywiadu\n", encoding="utf-8")
        ok, msg, _ = check_cp_file(tmp)
        print(f"TEST RED: {tmp.name} -> {'PASS' if ok else 'FAIL'} ({msg})")
        if not ok:
            print("✅ TEST RED UDANY: bramka poprawnie zablokowała brak wywiadu")
            return 0
        print("❌ TEST RED FAIL: bramka przepuściła pusty CP")
        return 1

    if not ACTIVE.exists():
        print(f"FAIL: brak {ACTIVE} — nie mogę potwierdzić braku zadań (fail-closed)")
        return 1

    text = ACTIVE.read_text(encoding="utf-8", errors="ignore")
    in_progress = find_active_tasks(text)
    if not in_progress:
        print("Brak zadań IN_PROGRESS w ACTIVE.md — PASS")
        return 0

    failed: list[str] = []
    checked = 0
    for cp_id in in_progress:
        candidates = sorted(TASKS_DIR.glob(f"{cp_id}*.md"))
        if not candidates:
            failed.append(f"{cp_id}: brak pliku {TASKS_DIR}/{cp_id}*.md")
            continue
        for cand in candidates:
            ok, msg, warns = check_cp_file(cand)
            checked += 1
            print(f"{'PASS' if ok else 'FAIL'}: {cand.name} -> {msg}")
            for w in warns:
                print(f"  WARN: {w}")
            if not ok:
                failed.append(f"{cand.name}: {msg}")

    if len(in_progress) > 1 and not args.allow_multi_wip:
        print(f"\n🚩 WIP=1 NARUSZONE: {len(in_progress)} zadań IN_PROGRESS ({', '.join(in_progress)})")
        print("   Reguła 7.11 / 2.9: maksymalnie jedno zadanie STANDARD_TRACK w toku.")
        failed.append("WIP>1")

    if failed:
        print(f"\n🚩 INCEPTION GATE FAILED: {len(failed)} problemów")
        for f in failed:
            print(f" - {f}")
        return 1

    print(f"\n✅ INCEPTION GATE PASSED: {checked} plik(ów) z wywiadem, WIP={len(in_progress)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
