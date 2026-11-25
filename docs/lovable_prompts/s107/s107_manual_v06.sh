#!/usr/bin/env bash
# s107_manual_v06.sh -- S107 / ADR-033 D7, I-002 row 17 (manual part): build manual v0.6 (Pin = gross pin; Net peak)
# into ~/meridian-connect/public/help/manual.json.
# Reads the engine source read-only from ~/meridian-engine; edits a copy in /tmp/s107man; never touches the engine tree; never commits.
# Run on the box outside 08:30-15:40 IST, AFTER ~/meridian-connect is at the labels commit (457fc99).
#   bash ~/s107_manual_v06.sh
set -euo pipefail
ENG="${ENG:-$HOME/meridian-engine}"; MC="${MC:-$HOME/meridian-connect}"; W=/tmp/s107man
rm -rf "$W"; mkdir -p "$W"
cp "$ENG/docs/marketview_manual/marketview_user_manual.md" "$ENG/docs/marketview_manual/build_help_pack.py" "$W/"
echo "e4872ab61e9c86e134bd66f3caaf0d20166030c48a8bf873febaf0e3e3b26e7c  $W/marketview_user_manual.md" | sha256sum -c -
echo "e6b673654631a28d164a28f18159b4bd28fdebae83f0a6029b51fc060060f6f4  $W/build_help_pack.py" | sha256sum -c -
cat > "$W/edits_man.py" <<'PYEOF'
"""S107 ADR-033 D7 -- manual v0.5 -> v0.6: the Pin is the gross pin; state, conviction and concentration sit under Net peak.
Canon-v3: each old string must occur exactly once."""
E = [
 ("| Manual version | v0.5 (draft) |", "| Manual version | v0.6 (draft) |"),
 ("**the screenshots still show the earlier scale** (100 × larger). |",
  "**the screenshots still show the earlier scale** (100 × larger). v0.6 (2026-11-25, ADR-033): the **Pin is the gross pin**, and pin state, conviction and concentration are shown under **Net peak**. Worked examples and screenshots read before 2026-11-25 show the earlier net-γ pin, labelled γ-conc, whose share the board then called \"of gross\"; they are marked where they appear. A gross-pin worked example is owed. |"),
 ("- **Read it with.** Pin (γ-conc), Flip, and on the Gamma tab, Gross |Γ|.", "- **Read it with.** Pin (gross γ), Flip, and on the Gamma tab, Gross |Γ|."),
 ("### 2.6 PIN (γ-conc)", "### 2.6 PIN (gross γ)"),
 ("- **What it is.** The single strike holding the largest share of gross |γ|.",
  "- **What it is.** The strike with the largest gross γ among strikes within 5 % of spot. Gross γ uses one gamma per strike (the mean of the two vendor gammas, or the one that exists) times call plus put open interest, so it has no sign. Until 2026-11-25 this tile showed the net-γ top strike instead; that strike is now the **Net peak** on the Pin tab (§3.2)."),
 ("- **How to read it.** The value is the strike. The sub-line gives its share of gross and the **lead** over the runner-up in share points. \"≡ put OI wall\" appears when the pin sits on the same strike as a wall.",
  "- **How to read it.** The value is the strike. The sub-line gives its share **of band gross** (gross γ over the strikes within 5 % of spot), the **lead** over the runner-up in share points, and the time of the read. \"≡ put OI wall\" appears when the pin sits on the same strike as a wall. These shares are not comparable with the net shares on the Gamma tab or on the Pin tab's bars."),
 ("  - NIFTY 09:41: `22,700 · 10.8 % of gross · lead 1.7 pts`.",
  "  - *(Both lines were read on 2026-10-12, when the tile showed the net-γ top strike and called its share \"of gross\".)* NIFTY 09:41: `22,700 · 10.8 % of gross · lead 1.7 pts`."),
 ("**List rows.** Net Γ · Flip · Corridor · Pin (γ-conc) · Priced move", "**List rows.** Net Γ · Flip · Corridor · Pin (gross γ) · Priced move"),
 ("the pin is a dotted γ-CONC rule, and the flip", "the pin is a dotted PIN rule, and the flip"),
 ("**\"pin state · this session · front leg\"** in market hours, or **\"pin state · previous session yyyy-mm-dd\"** before",
  "**\"net peak state · this session · front leg\"** in market hours, or **\"net peak state · previous session yyyy-mm-dd\"** before"),
 ("| **PIN (γ-conc)** | the strike with the largest share of gross \\|γ\\| | 22,700 · 10.8 % · dampening | Not a forecast of the close (S74). P1: high/low no closer to it than to random strikes (n = 85). |",
  "| **PIN (gross γ)** | the strike with the largest gross γ within 5 % of spot, with its share of that band | 22,700 · 10.8 % of band gross (illustrative) | Not a forecast of the close (S74). The P1 result (high/low no closer to it than to random strikes, n = 85) was measured on the earlier net-γ pin. \"call γ only\" or \"put γ only\" appears when the vendor gave a gamma for one leg only. |"),
 ("| **PIN STATE** | whether the leader has held through today's open 5-minute cycles: NO PIN · SHIFTING · STABLE · LOCKED |",
  "| **NET PEAK** | the strike with the largest net γ at the latest cycle, with \"= Pin\" or \"≠ Pin\" | 22,700 · = Pin (illustrative) | The earlier pin construction. Net γ depends on the two vendor leg gammas agreeing. The three tiles below are computed on this strike, not on the Pin. |\n| **NET PEAK STATE** | whether the net peak has held through today's open 5-minute cycles: NO PIN · SHIFTING · STABLE · LOCKED |"),
 ("| **CONVICTION** | lead clarity scaled by time to expiry |", "| **NET PEAK CONVICTION** | the net peak's lead clarity (1 − net #2 ÷ #1) scaled by time to expiry |"),
 ("| **RUNNER-UP** | the #2 strike and #2 ÷ #1 | 22,650 · #2/#1 = 0.84 | Near 1 means two strikes share the centre. Ranking is by \\|γ\\| only;",
  "| **RUNNER-UP** | the #2 strike by gross γ in the band, with its share | 22,650 · 9.1 % of band gross (illustrative) | The #2 ÷ #1 ratio is a net figure and now sits with Net peak conviction. Ranking is by gross γ only;"),
 ("| **LEAD** | #1 share − #2 share, in points |", "| **LEAD** | #1 share − #2 share of band gross, in points |"),
 ("| **LEADER TODAY** | each stretch with the same leader |", "| **NET PEAK TODAY** | each stretch with the same net peak |"),
 ("| **CONCENTRATION (HHI)** | the true Herfindahl index, Σ share², plus top-5 share |", "| **NET CONCENTRATION (HHI)** | the true Herfindahl index of net γ shares, Σ share², plus top-5 share |"),
 ("**The ladder: share of gross |γ|.**", "**The ladder: net γ share by strike (share of |net γ|).** The bars are on the net ranking, not the gross pin."),
 ("- **\"γ-CONC #1\"** and **\"#2\"** are outlined.", "- **\"PIN #1\"** and **\"#2\"** (the gross pin and its runner-up) are outlined, and a **\"NET PEAK\"** rule is drawn when the net peak is a different strike."),
 ("| **Top-strike share** | the largest strike's share of gross \\|γ\\| (max ÷ sum),", "| **Top-strike share** | the largest strike's share of \\|net γ\\| (max ÷ sum),"),
 ("| γ-conc (pin), Net-long γ, K98, **S\\*** | **dotted** | γ-CONC, NET-LONG γ |", "| Pin (gross γ), Net peak, Net-long γ, K98, **S\\*** | **dotted** | PIN, NET PEAK, NET-LONG γ |"),
 ("for example *\"PUT OI WALL ≡ γ-CONC\"*.", "for example *\"PUT OI WALL ≡ PIN\"*."),
 ("| **γ-conc / Pin** | the strike holding the largest share of gross \\|γ\\|. |",
  "| **Pin** | the strike with the largest gross γ among strikes within 5 % of spot (gross γ = one gamma per strike × call plus put OI). Until 2026-11-25 the Pin was the net-γ top strike, labelled γ-conc. |\n| **Net peak** | the strike with the largest net γ; pin state, conviction and net concentration are computed on it. |"),
]
PYEOF
cd "$W" && python3 - <<'PYEOF'
import sys; sys.path.insert(0,'.'); from edits_man import E
p='marketview_user_manual.md'; t=open(p,encoding='utf-8').read()
for o,n in E:
    k=t.count(o); assert k==1, (k,o[:80]); t=t.replace(o,n)
open(p,'w',encoding='utf-8').write(t); print("edits",len(E),"applied")
PYEOF
echo "5e5ad2482efb67bdf45e21159d07392f2a59141ecf2a7ab7841b433d737dc9d0  $W/marketview_user_manual.md" | sha256sum -c -
python3 "$W/build_help_pack.py" "$MC"
python3 - "$MC/public/help/manual.json" <<'PYEOF'
import json, sys
p = sys.argv[1]; s = open(p, encoding="utf-8").read(); j = json.loads(s)
assert j.get("manual_version", "").startswith("v0.6"), j.get("manual_version")
assert j.get("source_sha256") == "5e5ad2482efb67bdf45e21159d07392f2a59141ecf2a7ab7841b433d737dc9d0", j.get("source_sha256")
assert "NET PEAK" in s and "PIN (gross γ)" in s and "of band gross" in s
assert "2.6 PIN (γ-conc)" not in s
print("ok   manual.json is v0.6, built from the pinned source; markers present")
PYEOF
echo "   manual.json sha256 (record it; it depends on the box's markdown library, so it is not pinned here): $(sha256sum "$MC/public/help/manual.json" | cut -c1-64)"
cd "$MC" && git status --porcelain
echo "== MANUAL v0.6 BUILT in $MC/public/help/manual.json -- not committed. The edited source is $W/marketview_user_manual.md (engine copy owed at the S107 close)."
