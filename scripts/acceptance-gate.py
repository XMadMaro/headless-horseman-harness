#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""acceptance-gate.py — testy akceptacyjne poza zasięgiem agenta.

DLACZEGO TO ISTNIEJE
    ImpossibleBench (Zhong, Raghunathan, Carlini, 2025): GPT-5 "przechodziło" 54%
    zadań, których test daje się spełnić TYLKO łamiąc specyfikację. Gdy testy były
    ukryte przed agentem, odsetek spadał do ~0%. Metafora "cena twierdzenia" była
    naszą hipotezą; to jest jej najmocniejszy znany dowód i brakowało go w uprzęży.
    Szczegóły i zastrzeżenia: docs/research/AI-DEGRADATION-EVIDENCE.md (M5).

ZASADA
    Agent nie widzi testów akceptacyjnych i nie może ich zmienić.

      1. manifest (hidden/manifest.json) pinuje sha256 każdego testu,
      2. manifest i testy są w harness.lock -> każda zmiana jest widoczna w review,
      3. podmiana pliku testu = STOP (exit 3) i ZERO uruchomień: nie ufamy kodowi,
      4. uruchamiane są zweryfikowane bajty skopiowane do katalogu tymczasowego
         (brak TOCTOU, brak podmiany przez plik w repo),
      5. domyślnie nie drukujemy ani treści testu, ani jego wyjścia — tylko nazwę
         i wynik. Agent dostaje "test X nie przeszedł", nie oracle.
         Ujawnienie szczegółów jest decyzją człowieka: --verbose.

CZEGO BRAMKA *NIE* WYMAGA (zmierzone w selftest, nie założone)
    * czystego working tree — testy idą na plikach roboczych, czyli dokładnie na tym,
      co agent właśnie zmienił (także przed commitem); śmieci i niezacommitowane
      zmiany w produkcie nie mają znaczenia,
    * gita — bez katalogu .git bramka działa tak samo (tylko hashe i bash),
    * bezgrzesznego repo — dług w kodzie produktu nie blokuje bramki.
    Wymagane jest JEDNO: bajty testów (i manifestu) muszą być nietknięte.
    Uwaga na sprzężenie: jeśli zmienisz plik bramki objęty harness.lock, test
    "lock-intact" padnie do momentu `bash scripts/gate-lock.sh --update` — to nie
    brud w repo, to lock, który pilnuje własnej integralności.

KODY WYJŚCIA
    0  wszystkie testy przeszły
    1  co najmniej jeden test nie przeszedł (robota dla agenta)
    2  błąd konfiguracji (brak manifestu / zero testów) — bramka nie może być pusta
    3  STOP: pliki testów lub manifest zmienione (tamper)

UŻYCIE
    python3 scripts/acceptance-gate.py --run       # domyślne: integralność + testy
    python3 scripts/acceptance-gate.py --verify    # tylko integralność
    python3 scripts/acceptance-gate.py --list
    python3 scripts/acceptance-gate.py --verbose   # pokaż wyjście nieudanego testu
    python3 scripts/acceptance-gate.py --seal      # przelicz sha256 (potem gate-lock --update!)
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "hidden", "manifest.json")
EVENTS = os.path.join(ROOT, ".hhh", "events.jsonl")
TIMEOUT_S = 120

RED, GREEN, YELLOW, NC = "\033[0;31m", "\033[0;32m", "\033[1;33m", "\033[0m"


def die(msg: str, code: int) -> int:
    print(f"{RED}❌ {msg}{NC}")
    return code


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> tuple[dict | None, int]:
    if not os.path.isfile(MANIFEST):
        return None, die(
            f"brak {os.path.relpath(MANIFEST, ROOT)} — bramka akceptacyjna nie ma czego sprawdzać "
            "(fail-closed). Utwórz manifest albo usuń bramkę świadomie.",
            2,
        )
    try:
        with open(MANIFEST, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        return None, die(f"manifest nieczytelny: {exc}", 2)

    if not isinstance(data.get("tests"), list) or not data["tests"]:
        return None, die(
            "manifest bez testów — pusta bramka zawsze przechodzi, więc nie jest bramką",
            2,
        )
    for entry in data["tests"]:
        for key in ("name", "file", "sha256"):
            if not entry.get(key):
                return None, die(f"wpis w manifeście bez pola '{key}': {entry}", 2)
    return data, 0


def verify(data: dict) -> list[dict]:
    """Zwraca listę wpisów, których plik nie zgadza się z manifestem."""
    bad = []
    for entry in data["tests"]:
        path = os.path.join(ROOT, entry["file"])
        if not os.path.isfile(path):
            bad.append({**entry, "reason": "brak pliku"})
            continue
        got = sha256_file(path)
        if got != entry["sha256"]:
            bad.append({**entry, "reason": f"sha256 {got[:12]}… != {entry['sha256'][:12]}…"})
    return bad


def log_event(result: str, passed: int, failed: int, tampered: int, ticket: str) -> None:
    """Dziennik zdarzeń — jedyne miejsce, z którego da się policzyć precyzję bramki."""
    try:
        os.makedirs(os.path.dirname(EVENTS), exist_ok=True)
        with open(EVENTS, "a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "gate": "acceptance",
                        "ticket": ticket,
                        "result": result,
                        "pass": passed,
                        "fail": failed,
                        "tamper": tampered,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except OSError as exc:  # log jest wtórny: nie zmieniamy wyniku bramki
        print(f"{YELLOW}⚠️  nie zapisano zdarzenia w {EVENTS}: {exc}{NC}")


def run_tests(data: dict, verbose: bool) -> tuple[int, int, list[str]]:
    passed = failed = 0
    failed_names: list[str] = []
    tmpdir = tempfile.mkdtemp(prefix="hhh-acceptance-")
    try:
        for idx, entry in enumerate(data["tests"], start=1):
            src = os.path.join(ROOT, entry["file"])
            # wykonujemy zweryfikowane bajty, nie ścieżkę z repo
            dst = os.path.join(tmpdir, f"{idx:02d}-test.sh")
            shutil.copyfile(src, dst)
            os.chmod(dst, 0o700)

            env = {**os.environ, "HHH_ACCEPTANCE": "1"}
            try:
                proc = subprocess.run(
                    ["bash", dst],
                    cwd=ROOT,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_S,
                )
                code = proc.returncode
                output = (proc.stdout or "") + (proc.stderr or "")
            except subprocess.TimeoutExpired:
                code = 124
                output = f"przekroczono limit {TIMEOUT_S}s"

            if code == 0:
                passed += 1
                print(f"  {GREEN}✅{NC} {entry['name']}")
            else:
                failed += 1
                failed_names.append(entry["name"])
                print(f"  {RED}❌{NC} {entry['name']}  (exit {code})")
                # Domyślnie NIE pokazujemy wyjścia: to oracle, za który agent nie płaci.
                if verbose:
                    for line in output.strip().splitlines()[-12:]:
                        print(f"     │ {line}")
                else:
                    print("     │ (szczegóły ukryte — ujawnij człowiekowi: --verbose)")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return passed, failed, failed_names


def seal() -> int:
    with open(MANIFEST, encoding="utf-8") as fh:
        data = json.load(fh)
    for entry in data["tests"]:
        entry["sha256"] = sha256_file(os.path.join(ROOT, entry["file"]))
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"{YELLOW}⚠️  manifest przepieczętowany. To ZMIANA TESTÓW — musi przejść review.{NC}")
    print("   Następny krok: bash scripts/gate-lock.sh --update (inaczej --check padnie).")
    return 0


def main(argv: list[str]) -> int:
    verbose = "--verbose" in argv
    ticket = ""
    for i, arg in enumerate(argv):
        if arg == "--ticket" and i + 1 < len(argv):
            ticket = argv[i + 1]

    data, rc = load_manifest()
    if data is None:
        return rc

    if "--list" in argv:
        for entry in data["tests"]:
            print(f"  {entry['name']}\t{entry['file']}\t{entry.get('expects', '')}")
        return 0

    if "--seal" in argv:
        return seal()

    bad = verify(data)
    if bad:
        print(f"{RED}🛑 STOP: pliki testów akceptacyjnych nie zgadzają się z manifestem.{NC}")
        for entry in bad:
            print(f"   - {entry['name']} ({entry['file']}): {entry['reason']}")
        print("   Testy są poza zasięgiem agenta. Zmiana wymaga człowieka + --seal + gate-lock --update.")
        log_event("tamper", 0, 0, len(bad), ticket)
        return 3

    if "--verify" in argv:
        print(f"{GREEN}✅ integralność testów akceptacyjnych OK ({len(data['tests'])} testów){NC}")
        return 0

    print(f"🐎 Acceptance Gate: {len(data['tests'])} testów, których agent nie widzi")
    passed, failed, failed_names = run_tests(data, verbose)
    log_event("pass" if failed == 0 else "fail", passed, failed, 0, ticket)

    if failed:
        print(f"{RED}❌ nie przeszło: {failed}/{passed + failed}{NC} — {', '.join(failed_names)}")
        return 1
    print(f"{GREEN}✅ wszystkie {passed} testów akceptacyjnych przeszło{NC}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
