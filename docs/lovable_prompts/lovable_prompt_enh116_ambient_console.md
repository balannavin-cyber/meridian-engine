# ENH-116 — Ambient Environment console (Marketview) — Lovable build prompt

**Paste this into the `meridian-connect` Lovable project.** It adds an **Ambient** view to the
existing MERDIAN Marketview (Vite + React + shadcn/ui + Tailwind, Supabase anon client already
configured via `import.meta.env.VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY`). Read-only; anon
`SELECT` is already granted on all three surfaces. Do **not** create a new Supabase project or
scaffold new tables — read the existing ones.

---

## What to build

A new top-level **Ambient** tab (or route `/ambient`) with **NIFTY** and **SENSEX** shown together.
Three stacked tiers per the reconciliation model. The governing design rule (ADR-017): **boring on
aligned days, loud on divergent ones** — when the lenses agree, the strip is muted; when one
diverges, its cell lights up and the verdict carries the caveat. Show **state and color, not
numbers**, up top; numbers are one glance below.

### Data sources (existing tables/view — read only)

**`market_environment_snapshots`** — the compiler's nightly verdict. Take the **latest row per
symbol**: filter `source = 'ambient_compiler_s62'`, order by `for_session_date desc, created_at desc`,
one row each for NIFTY and SENSEX. Columns used:
- Verdict: `ambient_regime` (TREND_UP|TREND_DOWN|RANGE|DISTRIBUTION|ACCUMULATION|UNSTABLE),
  `lens_alignment` (ALIGNED|DIVERGENT), `regime_conditional_note` (the base-rate receipt string),
  `session_prior` (full reconciled sentence), `for_session_date`, `as_of_date`.
- Gamma lens: `net_gex_regime` (POSITIVE_γ|NEGATIVE_γ|MIXED), `gex_regime_persistence_20d`,
  `concentration_trend_5d`, `max_gamma_strike_drift_5d`.
- Breadth lens: `price_vs_breadth_div` (CONFIRM|BEARISH_DIV|BULLISH_DIV|NEUTRAL), `wcb_slope_5d`,
  `pct_above_20dma_slope_5d`.
- Participant lens: `cycle_oi_call_put_asym`, `fii_index_fut_ls_delta_5d`, `pro_options_imbalance`
  (all three NULL together = stale board).
- Macro lens: `macro_tilt` (currently always NULL → render "pending").

**`v_expiry_base_rates`** — expiry-memory distribution. Match on the current row's
`(ambient_regime, lens_alignment)` and the upcoming `expiry_type`. Columns: `n`, `pinned_pct`,
`broke_up_pct`, `broke_down_pct`, `dominant_break` (UP|DOWN|MIXED), `avg_abs_settle_pct`,
`avg_range_pct`.

---

### Tier 1 — The Ambient Verdict (headline, always visible, top)

Per symbol, one large line: the `ambient_regime` as the headline word, a pill for `lens_alignment`
(ALIGNED = calm/neutral color, DIVERGENT = amber/alert), and the `regime_conditional_note` receipt
beneath in smaller text. Example rendered shape:

> **NIFTY — UNSTABLE** · lenses ALIGNED
> *WEEKLY: no prior expiries at UNSTABLE/ALIGNED*

The receipt text comes verbatim from `regime_conditional_note` (it already formats itself, including
"insufficient N" / "no prior expiries" honesty). If that column is null, show "—".

### Tier 2 — The Four-Lens Strip (the receipts, one glance below)

Four cells side by side: **Gamma · Breadth · Participant · Macro**. Each cell = a short state label +
color. The critical visual is **alignment vs divergence**, legible in half a second:

- **Gamma:** `net_gex_regime` → "LONG-γ CAGE" (POSITIVE_γ) / "SHORT-γ AMPLIFY" (NEGATIVE_γ) / "MIXED".
  Muted teal for long-γ (stabilizing), amber for short-γ (amplifying).
- **Breadth:** `price_vs_breadth_div` → "CONFIRMING" (CONFIRM) muted / "NARROWING — bearish div"
  (BEARISH_DIV) lit red / "IMPROVING — bullish div" (BULLISH_DIV) lit green / "NEUTRAL" muted.
- **Participant:** derive a one-line tilt from the three fields — e.g. `fii_index_fut_ls_delta_5d < 0`
  → "FII shedding longs", `cycle_oi_call_put_asym < 0` → "put-floor" / `> 0` → "call-ceiling",
  `pro_options_imbalance > 0` → "Pro call-lean". If all three null → "stale board" (grey, per the
  ADR-018 recency guard). Lit only when it disagrees with the verdict direction.
- **Macro:** `macro_tilt` null → "pending" (permanently muted for now).

Coloring rule tied to `lens_alignment`: when the verdict is **ALIGNED**, keep the whole strip muted
(no news, trust the structure). When **DIVERGENT**, light the cell(s) that disagree in amber/red and
leave the rest muted — the diverging cell is the signal. Never a wall of colored cells.

### Tier 3 — Expiry Memory (the distribution, below the strip)

For the matched `v_expiry_base_rates` cell: a small horizontal stacked bar — `pinned_pct` /
`broke_up_pct` / `broke_down_pct` — with `N` and `dominant_break` labeled, plus `avg_abs_settle_pct`
and `avg_range_pct` as secondary text. If `N` is low or no cell matches, render "insufficient history
(N=x)" rather than a misleading bar. This tier is the expiry-memory receipt — honest about thin N.

---

## Auto-refresh (required)

**Poll both queries every 60 seconds**, aligned to the 1-minute spot-capture cadence so the Ambient
view updates in lockstep with the rest of Marketview. Use a `setInterval(fetch, 60000)` in a
`useEffect` (clear on unmount); no websockets, no browser storage. Show a small **"updated Ns ago"**
ticker that counts up and resets on each successful fetch (ADR-017 motion-over-timestamps — the
motion, not the timestamp, tells the operator it's live). The ambient data itself only changes
twice a day (evening compile + at-open reconcile), so most polls return the same row — that's
expected; the poll keeps it consistent with the minutely dashboard and catches the two daily updates
within a minute.

## Design constraints

- shadcn/ui + Tailwind, match the existing Marketview visual language (same card/typography system).
- Atomic — each tier answers one question; do not merge into a paragraph Hero (ADR-017 P1).
- Read-only. No inserts/updates. No new tables. Reuse the existing Supabase client.
- Empty/null states render honestly ("—", "pending", "stale board", "insufficient history"), never
  fabricated values.

## Deploy (after Lovable iteration, unchanged pipeline)

Ships via Lovable → GitHub `meridian-connect` → AWS nginx:

```
cd ~/meridian-connect && git pull && npm install && npm run build && sudo rsync -av --delete dist/ /var/www/marketview/ && sudo systemctl reload nginx
```
