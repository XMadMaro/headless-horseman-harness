#!/usr/bin/env python3
"""
docs-provenance.py — Inception Gate dla monorepo
Sprawdza czy zadania STANDARD_TRACK mają ## Decyzje z wywiadu (/grill-me) >= 50 znaków.
FAST_TRACK (tylko docs) jest przepuszczany.
"""
import re
import sys
from pathlib import Path

TASKS_DIR = Path("docs/tasks")
ACTIVE = TASKS_DIR / "ACTIVE.md"
TEMPLATE_MARKER = "## Decyzje z wywiadu (/grill-me)"

FAST_TRACK_PATTERNS = [".md", ".env.example", ".github/"]
STANDARD_GLOBS = ["apps/", "packages/", "src/"]

def is_fast_track_only(diff_files: list[str]) -> bool:
    if not diff_files:
        return True
    for f in diff_files:
        is_standard = any(f.startswith(g) for g in STANDARD_GLOBS)
        if is_standard:
            return False
    return True

def check_cp_file(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return True, "brak pliku"
    text = path.read_text(encoding="utf-8", errors="ignore")
    # znajdź sekcję
    m = re.search(r"## Decyzje z wywiadu \(/grill-me\)(.*?)(?=\n## |\n---|\Z)", text, re.S | re.I)
    if not m:
        if TEMPLATE_MARKER.lower() in text.lower():
            # marker istnieje ale regex nie złapał — policz znaki po markerze
            idx = text.lower().index(TEMPLATE_MARKER.lower()) + len(TEMPLATE_MARKER)
            tail = text[idx:idx+2000]
            if len(tail.strip()) >= 50:
                return True, f"OK ({len(tail.strip())} znaków)"
            return False, f"sekcja <50 znaków ({len(tail.strip())})"
        return False, "brak sekcji 'Decyzje z wywiadu (/grill-me)'"
    content = m.group(1).strip()
    if len(content) < 50:
        return False, f"sekcja za krótka: {len(content)} < 50 znaków"
    # sprawdź 3 filary
    has_source = bool(re.search(r"props|sesja|endpoint|źródł|pochodz|RLS|Qdrant|DB", content, re.I))
    has_error = bool(re.search(r"błąd|403|404|brak danych|fail|obsług|toast|redirect", content, re.I))
    has_must_not = bool(re.search(r"Must NOT|nie ruszamy|granice|zakaz|Nie robimy", content, re.I))
    missing = []
    if not has_source: missing.append("źródło danych")
    if not has_error: missing.append("obsługa błędu")
    if not has_must_not: missing.append("Must NOT")
    if missing:
        return False, f"brak filarów: {', '.join(missing)}"
    return True, f"OK ({len(content)} znaków, 3 filary)"

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="sprawdź ACTIVE.md vs CP-*.md")
    ap.add_argument("--file", type=str, help="sprawdź konkretny plik CP")
    ap.add_argument("--test-red", action="store_true", help="test RED: celowo sprawdź plik bez sekcji")
    args = ap.parse_args()

    if args.file:
        ok, msg = check_cp_file(Path(args.file))
        print(f"{'PASS' if ok else 'FAIL'}: {args.file} -> {msg}")
        sys.exit(0 if ok else 1)

    if args.test_red:
        # tworzy tymczasowy plik bez sekcji aby udowodnić że bramka blokuje
        tmp = Path("/tmp/CP-TEST-RED.md")
        tmp.write_text("# CP-TEST\n## Cel\nBrak wywiadu\n")
        ok, msg = check_cp_file(tmp)
        print(f"TEST RED: {tmp} -> {'PASS' if ok else 'FAIL'} ({msg})")
        # oczekujemy FAIL
        if not ok:
            print("✅ TEST RED UDANY: bramka poprawnie zablokowała brak wywiadu")
            sys.exit(0)
        else:
            print("❌ TEST RED FAIL: bramka przepuściła pusty CP")
            sys.exit(1)

    # domyślnie: sprawdź ACTIVE.md
    if not ACTIVE.exists():
        print("Brak docs/tasks/ACTIVE.md — pomijam (FAST_TRACK?)")
        sys.exit(0)

    text = ACTIVE.read_text(encoding="utf-8", errors="ignore")
    # szukaj wierszy | CP-xxx | IN_PROGRESS |
    in_progress = re.findall(r"\|\s*(CP-\d+)\s*\|\s*IN_PROGRESS", text, re.I)
    if not in_progress:
        print("Brak zadań IN_PROGRESS w ACTIVE.md — PASS")
        sys.exit(0)

    failed = []
    for cp_id in in_progress:
        candidates = list(TASKS_DIR.glob(f"{cp_id}*.md"))
        if not candidates:
            failed.append(f"{cp_id}: brak pliku docs/tasks/{cp_id}*.md")
            continue
        for cand in candidates:
            ok, msg = check_cp_file(cand)
            status = "PASS" if ok else "FAIL"
            print(f"{status}: {cand.name} -> {msg}")
            if not ok:
                failed.append(f"{cand.name}: {msg}")

    if failed:
        print(f"\n🚩 INCEPTION GATE FAILED: {len(failed)} zadań bez wywiadu")
        for f in failed:
            print(f" - {f}")
        sys.exit(1)
    else:
        print(f"\n✅ INCEPTION GATE PASSED: {len(in_progress)} zadań z wywiadem")
        sys.exit(0)

if __name__ == "__main__":
    main()
