# MERDIAN Testing Protocol v1

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | `MERDIAN_Testing_Protocol_v1.md` |
| Version | v1 |
| Created | (this session) |
| Type | Operational — what to test, where, when, how |
| Companion | `MERDIAN_Change_Protocol_v1.md` (governs deployment), `MERDIAN_Documentation_Protocol_v3.md` (governs records) |

---

## Why this document exists

Testing rules in MERDIAN have lived inside the Change Protocol (preflight stages), inside session appendices (replay procedures), and inside Navin's head (canary discipline). Pulling them into one file gives Claude a single place to consult when asked "is this safe to run?" and gives Navin a single place to update when a new test stage is added.

This file does **not** define what *unit tests* exist for individual functions — those live alongside the code in `tests/` (or, where MERDIAN doesn't yet have them, are themselves tech debt — see `tech_debt.md`). This file defines the **system-level test gates** that prevent bad code from reaching the live market.

---

## The five gates

Every code change passes through up to five gates before it can run live. Lower-numbered gates must pass before higher-numbered gates are attempted.

| Gate | What it validates | Where it runs | Required for |
|---|---|---|---|
| **0 · Static** | Syntax, imports, hardcoded paths, debug prints | Pre-commit | All code changes |
| **1 · Auth/API** | Token refresh, IDX_I, expiry-list, LTP smoke | Local + AWS | Any change touching Dhan API |
| **2 · DB contract** | Tables, columns, indexes, calendar row, freshness | Local + AWS | Any DATA-tagged change |
| **3 · Runner dry-start** | Runner starts and exits cleanly outside session | Local + AWS | Any runner script change |
| **4 · Replay** | Analytics on stored fixtures; deterministic output | Local | Any SIGNAL-tagged change |
| **5 · Live canary** | Behaviour on live changing data, market hours | Local PRIMARY only | Final gate before declaring "promoted" |

> **Rule:** Live canary is for validating live-data behaviour on already-validated code. It is **not** for discovering import errors, schema mismatches, path failures, or auth failures. Those belong in Gates 0–4.

---

## Gate 0 — Static (pre-commit)

Run before every commit. Should be a one-line script.

```
☐ ast.parse() on every .py file changed (catches syntax errors silently introduced by patch scripts)
☐ grep for hardcoded "C:\\GammaEnginePython" in any file destined for AWS
☐ grep for orphan print() in production runner files
☐ grep for hardcoded .env values in any file
☐ Confirm file is full replacement, not a fragment
```

**Failure response:** Do not commit. Fix locally and re-run.

**Standing rule:** Any `fix_*.py` patch script must end with `ast.parse()` of the target file before writing it. If `SyntaxError`: print error and `sys.exit(1)`. (Established Research Session 4, 2026-04-17, after `force_wire_breadth.py` shipped invalid indent and `IndentationError` was discovered at market open.)

---

## Gate 1 — Auth / API smoke

Confirms the runtime can reach Dhan. Required when any auth path, token plumbing, or API call signature changes.

```
☐ Token refresh succeeds (Local + AWS, 08:15 IST cadence)
☐ IDX_I scrip resolution returns expected ID for NIFTY and SENSEX
☐ Expiry-list fetch returns the expected next weekly expiry (Tue for NIFTY, Fri for SENSEX as of 2026)
☐ LTP fetch on one ATM strike returns a number (not None, not 0)
```

**Failure response:** Do not run runner. Investigate auth/token. Common causes: token expired, .env not sourced, BREAK_GLASS edit on AWS not synced.

**Files involved:** `pull_token_from_supabase.py` (AWS), token cache files, `.env`

---

## Gate 2 — DB contract

Confirms the schema the code expects matches the schema the DB has.

```
☐ All tables in merdian_reference.json "tables" exist with expected columns
☐ All UNIQUE constraints expected by UPSERT logic exist
☐ trading_calendar row for today exists (HARD GATE — missing row = system treats day as closed)
☐ Last 5 trading_calendar rows look correct (no accidental holiday inserts)
☐ Last write timestamp on each critical hot table is within expected freshness window
```

**Failure response:** Do not run runner. Investigate via direct SQL on Supabase. **DB is truth — logs are supporting evidence.**

**Critical rule:** trading_calendar must have entries at least 1 week ahead at all times. Missing row is **not** a soft warning — it causes authoritative skip for ALL calendar-gated scripts (V18A-03 historical learning).

---

## Gate 3 — Runner dry-start

Confirms a runner can boot, do its first cycle, and exit cleanly without market data dependency.

```
☐ Runner starts without ImportError, AttributeError, ConfigError
☐ Runner connects to Supabase, reads required config rows
☐ First cycle returns expected log line ("Run ID: ..." stdout contract for ingest_option_chain_local.py)
☐ Runner exits on SIGTERM/Ctrl-C without leaving zombie subprocesses
```

**Failure response:** Do not run live. Common causes: missing env var, wrong Python interpreter, file path drift between Local and AWS.

**Hash match precondition:** Local commit hash must equal AWS commit hash before AWS dry-start counts.

---

## Gate 4 — Replay

Confirms the signal/analytics computation produces the same output on stored input. Required for any SIGNAL-tagged change.

### Fixture locations

| Fixture | Path | Refresh cadence |
|---|---|---|
| Option chain snapshot (NIFTY clean session) | `fixtures/option_chain_NIFTY_<date>.json` | After every meaningful schema or contract change |
| Option chain snapshot (SENSEX clean session) | `fixtures/option_chain_SENSEX_<date>.json` | After every meaningful schema or contract change |
| Spot tape window (1m bars, 1 session) | `fixtures/spot_bars_1m_<date>.csv` | Quarterly or after expiry rule change |
| Pre-computed expected outputs | `fixtures/expected/<run_id>.json` | Regenerate after any deliberate signal logic change |

### Replay procedure

```
☐ Load fixture into a sandbox DB or in-memory structure
☐ Run the same code path that consumed live data, against fixture
☐ Diff actual output vs fixtures/expected/<run_id>.json
☐ All differences must be either (a) zero, or (b) explained by the change being tested
```

**Failure response:** Either the change is wrong, or the expected fixture is stale. Investigate before promoting.

**Capture cadence (Change Protocol Step 9):** Capture fresh fixtures the first clean session after any meaningful change. Stale fixtures are silent failures waiting to happen.

---

## Gate 5 — Live canary

The final gate. Run during market hours on Local PRIMARY only.

### Preconditions (ALL must be true)

```
☐ Gates 0–4 PASS
☐ Local commit hash == AWS commit hash
☐ trading_calendar row for today exists
☐ Token refresh confirmed PASS at 08:15 IST
☐ Preflight auto-run at 08:30 IST returned PASS via Telegram
```

### Canary procedure

```
☐ 09:15 IST — start canary runner (one cycle window, ~5 min)
☐ Watch first three signal cycles
☐ Confirm signal_snapshots writes happen at expected cadence
☐ Confirm no Telegram error alerts
☐ Confirm shadow vs live divergence (if shadow runner active) is within expected band
```

### Outcome

| Result | Action |
|---|---|
| PASS | `git tag vYYYYMMDD-canary-pass` and `git push --tags`. Promote change to "live-validated" in Enhancement Register / tech_debt. |
| FAIL | Stop session. Capture exact failure (stdout, log, DB row). Open C-N in `merdian_reference.json`. Do not retry without root-cause fix. Consider rollback (Change Protocol Step 8B). |

---

## Daily cadence (operational summary)

```
08:15 IST   Token refresh (Local + AWS)
08:30 IST   Preflight auto-run (Local + AWS) → Telegram PASS/FAIL
08:30–09:10 Investigation window if FAIL
09:15 IST   Live canary (PASS only)
Post-market Capture fixtures + update registers + commit + tag
```

---

## Failure mode reference

| Mode | Condition | Response |
|---|---|---|
| FULL | Local + AWS preflight PASS, hash match | Proceed to live canary |
| LOCAL_ONLY | AWS preflight FAIL, Local PASS | Local runs, AWS sits out |
| NO_SESSION | Local preflight FAIL | No live session today; investigate |
| DEGRADED | Hash mismatch, both may preflight PASS individually | Resolve sync **before** any run — different code on two environments is the worst failure mode |

---

## When to add a new gate

Add a new gate when a real failure escapes all current gates and reaches live. Add it at the lowest number where it could have caught the failure. Document the originating incident inline.

Do **not** add gates speculatively. Gates that don't catch real failures become noise that gets ignored.

---

## What this document does NOT cover

- **Unit tests for individual functions** — those live in `tests/` next to the code. Where MERDIAN currently has none, that is itself tech debt (consider TD-NNN).
- **Performance / load testing** — MERDIAN's load is bounded by Dhan rate limits, not runtime; not currently relevant. If commercial API tier launches, add Gate 6.
- **Security testing** — `.env` discipline + AWS SSM access controls cover current threat model. Add gate when commercial API exposes endpoints.

---

*MERDIAN Testing Protocol v1 — Markdown, lives in `docs/operational/`. Update version number when a new gate is added or an existing gate's procedure changes.*
