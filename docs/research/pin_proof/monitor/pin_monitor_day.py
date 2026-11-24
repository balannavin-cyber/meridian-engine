#!/usr/bin/env python3
"""Pin monitor -- the daily read. One line per symbol appended to pin_monitor.csv.

Read-only, through bin/roq.sh as merdian_ro. Writes only under
docs/research/pin_proof/monitor/. No secrets are read, printed or stored: the
only credential is the one roq.sh keeps outside every git tree, and this script
never touches it (CLAUDE.md rule 19).

SHA256SUMS over the day folder is NOT written here. run_day.sh tees this
script's output to a log inside that same folder, so a manifest built here would
hash the log mid-write and `sha256sum -c` would fail on it every day. run_day.sh
builds and verifies the manifest after the tee pipeline has closed.

  usage: pin_monitor_day.py <YYYY-MM-DD>
         pin_monitor_day.py --explain          plain EXPLAIN gate, no rows read

Normally invoked through run_day.sh, which holds the refusals (before 16:30 IST
of the date, a date before 2026-11-25, a date already in the csv) and runs the
self-test first.

QUERY DISCIPLINE (build condition 3): one symbol-day per query, 5 s between
queries, STOP at the first error or any query over 10 s. No retry.

--explain prints `EXPLAIN <template>` for the IDENTICAL template text the daily
run sends, with the 2026-11-23 date literal, and FAILS on a Seq Scan over
gex_strike_snapshots, option_chain_snapshots or hist_spot_bars_1m. Gating the
text that actually runs is the point: a gate over a paraphrase gates nothing.

GUARDS, each able to fail for the reason it names:
  G1 instruments.strike_step must equal the PREREG step (NIFTY 50, SENSEX 100).
  G2 the day's LAST bar label must be '<date> 09:59:00+00'. A label of
     15:29:00+00 means the legacy IST-as-UTC era (ruling R2 would be wrong); an
     earlier label means the 16:20 IST CAS close has not landed yet (ruling R3).
  G3 the 15:29 IST bar itself must be present. No fallback to another bar.
  G4 no query over 10 s, no non-empty stderr, no non-zero exit.
"""
from __future__ import annotations

import subprocess
import sys
import time as _time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pin_monitor_lib import (  # noqa: E402
    IST, STRIKE_STEP, TAU_FALLBACK, UTC, format_line, header_line, measure_day,
)

HERE = Path(__file__).resolve().parent
ROQ = HERE.parents[3] / "bin" / "roq.sh"
CSV = HERE / "pin_monitor.csv"
SYMBOLS = ("NIFTY", "SENSEX")
EXPLAIN_DATE = date(2026, 11, 23)        # build condition 3
MAX_SECONDS = 10.0
SLEEP_BETWEEN = 5.0
# The three the build conditions name, plus gex_cycle_history, which the daily
# run reads at T2 and which the conditions omitted (ruling R5).
GUARDED = ("gex_strike_snapshots", "option_chain_snapshots", "hist_spot_bars_1m",
           "gex_cycle_history")

PSET = ("\\pset format unaligned\n\\pset fieldsep '|'\n"
        "\\pset tuples_only on\n\\pset null ''\n")


class Stop(SystemExit):
    def __init__(self, msg):
        super().__init__(f"STOP: {msg}")


# ---------------------------------------------------------------- templates
def templates(symbol: str, day: date) -> list[tuple[str, str]]:
    """The exact SQL the daily run sends. --explain gates this same text.

    Timestamps are rendered explicitly in UTC with to_char rather than left to
    the session's TimeZone, so the text the reader parses cannot change meaning
    with a server setting. The projection does not affect any plan.
    """
    d0, d1 = day.isoformat(), (day + timedelta(days=1)).isoformat()
    inst = f"(SELECT id FROM public.instruments WHERE symbol = '{symbol}')"
    return [
        ("T0_instrument", f"""
SELECT id::text, symbol, strike_step::text, timezone
  FROM public.instruments
 WHERE symbol = '{symbol}'"""),

        ("T5_tau", f"""
SELECT COALESCE(public.get_parameter_num('pin.tau.' || '{symbol}'), {TAU_FALLBACK})::text"""),

        ("T1_strikes", f"""
SELECT run_id::text,
       to_char(ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS') AS ts_utc,
       expiry_date::text, dte::text, strike::text, spot::text,
       oi_call::text, oi_put::text, gamma_call::text, gamma_put::text,
       gex_cr::text
  FROM public.gex_strike_snapshots
 WHERE symbol = '{symbol}'
   AND ts >= timestamptz '{d0} 00:00:00+05:30'
   AND ts <  timestamptz '{d1} 00:00:00+05:30'
 ORDER BY ts, expiry_date, strike"""),

        ("T2_board", f"""
SELECT run_id::text,
       to_char(ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS') AS ts_utc,
       expiry_date::text, dte::text, spot::text,
       pin_leader_strike::text, session_gate_state
  FROM public.gex_cycle_history
 WHERE symbol = '{symbol}'
   AND ts >= timestamptz '{d0} 00:00:00+05:30'
   AND ts <  timestamptz '{d1} 00:00:00+05:30'
 ORDER BY ts, expiry_date"""),

        ("T3_close_bar", f"""
SELECT to_char(bar_ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS') AS bar_ts_utc,
       close::text
  FROM public.hist_spot_bars_1m
 WHERE instrument_id = {inst}
   AND bar_ts = timestamptz '{d0} 09:59:00+00'"""),

        ("T4_bar_guard", f"""
SELECT to_char(min(bar_ts) AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS') AS first_bar,
       to_char(max(bar_ts) AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS') AS last_bar,
       count(*)::text AS n_bars
  FROM public.hist_spot_bars_1m
 WHERE instrument_id = {inst}
   AND bar_ts >= timestamptz '{d0} 00:00:00+00'
   AND bar_ts <  timestamptz '{d1} 00:00:00+00'"""),
    ]


# -------------------------------------------------------------------- runner
def roq(sql: str, sql_path: Path, out_path: Path, label: str) -> list[str]:
    sql_path.write_text(PSET + sql.strip() + ";\n", encoding="utf-8")
    t0 = _time.monotonic()
    p = subprocess.run([str(ROQ), str(sql_path)], capture_output=True, text=True)
    el = _time.monotonic() - t0
    out_path.write_text(p.stdout, encoding="utf-8")
    if p.stderr.strip():
        (out_path.with_suffix(".err")).write_text(p.stderr, encoding="utf-8")
    print(f"    {label:14s} rc={p.returncode} {el:5.2f}s "
          f"{len([l for l in p.stdout.splitlines() if l.strip()])} rows")
    if p.returncode != 0:
        raise Stop(f"{label} exited {p.returncode}; stderr in {out_path.with_suffix('.err')}")
    if p.stderr.strip():
        raise Stop(f"{label} wrote to stderr -- see {out_path.with_suffix('.err')}")
    if el > MAX_SECONDS:
        raise Stop(f"{label} took {el:.2f}s, over the {MAX_SECONDS:.0f}s limit")
    return [l for l in p.stdout.splitlines() if l.strip()]


def cells(line: str, n: int, label: str) -> list[str]:
    c = line.split("|")
    if len(c) != n:
        raise Stop(f"{label}: expected {n} fields, got {len(c)}: {line!r}")
    return [x.strip() for x in c]


def f_or_none(s):
    return None if s == "" else float(s)


def i_or_none(s):
    return None if s == "" else int(s)


def ts_utc(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC)


# ------------------------------------------------------------------ explain
def seq_scan_offenders(plan_text: str) -> list[str]:
    """Plan lines that are a Seq Scan over a guarded relation.

    Pure, and asserted in the self-test against a synthetic offending plan --
    otherwise the gate's PASS would only mean the detector never fires.
    """
    return [l.strip() for l in plan_text.splitlines()
            if "Seq Scan" in l and any(g in l for g in GUARDED)]


def explain_gate() -> int:
    day = EXPLAIN_DATE
    out = HERE / "build"
    out.mkdir(exist_ok=True)
    sql = ["-- Generated by pin_monitor_day.py --explain. The daily run sends the",
           "-- same template text with a different date literal.", ""]
    for symbol in SYMBOLS:
        for label, t in templates(symbol, day):
            sql += [f"\\echo == {label} {symbol} ==", "EXPLAIN" + t + ";", ""]
    path = out / "q_explain_final.sql"
    path.write_text("\n".join(sql), encoding="utf-8")
    p = subprocess.run([str(ROQ), str(path)], capture_output=True, text=True)
    (out / "out_explain_final.txt").write_text(p.stdout, encoding="utf-8")
    (out / "err_explain_final.txt").write_text(p.stderr, encoding="utf-8")
    print(p.stdout)
    if p.returncode != 0 or p.stderr.strip():
        print(f"EXPLAIN GATE: FAIL (rc={p.returncode})", file=sys.stderr)
        print(p.stderr, file=sys.stderr)
        return 2
    bad = seq_scan_offenders(p.stdout)
    if bad:
        print("EXPLAIN GATE: FAIL -- Seq Scan on a guarded table:", file=sys.stderr)
        for b in bad:
            print("  " + b, file=sys.stderr)
        return 2
    seq = [l.strip() for l in p.stdout.splitlines() if "Seq Scan" in l]
    print(f"EXPLAIN GATE: PASS -- no Seq Scan on {', '.join(GUARDED)}.")
    print(f"  {len(seq)} Seq Scan line(s), all on unguarded relations:")
    for s in sorted(set(seq)):
        print("    " + s)
    return 0


# -------------------------------------------------------------------- a day
def read_symbol(symbol: str, day: date, outdir: Path) -> dict:
    print(f"  {symbol}")
    tpl = dict(templates(symbol, day))
    got = {}
    for i, (label, sql) in enumerate(templates(symbol, day)):
        if i:
            _time.sleep(SLEEP_BETWEEN)
        got[label] = roq(sql, outdir / f"{symbol}_{label}.sql",
                         outdir / f"{symbol}_{label}.txt", label)
    del tpl

    # ---- G1 strike step
    if len(got["T0_instrument"]) != 1:
        raise Stop(f"{symbol}: instruments has {len(got['T0_instrument'])} rows, expected 1")
    _, _, step_s, _ = cells(got["T0_instrument"][0], 4, "T0")
    if float(step_s) != STRIKE_STEP[symbol]:
        raise Stop(f"G1 {symbol}: instruments.strike_step is {step_s}, "
                   f"PREREG says {STRIKE_STEP[symbol]}")

    tau = float(cells(got["T5_tau"][0], 1, "T5")[0])

    strike_rows = []
    for l in got["T1_strikes"]:
        c = cells(l, 11, "T1")
        strike_rows.append({
            "run_id": c[0], "ts": ts_utc(c[1]),
            "expiry_date": date.fromisoformat(c[2]), "dte": i_or_none(c[3]),
            "strike": float(c[4]), "spot": float(c[5]),
            "oi_call": i_or_none(c[6]), "oi_put": i_or_none(c[7]),
            "gamma_call": f_or_none(c[8]), "gamma_put": f_or_none(c[9]),
            "gex_cr": f_or_none(c[10])})
    if not strike_rows:
        raise Stop(f"{symbol}: no gex_strike_snapshots rows for {day} -- "
                   f"the day's line cannot be produced (PREREG Part 1 stop condition)")

    board_rows = []
    for l in got["T2_board"]:
        c = cells(l, 7, "T2")
        board_rows.append({
            "run_id": c[0], "ts": ts_utc(c[1]),
            "expiry_date": date.fromisoformat(c[2]), "dte": i_or_none(c[3]),
            "spot": f_or_none(c[4]), "pin_leader_strike": f_or_none(c[5]),
            "session_gate_state": c[6]})

    # ---- G2 bar-label convention and CAS arrival
    want_last = f"{day.isoformat()}T09:59:00"
    c = cells(got["T4_bar_guard"][0], 3, "T4")
    first_bar, last_bar, n_bars = c[0], c[1], c[2]
    if n_bars in ("", "0"):
        raise Stop(f"G2 {symbol}: no hist_spot_bars_1m rows on {day}")
    if last_bar != want_last:
        extra = ""
        if last_bar.endswith("T15:29:00"):
            extra = (" -- that is the LEGACY IST-as-UTC labelling; ruling R2 "
                     "says these rows are true UTC, so the convention has to be "
                     "settled before this day is measured")
        elif last_bar < want_last:
            extra = (" -- earlier than 09:59, so the 16:20 IST CAS close "
                     "(capture_cas_close.py, ADR-022) has not landed yet")
        raise Stop(f"G2 {symbol}: last bar label is {last_bar}, expected "
                   f"{want_last} (first {first_bar}, {n_bars} bars){extra}")

    # ---- G3 the close bar itself
    if len(got["T3_close_bar"]) != 1:
        raise Stop(f"G3 {symbol}: the 15:29 IST bar ({day} 09:59:00+00) returned "
                   f"{len(got['T3_close_bar'])} rows -- no fallback bar is used")
    c = cells(got["T3_close_bar"][0], 2, "T3")
    bar_rows = [{"bar_ts": ts_utc(c[0]), "close": float(c[1])}]
    read_at = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

    return measure_day(day, symbol, strike_rows, board_rows, bar_rows, tau,
                       float(step_s), read_at)


def main(argv: list[str]) -> int:
    if len(argv) == 1 and argv[0] == "--explain":
        return explain_gate()
    if len(argv) != 1:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    day = date.fromisoformat(argv[0])

    outdir = HERE / day.isoformat()
    outdir.mkdir(exist_ok=True)
    print(f"pin monitor {day} -- raw reads in {outdir.name}/")

    recs = []
    for i, symbol in enumerate(SYMBOLS):
        if i:
            _time.sleep(SLEEP_BETWEEN)
        recs.append(read_symbol(symbol, day, outdir))

    new = not CSV.exists()
    with CSV.open("a", encoding="utf-8", newline="\n") as fh:
        if new:
            fh.write(header_line() + "\n")
        for r in recs:
            fh.write(format_line(r) + "\n")
    print(f"  appended {len(recs)} line(s) to {CSV.name}"
          + (" (header written)" if new else ""))

    for r in recs:
        if r["stop_flag"]:
            print(f"  STOP CONDITION {r['symbol']}: {r['stop_reason']} "
                  f"-- report this evening (PREREG Part 1)")
        if not r["has_ref_run"]:
            print(f"  NO REFERENCE RUN {r['symbol']}: Part 2 blank for {day}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
