# Marketview v5 — restructure into a multi-page terminal — Lovable build prompt

**Paste into the `meridian-connect` Lovable project.** This restructures the existing single-scroll
Marketview into a navigable multi-page terminal and makes four specific changes. **Reorganize and
modify existing wired components — do not rebuild data wiring or scaffold new tables.** Reuse the
existing Supabase anon client (`VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY`). Read-only.

The mental model: the current page shows everything at once, which forces the operator to hunt. A
trading desk separates the **environment read** (home) from the **drill-downs**, one question per
page, reachable from a persistent left sidebar. Below is the information architecture and the four
changes.

---

## 1. Left-sidebar navigation — break the single page into pages

Add a persistent **left rail** (shadcn sidebar, collapsible) with these pages. A **global NIFTY /
SENSEX toggle** lives at the top of the rail and persists across every page (one selected symbol
drives all pages). Route each page; default route is **Home**.

- **Home — Ambient** *(new landing page; see §2)*
- **Positioning** — the gamma/dealer view: net dealer gamma (§4), flip level, PIN / ACCEL zones,
  gamma-by-strike histogram, pin risk score, ATM straddle. (Move the existing GEX/positioning cards here.)
- **Max Pain / OI** — max pain (§3) + OI call/put walls. (Move the existing max-pain card here.)
- **Breadth** — WCB, market breadth, % > 10/20/40 DMA, advances/declines, India VIX, IV skew.
  (Move the existing breadth/VIX/IV cards here.)
- **Structure — ICT** — ICT HTF zones, PDH/PDL, the signals stream. (Move the existing ICT + signals cards here.)
- **Expiry Memory** — the full `v_expiry_base_rates` distribution + recent `expiry_outcomes` history table.
- **Calibration** — the existing Settings / `merdian_parameters` console.
- **Health** — the existing `/health` dashboard (link or embed).

Each page keeps the components it already has; this is a move + group operation. Nothing loses its
data source. Keep the existing card/typography system so pages feel like one product.

---

## 2. Home — Ambient (the landing page)

Home is the ENH-116 ambient read plus a compact market snapshot. Top to bottom:

**(a) Market snapshot strip** — a thin row for the selected symbol: **Spot**, **Futures**, **Gap**
(session open vs prior settlement, shown as pts and %, green up / red down), and **Day range**
(high–low). Reuse the spot/futures the dashboard already reads (`gamma_metrics.spot`, the existing
index-futures snapshot the futures card uses); Gap = today's open minus prior close from the same
prev-close the breadth/marker layer already tracks. Keep it one glance — numbers, no charts.

**(b) The Ambient Verdict** *(Tier 1)* — from the latest `market_environment_snapshots` row for the
symbol (`source = 'ambient_compiler_s62'`, order `for_session_date desc, created_at desc`): the
`ambient_regime` as a large headline word, an `lens_alignment` pill (ALIGNED = calm, DIVERGENT =
amber), and `regime_conditional_note` verbatim beneath as the base-rate receipt (it self-formats,
incl. "insufficient N" / "no prior expiries"; null → "—").

**(c) The Four-Lens Strip** *(Tier 2)* — four cells, **Gamma · Breadth · Participant · Macro**, each a
short state label + color. **Boring on aligned, loud on divergent (ADR-017):** when
`lens_alignment = ALIGNED`, keep the whole strip muted; when `DIVERGENT`, light only the cell(s) that
disagree. State per lens:
- Gamma: `net_gex_regime` → "LONG-γ CAGE" (POSITIVE_γ, muted teal) / "SHORT-γ AMPLIFY" (NEGATIVE_γ, amber) / "MIXED".
- Breadth: `price_vs_breadth_div` → "CONFIRMING" muted / "NARROWING — bearish div" red / "IMPROVING — bullish div" green / "NEUTRAL" muted.
- Participant: derive a tilt line from `fii_index_fut_ls_delta_5d` (<0 "FII shedding longs"), `cycle_oi_call_put_asym` (<0 "put-floor" / >0 "call-ceiling"), `pro_options_imbalance` (>0 "Pro call-lean"). All three null → "stale board" (grey).
- Macro: `macro_tilt` null → "pending" (muted).

**(d) Expiry Memory** *(Tier 3)* — matched `v_expiry_base_rates` cell on `(ambient_regime,
lens_alignment)` + upcoming `expiry_type`: a stacked bar `pinned_pct / broke_up_pct / broke_down_pct`
with `N` + `dominant_break`; low/absent N → "insufficient history (N=x)", never a misleading bar.

---

## 3. Max Pain — show only 20 strikes each side

The max-pain distribution currently renders the full strike ladder, which is unreadable. **Limit it
to the 20 strikes above and 20 below the current spot** (≈40 strikes, centered on ATM) — NIFTY on the
50-pt grid, SENSEX on the 100-pt grid. Drop the long tail entirely; the pin dynamics live near ATM.
Same data source, just a windowed slice around spot before rendering.

---

## 4. Net dealer gamma — direction + intraday line, not a raw number

The absolute net-gamma Crore figure doesn't read. Replace the primary display with **direction and an
intraday chart**:

**(a) Trend read** — compare the latest cycle's `net_gex` to the **session-open** cycle (first cycle
after 09:15 IST today): **▲ RISING / ▼ FALLING / — FLAT**, with the change magnitude. Keep the raw Cr
value only as secondary/hover text; the headline is the direction.

**(b) Intraday line chart** — plot `net_gex` across today's `gamma_metrics` cycles for the selected
symbol, **x-axis 09:15 → 15:30 IST**, one line. **Mark the zero line prominently** — it's the
long-γ / short-γ regime boundary, so a crossing shows dealers flipping regime intraday, which is the
whole point of watching it move. Shade above-zero teal (cage) / below-zero amber (amplify). This
belongs on the Positioning page.

---

## Auto-refresh (all pages)

**Poll every 60 seconds**, aligned to the 1-minute spot-capture cadence, so the terminal updates in
lockstep. `setInterval(fetch, 60000)` in `useEffect`, cleared on unmount; no websockets, no browser
storage. Show a small **"updated Ns ago"** ticker that counts up and resets on each fetch (ADR-017
motion-over-timestamps). The intraday net-gamma line and the spot strip genuinely move minute to
minute; the ambient verdict changes only twice a day (evening compile + at-open reconcile) — same
poll catches both within a minute.

## Constraints

- shadcn/ui + Tailwind, existing Marketview visual language; each card answers one question (ADR-017 P1).
- Read-only. No inserts/updates, no new tables, reuse the existing client. This is restructure + four edits.
- Honest empty states ("—", "pending", "stale board", "insufficient history") — never fabricated numbers.

## Deploy (unchanged pipeline, after Lovable iteration)

```
cd ~/meridian-connect && git pull && npm install && npm run build \
  && sudo rsync -av --delete dist/ /var/www/marketview/ && sudo systemctl reload nginx
```
(`npm install`, not `npm ci`.)
