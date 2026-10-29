#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
decision-gate.py — punkt decyzyjny: agent MUSI się zatrzymać i zostać zgrillowany.

Model: agent nie potrafi zgrillować sam siebie (self-critique = teatr).
Więc wymuszamy ARTEFAKT DECYZJI podpisany przez człowieka, zanim krok ruszy dalej.

Reguły (blokujące):
  D1 kompletność pól
  D2 >= 2 opcje (jedna opcja to nie decyzja)
  D3 'chosen' istnieje w opcjach
  D4 uzasadnienie >= 20 znaków
  D5 'must_not' niepuste (granice zakresu)
  D6 'done_when' obserwowalne (>= 10 znaków, nie "działa")
  D7 ZAKAZ SAMO-AKCEPTACJI (confirmed_by != asked_by i nie jest tożsamością agenta)
  D8 fraza potwierdzenia dokładnie: "Potwierdzam: RRRR-MM-DD, CP-xxx, krok=WYBÓR"
  D9 niewygasła
  D10 decyzja nieodwracalna wymaga acknowledged_irreversible + blast_radius

Tryby:
  --verify --ticket CP-x --step scope    (CI/hook; fail-closed)
  --ask    --ticket CP-x --step scope    (interaktywnie: pyta człowieka i zapisuje)
  --list   --ticket CP-x                 (jakie decyzje są wymagane/obecne)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

RED = "\033[0;31m"; GREEN = "\033[0;32m"; YELLOW = "\033[1;33m"; BLUE = "\033[0;34m"; NC = "\033[0m"

DECISIONS_DIR = Path("docs/decisions")
STEPS = ("scope", "approach", "accept")
REQUIRED = ("ticket", "step", "question", "options", "chosen", "why", "must_not", "done_when",
            "asked_by", "asked_at", "confirmed_by", "confirmed_at", "confirmation")
# tożsamości, którym nie wolno "potwierdzać" decyzji człowieka
DEFAULT_AGENT_IDS = "agent,assistant,claude,gpt,codex,cursor,antigravity,copilot,gemini,ci-bot,github-actions,harness"
VAGUE = {"ok", "dziala", "działa", "gotowe", "done", "testy", "przechodzi", "fine"}


def agent_ids() -> set[str]:
    raw = os.environ.get("HHH_AGENT_IDENTITIES", DEFAULT_AGENT_IDS)
    return {x.strip().lower() for x in raw.split(",") if x.strip()}


def norm(x) -> str:
    return re.sub(r"\s+", " ", str(x)).strip()


def decision_path(ticket: str, step: str) -> Path:
    return DECISIONS_DIR / ticket / f"{step}.json"


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
        print("─" * 80)
        print(f"| {'Poziom':8s} | {'Reguła':6s} | Opis")
        print("─" * 80)
        if not self.blocking and not self.advisory:
            print(f"| {'PASS':8s} | {'-':6s} | Decyzja kompletna, podpisana przez człowieka.")
        for rule, msg in self.advisory:
            print(f"| {YELLOW}{'WARN':8s}{NC} | {rule:6s} | {msg}")
        for rule, msg in self.blocking:
            print(f"| {RED}{'BLOCKING':8s}{NC} | {rule:6s} | {msg}")
        print("─" * 80)
        print(f"Podsumowanie: BLOCKING={len(self.blocking)}, ADVISORY={len(self.advisory)}")


def validate(doc: dict, ticket: str, step: str) -> Report:
    r = Report()

    missing = [k for k in REQUIRED if k not in doc]
    if missing:
        r.block("D1", f"brak pól: {', '.join(missing)}")
        return r

    if norm(doc["ticket"]) != ticket:
        r.block("D1", f"decyzja dotyczy biletu '{doc['ticket']}', a sprawdzamy '{ticket}'")
    if norm(doc["step"]) != step:
        r.block("D1", f"decyzja dotyczy kroku '{doc['step']}', a sprawdzamy '{step}'")

    options = doc.get("options") or []
    ids = [norm(o.get("id", "")) for o in options if isinstance(o, dict)]
    if len(options) < 2:
        r.block("D2", f"tylko {len(options)} opcja — decyzja bez alternatywy to nie decyzja")
    if len(set(ids)) != len(ids) or any(not i for i in ids):
        r.block("D2", "opcje muszą mieć unikalne, niepuste 'id'")
    for o in options:
        if isinstance(o, dict) and not norm(o.get("label", "")):
            r.block("D2", f"opcja {o.get('id')} bez 'label'")
        if isinstance(o, dict) and not norm(o.get("cost", "")) and not norm(o.get("risk", "")):
            r.warn("D2", f"opcja {o.get('id')} bez 'cost'/'risk' — nie widać ceny wyboru")

    chosen = norm(doc.get("chosen", ""))
    if chosen not in ids:
        r.block("D3", f"chosen='{chosen}' spoza opcji {ids}")

    if len(norm(doc.get("why", ""))) < 20:
        r.block("D4", "uzasadnienie < 20 znaków — to nie uzasadnienie")

    must_not = doc.get("must_not") or []
    if not must_not:
        r.block("D5", "must_not puste — brak granic, krok może się rozrosnąć")
    for m in must_not:
        if len(norm(m)) < 5:
            r.block("D5", f"must_not '{m}' zbyt ogólne")

    done_when = norm(doc.get("done_when", ""))
    if len(done_when) < 10 or done_when.lower() in VAGUE:
        r.block("D6", f"done_when='{done_when}' nie jest obserwowalne (podaj komendę lub warunek)")

    asked_by = norm(doc.get("asked_by", "")).lower()
    confirmed_by = norm(doc.get("confirmed_by", "")).lower()
    if not confirmed_by:
        r.block("D7", "brak confirmed_by — decyzja niepodpisana")
    elif confirmed_by == asked_by:
        r.block("D7", f"samo-akceptacja: confirmed_by == asked_by ('{confirmed_by}') — agent nie może zatwierdzić własnej decyzji")
    elif confirmed_by in agent_ids():
        r.block("D7", f"confirmed_by='{confirmed_by}' to tożsamość agenta ({'/'.join(sorted(agent_ids()))[:60]}...) — potrzebny człowiek")

    expect = f"Potwierdzam: {date.today().isoformat()}, {ticket}, {step}={chosen}"
    got = norm(doc.get("confirmation", ""))
    pattern = rf"^Potwierdzam:\s*(?P<d>\d{{4}}-\d{{2}}-\d{{2}}),\s*{re.escape(ticket)},\s*{re.escape(step)}={re.escape(chosen)}$"
    m = re.match(pattern, got)
    if not m:
        r.block("D8", f"fraza potwierdzenia niezgodna. Wpisz dokładnie: '{expect}'")
    else:
        try:
            if date.fromisoformat(m.group("d")) > date.today():
                r.block("D8", f"potwierdzenie datowane w przyszłości ({m.group('d')}) — to nie jest podpis")
        except ValueError:
            r.block("D8", f"data w potwierdzeniu niepoprawna: {m.group('d')}")

    expires = norm(doc.get("expires_at", ""))
    if expires:
        try:
            if date.fromisoformat(expires) < date.today():
                r.block("D9", f"decyzja wygasła {expires} — wymagane potwierdzenie na nowo")
        except ValueError:
            r.block("D9", f"expires_at='{expires}' nie jest datą ISO")
    else:
        r.warn("D9", "brak expires_at — decyzja bezterminowa (ryzyko: zamrożone założenie)")

    if doc.get("reversible") is False:
        if not doc.get("acknowledged_irreversible"):
            r.block("D10", "reversible=false bez acknowledged_irreversible — nieodwracalna decyzja wymaga jawnej zgody")
        if not (doc.get("blast_radius") or []):
            r.block("D10", "reversible=false bez blast_radius — nie wiadomo, czego nie da się cofnąć")

    return r


def cmd_verify(ticket: str, step: str) -> int:
    path = decision_path(ticket, step)
    print(f"{BLUE}🛑 Decision Gate — {ticket} / {step}{NC}")
    if not path.is_file():
        print(f"{RED}✖ BRAK DECYZJI: {path}{NC}")
        print("   Agent NIE może iść dalej. Najpierw zgrilluj człowieka:")
        print(f"   python3 scripts/decision-gate.py --ask --ticket {ticket} --step {step}")
        return 1
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"{RED}✖ niepoprawny JSON w {path}: {exc}{NC}")
        return 1
    report = validate(doc, ticket, step)
    report.render()
    if report.blocking:
        print(f"{RED}❌ DECISION GATE FAILED: {len(report.blocking)} blokad. Krok '{step}' nie może wystartować.{NC}")
        return 1
    print(f"{GREEN}✅ DECISION GATE PASSED: decyzja '{step}' podpisana ({doc.get('confirmed_by')}), wybór={doc.get('chosen')}{NC}")
    return 0


QUESTIONS = {
    "scope": [
        ("Co dokładnie dowozimy (definicja ukończenia)?", "done_when"),
        ("Czego NIE robimy w tym kroku? (Must NOT, minimum 1)", "must_not"),
    ],
    "approach": [
        ("Który wariant wybieramy?", "chosen"),
        ("Dlaczego właśnie ten? (min. 20 znaków)", "why"),
    ],
    "accept": [
        ("Czy dowody wystarczają, by uznać krok? (tak/nie)", "chosen"),
    ],
}

DEFAULT_OPTIONS = {
    "scope": [{"id": "A", "label": "zakres wąski: tylko to, co w bilecie", "cost": "mały"},
              {"id": "B", "label": "zakres szeroki: przy okazji refactor", "cost": "duży, ryzyko rozrostu"}],
    "approach": [{"id": "A", "label": "zmiana w istniejącym module (reuse)", "cost": "niski"},
                 {"id": "B", "label": "nowy moduł (greenfield)", "cost": "wyższy, ryzyko duplikacji"}],
    "accept": [{"id": "A", "label": "akceptuję dowody", "cost": "-"},
               {"id": "B", "label": "odrzucam: brakuje dowodu (podaj czego)", "cost": "kolejna iteracja"}],
}


def cmd_ask(ticket: str, step: str) -> int:
    if not sys.stdin.isatty():
        print(f"{RED}✖ --ask wymaga interaktywnego terminala (stdin nie jest TTY).{NC}")
        print("   To celowe: decyzję podejmuje człowiek, nie proces w tle.")
        return 1

    human = os.environ.get("HHH_HUMAN", "")
    if not human:
        print(f"{YELLOW}Kim jesteś (podpis pod decyzją)?{NC} ", end="", flush=True)
        human = norm(sys.stdin.readline())
    if not human or human.lower() in agent_ids():
        print(f"{RED}✖ '{human}' jest tożsamością agenta albo puste — decyzji nie może podpisać agent.{NC}")
        return 1

    options = DEFAULT_OPTIONS[step]
    print(f"\n{BLUE}🛑 GRILL: {ticket} / krok '{step}'{NC}")
    print("   Odpowiedz na pytania. Nic nie ruszy dalej bez tej decyzji.\n")
    for i, o in enumerate(options, 1):
        print(f"   [{o['id']}] {o['label']}  (koszt: {o.get('cost', '?')})")

    print(f"\n   Wybór [{('/'.join(o['id'] for o in options))}]: ", end="", flush=True)
    chosen = norm(sys.stdin.readline()).upper()
    ids = [o["id"] for o in options]
    if chosen not in ids:
        print(f"{RED}✖ '{chosen}' nie jest jedną z opcji {ids}{NC}")
        return 1

    print("   Definicja ukończenia (obserwowalna, np. komenda/warunek): ", end="", flush=True)
    done_when = norm(sys.stdin.readline())
    print("   Must NOT (oddziel przecinkami; czego NIE robimy): ", end="", flush=True)
    must_not = [norm(x) for x in sys.stdin.readline().split(",") if norm(x)]
    print("   Dlaczego ten wybór (min. 20 znaków): ", end="", flush=True)
    why = norm(sys.stdin.readline())

    doc = {
        "ticket": ticket, "step": step,
        "question": QUESTIONS[step][0][0],
        "options": options, "chosen": chosen, "why": why,
        "must_not": must_not, "done_when": done_when,
        "reversible": step != "accept",
        "blast_radius": [] if step != "accept" else ["merge do main"],
        "asked_by": os.environ.get("HHH_AGENT_ID", "agent"),
        "asked_at": datetime.now().isoformat(timespec="seconds"),
        "confirmed_by": human,
        "confirmed_at": datetime.now().isoformat(timespec="seconds"),
        "confirmation": f"Potwierdzam: {date.today().isoformat()}, {ticket}, {step}={chosen}",
    }
    path = decision_path(ticket, step)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = validate(doc, ticket, step)
    report.render()
    if report.blocking:
        print(f"{RED}❌ zapisano, ale decyzja jest niepełna: {path}{NC}")
        return 1
    print(f"{GREEN}✅ zapisano decyzję: {path}{NC}")
    return 0


def cmd_list(ticket: str) -> int:
    print(f"{BLUE}Decyzje dla {ticket}:{NC}")
    for step in STEPS:
        p = decision_path(ticket, step)
        if not p.is_file():
            print(f"  ⬜ {step:9s} BRAK ({p})")
            continue
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
            rep = validate(doc, ticket, step)
            mark = "✅" if not rep.blocking else "❌"
            print(f"  {mark} {step:9s} {p}  wybór={doc.get('chosen')} przez={doc.get('confirmed_by')}")
        except Exception as exc:  # noqa: BLE001
            print(f"  ❌ {step:9s} {p} (błąd: {exc})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Punkt decyzyjny: grill i podpis człowieka przed krokiem.")
    ap.add_argument("--ticket", required=True)
    ap.add_argument("--step", choices=STEPS)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--ask", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        return cmd_list(args.ticket)
    if not args.step:
        print(f"{RED}✖ podaj --step {STEPS}{NC}")
        return 1
    if args.ask:
        return cmd_ask(args.ticket, args.step)
    return cmd_verify(args.ticket, args.step)


if __name__ == "__main__":
    sys.exit(main())
