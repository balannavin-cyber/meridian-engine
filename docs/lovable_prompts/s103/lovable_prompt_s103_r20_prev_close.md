# Lovable prompt — S103 round 3: previous close from `v_close_print` (R20 / S103-J)

Base: `main` at `2f3c2f0` (= live). Ruling S103-J (2026-10-30 21:05 IST, `claude/rulings_s103.md`). TD-S97-NEW-13.
The view `public.v_close_print` is live (anon SELECT; `claude/2026-10-30_s103_v_close_print.sql`, T1–T3 PASS 21:36 IST).

Paste everything below the line into Lovable, on `main`.

---

Make exactly the 1 replacement below, in exactly one file: `src/lib/board.ts`. The OLD text appears in that file exactly once;
replace it with the NEW text verbatim.

Rules:
- Change nothing else. Do not touch any other file, any formatter, any hook, any other data read, any query key.
- Commit directly to `main` with the message: `S103-J: previous close read from v_close_print (16:00 print first, the reconciler's close as the fallback)`.

### R1. `src/lib/board.ts` — `useOpenGap`: the previous-close read

OLD:
```
        const { data: pc } = await mss().eq("source_table", "dhan_idx_i")
          .gte("ts", istAt(prev, "16:00")).lt("ts", istAt(prev, "16:10"))
          .order("ts", { ascending: true }).limit(1).maybeSingle();
```
NEW:
```
        // S103-J: v_close_print ranks the 16:00 dhan_idx_i print (1) above the 08:50 reconciler's 15:29 close (2), so a failed
        // 16:00 capture (10-21) no longer reads "prev close missing"; the 16:00 print still wins whenever it exists.
        const { data: pc } = await supabase.from("v_close_print").select("spot").eq("symbol", s)
          .gte("ts", istAt(prev, "15:00")).lt("ts", istAt(prev, "16:10"))
          .order("close_rank", { ascending: true }).order("ts", { ascending: true }).limit(1).maybeSingle();
```

---

## Operator notes (not for Lovable)

- **Effect:** none on any normal day (the 16:00 print is rank 1 and equals what the board read before — T1: 16 of 16 normal rows identical). On a day whose 16:00 capture failed, the board uses the reconciler's 15:29 close instead of "prev close missing" (10-21: NIFTY 22,811.35, SENSEX 73,709.69). No wording changes; the fallback is not labelled on the board (the view carries `source_table`; the 15:29 row's accuracy against the official close could not be checked on 10-21 because the chain run was also missing that day).
- **Reads before promote (staging, Chrome):** Home and Board for NIFTY and SENSEX: the change line under spot (`+x · +y %`) and the Board's open-gap tile read as on live (prev close = Thursday's 22,936.75 → today's 23,053.1 session shows `+116.3 · +0.51 %` as live does). The fallback branch has no live case until the next failed 16:00 capture; it is proven by T1 (the view returns the fallback row) and by this edit being the only change.
- **Guard:** `mv_lovable_guard_s103r20.sh 2f3c2f0` (allowlist = `src/lib/board.ts`, exactly 1 path; exactly one added `.from(` and it names `v_close_print`; fingerprint: `v_close_print` ×1, `close_rank` ≥ 1, the old `istAt(prev, "16:00")` gone).
- Closes TD-S97-NEW-13 (R20) at the next live read.
