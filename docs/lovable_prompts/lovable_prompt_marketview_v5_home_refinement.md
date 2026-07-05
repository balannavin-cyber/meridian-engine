# Marketview v5 — Home refinement — Lovable prompt

**Paste into the same `meridian-connect` Lovable project** (iterating on the restructured Terminal).
Three fixes to the **Home — Ambient** page. Read-only, existing tables, existing client.

---

## 1. Surface the open-vs-settled "SHIFT" line (the reconciler's read)

The ambient verdict is computed at the **prior close** for the upcoming session; the pre-market
reconciler then compares it to the **open** and records whether the open confirms or shifts it. That
comparison already exists in the `market_environment_snapshots.session_prior` string but isn't shown,
so today's genuine overnight regime flip (NIFTY was NEGATIVE_γ at settle, POSITIVE_γ at open) reads
like two panels disagreeing instead of the signal it is.

`session_prior` has two parts joined by the literal delimiter `"  ||  "` (two spaces, `||`, two spaces):
- **compute part** (always present): e.g. `UNSTABLE · lenses ALIGNED · gamma NEGATIVE_γ · breadth NEUTRAL/NEUTRAL · participant NEUTRAL · (L4 pending)`
- **relate part** (present after the ~09:25 reconciler runs), a segment starting with `OPEN `: e.g. `OPEN SHIFTS: settled NEGATIVE_γ vs open POSITIVE_γ pin 24500 flip 24450 -> prior weakened — regime moved overnight`

Parse it: `const relate = session_prior.split("  ||  ").find(s => s.startsWith("OPEN "))`.

Render the relate line as a distinct callout inside the Ambient Verdict block, directly under the
regime/alignment:
- If it contains `SHIFTS` → **highlight** it (amber banner, e.g. "⚠ OPEN SHIFT — dealers re-caged
  overnight; trust the settled verdict less today"), using the text after `OPEN SHIFTS:` verbatim.
- If it contains `CONFIRMS` → show it **muted** (e.g. "open confirms the prior").
- If there's no `OPEN ` segment yet → show nothing (reconciler hasn't run for the session).

## 2. Label the ambient block as prior-close, distinct from the live blocks

The contradiction operators are seeing is a **time** mismatch, not a data error: the Ambient Verdict +
Four-Lens Strip are the **settled read** (`as_of_date`, the prior close) computed **for** this session
(`for_session_date`); the top snapshot strip and Key Parameters are **live intraday**. Make that
explicit so a settled-vs-live difference reads as information, not conflict:
- Under the "AMBIENT VERDICT" heading, replace the small "session ####" tag with:
  **`AS-OF {as_of_date} close → FOR {for_session_date} session`** (from the row's own columns).
- Add a subtle **`LIVE`** tag on the snapshot strip and on the Key Parameters "REGIME" / "NET DEALER γ"
  cards, so the operator reads the strip regime (live now) and the ambient regime (settled) as two
  clocks, not a disagreement.

## 3. Four-Lens Strip — mute on ALIGNED, light only on divergence

The strip currently colors each cell by its own value (reds/ambers everywhere), which defeats the
half-second divergence read — an ALIGNED day looks identical to a divergent one. The alarm color must
be driven by **`lens_alignment`**, not per-cell values (ADR-017: boring on aligned, loud on divergent):
- **`lens_alignment = ALIGNED`** → render the **entire strip muted/neutral** (state text still shows —
  NEGATIVE_γ, NEUTRAL, −0.1057, etc. — but in the calm/grey style, no red/amber).
- **`lens_alignment = DIVERGENT`** → light **only the Breadth and Participant cells** (the directional
  pair the verdict reconciles) in amber/red; keep Gamma and Macro muted.

Keep the cell **state labels and values** exactly as they are; this changes only the alarm styling.
Result: today's ALIGNED NIFTY/SENSEX strips go calm, and a genuinely divergent day will stand out
because the Breadth/Participant cells light while the rest stay quiet.

---

Deploy unchanged: `cd ~/meridian-connect && git pull && npm install && npm run build && sudo rsync -av --delete dist/ /var/www/marketview/ && sudo systemctl reload nginx`.
