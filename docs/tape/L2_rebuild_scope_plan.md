# Tape live L2, R-F step one: rebuild only the symbols whose filtered token map changed (plan)

Sun 2026-11-08 (prompt dated Sat 11-07). Branch `tape/live-l0` at `276e221`. Ruling **R-F** (operator, 2026-11-07 16:05
IST): step one approved; step two (`extend_meta`) held; option C rejected; option B kept on file, not built. The late
segment trigger is unchanged in scope (its own symbol only). Plan only. Nothing is built until the operator switches model.

## 0. Housekeeping (done)

- PASS `git status --porcelain` empty.
- PASS `git log --oneline -3`: `276e221 tape live L0: snapshot ts fraction width normalised…`, `0a1c681 tape live L0:
  flow-vs-book writer…`, `79efb0b Merge tape/scoring-v04…`. 276e221 is HEAD.
- PASS re-read: `writer.py` `add_subscriptions:123-130`, `add_segment:132-147`, `_rebuild_sym:170-177`,
  `_rebuild_all:179-183`, `cycle:196-218`; `replay.py` `build_token_map:65-83`, `SymbolReplay.__init__:167-186`;
  `cli.py:186-209` (the loop: subscriptions before segments at each t, then `cycle`) and `:231` / `:237` (`rebuilds` into
  `run_manifest.json` and stdout); `tests/test_tape_live.py` `g_equal_offline:407-439`; `tests/tape_live/gen_live.py`.
- Counts found: guards **13** (`GUARDS`, `test_tape_live.py:790-794`); mutants **24**, controls **13**
  (`tape_live_mutants.py:12`); suite **42** steps (`run_offline.sh:3`); steps 41/42 are the tape live guards and mutants
  (`run_offline.sh:219-220`).

## 1. The per-symbol filtered map

`SymbolReplay.__init__` (`replay.py:167-174`) depends on the token map only through this line:

```python
171        self.meta = {t: m for t, m in meta.items() if m.get("sym") == sym}
172        self.strikes = sorted({m["strike"] for m in self.meta.values()
173                               if m["role"] == "OPT" and m.get("strike") is not None})
174        self.sidx = {k: i for i, k in enumerate(self.strikes)}
```

`strikes` and `sidx` are functions of `self.meta`. Every other later read of the map goes through `self.meta`
(`replay.py:210` `feed`, `:288`, `:326` `book.rows(self.day, self.meta)`, `:331`). `sym`, `day` and `win` are fixed for
the whole day. So **two replays fed the same lines are identical exactly when their filtered `self.meta` dicts are
equal.** That is the test.

**Derivation, with no second copy of the filter.** The writer gets the filtered map from `SymbolReplay` itself:

```python
def _filtered(self, meta, sym):
    return replay.SymbolReplay(sym, self.day, meta, self.win).meta
```

Building an empty `SymbolReplay` costs microseconds (empty heap, empty books). This way the writer **cannot** drift
from `replay.py:171`, because it runs that line. Rule 0's parity clause does not come up: there is one implementation, not
two. (I rejected copying the dict comprehension into the writer. That would be a second implementation and would need a
comparison test.)

**Metadata change.** Dict equality compares the whole metadata dict per token (`_META_FIELDS`, `replay.py:62`). A change to
one field of one SENSEX token makes SENSEX's filtered map differ, so SENSEX is rebuilt. If the field is `sym` itself, the
token leaves one symbol's map and joins the other's, so both differ and both are rebuilt. That is correct.

**Removal.** `build_token_map` is a union over all files, and the first file in `sub_sort_key` order fixes each token
(`:68`, `:78-82`). A later file cannot remove a token, and a later file that disagrees is a *conflict*, not a change. So
removal **cannot happen** through `add_subscriptions`. The only real way a token's metadata changes is a file that arrives
late but **sorts earlier**, for example `subscriptions_085500.json` arriving after `085501`. The dict comparison would also
handle a removal correctly (the map differs, so that symbol is rebuilt), but no planted case can produce one. I say so
rather than plant an impossible case.

**What is not compared.** `self.added` (`added_minutes`) and `self.conflicts` are not replay state. `added` is read
fresh in every `cycle` (`writer.py:205`), and `conflicts` only goes to the manifest. Neither forces a rebuild today, and
neither will afterwards.

## 2. `dirty` becomes `{symbol: why}`

```python
self.dirty = {}                                   # was None

def add_subscriptions(self, name, doc, at):
    self.subs.append((name, doc))
    meta, self.conflicts = replay.build_token_map(self.subs)
    self.added = added_minutes(self.subs)
    if meta != self.meta:
        old, self.meta = self.meta, meta
        for sym in SYMBOLS:
            if sym in self.rp and self._filtered(meta, sym) != self._filtered(old, sym):
                self.dirty[sym] = {"trigger": "subscriptions", "at": at, "file": name}

def add_segment(self, sym, name, at):
    ...                                           # parse, late record, known.append: unchanged
    if sym in self.dirty:                         # absorbed: the pending rebuild re-feeds known[sym], this one included
        return
    if sym in self.last and (key, name) < self.last[sym]:
        self._rebuild_sym(sym, {"trigger": "late_segment", "at": at, "file": "%s/%s" % (sym, name)})   # line verbatim
        return
    self._feed(sym, name)

def _rebuild_dirty(self):                         # was _rebuild_all
    dirty, self.dirty = self.dirty, {}
    for sym in SYMBOLS:
        if sym in dirty:
            self._rebuild_sym(sym, dirty[sym])

def cycle(...):
    if self.dirty:
        self._rebuild_dirty()
```

Decisions:

- **Guard on `sym in self.rp`**, per symbol (was `if self.rp`, any symbol). A symbol with no replay yet builds its first
  replay from the current `self.meta` in `_new_replay`, so it needs nothing.
- **Last file wins `why`** (assignment, not `setdefault`). This matches today: `self.dirty = {...}` overwrites on every
  changing file. Only `file` can differ, since `at` is the same within one cycle.
- **Call site 1 (`add_segment`) changes from "rebuild everything now" to "absorb".** For a dirty symbol, the segment is
  appended to `known` and not fed. Segments of a non-dirty symbol take today's path unchanged, including the verbatim
  `late_segment` line (mutant M-L-DROPS-LATE-SEGMENT anchors on it). The other dirty symbols are **not** rebuilt here.
  **Call site 2 (start of `cycle`)** is now the only place a subscription rebuild runs.
- **Why defer to `cycle`, not rebuild at the first segment as today.** This is how the triggers compose (case f). If
  the rebuild ran at the first segment of the symbol in a cycle, a later segment in the same cycle that sorts earlier
  (a late segment) would rebuild the same symbol **a second time**. With deferral, every segment of a dirty symbol in the
  cycle is absorbed into **one** rebuild, late ones included. **Correction at build (measured):** the first draft
  said that in `cli` replay the late segment always sorts first in its cycle, so the old timing gave one rebuild there.
  That is false across symbols. `segs.sort` is by `(m, si, k, name)` (`cli.py:181`), so NIFTY (`si = 0`) comes first.
  On the unchanged tree, the scope day at 14:05 rebuilt NIFTY and SENSEX at NIFTY `seg_1400`, then rebuilt SENSEX again
  as `late_segment` at SENSEX `seg_1350`. The deferral is therefore needed in `cli` replay too, not only live. The work done is the same: the same segments
  are re-fed, a few lines later in the same t.
- **Late trigger on a non-dirty symbol: unchanged.** It is immediate, scoped to its own symbol, with the same `why`. A late
  segment for a symbol that becomes dirty later in the same cycle cannot happen in `cli` (subscriptions are applied before
  segments at each t, `cli.py:191-196`). Live it would mean one late rebuild followed by one subscription rebuild, which is
  correct and not covered by the ruling. Not changed.
- **Behaviour change on real days, stated plainly.** `rebuilds` shrinks wherever a change touched one symbol: 11-06 at 875,
  and the 09:01 files on 11-03 and 11-05 (SENSEX-only, per `L2_rebuild_options.md` §1). Entry order within a cycle is
  now SYMBOLS order at the cycle start. A `late_segment` entry of a non-dirty symbol in the same cycle is therefore listed
  before the subscription entries. That cannot occur in `cli` replay with the default arrival rule.

## 3. Manifest

`rebuilds` stays a list of `dict(why, symbol=sym)`, one entry per symbol rebuilt, appended by `_rebuild_sym:171`
(unchanged). Keys stay `trigger, at, file, symbol`. **No schema change.** `schema` stays `tape_live_replay_manifest_v1`,
and `cli.py:231` / `:237` are not touched. A symbol dirty from both triggers in one cycle produces **one** entry, with
trigger `subscriptions`. The late segment is still recorded in `late_segments` (`add_segment:138-139`, before the absorb).

## 4. Guard `live-rebuild-scope`, and the mutants

**Fixture.** `gen_live.build(root, scope=True)` builds a second day. The default `build(root)` stays byte-identical:
the existing 13 guards and `PLANTED` pin it, and the new guard also asserts that the default fixture's session files
are unchanged against their pre-change sha256, written into the test. The scope day is the default day plus:

| file (arrival) | content | case | expected `rebuilds` entries at that `at` (hand-written) |
|---|---|---|---|
| `subscriptions_113300.json` (11:35 = 695) | existing: + NIFTY 10107 23650 CE | b | `[(subscriptions, 695, NIFTY)]` |
| `subscriptions_120300.json` (12:05 = 725) | + SENSEX 20205 77200 CE, packets from 12:04 | a | `[(subscriptions, 725, SENSEX)]` |
| `subscriptions_123300.json` (12:35 = 755) | + NIFTY 10108 23700 CE, + SENSEX 20206 77200 PE, packets from 12:34 | c | `[(subscriptions, 755, NIFTY), (subscriptions, 755, SENSEX)]` |
| `subscriptions_130300.json` (13:05 = 785) | exactly the cumulative token list (nothing new) | d | `[]` |
| `subscriptions_085500.json`, `--arrival session/…=13:35` (815) | one row: SENSEX 20203 with a different `tradingsymbol`, same `added_minute` | e | `[(subscriptions, 815, SENSEX)]` |
| `subscriptions_140300.json` (14:05 = 845) + `--arrival SENSEX/seg_1350.ndjson.gz=14:05` | + SENSEX 20207 77300 CE, packets from 14:04; seg_1350 late (1355 fed at 14:00) | f | `[(subscriptions, 845, SENSEX)]`, no `late_segment` entry, `late_segments` names `SENSEX/seg_1350` |

So the full expected list is exactly these **6** entries, in this order. (The first draft of this plan said 7; the table
holds 6. Corrected at build, before the guard was run.) It is compared as a list of `(trigger, at, symbol)`
tuples against `run_manifest.json`. `tradingsymbol` is a cycle column (`cycle.py:17`), so case e reaches the bytes.

**Assertions (one cli replay plus one batch run on the scope day).**
1. `rebuilds` equals the hand-written list above.
2. `tape_live_cycle.csv` and `tape_live_events.csv` equal the batch `tape_strike_cycle.csv` / `tape_events.csv` **byte
   for byte**, both as written and as reconstructed from the per-cycle deltas (`_reconstruct`, as `g_equal_offline`
   does). This shows that every skipped rebuild was redundant.
3. **f2, in-process.** Drive `LiveDay` on the scope day with the `cli` event order, except that at 845 `SENSEX/seg_1400`
   is added **before** `SENSEX/seg_1350`. Assert one entry at 845 (`(subscriptions, 845, SENSEX)`) and the final state
   equal to the batch bytes. Without this, case f cannot tell "once" from "twice", because the `cli` sort always puts
   the late segment first.
4. Control: the default fixture's session-file sha256 is unchanged.

**What makes it fail** (Rule 0): cases a, b and e fail on (1) if the other symbol is rebuilt. Cases a, c, e and f fail on
(2) if a needed rebuild is skipped: the new SENSEX tokens' packets are dropped as `unmapped_token`, or the old
`tradingsymbol` is rendered. f2 fails on (3) if a dirty symbol is rebuilt at the segment.

**Before the change** (unchanged tree), the guard is expected to FAIL on (1): 695 → `[NIFTY, SENSEX]` (b), 725 →
`[NIFTY, SENSEX]` (a), 815 → both (e), 845 → both (f). (2) is expected to pass, because today's code over-rebuilds.

**Mutants** (in `tape_live_mutants.py`, writer patches):

| mutant | patch | caught by |
|---|---|---|
| M-L-REBUILD-BOTH | `if sym in self.rp and self._filtered(meta, sym) != self._filtered(old, sym):` → `if sym in self.rp:` | (1) at 695, 725, 815, 845 |
| M-L-REBUILD-NONE | the `self.dirty[sym] = {...}` line → `pass` | (2): SENSEX bytes diverge (cases a, c, e, f); (1) too |
| M-L-FILTER-FULL-MAP | `return replay.SymbolReplay(sym, self.day, meta, self.win).meta` → `return meta` | (1): the other symbol is listed at 695, 725, 815, 845 (d stays clean: the full map is unchanged too) |
| M-L-DIRTY-REBUILDS-AT-SEGMENT (proposed fourth, §6) | absorb `return` → `self._rebuild_dirty(); return` | (3) f2: two entries at 845 |

Totals afterwards: guards **14**, mutants **27** (28 with the fourth), controls **14** (one per guard), and the suite stays
**42** steps. `run_offline.sh:219-220` labels go to `(14)` and `(27 x5)` / `(28 x5)`, and the guard and mutant docstring
last lines change to match.

## 5. Real-day check, 2026-11-06 from `C:\tape_data` (read-only)

- **Before:** replay on the current tree (`276e221`) **before** any edit, with the same arguments as
  `tests/tape_live_equal_offline.py` uses for that day, output under `_l0_logs/rf_before/`, stderr through `Tee-Object`
  (Rule 21).
- **After:** the same command on the committed change (so `code_sha` is a clean commit), output `_l0_logs/rf_after/`.
- **Expected `rebuilds`:** before `[subscriptions@875 NIFTY, subscriptions@875 SENSEX]`, after
  `[subscriptions@875 SENSEX]`. This is written here first and measured second.
- **Expected equality:** `tape_live_cycle.csv`, `tape_live_events.csv`: sha256 **identical outright**. They carry no
  provenance column (`CYCLE_COLS`, `EVENT_COLS`). `tape_live_wall.csv`, `tape_live_label.csv`: identical after dropping
  the `live_run_id` and `code_sha` columns, which change with the code version (`as_of` does not). I report the raw
  sha256 pairs and the column-stripped sha256 pairs.
- **Per-cycle seconds** for the 14:35 cycle before and after, read from the `cycle 14:35 X s` stderr line, **on this
  Windows machine, not the production box.** The 109 s figure is a production-box estimate and is not checked here.
- **Three-day gate:** `python tests/tape_live_equal_offline.py --data C:\tape_data --work _l0_logs\rf_gate` (default
  days 11-04, 11-05, 11-06), after the change. I report each day's lines. 11-05's 09:01 SENSEX-only change now
  rebuilds SENSEX only, which the gate does not assert on.

## 6. Not settled by the prompt, with my defaults

1. **Rebuild timing moves from the first segment to the cycle start** (§2). It is needed for "once" under live arrival
   order. **Default: do it**, and guard it with f2.
2. **A fourth mutant, M-L-DIRTY-REBUILDS-AT-SEGMENT,** so that the deferral in (1) has a check that can fail (Rule 0).
   **Default: add it** (mutants 24 → 28). If the operator wants exactly three, f2 stays in the guard without a mutant.
3. **`why` for two changing files of the same symbol before one rebuild:** last file wins, as today. **Default: keep.**
4. **Case (e)'s mechanism** is an earlier-sorting file that arrives late, the only way metadata can change (§1). **Default:
   plant that.** The removal case is not planted because `build_token_map` cannot produce it.
5. **Entry order in `rebuilds`:** SYMBOLS order at the cycle start. **Default: accept.** The guard compares the full
   ordered list, so any reordering is visible.
6. **Rule 23 on Windows:** the `ulimit -v` half cannot be enforced here (as in S105). The time window does not apply,
   because the run is on a Sunday. Steps of `run_offline.sh` that need bash or Linux are reported as not run, and steps
   2, 8 and 10 are known to fail identically on the unmodified tree on this machine.
