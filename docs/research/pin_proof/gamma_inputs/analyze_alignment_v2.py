#!/usr/bin/env python3
"""Alignment RE-CHECK on a later pair of days. Copy of analyze_alignment.py, body
rewritten for the second pair; the original is untouched.

READ-ONLY, NO DATABASE ACCESS. Reads only files already in this folder:
  _partF_raw.txt  -- hist_future_bars_1m rows at the EXACT sampled minutes (tag F1:
                     contract_series, expiry_date, fut_close, fut_dte)
  _partH_raw.txt  -- fyers_futures_bars_1m rows in the +/-120 s windows (tag H1:
                     symbol, expiry_date, off_sec, close), reading 'UTC' only

This is the re-check the FUTURES CONTRACT RULE's ALIGNMENT BASIS line requires: the
rule adopted offset 0 under the true-UTC reading on a two-day test (NIFTY 2025-04-01,
SENSEX 2025-05-02), and is VOID if a later pair does not reproduce exact matches.

Pairs: NIFTY 2026-03-04 and SENSEX 2026-03-02, three minutes each.
Hist contracts are keyed by (contract_series, expiry_date) -- NOT contract_series alone,
which is degenerate for SENSEX where every contract carries contract_series = 0.
Pairing is decided by EXACT float equality of closes: no rank mapping, and no assumption
about which Fyers contract belongs with which hist contract.

NO r is computed and no price is used for anything else.
"""
import json
import sys
from collections import defaultdict

PAIRS = [("NIFTY", "2026-03-04"), ("SENSEX", "2026-03-02")]
MINUTES = ("10:00", "12:30", "15:00")
OFFSETS = (-60.0, 0.0, 60.0)
READING = "UTC"


def load_hist(path="_partF_raw.txt"):
    """hist_future_bars_1m rows at the exact sampled minutes, tag F1."""
    out = defaultdict(list)
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            sym, day, tag, payload = line.split("|", 3)
            if tag != "F1":
                continue
            d = json.loads(payload)
            out[(d["sym"], d["d"], d["tname"])].append(d)
    return out


def load_fyers(path="_partH_raw.txt"):
    """fyers rows, tag H1, reading UTC only, keyed by (sym, day, minute)."""
    out = defaultdict(list)
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            sym, day, tag, payload = line.split("|", 3)
            if tag != "H1":
                continue
            d = json.loads(payload)
            if d["reading"] != READING:
                continue
            if float(d["off_sec"]) not in OFFSETS:
                continue
            out[(sym, day, d["tname"])].append(d)
    return out


def fmt(v):
    return "     -    " if v is None else f"{v:10.2f}"


def nearest_hist_key(sym, keys):
    """NEAREST hist contract: smallest contract_series for NIFTY (expiry_date is NULL
    there), smallest expiry_date for SENSEX (contract_series is always 0 there)."""
    if sym == "NIFTY":
        return min(keys, key=lambda k: (k[0] is None, k[0] if k[0] is not None else 0))
    return min(keys, key=lambda k: (k[1] is None, str(k[1])))


def main():
    hist = load_hist()
    fy = load_fyers()
    # per (sym, date, minute, hist_key) -> summary record. Replaces an earlier
    # EQUAL/NOT_EQUAL pair tally, which counted comparison pairs and so could not say
    # whether a given hist contract matched anything.
    results = {}
    hist_keys = defaultdict(set)          # (sym, date) -> set of hist keys seen
    fyers_nearest = {}                    # (sym, date, minute) -> nearest fyers expiry

    for sym, date in PAIRS:
        print("=" * 112)
        print(f"{sym} {date} -- ALIGNMENT RE-CHECK   hist_future_bars_1m vs "
              f"fyers_futures_bars_1m (reading {READING})")
        print("=" * 112)
        for minute in MINUTES:
            hrows = hist.get((sym, date, minute), [])
            frows = fy.get((sym, date, minute), [])
            print(f"\n-- minute {minute} IST   hist rows: {len(hrows)}   "
                  f"fyers rows at offsets {{-60, 0, +60}}: {len(frows)}")
            if not hrows:
                print("   NO hist_future_bars_1m row at this minute -- no comparison")
                continue
            if not frows:
                print("   NO fyers row at the three offsets -- no comparison")
                continue
            by_contract = defaultdict(dict)
            for r in frows:
                by_contract[(r["symbol"], r["expiry_date"])][float(r["off_sec"])] = r
            print("   hist(series,expiry)        | hist_close | fyers_contract         "
                  "| fyers_expiry | f(-60)     | f(0)       | f(+60)     | diff(0)")
            # nearest-expiry Fyers contract present in THIS window, by measured expiry
            fexps = [k[1] for k in by_contract if k[1] is not None]
            if fexps:
                fyers_nearest[(sym, date, minute)] = min(fexps)
            for h in sorted(hrows, key=lambda x: (x["contract_series"] is None,
                                                  x["contract_series"] or 0,
                                                  str(x["expiry_date"]))):
                hc = h.get("fut_close")
                hkey = (h["contract_series"], h["expiry_date"])
                hlab = f"({hkey[0]},{hkey[1]})"
                if hc is None:
                    print(f"   {hlab:26} | (null close) -- skipped")
                    continue
                hc = float(hc)
                hist_keys[(sym, date)].add(hkey)
                matched = {-60.0: [], 0.0: [], 60.0: []}
                for ckey in sorted(by_contract):
                    offs = by_contract[ckey]
                    vals = {}
                    for o in OFFSETS:
                        c = offs.get(o, {}).get("close")
                        vals[o] = None if c is None else float(c)
                        # EXACT float equality decides the pairing.
                        if vals[o] is not None and hc == vals[o]:
                            matched[o].append(ckey)
                    d0 = None if vals[0.0] is None else abs(hc - vals[0.0])
                    print(f"   {hlab:26} | {hc:10.2f} | {ckey[0]:22} | "
                          f"{str(ckey[1]):12} | {fmt(vals[-60.0])} | {fmt(vals[0.0])} | "
                          f"{fmt(vals[60.0])} | "
                          f"{'    -    ' if d0 is None else f'{d0:9.2f}'}")
                if matched[0.0]:
                    verdict = "MATCH_AT_0"
                elif matched[-60.0]:
                    verdict = "MATCH_ONLY_AT_-60"
                elif matched[60.0]:
                    verdict = "MATCH_ONLY_AT_+60"
                else:
                    verdict = "UNMATCHED"
                results[(sym, date, minute, hkey)] = {
                    "hist_close": hc, "matched": matched, "verdict": verdict}

            print("\n   summary, one line per hist contract:")
            print("   hist(series,expiry)        | hist_close | match@0          "
                  "| match@-60        | match@+60        | verdict")
            for (s, d_, m_, hk), rec in sorted(
                    results.items(), key=lambda kv: str(kv[0][3])):
                if (s, d_, m_) != (sym, date, minute):
                    continue

                def show(o, rec=rec):
                    v = rec["matched"][o]
                    return "none" if not v else ",".join(f"{a} {b}" for a, b in v)
                print(f"   ({hk[0]},{hk[1]})".ljust(30) +
                      f"| {rec['hist_close']:10.2f} | {show(0.0):16} | "
                      f"{show(-60.0):16} | {show(60.0):16} | {rec['verdict']}")
        print()

    print("=" * 112)
    print("### Verdict on the NEAREST hist contract")
    print("# NEAREST = smallest contract_series for NIFTY (its expiry_date is NULL),")
    print("# smallest expiry_date for SENSEX (its contract_series is always 0).")
    print("# THREE outcomes:")
    print("#   ALIGNMENT HOLDS        -- at all six minutes the nearest hist contract is")
    print("#     MATCH_AT_0 to the NEAREST Fyers contract, AND its close matches NOTHING")
    print("#     at -60 or +60. The second clause matters because a flat price makes an")
    print("#     offset-0 match non-discriminating.")
    print("#   ALIGNMENT VOID         -- any minute is not MATCH_AT_0, or matches only at")
    print("#     -60 or +60, or is UNMATCHED, or has no record, or the matched Fyers")
    print("#     contract is not the nearest. VOID takes priority over INCONCLUSIVE.")
    print("#   ALIGNMENT INCONCLUSIVE -- no minute is void, but at least one also matches")
    print("#     at -60 or +60, so offset 0 is not singled out at those minutes.")
    print("sym|day|minute|nearest_hist|verdict|matched_fyers|nearest_fyers_in_window|"
          "also_matches_at_other_offsets|both_ok")
    failures = []
    inconclusive = []
    for sym, date in PAIRS:
        keys = hist_keys.get((sym, date), set())
        if not keys:
            failures.append(f"{sym} {date} (no hist contract with a close)")
            continue
        nearest_h = nearest_hist_key(sym, keys)
        for minute in MINUTES:
            rec = results.get((sym, date, minute, nearest_h))
            if rec is None:
                failures.append(f"{sym} {date} {minute} (no record)")
                print(f"{sym}|{date}|{minute}|({nearest_h[0]},{nearest_h[1]})|"
                      f"NO_RECORD|-|-|-|NO")
                continue
            m0 = rec["matched"][0.0]
            fn = fyers_nearest.get((sym, date, minute))
            matched_lab = "none" if not m0 else ",".join(f"{a} {b}" for a, b in m0)
            # STRICT: every matched Fyers contract at offset 0 must be the nearest.
            is_nearest = bool(m0) and fn is not None and all(b == fn for _, b in m0)
            # A close that ALSO equals the -60 or +60 close makes offset 0
            # non-discriminating at this minute: a flat price would match anywhere.
            other = []
            if rec["matched"][-60.0]:
                other.append("-60")
            if rec["matched"][60.0]:
                other.append("+60")
            other_lab = "none" if not other else ",".join(other)
            is_void = rec["verdict"] != "MATCH_AT_0" or not is_nearest
            if is_void:
                failures.append(f"{sym} {date} {minute}")
            elif other:
                inconclusive.append(f"{sym} {date} {minute} (also matches at "
                                    f"{other_lab})")
            print(f"{sym}|{date}|{minute}|({nearest_h[0]},{nearest_h[1]})|"
                  f"{rec['verdict']}|{matched_lab}|{fn}|{other_lab}|"
                  f"{'NO' if is_void else 'YES'}")

    print()
    if failures:
        print(f"ALIGNMENT VOID: {'; '.join(failures)}")
    elif inconclusive:
        print(f"ALIGNMENT INCONCLUSIVE: {'; '.join(inconclusive)}")
    else:
        print("ALIGNMENT HOLDS")

    print()
    print("### Other hist contracts -- INFORMATION ONLY, does not decide the outcome")
    print("sym|day|hist(series,expiry)|MATCH_AT_0|UNMATCHED|other")
    for sym, date in PAIRS:
        keys = hist_keys.get((sym, date), set())
        if not keys:
            continue
        nearest_h = nearest_hist_key(sym, keys)
        for hk in sorted(keys, key=str):
            if hk == nearest_h:
                continue
            v = [results[(sym, date, m, hk)]["verdict"]
                 for m in MINUTES if (sym, date, m, hk) in results]
            print(f"{sym}|{date}|({hk[0]},{hk[1]})|{v.count('MATCH_AT_0')}|"
                  f"{v.count('UNMATCHED')}|"
                  f"{len(v) - v.count('MATCH_AT_0') - v.count('UNMATCHED')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
