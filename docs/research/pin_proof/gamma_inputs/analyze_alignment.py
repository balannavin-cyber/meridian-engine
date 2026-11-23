#!/usr/bin/env python3
"""Compare hist_future_bars_1m closes against fyers_futures_bars_1m closes.

READ-ONLY, NO DATABASE ACCESS. Reads only files already in this folder:
  _partF_raw.txt                  -- hist_future_bars_1m rows at the EXACT sampled
                                     minutes (tag F1: contract_series, expiry_date,
                                     fut_close, fut_dte)
  _qH_trial_<SYM>_<DATE>.txt      -- fyers_futures_bars_1m rows in the +/-120 s windows
                                     (tag H1: symbol, expiry_date, off_sec, close)

For each of the two pairs below, at each of the three sampled IST minutes, every
hist_future_bars_1m close is compared with the Fyers close of every contract at the
candidate bar offsets -60, 0 and +60 seconds around the TRUE-UTC instant
(10:00 IST = 04:30 UTC, 12:30 = 07:00, 15:00 = 09:30).

Prints every comparison with its absolute difference, then for each
hist_future_bars_1m contract_series the Fyers contract and offset with the smallest
difference. DIFFERENCES ONLY -- this script states no conclusion about the alignment,
and no Fyers price is used in any sensitivity.
"""
import json
import sys
from collections import defaultdict

PAIRS = [("NIFTY", "2025-04-01"), ("SENSEX", "2025-05-02")]
OFFSETS = (-60.0, 0.0, 60.0)
READING = "UTC"
MINUTES = ("10:00", "12:30", "15:00")


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


def load_fyers(sym, date):
    """fyers_futures_bars_1m rows from a qH trial file, tag H1, true-UTC reading only."""
    out = defaultdict(list)
    path = f"_qH_trial_{sym}_{date}.txt"
    try:
        fh = open(path)
    except FileNotFoundError:
        print(f"# MISSING FILE {path} -- no Fyers rows for {sym} {date}")
        return out
    with fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            tag, payload = line.split("|", 1)
            if tag != "H1":
                continue
            d = json.loads(payload)
            if d["reading"] != READING:
                continue
            if float(d["off_sec"]) not in OFFSETS:
                continue
            out[d["tname"]].append(d)
    return out


def main():
    hist = load_hist()
    for sym, date in PAIRS:
        print("=" * 100)
        print(f"{sym} {date} -- hist_future_bars_1m close vs fyers_futures_bars_1m close")
        print(f"  Fyers rows restricted to reading={READING} and off_sec in "
              f"{{{', '.join(str(int(o)) for o in OFFSETS)}}}")
        print("=" * 100)
        fy = load_fyers(sym, date)
        for minute in MINUTES:
            hrows = hist.get((sym, date, minute), [])
            frows = fy.get(minute, [])
            print(f"\n-- minute {minute} IST   "
                  f"hist rows: {len(hrows)}   fyers rows (at the 3 offsets): {len(frows)}")
            if not hrows:
                print("   NO hist_future_bars_1m row at this minute -- nothing to compare")
                continue
            if not frows:
                print("   NO fyers row at the 3 candidate offsets -- nothing to compare")
                continue
            print("   hist_series | hist_expiry | hist_close | fyers_contract         "
                  "| fyers_expiry | off_sec | fyers_close | abs_diff")
            best = {}
            for h in sorted(hrows, key=lambda x: (x["contract_series"] is None,
                                                  x["contract_series"] or 0)):
                hc = h.get("fut_close")
                if hc is None:
                    print(f"   {str(h['contract_series']):11} | "
                          f"{str(h['expiry_date']):11} | (null close) -- skipped")
                    continue
                hc = float(hc)
                for f in sorted(frows, key=lambda x: (float(x["off_sec"]), x["symbol"])):
                    fc = f.get("close")
                    if fc is None:
                        continue
                    fc = float(fc)
                    diff = abs(hc - fc)
                    print(f"   {str(h['contract_series']):11} | "
                          f"{str(h['expiry_date']):11} | {hc:10.2f} | "
                          f"{f['symbol']:22} | {str(f['expiry_date']):12} | "
                          f"{int(float(f['off_sec'])):7} | {fc:11.2f} | {diff:9.2f}")
                    # Keyed on (contract_series, expiry_date), NOT contract_series alone.
                    # SENSEX carries contract_series = 0 on every contract, so a
                    # series-only key is degenerate there and silently kept one hist
                    # contract per minute, dropping the other from the summary
                    # (_alignment_v1_degenerate_key.txt shows that version).
                    k = (h["contract_series"], h["expiry_date"])
                    if k not in best or diff < best[k][0]:
                        best[k] = (diff, f["symbol"], int(float(f["off_sec"])),
                                   fc, hc, f["expiry_date"], h["expiry_date"])
            if best:
                print("\n   smallest absolute difference per hist "
                      "(contract_series, expiry_date):")
                print("   hist_series | hist_expiry | hist_close | best_fyers_contract    "
                      "| fyers_expiry | off_sec | fyers_close | abs_diff")
                for k in sorted(best, key=lambda x: (x[0] is None, x[0] or 0,
                                                     str(x[1]))):
                    diff, fsym, off, fc, hc, fexp, hexp = best[k]
                    print(f"   {str(k[0]):11} | {str(hexp):11} | {hc:10.2f} | "
                          f"{fsym:22} | {str(fexp):12} | {off:7} | {fc:11.2f} | {diff:9.2f}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
