# Lovable prompt — S102 / ADR-032 D1 round 2: legacy pages state Γ in ₹ Cr per 1 % move

Base: `main` at `8326ed0`. Operator ruling 2026-10-30 09:43 IST: legacy pages **rescale** (not retire).

Paste everything below the line into Lovable, on `main`.

---

Make exactly the 10 replacements below, in exactly two files: `src/lib/queries.ts` and `src/marketview/sections.tsx`.
Each OLD text appears in the file exactly the number of times stated; replace it with the NEW text verbatim.

Rules:
- Change nothing else. Do not touch any other file, any formatter (`fmtNum`, `fmtSigned`, `fmtPct`), `src/marketview/state.ts` or `src/marketview/ui.tsx`.
- Do not add or remove any other data read. The only new reads are of the views `v_gamma_metrics_1pct` and `v_gex_strike_snapshots_1pct`, which already exist.
- The two remaining `.from("gamma_metrics")` reads that select only `ts, spot, straddle_atm` / `ts, straddle_atm` stay as they are.
- Commit directly to `main` with the message: `S102 ADR-032 D1 round 2: legacy pages read the _1pct views; Γ in ₹ Cr per 1 % move`.

### R1. `src/lib/queries.ts` — replace the one occurrence

OLD:
```
      const { data, error } = await supabase
        .from("gamma_metrics")
        .select("*")
        .eq("symbol", symbol)
        .order("ts", { ascending: false })
        .limit(1)
        .maybeSingle();
      if (error) throw error;
      return data;

```
NEW:
```
      const { data, error } = await supabase
        .from("v_gamma_metrics_1pct")
        .select("*")
        .eq("symbol", symbol)
        .order("ts", { ascending: false })
        .limit(1)
        .maybeSingle();
      if (error) throw error;
      // S102 ADR-032 D1: net_gex carries the per-1 % value (net_gex_1pct) on the legacy pages.
      return data ? { ...(data as any), net_gex: (data as any).net_gex_1pct } : data;

```

### R2. `src/lib/queries.ts` — replace every one of the 3 occurrences

OLD:
```
.from("gex_strike_snapshots")
```
NEW:
```
.from("v_gex_strike_snapshots_1pct")
```

### R3. `src/lib/queries.ts` — replace the one occurrence

OLD:
```
.select("strike, gex_cr, oi_call, oi_put, spot")
```
NEW:
```
.select("strike, gex_cr_1pct, oi_call, oi_put, spot")
```

### R4. `src/lib/queries.ts` — replace the one occurrence

OLD:
```
      if (error) throw error;
      return data ?? [];
    },
  });
}

export function usePinZone
```
NEW:
```
      if (error) throw error;
      // S102 ADR-032 D1: gex_cr carries the per-1 % value (gex_cr_1pct) on the legacy pages.
      return (data ?? []).map((r: any) => ({ ...r, gex_cr: r.gex_cr_1pct }));
    },
  });
}

export function usePinZone
```

### R5. `src/lib/queries.ts` — replace the one occurrence

OLD:
```
        .from("gamma_metrics")
        .select("ts, spot, pin_risk_score, straddle_atm, expansion_probability, net_gex")
```
NEW:
```
        .from("v_gamma_metrics_1pct")
        .select("ts, spot, pin_risk_score, straddle_atm, expansion_probability, net_gex_1pct")
```

### R6. `src/lib/queries.ts` — replace the one occurrence

OLD:
```
      if (error) return [];
      return data ?? [];
    },
  });
}
```
NEW:
```
      if (error) return [];
      // S102 ADR-032 D1: net_gex carries the per-1 % value (net_gex_1pct) on the legacy pages.
      return (data ?? []).map((r: any) => ({ ...r, net_gex: r.net_gex_1pct }));
    },
  });
}
```

### R7. `src/marketview/sections.tsx` — replace the one occurrence

OLD:
```
    { label: "NET γ", value: s.netDealerGamma != null ? `${fmtSigned(s.netDealerGamma)} Cr` : "—",

```
NEW:
```
    { label: "NET γ", value: s.netDealerGamma != null ? `${fmtSigned(s.netDealerGamma)} Cr` : "—", sub: "₹ Cr per 1 % move",

```

### R8. `src/marketview/sections.tsx` — replace the one occurrence

OLD:
```
`Σdmp ${fmtNum(s.dampenTotal)}k · Σamp ${fmtNum(s.amplifyTotal)}`
```
NEW:
```
`Σdmp ${fmtNum(s.dampenTotal)} · Σamp ${fmtNum(s.amplifyTotal)} · ₹ Cr per 1 % move`
```

### R9. `src/marketview/sections.tsx` — replace the one occurrence

OLD:
```
subtitle={`dampening (long γ) vs amplifying (short γ) · σ-band to expiry · ${s.strikes.data?.length ?? 0} strikes`}
```
NEW:
```
subtitle={`dampening (long γ) vs amplifying (short γ) · ₹ Cr per 1 % move · σ-band to expiry · ${s.strikes.data?.length ?? 0} strikes`}
```

### R10. `src/marketview/sections.tsx` — replace the one occurrence

OLD:
```
subtitle={`Cr · positive = dampening flows · negative = amplifying flows`}
```
NEW:
```
subtitle={`₹ Cr per 1 % move · positive = dampening flows · negative = amplifying flows`}
```

---

## Operator notes (not for Lovable)

- Effect: Snapshot NET γ, Dealer γ Σdmp/Σamp, Hero bars, Pin peak, Σ dampen/amplify scalars and the Net γ intraday line on the legacy pages fall 100× and gain "per 1 % move". `state.ts` / `ui.tsx` are unchanged: the hooks hand them per-1 % values under the old field names.
- "Σdmp …k" was a mislabel (values were Cr, not thousands) — fixed in R8.
- Rehearsed at `8326ed0` in a scratch clone: anchors 10/10 at the stated counts, `tsc --noEmit` clean, `vite build` OK.
- Guard: `bash ~/mv_lovable_guard_s102b.sh 8326ed0` (sha256 `00767d959b36406dcc8ee12b4337e2fe4d9ef167b7c34076c06ff0d6dd7bab80`); rehearsed PASS, negative control (one raw read + `k` left) FAIL ×4.
