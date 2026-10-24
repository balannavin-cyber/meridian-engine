# Part C additions from S100 Saturday work (Monday 2026-10-26)

- **S100-M (b)** 08:20 refresh + 09:09 probe run on 418a75b; any Dhan plan lapse now logs `SUBSCRIPTION_LAPSED` (none expected).
- **S100-M (a)** `/health` during trading (10:00–15:00 IST): writer fleet N / 14; OVERALL green unless a tracked writer is
  actually stale — read OVERALL and the fleet line together.
- **S100-N discriminating read** (09:20–16:00 IST, both symbols): Context SPOT change = Board Spot cell change at the same
  moment; old code would differ by Friday's whole move (prev close two sessions back). Expected figures computed from the
  database at the read (live 1-min spot − 10-23 16:00 `dhan_idx_i` close).
- **R19** after the evening EOD run: `breadth_indicators_daily` gains 10-23 (and 10-22 if equity_eod filled); `gap dates filled : none`.
- **S100-R** after 15:41 IST: Board Spot tile label `Spot · close` with the 15:40 chain spot (= the official close); between 15:15 and ~15:25 `Spot · held since 15:15`.
- **S100-Q.1**: read sentence's local word and `Net gamma is long|short` agree with the NET Γ tile through the session.
- **S100-S**: before 09:16 the strip reads `Pre-open · figures are from the pre-open chain …`; 15:15–15:45 `Closing session · spot held since 15:15 …`; from 15:45 `Closed · showing the 26 Oct session · next open 27 Oct`; a γ run > 10 min old between 15:25 and 15:45 raises the stale strip; FUT·BASIS sub-line `vs spot X @ hh:mm` — at 15:30–15:40 expect the stale 15:15 spot on the futures row (TD candidate), at 16:00 the close.
