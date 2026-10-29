# 🐎 Headless Horseman Harness (HHH)

[Polski](README.md) · **English**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Self-test](https://img.shields.io/badge/selftest-46%2F46%20PASS-success)](#verify-it-yourself-60-seconds)
[![Zero LLM Gates](https://img.shields.io/badge/Gates-Deterministic%20(Zero%20LLM)-orange)](#the-8-gates)

> **An engineering harness for AI coding agents in large monorepos.**
> Deterministic gates with real exit codes, hash-pinned integrity, and human checkpoints — instead of an 18-rule prompt that agents learn to satisfy.

---

## What this is (and what it is not)

**It is** a set of small, deterministic gates that make *claiming* "done" more expensive than *proving* it. The agent cannot fake a file it never read, cannot self-approve a decision, and cannot loop forever without the harness stopping it.

**It is not** a promise that agents become smart. It does not verify architectural taste, product direction, or whether a requirement makes business sense. It also does not make your tests slow — that is what a build system (Nx, Turborepo) is for.

Honest scale, measured not declared:

| Claim | Reality |
|---|---|
| "8 gates that block a commit" | true — each has an exit code and a self-test |
| "Physically prevents agents from guessing" | **no** — it raises the cost of faking, and review still matters |
| "Makes agents think critically" | **no** — it makes lying expensive; thinking is not observable |
| "Battle-tested" | n=1, author-reported case study, numbers do not fully reconcile (see [`AUDYT-KRYTYCZNY.md`](AUDYT-KRYTYCZNY.md)) |

---

## 🛻 Two modes: Hilux (default) or Full

A harness that is too heavy gets bypassed with `--no-verify`. So the default is the cheap profile. Configured in `hhh.profile`:

| | **hilux** (default) | **full** |
|---|---|---|
| Steps in the loop | 7 | 9 |
| Human signatures per ticket | **2** (`scope`, `accept`) | 3 (+`approach`) |
| Gates executed in the loop | 3 | 6 |
| pre-commit (measured) | **~146 ms** | ~197 ms |
| Use when | 1–5 people, no RLS, you want speed | multi-tenant / regulated, long regression history |

**Maintenance rule:** a gate with > 5% false positives in a week is **removed**, not tuned. False alarms teach people to bypass *all* gates — measured, not theoretical.

---

## The 8 gates

```text
  [ Human intent ]
            │
            ▼
  1. Inception Gate .......... interview + WIP=1 (docs-provenance.py)
            │
            ▼
  2. Preflight (7.19) ........ were the files READ? quote from each one
            │                  plan starts with subtract/diagnose, no duplicates
            ▼
  🛑 3. DECISION: scope ...... human signature (decision-gate.py)
            │
            ▼
  4. Implementation (agent) .. code + test RED→GREEN
            │
            ▼
  5. Adversarial Review ...... 7 sins, added lines only, real file:line
            │
            ▼
  6. Epistemic (7.20) ........ proofs EXECUTED (--execute), not declared
            │
            ▼
  🛑 7. DECISION: accept ..... human sign-off
            │
            ▼
  8. Gate Integrity .......... harness.lock: gate tampering is detected
            │
            ▼
      [ Commit to main ]
```

| # | Gate | Tool | What it blocks |
|---|---|---|---|
| 1 | Inception | `docs-provenance.py` | `IN_PROGRESS` without a documented interview; more than one task in flight (WIP=1) |
| 2 | **Preflight** | `preflight-gate.py` | coding without a **verbatim quote from every touched file** (proof of reading), plans starting with "implement", missing Subtract section, duplicate symbols, >15 files / >400 LOC |
| 3 | **Decision** | `decision-gate.py` | moving on without a **human-signed** decision: ≥2 options with cost, `must_not` boundaries, observable `done_when`, self-approval forbidden (D7) |
| 4 | Adversarial | `adversarial-review.sh` | silent fallbacks, `!important`, fake assertions, secrets, destructive migrations, tenant leaks — **added lines only** (deleting a sin is never punished) |
| 5 | **Epistemic** | `epistemic-gate.py` | claims without `cmd`/`expected`/`observed`, `echo`-based proofs, `\|\| true` masking, `confidence: high` without an executed proof, hypotheses without a falsifier |
| 6 | Gate Integrity | `gate-lock.sh` | a gate swapped for `exit 0`, a deleted gate, 18 empty headings instead of rules |
| 7 | Orchestrator | `hhh-run.py` | running ahead: exit **3** = human decision required, **1** = agent's own work, **4** = no progress (breaker) |
| 8 | Self-test | `selftest.sh` | the harness itself: every gate must pass *and* must block what it claims to block |

---

## Quick start

```bash
# 1. Copy the harness into an existing repo (install.sh downloads nothing)
npx degit XMadMaro/headless-horseman-harness/. ./_h && cp -r ./_h/. . && rm -rf ./_h

# 2. Install git hooks (pre-commit: integrity + preflight; pre-push: scanner + decisions)
bash install.sh

# 2b. Enable CI — ready-made workflows live in docs/ci/
#     (a token without `workflows` permission cannot write .github/workflows)
cp docs/ci/gates.yml docs/ci/adversarial-review.yml .github/workflows/

# 3. Verify: every gate must pass AND block what it should
bash scripts/selftest.sh                      # expected: 46/46
bash scripts/gate-lock.sh --check             # integrity of gates
bash scripts/adversarial-review.sh origin/main
python3 scripts/docs-provenance.py --check
python3 scripts/preflight-gate.py --ticket CP-XXX
python3 scripts/epistemic-gate.py --ticket CP-XXX --execute

# 4. Drive the work step by step (stops at human decisions)
python3 scripts/hhh-run.py --ticket CP-XXX --status
python3 scripts/hhh-run.py --ticket CP-XXX --run     # 0 done · 1 agent's job · 3 STOP: human decision
python3 scripts/decision-gate.py --ask --ticket CP-XXX --step scope
```

Exit codes are the interface for an agent loop:

| Code | Meaning | What the agent does |
|---|---|---|
| `0` | done | stop |
| `1` | gate failed / no code yet | fix it yourself |
| `3` | **human decision required** | stop, ask, wait |
| `4` | no progress twice (breaker) | escalate, do not retry |

---

## The core idea: price the claim

A model does not lie because it is malicious — it lies because **declaring is cheaper than verifying**. So the harness does not ask for critical thinking (unobservable); it changes the price list:

| Shortcut | Cost before | Cost now |
|---|---|---|
| Say "done" | 0 | a gate with an exit code |
| Invent `file:line` | 0 | Preflight: the quote must exist in the file |
| Weaken a test to pass it | 0 | Epistemic E5/E6 + mutation score (advisory) |
| Change the hypothesis after the result | 0 | preregistration: prediction *and* counter-prediction before the command |
| Self-approve a decision | 0 | D7: `confirmed_by` must be a human identity |
| Loop forever | 0 | breaker on unchanged diff + failure set 2× |

More on the reasoning: [`docs/architecture/CRITICAL-THINKING-ENFORCEMENT.md`](docs/architecture/CRITICAL-THINKING-ENFORCEMENT.md).

---

## How AI codebases actually drift

Six measured signatures, each with the countermeasure that has evidence behind it. Full review with sources, sample sizes and a section on **where the evidence contradicts this repo** is in [`docs/research/AI-DEGRADATION-EVIDENCE.md`](docs/research/AI-DEGRADATION-EVIDENCE.md).

| Signature | Number | Countermeasure that works |
|---|---|---|
| Refactoring dies, copy-paste wins | moved code 24.8% → 3.8%; duplicated blocks +81% (GitClear, 211M lines) | duplication check per commit, "subtract" step |
| "Almost right" is slower than wrong | +19% time on mature repos, while devs believed −20% (METR RCT, 246 tasks) | proof must be *executed*, not described |
| Bigger batches, worse stability | +25% AI adoption → −1.5% throughput, −7.2% stability (DORA 2024); stability still negative in 2025 | batch size limits, human sign-off |
| The agent optimises the test, not the task | 54% of impossible tasks "passed" by cheating; **~0% when tests are hidden** (ImpossibleBench) | tests the agent cannot see or edit |
| Hallucinated dependencies | 19.7% of recommended packages do not exist; 43% recur every run (USENIX 2025) | allow-list, verify before install |
| Slop shifts the cost onto maintainers | ~1 in 4 incoming changes low quality; curl closed its bug bounty (confirmed <5%) | disclosure, reproduction required, price the claim |

The uncomfortable finding for *this* repo: instructions written as prose are **faithfully followed but barely change outcomes** — human-written `AGENTS.md` gave +4% success at +19% cost, LLM-written gave −3% at +20% cost (ETH Zurich, 2026); and where rules were audited, "this file + this pattern" rules held at 100% while global properties held at 69%. That is the argument for mechanising rules instead of writing more of them.

---

## Verify it yourself (60 seconds)

```bash
bash scripts/selftest.sh          # 46 assertions: every gate passes and blocks
```

The self-test includes deliberate sabotage: a scanner replaced with `exit 0`, a deleted gate, 18 placeholder rules, a self-approved decision, a proof written with `echo`, a lying artifact that is internally consistent (it passes static mode and fails under `--execute` — that limitation is a test case, not a bug).

---

## Audit and known limitations

This repo was audited against six critical-thinking standards before the current state existed. The audit found the enforcement layer did not do what the documentation claimed: a scanner that returned exit 1 on PASS, an Inception Gate blind to its own documented format, and integrity checks that counted headings. All of it is documented, with reproduction commands, in:

- [`AUDYT-KRYTYCZNY.md`](AUDYT-KRYTYCZNY.md) — the audit (Polish)
- [`docs/architecture/GATE-FIXES.md`](docs/architecture/GATE-FIXES.md) — what was fixed, what is proven, what remains open (Polish)
- [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) — what the harness will never do

**What is still open:** all 46 assertions are synthetic (my fixtures, my repo). They prove the gates behave as specified — not that they help in a real monorepo. The honest next step is 2 weeks, 5 tickets, one real agent — and then deleting whichever gate produced false alarms.

---

## Repository layout

```text
headless-horseman-harness/
├── AGENTS.md                 # agent operating rules (7.1 - 7.21), Polish
├── hhh.profile               # hilux (default) | full
├── harness.lock              # sha256 pin of every gate file
├── install.sh                # installs git hooks (no network)
├── scripts/
│   ├── adversarial-review.sh # 7 sins, added lines only, real file:line
│   ├── preflight-gate.py     # 7.19: read → subtract → plan before code
│   ├── epistemic-gate.py     # 7.20: executable proofs (E1-E10)
│   ├── decision-gate.py      # 7.21: human-signed decisions (D1-D10)
│   ├── hhh-run.py            # step orchestrator with STOP semantics
│   ├── gate-lock.sh          # integrity (hash pin + rule set)
│   ├── docs-provenance.py    # Inception Gate + WIP=1
│   ├── selftest.sh           # 46-assertion matrix of all gates
│   ├── install-hooks.sh      # hooks, backs up foreign hooks
│   └── ub-metrics.sh         # complexity/duplication report (report-only)
├── docs/
│   ├── architecture/         # monorepo platform, critical thinking, fixes
│   ├── preflight/  epistemic/  decisions/   # artifact schemas + fixtures
│   └── ci/                   # ready-to-copy GitHub workflows
├── skills/                   # grill-me, ub-mode, code-review, tdd, ROUTING.md
├── tests/fixtures/negative/  # detector fixtures (allow-listed, with expiry)
└── .adversarial-allow        # exceptions: owner + reason + expiry (no expiry = BLOCKING)
```

---

## Language

Primary documentation, `AGENTS.md`, artifact schemas and all script messages are in **Polish** (this is a Polish project; the case study is Polish GovTech). This file is a faithful English summary. If you need English documentation for a wider team, that is a real gap — open an issue rather than assuming it exists.

---

## License

MIT. No telemetry, no outbound calls from the gates (`ub-metrics.sh` clones pinned upstream tools only when you run it explicitly).
