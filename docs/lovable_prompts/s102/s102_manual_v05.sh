#!/usr/bin/env bash
# s102_manual_v05.sh — S102 / ADR-032 D1: build manual v0.5 (Γ in ₹ Cr per 1 % move) into ~/meridian-connect/public/help/manual.json.
# Reads the engine source read-only from ~/meridian-engine; edits a copy in /tmp/s102man; never touches the engine tree; never commits.
set -euo pipefail
ENG="${ENG:-$HOME/meridian-engine}"; MC="${MC:-$HOME/meridian-connect}"; W=/tmp/s102man
rm -rf "$W"; mkdir -p "$W"
cp "$ENG/docs/marketview_manual/marketview_user_manual.md" "$ENG/docs/marketview_manual/build_help_pack.py" "$W/"
echo "0f103a58860eec774e8126b21027b5091ed7eea47f51eb4b7bac7a85136e95cb  $W/marketview_user_manual.md" | sha256sum -c -
echo "2c93bd1652b7a17d86fd0873c6b91eddde71d12d9f5c325858390e6de4aa2771  $W/build_help_pack.py" | sha256sum -c -
cat > "$W/edits_man.py" <<'PYEOF'
"""S102 ADR-032 D1 — manual v0.4 -> v0.5: Γ sizes restated in ₹ Cr per 1 % move. Canon-v3: each old must occur exactly once."""
L58_NEW = ('**Gamma** is how fast delta itself changes as the index moves. It is largest for strikes near spot and close to expiry. '
 'The board weights each strike\'s gamma by its OI and writes the result as **γ exposure**, in **₹ Cr per 1 % move**: roughly, '
 'the rupees of index exposure that would have to be re-hedged if the index moved 1 % (ADR-032 D1, from 2026-10-30; until then the '
 'board showed 100 × this figure under "unit definition pending"). It is not normalised for time to expiry — the parity target also '
 'scales it by √(τ / 5 d) — so across days compare its **sign** and its **share of the total**, not its size.')
E = [
 ("| Manual version | v0.4 (draft) |", "| Manual version | v0.5 (draft) |"),
 ("are checked on 2026-10-26. |",
  "are checked on 2026-10-26. v0.5 (2026-10-30, ADR-032 D1): every Γ size is restated in ₹ Cr per 1 % move. Figures quoted from earlier passes are divided by 100 and marked ≈ where the board had rounded them; **the screenshots still show the earlier scale** (100 × larger). |"),
 ('"band not measured", "unit definition pending", "not built"', '"band not measured", "not built"'),
 ("LINE58", L58_NEW),
 ("across every strike of the latest γ run, in ₹ Cr. The unit is still open.",
  "across every strike of the latest γ run, in ₹ Cr per 1 % move (ADR-032 D1). The sub-line ends \"₹ Cr per 1 % move\"."),
 ("NIFTY 09:41 showed `+9.2L Cr · long γ · 0.10 of gross`. At 09:00 the same symbol showed `−13.9L Cr · short γ · −0.23 of gross`, so the sign flipped across the open. SENSEX 09:40 showed `+5,444 Cr · long γ · 0.00 of gross`: positive, but so small against gross that the ratio rounds to 0.00. Treat that as balanced.",
  "NIFTY 09:41 (2026-10-12) read `+9,201 Cr · long γ · 0.10 of gross` on today's scale (then shown as +9.2L Cr). At 09:00 the same symbol read `−13,886 Cr · short γ · −0.23 of gross`, so the sign flipped across the open. SENSEX 09:40 read `+54 Cr · long γ · 0.00 of gross` (then +5,444 Cr): positive, but so small against gross that the ratio rounds to 0.00. Treat that as balanced. On 2026-10-30 SENSEX at 10:10 read `−256 Cr · short γ · -0.03 of gross · ₹ Cr per 1 % move`."),
 ("The size has no agreed unit (E-D1), so do not compare magnitudes across days.",
  "The size is not normalised for time to expiry (the parity target scales by √(τ / 5 d)), so compare sign and net/gross across days, not magnitude."),
 ("`v_gex_abs_exposure.net_gex_cr`; net/gross = `net_gex_cr ÷ abs_gex_cr`.",
  "`v_gex_abs_exposure_1pct.net_gex_cr_1pct` (= `net_gex_cr` × 0.01; the stored γ·OI·S²/1e7 is per 100 % move, ADR-032); net/gross = net ÷ gross."),
 ("with +78,596 on its row, put OI wall ≡ γ-conc at 72,000 with −88,006.",
  "with +786 on its row (then shown as +78,596), put OI wall ≡ γ-conc at 72,000 with −880 (then −88,006). Row values are ₹ Cr per 1 % move."),
 ("| SENSEX 09:00: 10.5L Cr | Unit pending (E-D1); compare within a day. |",
  "| SENSEX 09:00: ≈ 10,500 Cr per 1 % move (then shown as 10.5L Cr) | Not normalised for time to expiry; compare within a day, not magnitudes across days. |"),
 ("SENSEX 09:00: −4.5L Cr · amplifying", "SENSEX 09:00: ≈ −4,500 Cr (then −4.5L Cr) · amplifying"),
 ("| sparkline of net γ at each run today |", "| sparkline of net γ at each run today, in ₹ Cr per 1 % move |"),
 ("The book was long γ (+9.2L Cr), so the model buys on falls and sells on rises.",
  "The book was long γ (+9,201 Cr per 1 % move, then shown as +9.2L Cr), so the model buys on falls and sells on rises. Since 2026-10-30 the hedge and Net Γ show the same number, because flow = −net Γ × move."),
 ("*Caveats:* the unit is pending (E-D1). \"L3 flip",
  "*Caveats:* the hedge has always been per 1 % move (`flow_cr = −net_gex × move`); the tile now reads plain \"₹ Cr\". \"L3 flip"),
 ("∂Γ/∂t **−4.7L Cr / 40.5L Cr · ratio −0.12**; ∂Γ/∂σ **+60,256 Cr / 5.3L Cr · ratio 0.11**.",
  "∂Γ/∂t **≈ −4,700 Cr / ≈ 40,500 Cr · ratio −0.12**; ∂Γ/∂σ **+603 Cr / ≈ 5,300 Cr · ratio 0.11** (then shown as −4.7L / 40.5L and +60,256 / 5.3L). On 2026-10-30 (SENSEX, chain 10:15): ∂Γ/∂t **−102 Cr / 653 Cr · ratio −0.16**; ∂Γ/∂σ **−13 Cr / 507 Cr · ratio −0.02**. Units: ₹ Cr per 1 % move, per calendar day and per +1 IV point."),
 ("- NET Γ in full digits, e.g. \"-13,81,560.7 Cr\";",
  "- NET Γ in ₹ Cr per 1 % move, with that unit on its sub-line, e.g. \"+1,569.67 Cr\" (NIFTY, 2026-10-30 10:10; before 2026-10-30 it read 100 × larger, e.g. \"-13,81,560.7 Cr\");"),
 ("| **unit definition pending** / **unit pending (E-D1)** | Net Γ, Gross \\|Γ\\|, Hedge per 1 % | The size of this number has no agreed real-world unit yet. Compare signs and shares, not magnitudes across days. |",
  "| **₹ Cr per 1 % move** | Net Γ, Gross \\|Γ\\|, the ladder, ∂Γ/∂t, ∂Γ/∂σ, 3D, the legacy NET Γ | Rupees of index exposure re-hedged per 1 % move (ADR-032 D1, 2026-10-30). Not normalised for time to expiry; compare signs and shares across days, not magnitudes. Until 2026-10-30 these tiles read \"unit definition pending\" and showed 100 × this figure. |"),
 ("Height is |net γ| per strike at each session's settled run.",
  "Height is |net γ| per strike (₹ Cr per 1 % move) at each session's settled run; the label reads \"peak |γ| ₹ … Cr per 1 % move\"."),
]
PYEOF
cd "$W" && python3 - <<'PYEOF'
import sys; sys.path.insert(0,'.'); from edits_man import E
p='marketview_user_manual.md'; t=open(p,encoding='utf-8').read()
l58=[l for l in t.split('\n') if l.startswith('**Gamma** is how fast delta itself changes')]; assert len(l58)==1
for o,n in E:
    if o=="LINE58": o=l58[0]
    k=t.count(o); assert k==1, (k,o[:70]); t=t.replace(o,n)
open(p,'w',encoding='utf-8').write(t); print("edits",len(E),"applied")
PYEOF
echo "e4872ab61e9c86e134bd66f3caaf0d20166030c48a8bf873febaf0e3e3b26e7c  $W/marketview_user_manual.md" | sha256sum -c -
python3 "$W/build_help_pack.py" "$MC"
echo "ede04e14d990bf54e8eaf24f60e062c1ec423e6c6204591b0bbfea4f0d7c4481  $MC/public/help/manual.json" | sha256sum -c -
cd "$MC" && git status --porcelain
echo "== MANUAL v0.5 BUILT — not committed"
