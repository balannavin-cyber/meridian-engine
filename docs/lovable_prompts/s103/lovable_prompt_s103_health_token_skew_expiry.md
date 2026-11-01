# Lovable prompt — S103 round 1: Health token tile scored daily (S103-A); Context IV skew on expiry day (S103-C)

Base: `main` at `30998f2` (= live). Rulings S103-A and S103-C (2026-10-30 17:21 IST, `claude/rulings_s103.md`).

Paste everything below the line into Lovable, on `main`.

---

Make exactly the 5 replacements below, in exactly three files: `src/pages/Health.tsx`, `src/marketview/state.ts`,
`src/marketview/sections.tsx`. Each OLD text appears in its file exactly once; replace it with the NEW text verbatim.

Rules:
- Change nothing else. Do not touch any other file, any formatter, any data read (`supabase.from(...)`), any hook.
- Commit directly to `main` with the message: `S103-A/C: Health token tile scored like the daily writers; Context IV skew says SKIPPED_EXPIRY on a 0-DTE front leg and shows the next leg`.

### R1. `src/pages/Health.tsx` — the token tile uses the daily-writer scale (S103-A)

OLD:
```
  } else if (tokenProbeHttp === 200 && tokenProbeAge != null && tokenProbeAge <= 30) {
    tokenStatus = "green";
  } else if (tokenProbeHttp === 200) {
    tokenStatus = "amber";
```
NEW:
```
  } else if (tokenProbeHttp === 200 && tokenProbeAge != null) {
    // S103-A: the probe is written once a day (08:20 IST refresh), so it is scored on the daily
    // writers' scale (statusFor with a 1440-min cadence: green <= 2 d, amber <= 4 d), not on 30 min.
    tokenStatus = statusFor(tokenProbeAge, 1440);
  } else if (tokenProbeHttp === 200) {
    tokenStatus = "amber";
```

### R2. `src/marketview/state.ts` — expose the front leg's status and the next leg's skew (S103-C)

OLD:
```
  const ivSkew98 = skewRow?.leg_skew_98 != null ? Number(skewRow.leg_skew_98) : null;
  const ivK98 = skewRow?.leg_k98 != null ? Number(skewRow.leg_k98) : null;
```
NEW:
```
  const ivSkew98 = skewRow?.leg_skew_98 != null ? Number(skewRow.leg_skew_98) : null;
  const ivK98 = skewRow?.leg_k98 != null ? Number(skewRow.leg_k98) : null;
  // S103-C: on a 0-DTE front leg the view sets leg_status = 'SKIPPED_EXPIRY' and leg_skew_98 = NULL by design
  // (skew is not comparable across expiries), so the card says so and shows the NEXT leg's skew, tagged.
  const ivSkewStatus = (skewRow?.leg_status as string | undefined) ?? null;
  const nextLegNo = frontLeg != null ? Math.min(...ivSurf.map((r) => Number(r.leg)).filter((l) => l > (frontLeg as number)), Infinity) : Infinity;
  const nextLegRow = Number.isFinite(nextLegNo) ? (ivSurf.find((r) => Number(r.leg) === nextLegNo) ?? null) : null;
  const ivNextSkew98 = nextLegRow?.leg_skew_98 != null ? Number(nextLegRow.leg_skew_98) : null;
  const ivNextK98 = nextLegRow?.leg_k98 != null ? Number(nextLegRow.leg_k98) : null;
  const ivNextExpiry = (nextLegRow?.expiry_date as string | undefined) ?? null;
```

### R3. `src/marketview/state.ts` — return them

OLD:
```
    ivSmile, ivSkew98, ivK98, zonesNearSpot, maxPainStrike, painSpotDistPct, gammaPainGap,
```
NEW:
```
    ivSmile, ivSkew98, ivK98, ivSkewStatus, ivNextSkew98, ivNextK98, ivNextExpiry, zonesNearSpot, maxPainStrike, painSpotDistPct, gammaPainGap,
```

### R4. `src/marketview/sections.tsx` — the big value on expiry day

OLD:
```
              {s.ivSkew98 == null ? "—" : `${s.ivSkew98 > 0 ? "+" : ""}${s.ivSkew98.toFixed(1)} vol pts`}
```
NEW:
```
              {s.ivSkew98 == null ? (s.ivSkewStatus === "SKIPPED_EXPIRY" ? "SKIPPED_EXPIRY" : "—") : `${s.ivSkew98 > 0 ? "+" : ""}${s.ivSkew98.toFixed(1)} vol pts`}
```

### R5. `src/marketview/sections.tsx` — the sub-line: why, and the next leg tagged with its expiry

OLD:
```
              {s.ivSkew98 == null ? "—" : `@ K98 ${s.ivK98 != null ? fmtNum(s.ivK98, { maximumFractionDigits: 0 }) : "—"} · front leg · from view`}
```
NEW:
```
              {s.ivSkew98 != null
                ? `@ K98 ${s.ivK98 != null ? fmtNum(s.ivK98, { maximumFractionDigits: 0 }) : "—"} · front leg · from view`
                : s.ivSkewStatus === "SKIPPED_EXPIRY"
                  ? `front leg expires today · next leg ${s.ivNextExpiry ?? "—"}: ${s.ivNextSkew98 == null ? "—" : `${s.ivNextSkew98 > 0 ? "+" : ""}${s.ivNextSkew98.toFixed(1)} vol pts @ K98 ${s.ivNextK98 != null ? fmtNum(s.ivNextK98, { maximumFractionDigits: 0 }) : "—"}`}`
                  : "—"}
```

---

## Operator notes (not for Lovable)

- **S103-A effect:** Health TOKEN STATUS is green for a 200 probe up to 2 days old, amber to 4 days, red beyond or on any failure row; OVERALL stops reading DEGRADED on a healthy fleet (TD-S101-NEW-13). `statusFor` already exists in the file (used at lines 314 and 329).
- **S103-C effect:** on an expiry day the Context IV Skew card reads `SKIPPED_EXPIRY` with the sub-line `front leg expires today · next leg <date>: <skew> vol pts @ K98 <strike>`; every other day it is unchanged (TD-S101-NEW-14). No data read added — the surface rows already carry `leg_status`, `expiry_date` and the next leg.
- **Reads before promote (staging, Chrome):** Health → TOKEN STATUS green with the probe's age shown in hours, OVERALL green when the fleet is green. Context (NIFTY) → on a non-expiry day the card is byte-identical to live; the expiry-day branch is read on the next NIFTY expiry (Tuesday 2026-11-03 is the next weekly expiry — read it that day before 15:30 IST).
- **Guard:** `mv_lovable_guard_s103.sh 30998f2` (allowlist = these three files; no new `.from(`; fingerprint: `statusFor(tokenProbeAge, 1440)` in Health.tsx, `SKIPPED_EXPIRY` ×2 in sections.tsx, `ivNextSkew98` in both state.ts and sections.tsx; the old `<= 30` test gone).
- Not in this round: **S103-B** (board-side leg roll after the expiry-day close) — it touches the leg selection in four hooks (`useLadderStrikes`, `latestBySymbol` on `v_gex_abs_exposure_1pct`, the river, the greeks) and the session-state strip; its own prompt after a read of those hooks.
