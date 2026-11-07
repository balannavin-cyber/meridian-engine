# Tape live L2: rebuild-cost options (analysis only, nothing built)

Sat 2026-11-07. Branch `tape/live-l0` at `0a1c681`. **No option below is built.** The operator rules.

## 1. What was measured (production box, 11-06 recorded-day replay, `nice -n 15`)

- Per-cycle time 4.5-12 s through the morning, 17-19 s after 14:35. A live cycle is 300 s.
- **The 14:35 cycle took 235.55 s.** `run_manifest.json` `rebuilds`: trigger `subscriptions`, at 875 (14:35), NIFTY
  **and** SENSEX.
- Peak writer memory 522 MB (max RSS 534,612 kB).

Measured here from `C:\tape_data` (read-only):

- **`subscriptions_143300.json` added 26 tokens, all SENSEX, and none for NIFTY.** No existing token's metadata
  changed, and there were 0 conflicts. Across 11-02..11-06, every token-map change after the first file was a pure
  addition: 09:01 on 11-03 (+26 SENSEX), 09:01 on 11-05 (+38 SENSEX), 14:33 on 11-06 (+26 SENSEX).
- Segment bytes before 14:30 on 11-06: NIFTY 67 files / 250,984 KiB; SENSEX 67 files / 253,491 KiB. That is about a
  50/50 split. Compressed bytes are only a stand-in for feed time; per-symbol rebuild time was not measured.

**Derived (stated as estimates).** The rebuild part of the 14:35 cycle is about 235.55 − ~17 (the ordinary cycle cost at
that hour) ≈ **218 s for both symbols, ≈ 73 % of a cycle**. Rebuild cost should grow with the number of segments fed
so far (`_rebuild_sym` re-feeds `order_segments(self.known[sym])`, every segment since 08:55). On that assumption, a map
change at 15:30 would rebuild about 80 instead of 67 files per symbol: ≈ 260 s + ~19 s ≈ **279 s, ≈ 93 % of the
cycle**, before S3 poll latency. The linearity is an assumption, not a measurement.

## 2. Which triggers force a rebuild (the prompt's claim, checked)

The claim "only the subscription change itself forces a rebuild" is **false**. `writer.py` has two triggers:

1. **Subscriptions** (`add_subscriptions:123-130`). It fires when `replay.build_token_map(self.subs)` differs from
   `self.meta` **and** some replay already exists (`if self.rp`). It sets `dirty`, and `_rebuild_all` runs at the next
   `add_segment` (`:141-143`) or at the start of the next `cycle` (`:199-200`). It rebuilds **every symbol with segments**
   (`_rebuild_all:181-183`), even though `SymbolReplay` keeps only its own symbol's tokens (`replay.py:170`). The 14:35
   NIFTY rebuild was therefore pure waste: NIFTY's filtered map did not change.
   - It does not fire on the 08:55 and 09:00 files: both are applied at t = 09:00 before the first segment, so `self.rp`
     is still empty.
   - It does fire on a 09:01 file (11-03, 11-05): available at 09:05, after `seg_0855` was fed. That rebuild is cheap
     because only two segments exist yet.
   - A change in `added_minutes` alone does **not** trigger a rebuild. `self.added` is read fresh in every `cycle`
     (`:205`) and is not carried state.
2. **Late or out-of-order segment** (`add_segment:144-146`). It fires when `(parse_seg_name(name), name) < self.last[sym]`:
   a segment that sorts before the last one fed for its symbol, including a `_cN` / `_rN` collision variant of a
   closed group. It rebuilds **that symbol only**. None of the three options below touches this trigger. On 11-06 it did
   not fire, but it would cost about half of the both-symbol figure.

Nothing else rebuilds. `bad_files` are recorded, not rebuilt. `add_segment` ignores a name it already knows (`:135`).

## 3. The options

Common to all three: the per-cycle `deepcopy(rp).finish()` plus the T1b recompute over the day so far is O(day), and it
is the 17-19 s that remains. No option changes it.

### Option A: extend the token map without a rebuild

**Change.** In `LiveDay.add_subscriptions`: compute the new map, then per symbol compare the filtered maps. If a symbol's
filtered map is unchanged, do nothing for it (this alone removes the 14:35 NIFTY rebuild). If it changed by **pure
addition** (every old token present with identical metadata) **and** no fed segment can already hold packets of the
new tokens, extend that symbol's live `SymbolReplay` in place. Otherwise fall back to today's rebuild, for that symbol
only. In-place extension needs `SymbolReplay` to update `meta`, `strikes`, `sidx` and reset `_atm` (`replay.py:170-173`,
`_atm_idx`). That is either a new `SymbolReplay.extend_meta(meta)` in `merdian_compute/tape/replay.py`, **owned by the
engine stream (outside this stream's write scope)**, or the writer setting those private attributes from outside. The
second is possible and fragile. I recommend asking the engine stream for the method.

**Why the result is the same as the batch.** Packets of a token that is not in the map are dropped as `unmapped_token`
at `feed` (`replay.py:207-209`) and never enter the heap. If no such packet was fed before the extension, then from that
point the extended replay sees exactly the packets the batch replay sees. `strikes` / `sidx` feed only `_group`
(ATM3 / OTHER), and that goes to `g3`, the data-quality report. The writer reads only `finish()["rows"]` from
`book.rows(day, meta)`, which is keyed by token and minute and renders metadata from the current `meta`. So label inputs
match the batch, while the ATM3 / OTHER split of packets classified before the extension can differ from the batch's.
**I have not proven that `g3` never reaches the cycle rows by running it.** It is a reading of `finish()` and
`writer.cycle`, and the equal-offline guard below has to assert it.

**The "no packet fed yet" condition.** The writer cannot see per-token `unmapped_token` drops (they are counted by
reason and bucket, not by token). It can instead check by time: for the affected symbol, no segment whose slot ends
after the subscription file's `HHMMSS` has been fed yet. In replay mode this always holds: `cli` applies subscriptions
before segments at the same t, and `subscriptions_143300` and `seg_1430` both become available at 14:35. **Live, it
depends on S3 arrival order.** That is unknown (§5).

**Rebuild-time share.** 0 % for the subscription trigger in the pure-addition case (dict and list updates, milliseconds).
In the fallback, one symbol, ≈ 50 % of the both-symbol figure (byte stand-in): ≈ 109 s at 14:35, ≈ 130 s at 15:30.

**O-2.** No grid point is put at risk by a subscription change in the extend path. The fallback shares B's risk at
half the cost.

**O-1 causes (label ≠ final-table label).** None added by the extend path when its conditions hold. If they are
mis-asserted (a packet of a new token was fed before the extension), the live rows lack that volume, and `verify` would
attribute the difference to `partial_cycle`. That is wrong but not invisible.

**Guard and mutant.** `live-extend-equals-batch`: on the existing `gen_live` day (NIFTY 23650 CE, subscribed 11:33),
plus a planted SENSEX-only addition, the replay's final cycle and event state equal the batch byte-for-byte, the manifest
records `extended` (not `rebuilt`) for the added symbol and nothing for the other, and a planted
segment-before-subscription arrival falls back to a rebuild. Mutants: M-L-EXTEND-NO-STRIKES (the strike list is not
extended), M-L-EXTEND-SKIPS-CHECK (always extends, so the planted early arrival diverges), M-L-REBUILD-BOTH (the
unchanged symbol is rebuilt anyway, caught by the manifest cell).

**Memory.** No change (the replay is mutated in place).

### Option B: label from the pre-rebuild state, rebuild after the label is written

**Change.** In `LiveDay`, defer `dirty`: `add_segment` keeps feeding the existing replay with the **old** map (it does
not call `_rebuild_all`), `cycle` labels from that state, and the rebuild runs after `_label` returns, inside the same
cycle. The CLI or L2 loop persists the labels before the rebuild starts. `verify_day` needs a new cause (for example
`rebuild_deferred`), meaning the stored label came from a cycle the manifest marks as pre-rebuild. Without it those
differences fall into `partial_cycle`. Adding a cause changes the spec and needs a ruling.

**Rebuild-time share.** Unchanged, ≈ 73 % at 14:35 and ≈ 93 % at 15:30 (estimate). Only the order changes: the label is
written at ~17 s instead of ~235 s.

**O-2.** Cycle T is safe. **T+5 is at risk.** If label + rebuild + poll latency exceeds 300 s, the next cycle starts
late. If the L2 loop skips a grid point it could not reach, that point is `missing` and never back-filled. By the 15:30
estimate (279 s of 300) this is plausible on a slow box.

**O-1 causes.** At cycle T, the new tokens' packets in the segments fed at T are dropped as unmapped. A wall at a newly
subscribed strike reads NO_READ "wall outside subscribed window" live, where the final table may read NO_READ "flow not
yet evaluable", or later a real label. One cycle is affected per symbol per change.

**Guard and mutant.** `live-deferred-rebuild`: the cycle-T labels equal those from a replay truncated before the
subscription; T+5 and the final state equal the batch; `verify` attributes every difference at T to the new cause.
Mutant: rebuild before the label (labels at T match the final state, and the guard fails because it requires the
pre-rebuild reading), and drop the cause (the differences then read `partial_cycle`).

**Memory.** Same as today. `_rebuild_sym` pops the old replay before building the new one.

### Option C: rebuild in the background while the cycle labels from the old state

**Change.** The largest by far. A worker builds a fresh replay for the affected symbol while the foreground keeps
labelling from the old one. Segments that arrive during the rebuild must be fed to **both**, and the swap happens at a
cycle boundary. The work is CPU-bound pure Python, so threads gain nothing (the GIL serialises them); it needs a
**process** (`multiprocessing`). The rebuilt state must cross back by pickling or by replaying the queue in the child.
The swap cycle depends on wall-clock rebuild time, so a replay would no longer be deterministic. `live-deterministic`
(uuid5 run id plus byte-identical outputs) breaks unless replay mode simulates the swap at a fixed rule (for example
always at T+5), and then replay no longer tests what live does.

**Rebuild-time share.** About 0 % of the foreground cycle **if** the box has a free core. A t3.small has 2 burstable
vCPUs shared with the recorder and the capture chain, and the run is under `nice -n 15`. The foreground cycles during
the rebuild will slow down by an amount that is unknown.

**O-2.** No direct miss, but foreground slowdown during a 218-260 s child run could push a cycle past 300 s.

**O-1 causes.** As B, but for every cycle until the swap: at least one, more if the child is slowed. It needs B's
verify cause plus a swap marker in the manifest.

**Guard and mutant.** As B, plus a swap-point guard, a both-fed-during-rebuild guard (mutant: a segment fed only to the
old replay is missing after the swap) and a determinism guard on the simulated swap rule.

**Memory.** The child holds a second full replay of the symbol plus its own interpreter: about +250-500 MB, so a peak
of about 0.8-1 GB on a 1.9 GB box. That box was OOM-killed twice on 2026-10-07 by a memory-heavy test run (Rule 23,
TD-S91-NEW-7). **This is the disqualifying cost.**

## 4. Recommendation

**Build A, in two separable steps.** Step one: scope the subscription trigger to the symbols whose filtered map
changed. That is one writer-side change, needs no engine-stream change, and on 11-06 it would have removed the NIFTY
half of the 218 s. Step two: in-place extension for pure additions, with a per-symbol rebuild as the fallback,
preferably through a `SymbolReplay.extend_meta` from the engine stream. **Reject C** on memory and on determinism. **Keep
B** as the fallback design for the case A cannot cover: a late segment, or a subscription file that arrives after
segments carrying its tokens.

**The measurement that would change it:** on live market-hours days, the arrival order at the writer of each
`subscriptions_*.json` relative to the segment that first holds its new tokens' packets. If the subscription file
routinely arrives **after** that segment, A's no-packet-fed condition fails and it falls back to a rebuild every time,
so B (label first) becomes the option that protects the label. Second: per-symbol rebuild time and its growth through
the day on the box, to replace the byte-share stand-in and the linearity assumption.

## 5. What could not be determined without market-hours data

1. S3 arrival order of subscription files against segments (it decides whether A's condition holds live).
2. Per-symbol rebuild time, and whether it really grows linearly with segments fed.
3. How often `late_segment` fires live (0 on the 11-06 replay, by construction of the replay arrival rule).
4. How often subscriptions change during the session. Three times in five days here, all pure additions, all SENSEX;
   five days is not a rate.
5. Foreground slowdown under a concurrent child process on the box (only matters for C).
6. Whether the recorder writes `subscriptions_HHMMSS.json` before or after it calls subscribe. That decides whether
   packets of new tokens can precede the file's own timestamp, so it is part of A's condition.
