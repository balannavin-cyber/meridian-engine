# NIFTY 13 Oct 2026 (0DTE) — pin scorecard, parity target vs MERIDIAN

**Close used: 22,721.95** = the target's last print at 15:30–15:40 IST ("Market closed", +1.60 % vs 12 Oct). Confirmed by press:
"Nifty ends at 22,722" (Business Standard, 13 Oct 2026). Expiry settlement uses the official close; treat 22,722 as final. Our board's spot was frozen at 22,702.1 from ≈15:16 and never recovered (see defects).

Pins are as rendered at each checkpoint: target = Pin · pressure header; ours = Marketview PIN (γ-conc) tile (one γ run behind the read time).
"—" = not read at that checkpoint.

| IST | their pin | Δ to close | our pin | Δ to close | same? |
|---|---|---|---|---|---|
| 09:34 | 22,400 | 322 | 22,600 | 122 | no (ours closer) |
| 09:44 | 22,500 | 222 | 22,600 | 122 | no (ours closer) |
| 09:54 | 22,500 | 222 | 22,600 | 122 | no (ours closer) |
| 10:04 | 22,500 | 222 | 22,500 | 222 | yes |
| 10:14 | 22,500 | 222 | 22,500 | 222 | yes |
| 10:25 | — | — | 22,500 | 222 |  |
| 10:35 | 22,500 | 222 | 22,500 | 222 | yes |
| 10:45 | 22,500 | 222 | 22,600 | 122 | no (ours closer) |
| 10:55 | 22,500 | 222 | 22,600 | 122 | no (ours closer) |
| 11:05 | 22,500 | 222 | 22,600 | 122 | no (ours closer) |
| 11:15 | 22,500 | 222 | — | — |  |
| 11:25 | 22,450 | 272 | 22,600 | 122 | no (ours closer) |
| 11:35 | 22,450 | 272 | 22,400 | 322 | no (theirs closer) |
| 11:45 | 22,500 | 222 | 22,600 | 122 | no (ours closer) |
| 11:55 | 22,500 | 222 | 22,600 | 122 | no (ours closer) |
| 12:05 | 22,500 | 222 | 22,600 | 122 | no (ours closer) |
| 12:15 | 22,500 | 222 | 22,600 | 122 | no (ours closer) |
| 12:25 | 22,500 | 222 | 22,600 | 122 | no (ours closer) |
| 12:35 | 22,500 | 222 | 22,600 | 122 | no (ours closer) |
| 12:45 | 22,500 | 222 | 22,600 | 122 | no (ours closer) |
| 12:55 | 22,500 | 222 | 22,500 | 222 | yes |
| 13:05 | 22,500 | 222 | 22,500 | 222 | yes |
| 13:15 | 22,500 | 222 | — | — |  |
| 13:25 | 22,500 | 222 | — | — |  |
| 13:35 | 22,500 | 222 | — | — |  |
| 13:55 | 22,500 | 222 | 22,500 | 222 | yes |
| 14:05 | 22,550 | 172 | — | — |  |
| 14:15 | 22,550 | 172 | 22,550 | 172 | yes |
| 14:25 | 22,550 | 172 | — | — |  |
| 14:30 | 22,550 | 172 | 22,550 | 172 | yes |
| 14:35 | — | — | 22,550 | 172 |  |
| 14:40 | 22,600 | 122 | 22,550 | 172 | no (theirs closer) |
| 14:50 | 22,650 | 72 | 22,600 | 122 | no (theirs closer) |
| 15:00 | 22,650 | 72 | 22,650 | 72 | yes |
| 15:05 | 22,650 | 72 | — | — |  |
| 15:10 | 22,650 | 72 | 22,650 | 72 | yes |
| 15:15 | 22,700 | 22 | 22,750 | 28 | no (theirs closer) |
| 15:20 | 22,700 | 22 | 22,750 | 28 | no (theirs closer) |
| 15:25 | 22,700 | 22 | 22,700 | 22 | yes |
| 15:30 | 22,700 | 22 | 22,700 | 22 | yes |

## Totals (n = 1 day; descriptive, not a test)
- Reads: theirs 38, ours 33. Same-checkpoint pairs 31: **same strike 12, ours closer 14, theirs closer 5.**
- Within ±50 of the close: **theirs 4/38, ours 4/33**, all from 15:15 on. **Neither pin forecast the close before 15:15.**
- Mean |pin − close|: **theirs 182, ours 141.**
- The pattern: their pin (ΔOI pressure + distance decay) sits on spot and steps up behind it as price trends (22,500 → 22,550 → 22,600 →
  22,650 → 22,700). Its LOCKED / 87–93 conviction from 10:14 to 14:05 at 22,500 described a 75-pt range, then failed. Ours (|γ| share)
  sat on the call OI wall 22,600 through midday, i.e. above spot, which happened to be nearer the day's close. That is luck of the trend,
  not skill: ours has no distance term and flipped on leads of 0.1–3 share points (22,600 ↔ 22,500 ↔ 22,400).
- Their **settlement probability** rose 21 % → 99 % into the close. It is a function of time-to-expiry and distance-to-pin, so it climbs
  whenever spot sits on the pin, including during the 15:16–15:25 frozen print (96 % on a stale spot).

## Regime sign (same minute, NIFTY)
Not tallied for every checkpoint (our reads lag one 5-min run). Explicit same-spot disagreements logged: 12:50, 13:00, 13:50, 14:16 (theirs long /
ours short, spot within ~10–25 of their zero-γ). Every other paired read agreed in sign. Inside ±25 pts of the flip, the sign is noise on both boards.

## Defects seen today — target
1. Pin pane: header, ranking #1 and settlement line computed or refreshed separately. Six instances (SENSEX 10:2x; NIFTY 11:38, 11:45, 11:56;
   SENSEX 13:15; NIFTY 14:06). The settlement line named a previous pin for up to ~25 min.
2. Strip net Γ vs Strike-profile net Γ: opposite signs on one screen (10:57, 12:16, 13:06, 14:30, 15:01, 15:16).
3. Two different "C WALL" values on one screen (Strike profile 22,600 vs Price × delta 22,800 at 14:30), unlabelled.
4. Delta · positioning totals print partial refreshes: ITM short-cover rows blank ("·") while READ says 100 % (15:16). Explains the 14:06,
   14:51 and 15:16 "drops", and the 15:40 final since-open Initiated of **+56,809** vs +1,96,825 at 15:01.
5. Positioning verdict vs own aggressor tape: 99 % "bullish / put writing" while aggressors net sold Δ and bought puts (12:56–13:06).
6. Stale spot not flagged (15:16–15:25), settlement probability computed on it.
7. Renderer freezes (CDP screenshot timeouts) from ~12:30; partial-load n/a tiles.

## Defects seen today — ours (Marketview / pipeline)
1. **Spot feed did not recover after the ≈15:16 upstream pause**: frozen at 22,702.1 through 15:40; basis computed against it (+146.7 → +158.0);
   IV tile "—"; latest γ run shown 15:20 at 15:40 ("20 min apart"). Check the tick table and whether the 15:25 / 15:30 γ runs exist.
2. Symbol switch slows to minutes as the tab ages, and the page is unresponsive meanwhile (13:10–13:50 NIFTY unreadable; γ runs were fine per the
   13:49 query).
3. "Pocket" word follows the nearest strike's γ sign, not net Γ: "dampening" while net short ×6, "amplifying" while net long ×2. Wording
   candidate; needs operator yes.
4. Pin tile "no run" / open-gap "prev close missing" on partial loads instead of "loading".
5. Pin lead unstable on 0DTE: 8.6 → 11.4 → 1.5 in three runs; 17.3 → 3.1 in one. No hysteresis, no state word on the tile.
6. Board one γ run behind (≈5 min) all day.

## SENSEX side note (2 DTE)
Flip gap ours − theirs stayed **+83 … +187** all day, always ours higher. The 13:28 per-strike read places the strike-axis sign change ~72,565
vs our repriced flip 72,658: the gap is likely construction inside ENH-131's repricing, not data. It needs both curves at one minute.
