#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hhh-run.py — orkiestrator krok po kroku: wywołuje wszystkie bramki w kolejności
i ZATRZYMUJE się na każdym punkcie decyzyjnym, dopóki człowiek nie podpisze decyzji.

Kody wyjścia (celowo różne, żeby pętla agenta wiedziała CO zrobić):
  0  wszystko zrobione
  1  bramka nie przeszła — agent ma coś naprawić (nie pytać człowieka)
  3  STOP: potrzebna decyzja człowieka (grill) — agent NIE może iść dalej
  4  STOP: brak postępu (breaker) — ten sam stan 2x, eskaluj do człowieka
  2  błąd użycia/środowiska

Użycie:
  python3 scripts/hhh-run.py --ticket CP-150 --status
  python3 scripts/hhh-run.py --ticket CP-150 --next
  python3 scripts/hhh-run.py --ticket CP-150 --run
  python3 scripts/hhh-run.py --ticket CP-150 --run --base origin/main --tests "nx affected -t test"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RED = "\033[0;31m"; GREEN = "\033[0;32m"; YELLOW = "\033[1;33m"; BLUE = "\033[0;34m"; NC = "\033[0m"

STATE_DIR = Path(".agent/state")
LEDGER = STATE_DIR / "ledger.jsonl"

EXIT_OK, EXIT_GATE, EXIT_ENV, EXIT_DECISION, EXIT_STALL = 0, 1, 2, 3, 4


def read_profile() -> str:
    """hilux (domyślnie) = minimalna uprząż; full = wszystkie bramki."""
    p = Path("hhh.profile")
    if not p.is_file():
        return "hilux"
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("profile="):
            val = line.split("=", 1)[1].strip().lower()
            if val in ("hilux", "full"):
                return val
            print(f"{YELLOW}⚠️  nieznany profil '{val}' w hhh.profile — używam hilux{NC}", file=sys.stderr)
    return "hilux"


def step_specs(ticket: str, base: str, tests: str | None, profile: str = "hilux") -> list[dict]:
    """Kolejność kroków. 'decision' = punkt, w którym agent MUSI się zatrzymać.
    W profilu hilux pomijamy: decyzję 'approach' (zwykle wynika z 'scope') i krok 'close'
    (integralność i tak leci w pre-commit). Zostają 2 decyzje i 3 bramki w pętli."""
    return [
        {"id": "intake", "kind": "gate", "desc": "rejestr zadań + wywiad (Inception)",
         "cmd": ["python3", "scripts/docs-provenance.py", "--check"]},
        {"id": "scope", "kind": "decision", "desc": "GRILL #1: zakres, Must NOT, definicja ukończenia",
         "cmd": ["python3", "scripts/decision-gate.py", "--verify", "--ticket", ticket, "--step", "scope"]},
        {"id": "preflight", "kind": "gate", "desc": "dive/subtract/duplikacja/budżet (7.19)",
         "cmd": ["python3", "scripts/preflight-gate.py", "--ticket", ticket]},
        {"id": "approach", "kind": "decision", "desc": "GRILL #2: wybór podejścia i cena alternatyw",
         "cmd": ["python3", "scripts/decision-gate.py", "--verify", "--ticket", ticket, "--step", "approach"],
         "profiles": ("full",)},
        {"id": "implement", "kind": "change", "desc": "kod: musi istnieć realna zmiana względem bazy",
         "cmd": None},
        {"id": "verify", "kind": "gate", "desc": "skan grzechów na liniach dodawanych + testy",
         "cmd": ["bash", "scripts/adversarial-review.sh", base],
         "tests": tests},
        {"id": "evidence", "kind": "gate", "desc": "dowody wykonane (--execute, E1-E10)",
         "cmd": ["python3", "scripts/epistemic-gate.py", "--ticket", ticket, "--execute"]},
        {"id": "accept", "kind": "decision", "desc": "GRILL #3: akceptacja dowodów (podpis człowieka)",
         "cmd": ["python3", "scripts/decision-gate.py", "--verify", "--ticket", ticket, "--step", "accept"]},
        {"id": "close", "kind": "gate", "desc": "integralność bramek po zmianie",
         "cmd": ["bash", "scripts/gate-lock.sh", "--check"], "profiles": ("full",)},
    ]


def resolve_base(preferred: str) -> str:
    """
    Baza musi być PRZODKIEM HEAD i istnieć. Kolejność: preferowana, main, master, HEAD~1, HEAD.
    Bez tego 'origin/main' w świeżym sandboksie dawał fałszywe "zmiana istnieje".
    """
    candidates = [preferred, "origin/main", "main", "master", "HEAD~1"]
    for ref in candidates:
        code, _ = run(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"])
        if code != 0:
            continue
        code, _ = run(["git", "merge-base", "--is-ancestor", ref, "HEAD"])
        if code == 0 and ref != "HEAD":
            return ref
    return "HEAD"


def state_path(ticket: str) -> Path:
    return STATE_DIR / f"{ticket}.json"


def load_state(ticket: str) -> dict:
    p = state_path(ticket)
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            # Fail-closed: uszkodzony stan NIE jest cicho zerowany (to byłby silent fallback).
            print(f"{RED}✖ Uszkodzony plik stanu: {p} ({exc}){NC}", file=sys.stderr)
            print(f"   Usuń go świadomie: rm {p}  (albo --reset), potem uruchom ponownie.", file=sys.stderr)
            sys.exit(EXIT_ENV)
    return {"ticket": ticket, "completed": [], "stalls": 0, "last_sig": "", "history": []}


def save_state(ticket: str, state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_path(ticket).write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(cmd: list[str], timeout: int = 900) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except FileNotFoundError:
        return EXIT_ENV, f"nie znaleziono komendy: {' '.join(cmd)}"
    except subprocess.TimeoutExpired:
        return EXIT_ENV, f"TIMEOUT: {' '.join(cmd)}"


def diff_signature(base: str, tests: str | None) -> str:
    """Sygnatura stanu: diff + (opcjonalnie) lista niepowodzeń testów. Do detektora braku postępu."""
    parts: list[str] = []
    paths = ["--", "apps", "packages", "src", "scripts", "services", "libs"]
    code, out = run(["git", "diff", "--stat", f"{base}...HEAD"] + paths)
    parts.append(out if code == 0 else "")
    code, out = run(["git", "diff", "--stat"] + paths)
    parts.append(out if code == 0 else "")
    if tests:
        code, out = run(tests.split(), timeout=1200)
        fails = sorted({ln for ln in out.splitlines() if ln.strip().startswith(("FAIL", "✕", "ERROR"))})
        parts.extend(fails)
    blob = "\n".join(parts)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


CODE_PATHS = (":!docs/**", ":!.agent/**", ":!*.md", ":!docs", ":!tests/fixtures/**")


def has_change(base: str) -> bool:
    """Zmiana KODU (nie dokumentacji/decyzji) — decyzje same w sobie nie są implementacją."""
    paths = ["--", "apps", "packages", "src", "scripts", "services", "libs"]
    for args in (["git", "diff", "--quiet", f"{base}...HEAD"] + paths,
                 ["git", "diff", "--quiet"] + paths,
                 ["git", "diff", "--quiet", "--cached"] + paths):
        code, _ = run(args)
        if code == 1:
            return True
    # nowe, jeszcze nieśledzone pliki kodu też są zmianą
    code, out = run(["git", "ls-files", "--others", "--exclude-standard"])
    if code == 0:
        for line in out.splitlines():
            if re.match(r"^(apps|packages|src|scripts|services|libs)/.*\.(ts|tsx|js|jsx|py|go|rs|sh|vue|svelte)$", line.strip()):
                return True
    return False


def print_status(ticket: str, specs: list[dict], state: dict) -> None:
    print(f"{BLUE}═══ HHH {ticket} ═══ (profil: {read_profile()}){NC}")
    done = set(state.get("completed", []))
    for s in specs:
        if s["id"] in done:
            mark = f"{GREEN}✅{NC}"
        elif s["kind"] == "decision":
            mark = f"{YELLOW}🛑{NC}"
        else:
            mark = "⬜"
        print(f"  {mark} {s['id']:11s} [{s['kind']:8s}] {s['desc']}")
    nxt = next((s["id"] for s in specs if s["id"] not in done), None)
    print(f"\n  następny krok: {nxt or '— (zamknięte)'}")
    if state.get("stalls"):
        print(f"  {YELLOW}stalls={state['stalls']} (2 = breaker){NC}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Orkiestrator kroków: bramki + punkty decyzyjne.")
    ap.add_argument("--ticket", required=True)
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--next", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--tests", default=None, help="komenda testów (opcjonalnie), np. 'nx affected -t test'")
    args = ap.parse_args()

    args.base = resolve_base(args.base)
    profile = read_profile()
    all_specs = step_specs(args.ticket, args.base, args.tests, profile)
    specs = [s for s in all_specs if profile in s.get("profiles", ("hilux", "full"))]
    if args.reset:
        if state_path(args.ticket).exists():
            state_path(args.ticket).unlink()
        print("🔄 stan wyczyszczony")
        return EXIT_OK

    if not Path("scripts/preflight-gate.py").is_file():
        print(f"{RED}✖ uruchom z katalogu repozytorium z uprzężą (brak scripts/preflight-gate.py){NC}")
        return EXIT_ENV

    state = load_state(args.ticket)

    if args.status or (not args.run and not args.next):
        print_status(args.ticket, specs, state)
        return EXIT_OK

    if args.next:
        nxt = next((s for s in specs if s["id"] not in set(state.get("completed", []))), None)
        if not nxt:
            print("— wszystko zamknięte")
            return EXIT_OK
        print(json.dumps(nxt, ensure_ascii=False))
        if nxt["kind"] == "decision":
            print(f"{YELLOW}🛑 To punkt decyzyjny. Agent NIE idzie dalej bez człowieka.{NC}")
            print(f"   python3 scripts/decision-gate.py --ask --ticket {args.ticket} --step {nxt['id']}")
            return EXIT_DECISION
        return EXIT_OK

    # ---- tryb --run: sekwencyjnie, stop na pierwszym problemie
    sig = diff_signature(args.base, args.tests)
    progressed = False

    for s in specs:
        if s["id"] in set(state.get("completed", [])):
            continue

        print(f"\n{BLUE}▶ {s['id']} — {s['desc']}{NC}")

        if s["kind"] == "decision":
            code, out = run(s["cmd"])
            print(out.rstrip())
            if code != 0:
                print(f"{YELLOW}🛑 STOP (exit {EXIT_DECISION}): potrzebna decyzja człowieka.{NC}")
                print(f"   python3 scripts/decision-gate.py --ask --ticket {args.ticket} --step {s['id']}")
                state["stalls"] = state.get("stalls", 0)
                save_state(args.ticket, state)
                return EXIT_DECISION
        elif s["kind"] == "change":
            if not has_change(args.base):
                print(f"{YELLOW}⏸  STOP (exit {EXIT_GATE}): brak zmiany względem {args.base}. "
                      f"To robota AGENTA (napisz kod), nie decyzja człowieka.{NC}")
                save_state(args.ticket, state)
                return EXIT_GATE
            print("   zmiana wykryta")
        else:
            code, out = run(s["cmd"])
            print(out.rstrip()[-2000:])
            if code != 0:
                print(f"{RED}❌ krok '{s['id']}' nie przeszedł (exit {code}). Napraw i uruchom ponownie.{NC}")
                state["history"].append({"at": datetime.now().isoformat(timespec="seconds"), "step": s["id"], "exit": code})
                save_state(args.ticket, state)
                return EXIT_GATE
            if s.get("tests"):
                tcode, tout = run(s["tests"].split(), timeout=1800)
                print(tout.rstrip()[-1500:])
                if tcode != 0:
                    print(f"{RED}❌ testy nie przeszły ({s['tests']}){NC}")
                    save_state(args.ticket, state)
                    return EXIT_GATE

        state.setdefault("completed", []).append(s["id"])
        state["history"].append({"at": datetime.now().isoformat(timespec="seconds"), "step": s["id"], "exit": 0})
        progressed = True
        save_state(args.ticket, state)

    # ---- breaker: brak postępu między uruchomieniami
    if not progressed:
        if sig == state.get("last_sig"):
            state["stalls"] = int(state.get("stalls", 0)) + 1
        else:
            state["stalls"] = 0
        state["last_sig"] = sig
        save_state(args.ticket, state)
        if state["stalls"] >= 2:
            print(f"{RED}🚩 BRAK POSTĘPU 2x (ta sama sygnatura {sig}) — STOP, eskaluj do człowieka.{NC}")
            save_state(args.ticket, state)
            return EXIT_STALL

    state["last_sig"] = sig
    state["stalls"] = 0
    save_state(args.ticket, state)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": datetime.now().isoformat(timespec="seconds"), "ticket": args.ticket,
                             "completed": state["completed"], "sig": sig}, ensure_ascii=False) + "\n")
    print(f"\n{GREEN}✅ wszystkie kroki zamknięte dla {args.ticket}{NC}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
