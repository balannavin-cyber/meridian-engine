# Session-state strip, stale window to 15:45, basis reference (ruling S100-S) — Lovable prompt

**Paste into the `meridian-connect` Lovable project.** Two files. Wording is operator-approved (S100-S); use it exactly. No
new database query (reuses `useNextOpen`, already exported from `@/lib/board`, and the futures row Board already reads).

## Context

The board has no closing / closed / pre-open state (the final report's A5, A1), its stale strip is silent after 15:30 while
the closing γ cycles run to 15:40 (A2), and the FUT·BASIS tile does not say which spot its basis is measured against (A4).

## Change 1 — `src/components/AppShell.tsx`

**1a.** In the import line `import { useIvFront, useWalls, useSessions, istToday } from "@/lib/board";` add `useNextOpen`:
`import { useIvFront, useWalls, useSessions, istToday, useNextOpen } from "@/lib/board";`

**1b.** Replace the whole `StaleStrip` function — exactly this:

```tsx
function StaleStrip() {
  const { symbol } = useSymbol();
  const chain = useIvFront(symbol);
  const walls = useWalls(symbol);
  const sess = useSessions();
  const [, setT] = useState(0);
  useEffect(() => { const id = setInterval(() => setT((t) => t + 1), 30_000); return () => clearInterval(id); }, []);
  const now = new Date();
  const ist = new Date(now.getTime() + 5.5 * 3600_000);
  const mins = ist.getUTCHours() * 60 + ist.getUTCMinutes();
  const inSession = sess.data?.session === istToday() && mins >= 9 * 60 + 25 && mins <= 15 * 60 + 30;
  if (!inSession) return null;
  const age = (ts?: string) => (ts ? Math.floor((now.getTime() - new Date(ts).getTime()) / 60000) : null);
  const items = [
    { name: "chain data", a: age((chain.data as any)?.ts) },
    { name: "gamma run", a: age((walls.data as any)?.ts) },
  ].filter((x) => x.a != null && x.a > STALE_MIN);
  if (!items.length) return null;
  return (
    <div className="w-full px-4 py-1.5 text-[12px]" style={{ background: "var(--alert-bg)", color: "var(--alert-fg)" }}>
      {items.map((x) => `${x.name} ${x.a} min old`).join(" · ")} · <Link to="/health" className="underline-offset-2 hover:underline">Health ›</Link>
    </div>
  );
}
```

with exactly this:

```tsx
function StaleStrip() {
  const { symbol } = useSymbol();
  const chain = useIvFront(symbol);
  const walls = useWalls(symbol);
  const sess = useSessions();
  const nextOpen = useNextOpen().data ?? null;  // S100-S
  const [, setT] = useState(0);
  useEffect(() => { const id = setInterval(() => setT((t) => t + 1), 30_000); return () => clearInterval(id); }, []);
  const now = new Date();
  const ist = new Date(now.getTime() + 5.5 * 3600_000);
  const mins = ist.getUTCHours() * 60 + ist.getUTCMinutes();
  // S100-S: session-state note (neutral): pre-open, closing session, closed
  const session = (sess.data?.session ?? null) as string | null;
  const sessToday = session != null && session === istToday();
  const dd = (d: string) => new Date(d + "T00:00:00").toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
  const note = session == null ? null
    : sessToday && mins < 9 * 60 + 16 ? "Pre-open · figures are from the pre-open chain until the first 1-min bar at 09:16"
    : sessToday && mins >= 15 * 60 + 15 && mins < 15 * 60 + 45 ? "Closing session · spot held since 15:15 · closing γ runs 15:30 / 15:35 / 15:40"
    : !sessToday || mins >= 15 * 60 + 45 ? `Closed · showing the ${dd(session)} session${nextOpen ? ` · next open ${dd(nextOpen)}` : ""}`
    : null;
  const inSession = sessToday && mins >= 9 * 60 + 25 && mins <= 15 * 60 + 45;  // S100-S: was 15:30
  const age = (ts?: string) => (ts ? Math.floor((now.getTime() - new Date(ts).getTime()) / 60000) : null);
  const items = inSession ? [
    { name: "chain data", a: age((chain.data as any)?.ts) },
    { name: "gamma run", a: age((walls.data as any)?.ts) },
  ].filter((x) => x.a != null && x.a > STALE_MIN) : [];
  if (!note && !items.length) return null;
  return (
    <>
      {note && <div className="w-full px-4 py-1.5 text-[12px]" style={{ background: "var(--s2)", color: "var(--ink-2)" }}>{note}</div>}
      {items.length > 0 && (
        <div className="w-full px-4 py-1.5 text-[12px]" style={{ background: "var(--alert-bg)", color: "var(--alert-fg)" }}>
          {items.map((x) => `${x.name} ${x.a} min old`).join(" · ")} · <Link to="/health" className="underline-offset-2 hover:underline">Health ›</Link>
        </div>
      )}
    </>
  );
}
```

## Change 2 — `src/pages/Board.tsx` (FUT·BASIS cell sub-line only)

Replace exactly:

```tsx
            {basisChg != null && <><Mark delta={basisChg} />{sgn(basisChg, 1)} · </>}{contract ?? ""}
```

with exactly:

```tsx
            {basisChg != null && <><Mark delta={basisChg} />{sgn(basisChg, 1)} · </>}{contract ?? ""}{n(fut?.spot_price) != null && fut?.ts ? ` · vs spot ${num(n(fut?.spot_price)!, 1)} @ ${istTime(fut.ts)}` : ""}
```

(`fut` is the `index_futures_snapshots` row Board already reads with `select("*")`; `n`, `num`, `istTime` already exist
in Board.tsx.) Nothing else in Board changes.

## Constraints

No `supabase.` line added, edited or removed; no other file; no colour token other than the two named (`--s2`, `--ink-2`
for the note; the alert strip unchanged).

## Reply with

Both files and each replacement (old → new). If any quoted text does not exist exactly as quoted, change nothing and say which.

---

## Checks (Claude / operator)

1. Guard: round copy, allowlist `src/components/AppShell.tsx|src/pages/Board.tsx`; two paths M; no new data reads; no
   credentials; no vanna/charm; tsc + build clean. Expected size computed with difflib on the quoted text: AppShell
   +23 / −9 (import ±1, StaleStrip +22 / −8), Board +1 / −1 → **+24 / −10** (git may align a line differently; a
   different count means read the diff, not fail).
2. Staging read (Saturday): the strip reads `Closed · showing the 23 Oct session · next open 26 Oct`; FUT·BASIS sub-line
   ends `· vs spot <x> @ <hh:mm>` with x = that row's `spot_price` (checked through roq); no stale strip (not in session).
   Pre-open / closing / stale-to-15:45: Part C Monday.
3. Promote, backup `.bak-1aeb000`, S100-L retention (delete `.bak-142c3e6`).

---

## Round record

**Wording** approved 2026-10-24 ~18:31 IST (S100-S). **Lovable** `8a5db77` "Changes" → `f964e40` "Updated AppShell and Board";
reply: both files as quoted.

**Guard** (`~/s100m/mv_lovable_guard_s100s.sh`, allowlist AppShell + Board; `diff` one line): two paths M; no new data
reads, no credentials, no vanna/charm; build clean; staging `f964e40`; **2 files, 24 insertions, 10 deletions** = the
difflib count of the quoted text.

**Staging read** 18:40 IST (NIFTY): strip `Closed · showing the 23 Oct session · next open 26 Oct`; FUT·BASIS `22,589 · −11.0`,
sub-line `▼ −59.4 · 27 OCT · vs spot 22,600.0 @ 16:00`.

**What the new sub-line exposed (box reads 18:41–18:42 IST, 10-23 NIFTY):** the index is held at the source from 15:15 to
15:29 (1-min 15:15:04, chain 15:15–15:25 and γ 15:15 / 15:20 all 22,516.4); the official close 22,600.0 appears on the chain
from the 15:30 run and in the 16:00 `dhan_idx_i` capture. `index_futures_snapshots` rows at 15:30 / 15:35 / 15:40 still carry
`spot_price` 22,516.4 (stored basis +63.7 / +67.6 / +72.6 against a true ≈ −20 / −16 / −11 vs the close); the 16:00 row
(spot 22,600.0, basis −11.0) is right. **TD candidate:** the futures writer's spot source lags the chain's by ≥ 10 min in the
closing window; fix = take the chain's spot. Refines R8: the same-fetch pair holds in session, not 15:30–15:40. Accepted as
not blocking the promote — the sub-line makes the stale reference visible ("vs spot 22,516.4 @ 15:40").

**Promoted** 18:48 IST (log `~/s100m/promote_f964e40.log`): bundle-string counts all 1; backup `.bak-1aeb000`; `LIVE = BUILD`;
bundle `assets/index-BFOk56iL.js`; S100-L: `.bak-142c3e6` deleted; left `.bak-1aeb000`, `.bak-3366bf1`, `.bak-2ee83e1` + 3
`PRE_*`. **Live read** 18:49 IST: strip and sub-line as on staging.
