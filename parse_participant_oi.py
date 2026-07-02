"""ENH-115 P1 — NSE participant-wise OI CSV parser.

Source: https://archives.nseindia.com/content/nsccl/fao_participant_oi_<DDMMYYYY>.csv
Format (verified against a real archive file):
  line 0: title  '"Participant wise Open Interest (...) as on Jul 02,2021",,,...'
  line 1: header 'Client Type,Future Index Long,Future Index Short,...'
  line 2+: Client / DII / FII / Pro / TOTAL rows, 14 numeric cols each.
Positional mapping with a header-shape assertion so a silent NSE column
reorder fails loud instead of writing scrambled data.
"""
from __future__ import annotations
import csv, io, re
from datetime import datetime

PARTICIPANTS = {"CLIENT", "DII", "FII", "PRO", "TOTAL"}

# canonical column order in the NSE file (14 numeric cols after 'Client Type')
COLS = [
    "fut_idx_long", "fut_idx_short", "fut_stk_long", "fut_stk_short",
    "opt_idx_call_long", "opt_idx_put_long", "opt_idx_call_short", "opt_idx_put_short",
    "opt_stk_call_long", "opt_stk_put_long", "opt_stk_call_short", "opt_stk_put_short",
    "total_long", "total_short",
]
EXPECTED_HEADER = [
    "client type", "future index long", "future index short",
    "future stock long", "future stock short",
    "option index call long", "option index put long",
    "option index call short", "option index put short",
    "option stock call long", "option stock put long",
    "option stock call short", "option stock put short",
    "total long contracts", "total short contracts",
]


def _to_int(v):
    v = (v or "").strip().replace(",", "")
    if v == "":
        return None
    return int(float(v))


def parse_nse_participant_oi(text: str, exchange: str = "NSE") -> tuple[str, list[dict]]:
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) < 3:
        raise ValueError("participant OI CSV too short / empty")

    # trade_date from the title line: '... as on Jul 02,2021'
    title = ",".join(rows[0])
    m = re.search(r"as on\s+([A-Za-z]{3,9})\s+(\d{1,2}),\s*(\d{4})", title)
    if not m:
        raise ValueError(f"could not parse date from title: {title[:80]!r}")
    trade_date = datetime.strptime(f"{m.group(1)[:3]} {m.group(2)} {m.group(3)}",
                                   "%b %d %Y").date().isoformat()

    header = [h.strip().strip('"').strip().lower() for h in rows[1]]
    if header != EXPECTED_HEADER:
        raise ValueError(
            "NSE participant-OI header changed — refusing to map positionally.\n"
            f"got:      {header}\nexpected: {EXPECTED_HEADER}")

    out = []
    for r in rows[2:]:
        if not r or not r[0].strip():
            continue
        participant = r[0].strip().upper()
        if participant not in PARTICIPANTS:
            continue
        vals = r[1:15]
        if len(vals) < 14:
            raise ValueError(f"{participant}: expected 14 cols, got {len(vals)}")
        rec = {"exchange": exchange, "trade_date": trade_date,
               "participant": "Client" if participant == "CLIENT" else participant.title()
               if participant in ("DII", "FII", "PRO") else participant}
        # normalize display casing: FII/DII/Pro/Client/TOTAL
        rec["participant"] = {"CLIENT": "Client", "DII": "DII", "FII": "FII",
                              "PRO": "Pro", "TOTAL": "TOTAL"}[participant]
        for col, v in zip(COLS, vals):
            rec[col] = _to_int(v)
        rec["source"] = "nse_fao_participant_oi"
        out.append(rec)
    return trade_date, out


if __name__ == "__main__":
    # Real archive sample: fao_participant_oi_02072021.csv (verbatim schema + one full board)
    SAMPLE = (
        '"Participant wise Open Interest (no. of contracts) in Equity Derivatives as on Jul 02,2021",,,,,,,,,,,,,,\n'
        'Client Type,Future Index Long,Future Index Short,Future Stock Long,"Future Stock Short ",'
        'Option Index Call Long,Option Index Put Long,Option Index Call Short,Option Index Put Short,'
        'Option Stock Call Long,Option Stock Put Long,Option Stock Call Short,Option Stock Put Short,'
        '"Total Long Contracts ",Total Short Contracts\n'
        'Client,166452,176152,1171319,170041,1128978,1028634,1190321,1260653,751440,219865,460197,370763,4466688,3628127\n'
        'DII,1945,57834,22378,1165246,401,24684,0,0,0,0,54751,0,49408,1277831\n'
        'FII,87447,29573,672407,714572,214266,302772,137101,154294,45032,47334,71831,35772,1369258,1143143\n'
        'Pro,28462,20747,257287,73532,333496,366114,349718,307257,135554,235212,345247,95876,1356125,1192377\n'
        'TOTAL,284306,284306,2123391,2123391,1677140,1722204,1677140,1722204,932026,502411,932026,502411,7241477,7241477\n'
    )
    td, recs = parse_nse_participant_oi(SAMPLE)
    print("trade_date:", td, "| rows:", len(recs))
    for rec in recs:
        fii_dir = ""
        if rec["participant"] in ("FII", "Pro", "Client", "DII"):
            net_fut_idx = (rec["fut_idx_long"] or 0) - (rec["fut_idx_short"] or 0)
            net_opt_idx = ((rec["opt_idx_call_long"] or 0) + (rec["opt_idx_put_long"] or 0)
                           - (rec["opt_idx_call_short"] or 0) - (rec["opt_idx_put_short"] or 0))
            fii_dir = f"  net_idx_fut={net_fut_idx:>+9d}  net_idx_opt={net_opt_idx:>+9d}"
        print(f"  {rec['participant']:<6} fut_idx L/S={rec['fut_idx_long']:>7}/{rec['fut_idx_short']:<7}"
              f" opt_idx CL/PL/CS/PS={rec['opt_idx_call_long']}/{rec['opt_idx_put_long']}/"
              f"{rec['opt_idx_call_short']}/{rec['opt_idx_put_short']}{fii_dir}")
    # sanity: TOTAL long must equal TOTAL short (book balances)
    tot = [r for r in recs if r["participant"] == "TOTAL"][0]
    print("TOTAL balances (long==short):", tot["total_long"] == tot["total_short"], tot["total_long"])
