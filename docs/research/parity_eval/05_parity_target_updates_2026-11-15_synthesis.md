# Parity target product updates, 2026-11-02 to 2026-11-15: record and how MERIDIAN could absorb them (for discussion)

Engine lane. Opened at the operator's word, 2026-11-15 11:45 IST ("document in Parity or Agentic build out doc for discussion and how we can synthesise it in MERIDIAN; ignore Diwali and pricing").

**This note rules nothing and reopens nothing.** ADR-025 closed parity on 2026-10-09; a layer outside the fourteen does not count toward parity (D5). Anything below that becomes work needs its own ruling, and a pre-registration where it makes a claim (ADR-009).

## 0. How this was read

- The operator's X account page and the product account's quoted posts, read through the operator's Chrome on 2026-11-15 ~11:40 IST: the latest 50 posts, 2026-11-02 to 2026-11-15, about 20 of them about the product. The rest are his own trading P&L and market views.
- Text only. Images and charts were not read. Some long posts were cut off in the timeline; the 11-13 validation thread was read in full on its own page (posts 1/ to 5/). The 9-part option-volume thread (11-14) was seen only as its first post.
- Everything below is the vendor's own statement of what its product does. Nothing was seen inside the workspace. Lines marked **[inference]** are mine.
- Prior record: `claude/engine_note_parity_target_observed_2026-11-12.md` (sign-up page and settings), `claude/target_read_Mar-Oct2026.md` (tabs as of September), `claude/parity_eval/00_inventory.md` and `03_findings.md` (the 10-13 terminal read).

## 1. What is new, in the vendor's words

| # | Date | Item | What was stated |
|---|---|---|---|
| H1 | 11-15 | **Futures OI build-up** | Described as the first feature that gives a directional read, from index-futures OI build-up: long build-up, short build-up, short covering, long unwinding. A subscriber replied that it suits only larger timeframes; the answer was that there is an intraday option. |
| H2 | 11-14 | **Per-minute futures OI labels** | The product account says every minute is now labelled with the same four classes. Positioned as a three-way read with gamma (concentration) and IV (what the market pays for movement), with futures OI as money coming in or leaving. |
| H3 | 11-14 | **Option volume, one number** | A 9-part thread: "Where did today's option volume really hit?" One number that puts OI and volume on one screen. **Only the first post was seen; the definition is not known.** |
| H4 | 11-13 | **Unusual volume flag, tested** | 20,101 flagged bursts over 435 NIFTY sessions, each compared with ordinary windows of the same option (same day, same length, within 45 minutes). 62 % moved the option's price more than 90 % of those windows; 10 % would be chance; 15 % did not spike at all. Trades tagged buyer- or seller-initiated from the bid and ask just before each trade: 25 % buyer-led, 17 % seller-led, 58 % mixed (far out of the money: 36 % against 14 %). Ten minutes after a buyer-led burst, OI at that strike fell about 5 times as often as it rose (25 % against 5 %); after seller-led bursts it rose 25 % and fell 11 %. Held in 2025 and 2026, calls and puts, expiry and other days (+34 points, 90 % range +31 to +37). After buyer-led bursts the price carried on less often than usual (30 % against 49 %). Stated as "what happened, not a forecast or advice". |
| H5 | 11-03 | **Unusual tab** | Described as going below price, OI and volume to what is happening inside them. |
| H6 | 11-05, 11-06 | **Burst and chain reads, live** | Calls traded at up to 23 times their normal pace; 2.4 crore shares of call OI gone in 30 minutes; short covering and ITM put activity read off the volume map. Bursts are "flagged as they happen". |

## 2. Where each sits against what MERIDIAN has

| Item | Nearest MERIDIAN thing | Gap, from the docs |
|---|---|---|
| H1, H2 futures OI build-up | FUT · BASIS tile (basis and futures change only, from `index_futures_snapshots`, 09:30 to 16:00 IST). D-4, the ΔOI × premium four-case on **options**, DECLINED-ON-EVIDENCE (S96-I): premium partly re-encodes the spot move, one day of evidence. The 10-09 triage left the four-case off the post-parity track. | Different object: the futures case uses the underlying's own price, so the S96-I reason (premium re-encodes spot) does not carry over. Whether `index_futures_snapshots` holds OI is **UNVERIFIED**. Capture starts 09:30, not 09:15. History with OI may exist in `hist_future_bars_1m` (GFDL carries Open Interest) and the tape recorder subscribes the front future with the index: UNVERIFIED which of these carry OI. |
| H4, H5, H6 unusual volume | `03_findings.md` F6 already lists "Volume ÷ OI rank with a positioning word per strike" as a feature with no MERIDIAN substrate. The 10-09 triage left "volume ≥ OI" off the track. | Burst detection against a strike's own normal pace needs minute-level volume. The chain tables are on the 5-minute run clock. The tape recorder has tick data on a subscribed window since 11-02 and already defines CONC and THIN events and aggressor classification (pre-registration v0.4, H-A and H-B). |
| H4 aggressor tagging | Tape design §2.3 aggressor classification from quotes; H-A's tape sign D = −(γ × (Buy − Sell)) per leg, "customers buying options leaves the other side short gamma". | See section 3: their OI result is a direct test of a premise H-A uses. |
| H3 volume and OI on one screen | L1 to L13 views; OI rotation `v_oi_rotation_since_open` (L13). | Definition unknown. Read the thread before any comparison. |
| Three-way read (gamma + IV + futures OI) | The board already shows gamma, IV and the FUT · BASIS tile. The retail Changes layer has 12 measures × 5 windows. | No futures-positioning measure. |
| Agentic facts layer | `agentic_layer_roadmap_S90.md` §8.1 state vector (8 dimensions; dimension 5 is flow) and §8.2 event grammar. Stage 4 is ON HOLD (S99-D). | Futures positioning is not a dimension; no event for a class change that persists. |

## 3. The one finding that bears on work already in flight

H4 says buyer-initiated bursts are followed, ten minutes later, by OI **falling** at that strike five times as often as rising. If it holds on NIFTY chains, a buyer lifting the ask at a strike is mostly closing, not opening. The tape pre-registration's sign step (S from D = −(γ_call × (BuyQty_call − SellQty_call) + γ_put × (BuyQty_put − SellQty_put))) reads aggressor-buy as customers opening, leaving dealers short gamma. Without an OI confirmation the sign could be wrong exactly where the flow is largest.

Caveats on the vendor's number, so it is not over-read:
- "62 % against a 10 % chance rate" is a lift over a 90th-percentile bar. It describes bursts coinciding with larger price moves of the same option. Volume and price movement are linked mechanically, so this does not show the flag predicts anything; the vendor says as much about direction.
- 58 % of trades were "mixed", so the buyer-led and seller-led groups are the minority of bursts. The OI result is about 42 % of the sample.
- The aggressor tag is from the bid and ask just before the trade, a quote-rule estimate like MERIDIAN's own. Its error rate is not stated.
- All figures are self-published and not reproduced here.

What MERIDIAN can do without waiting on the vendor: the tape lane holds its own tagged days (recording since 2026-11-02) and chain runs every 5 minutes, so the same question (change in strike OI over the next two runs after a buyer-led or seller-led burst) can be asked of our data. That is an exploration for the tape lane, not a change to a locked pre-registration; whether it becomes a secondary under a new version is the tape lane's and the operator's call.

## 4. Options for discussion

**Option A, futures OI build-up as a context layer (new L20 under spec §2.5, off the fourteen).**
- Step 0, read-only, no ruling needed: does `index_futures_snapshots` hold OI; does `hist_future_bars_1m` carry OI and how far back; what the tape recorder holds for the front future.
- Step 1, needs a ruling: re-admit the futures four-case to the post-parity track (the 10-09 triage covered the option four-case). Pre-register before any query (ADR-009): the baseline (bar-to-bar, session open, previous close), the minimum move and OI change for a non-neutral label, forward windows (15, 30, 60 minutes and to close), minimum n, and the null.
- Step 2: event study on 2025-05 onward with intervals. Outcome DONE with evidence or DECLINED-ON-EVIDENCE, as for P1 to P8.
- Display: a descriptive context cell beside FUT · BASIS ("futures OI up, price up"), no directional claim. For retail it must clear the wording lint and counsel's descriptive-only line (G1); the vendor's "directional read" wording would not.

**Option B, unusual volume bursts and aggressor, through the tape lane.**
- Stays operator-only (retail stance on the order-flow layer). The substrate is the tape's minute data, not the 5-minute chain.
- Add the H4 questions as exploration on our tagged days: OI response after buyer-led versus seller-led bursts; price continuation after buyer-led bursts; share of mixed trades.
- Feeds the sign assumption in H-A (section 3). No change to the locked pre-registration from this note.

**Option C, three-way board read.** Only after A has a result. Gamma (concentration), IV (price of movement) and futures OI (money in or out) as one context row in the retail Changes layer. Depends on A and on the retail lane's copy gate.

**Option D, agentic facts layer.** Add dimension 9 "futures positioning" (class, and class held for N cycles) to the state vector and one event ("class changes and persists ≥ 3 cycles") to the grammar, with an event study per context. Roadmap Stage 4 is ON HOLD (S99-D); this is a note against that stage, not a start.

**Option E, no action.** The vendor's items are marketing statements; MERIDIAN's priority track (§2.1) and the retail build stay as they are, and this note stays as the record.

Engine view (not a ruling): A step 0 and B's exploration cost a read each and change nothing in production; the rest waits on their results. The method point worth taking from the vendor is H4's form: publish a flag's hit rate with its limits. That is already the shape of ADR-009 pre-registration and ADR-020's "insufficient history".

## 5. Reads that would settle the UNVERIFIED items (engine box or SQL editor, read-only)

```sql
select table_name, column_name, data_type
from information_schema.columns
where table_schema = 'public' and table_name in ('index_futures_snapshots','hist_future_bars_1m','historical_index_futures_1m')
order by table_name, ordinal_position;
```
```sql
select 'hist_future_bars_1m' t, min(ts) lo, max(ts) hi, count(*) n from public.hist_future_bars_1m
union all select 'index_futures_snapshots', min(ts), max(ts), count(*) from public.index_futures_snapshots;
```
Run the second only after the first shows a `ts` column on each; if a name differs, adjust. The first read decides whether OI exists at all.

Also owed to read: the 9-part option-volume thread (11-14) and the vendor's public methodology page (49 metrics, per `target_read_Mar-Oct2026.md`) for the exact build-up definition and baseline, before any design.

## 6. Paste-ready text, held until the operator says to commit (repo files, not edited from this session)

**For `claude/parity_eval/03_findings.md`, under F6 (added lines):**
- Futures OI build-up classification (price × futures OI: long build-up, short build-up, short covering, long unwinding), intraday and per-minute, announced 2026-11-15. MERIDIAN has no substrate read yet (section 5).
- Unusual-volume bursts against a strike's own normal pace, with a published validation (62 % lift over chance, buyer-led bursts followed by OI falling 5 : 1). MERIDIAN's tape recorder is the only substrate.
- An option-volume view combining OI and volume in one number (definition unread).

**For `agentic_layer_roadmap_S90.md`, one line under Stage 4 notes:**
"2026-11-15: reference product added a futures OI build-up class (price × OI). Candidate state-vector dimension 9 and an event; held with Stage 4 (S99-D). See `claude/parity_eval/05_parity_target_updates_2026-11-15_synthesis.md`."

**For the tape lane:** section 3 and Option B, as context only.
