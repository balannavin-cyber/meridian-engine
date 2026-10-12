#!/usr/bin/env python3
"""Build the Marketview /help content pack from the manual.

Input:  marketview_user_manual.md (this directory) and SHOTS below.
Output: <out>/public/help/manual.json and <out>/public/help/shots/*.jpg (copied in by hand).

Lovable renders manual.json as-is. Every word on /help comes from the manual, never from Lovable.
Re-run after every manual change. The pack is versioned by `manual_version` and `board_bundle`.

Usage: python3 build_help_pack.py <out_root>
"""
import hashlib
import json
import re
import sys
from pathlib import Path

import markdown

HERE = Path(__file__).parent
MANUAL = HERE / "marketview_user_manual.md"

# Section id -> screenshots shown beside it. Every entry is a real capture from the live board.
# Fields: file, caption, symbol, date, time_ist (board/chain time as shown), bundle.
B = "index-CadQe4qO.js"
D = "2026-10-12"
SHOTS = {
    "part-1-getting-around": [
        ("nifty_0952_board_strip_overview.jpg", "The Board: header strip, read sentence, sub-tabs, ladder.", "NIFTY", "09:52"),
        ("nifty_0952_board_stale_strip.jpg", "The red stale strip at the top: \"chain data 12 min old · gamma run 17 min old · Health ›\".", "NIFTY", "09:52"),
    ],
    "s1-8": [
        ("nifty_1020_3d_gamma_terrain.jpg", "3D drill-down, γ terrain mode, 14 sessions.", "NIFTY", "10:20"),
    ],
    "part-2-the-header-strip": [
        ("nifty_0952_board_strip_overview.jpg", "Header strip in market hours (CLOCKS cell absent: clocks within one cycle).", "NIFTY", "09:52"),
        ("sensex_0940_board_strip_overview.jpg", "Header strip with the CLOCKS cell: \"γ 09:30 · chain 09:40 · 10 min apart\"; Flip \"carry unmeasurable\".", "SENSEX", "09:40"),
    ],
    "s2-4": [
        ("nifty_0952_overview_ladder.jpg", "Flip drawn as the dashed rule just below SPOT (22,496.7).", "NIFTY", "09:52"),
        ("nifty_1015_overview_spot_eq_flip_below_put_wall.jpg", "\"SPOT ≡ FLIP\" on one row; corridor \"below put wall\".", "NIFTY", "10:15"),
    ],
    "s2-10": [
        ("sensex_0940_board_strip_overview.jpg", "CLOCKS: \"γ 09:30 · chain 09:40 · 10 min apart\".", "SENSEX", "09:40"),
    ],
    "s3-1": [
        ("nifty_0952_overview_ladder.jpg", "Overview ladder: warm amplifying left, cool dampening right; SPOT, PUT OI WALL, FLIP, CALL OI WALL ≡ γ-CONC.", "NIFTY", "09:52"),
        ("nifty_0952_overview_drawer_net.jpg", "The drawer for Net Γ: WHAT IT IS · HOW TO READ IT · COMPUTED · SCALE · CAVEAT · READ IT WITH.", "NIFTY", "09:52"),
        ("nifty_1015_overview_hover_caption.jpg", "Hover a row: the caption line reads it (\"22,500 · −2.8L Cr · +0.06 % · PUT OI WALL\").", "NIFTY", "10:15"),
    ],
    "s3-2": [
        ("nifty_0952_pin.jpg", "Pin tab: PIN STATE SHIFTING, conviction, runner-up, lead, leader today, HHI, pin band.", "NIFTY", "09:52"),
    ],
    "s3-3": [
        ("nifty_0952_gamma.jpg", "Gamma tab: top-strike share, gross, net, contributing strikes, net-long γ; white dots = cumulative Σγ.", "NIFTY", "09:52"),
        ("nifty_0952_gamma_drawer_river.jpg", "Top-strike share drawer with call/put split; GAMMA RIVER below.", "NIFTY", "09:52"),
    ],
    "s3-4": [
        ("nifty_0952_oi.jpg", "OI butterfly: puts left (mid grey), calls right (light grey), max-pain rule and pain valley, ΔOI ticks.", "NIFTY", "09:50"),
        ("sensex_0955_oi_no_run_dOI_na.jpg", "SENSEX: \"ΔOI · n/a (SENSEX · TD-S84-NEW-4)\"; \"no run\" states.", "SENSEX", "09:55"),
    ],
    "s3-5": [
        ("nifty_0952_flows_hedge_tiles.jpg", "Flows: D-4 badge, hedge line with dashed L3 flip, ∂Δ and ∂Γ tiles with bricks.", "NIFTY", "09:50"),
        ("nifty_0952_flows_dex_sstar_caption.jpg", "DEX tiles with sub-lines and bricks, flow chip \"flow since 08:30 · against book\", S*, ∂Δ/∂t caption.", "NIFTY", "09:50"),
        ("sensex_0940_flows_dex_bricks_chip.jpg", "DEX bricks on the ladder: solid held, light added, dashed outline removed.", "SENSEX", "09:40"),
        ("sensex_0940_flows_unmeasurable_r.jpg", "Before carry was measurable: \"unmeasurable r\", \"flow · different run — not drawn\".", "SENSEX", "09:40"),
    ],
    "s3-6": [
        ("nifty_1020_iv.jpg", "IV tab: W1/W2 term structure and the W1 smile with ATM and K98 marks.", "NIFTY", "10:20"),
    ],
    "s3b-1": [
        ("sensex_1005_home_stale_strip.jpg", "Home: masthead, read, six question cards, context line (the red stale strip is showing).", "SENSEX", "10:05"),
    ],
    "s3b-2": [
        ("nifty_1014_context.jpg", "Context: legacy strip, WCB, market breadth, India VIX, IV skew.", "NIFTY", "10:14"),
    ],
    "s3b-3": [
        ("nifty_1014_structure.jpg", "Structure: ICT zones nearest to spot.", "NIFTY", "10:14"),
    ],
}


def plain(title: str) -> str:
    """Titles are rendered as text, not HTML, so strip Markdown emphasis and code marks."""
    return re.sub(r"[*`]", "", title).replace("\\*", "*").strip()


def slug(text: str) -> str:
    t = text.lower()
    t = re.sub(r"[*_`]", "", t)
    t = re.sub(r"[^a-z0-9\s-]", "", t)
    return re.sub(r"[\s-]+", "-", t).strip("-")


def to_html(md_text: str) -> str:
    # A list item that follows a continuation paragraph needs a blank line before it,
    # or python-markdown folds it into that paragraph (GitHub does not).
    lines, prev = [], ""
    for ln in md_text.split("\n"):
        if re.match(r"\s*([-*]|\d+\.)\s", ln) and prev.strip() and not re.match(r"\s*([-*]|\d+\.)\s", prev) and not prev.lstrip().startswith("|"):
            lines.append("")
        lines.append(ln)
        prev = ln
    md_text = "\n".join(lines)
    # Finding IDs point at the operator table (7.2), which /help does not carry.
    md_text = re.sub(r"\s*\((?:see )?findings? F-\d+(?:,? (?:and )?F-\d+)*(?:; [^)]*)?\)", "", md_text)
    md_text = re.sub(r";? ?(?:see )?findings? F-\d+(?:,? (?:and )?F-\d+)*", "", md_text)
    return markdown.markdown(md_text, extensions=["tables", "mdx_truly_sane_lists"], extension_configs={"mdx_truly_sane_lists": {"nested_indent": 2}})


def main(out_root: str) -> None:
    text = MANUAL.read_text(encoding="utf-8")
    head = re.search(r"\| Manual version \| (v[\d.]+)", text)
    manual_version = head.group(1) if head else "unknown"

    # Preface: everything before the first level-2 heading, minus the H1 (the page draws its own title).
    preface_md = re.split(r"(?m)^## ", text)[0]
    preface_md = re.sub(r"(?m)^# .*\n", "", preface_md).strip().rstrip("-").strip()

    # Split into level-2 parts, then level-3 sections inside each part.
    parts = []
    for block in re.split(r"(?m)^## ", text)[1:]:
        title, _, body = block.partition("\n")
        part = {"id": slug(title), "title": plain(title), "intro_html": "", "sections": []}
        chunks = re.split(r"(?m)^### ", body)
        intro = chunks[0].strip().strip("-").strip()
        part["intro_html"] = to_html(intro) if intro else ""
        part["shots"] = [s for s in SHOTS.get(part["id"], [])]
        for ch in chunks[1:]:
            st, _, sb = ch.partition("\n")
            if st.startswith("7.2 "):
                continue  # operator findings stay in the repo manual, not on /help
            num = re.match(r"(\d+b?(?:\.\d+)+)\s", st)
            sid = "s" + num.group(1).replace(".", "-") if num else slug(st)
            part["sections"].append({
                "id": sid,
                "title": plain(st),
                "html": to_html(sb.strip().rstrip("-").strip()),
                "shots": SHOTS.get(sid, []),
            })
        parts.append(part)

    known = {p["id"] for p in parts} | {s["id"] for p in parts for s in p["sections"]}
    missing = sorted(set(SHOTS) - known)
    if missing:
        sys.exit(f"SHOTS keys with no matching section: {missing}")

    def shot_obj(t):
        f, cap, sym, tm = t
        return {"file": f"help/shots/{f}", "caption": cap, "symbol": sym, "date": D, "time_ist": tm, "board_bundle": B}

    for p in parts:
        p["shots"] = [shot_obj(t) for t in p["shots"]]
        for s in p["sections"]:
            s["shots"] = [shot_obj(t) for t in s["shots"]]

    out = Path(out_root) / "public" / "help"
    out.mkdir(parents=True, exist_ok=True)
    shots_dir = out / "shots"
    used = {t[0] for v in SHOTS.values() for t in v}
    absent = sorted(f for f in used if not (shots_dir / f).exists())
    if absent:
        sys.exit(f"screenshots referenced but not in {shots_dir}: {absent}")

    doc = {
        "title": "Marketview user manual",
        "manual_version": manual_version,
        "board_bundle": B,
        "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "preface_html": to_html(preface_md),
        "parts": parts,
    }
    (out / "manual.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    n_sec = sum(len(p["sections"]) for p in parts)
    n_shot = sum(len(p["shots"]) + sum(len(s["shots"]) for s in p["sections"]) for p in parts)
    print(f"parts={len(parts)} sections={n_sec} shot_placements={n_shot} unique_shots={len(used)} version={manual_version}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
