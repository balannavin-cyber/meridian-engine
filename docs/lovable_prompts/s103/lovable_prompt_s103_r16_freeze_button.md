# Lovable prompt — S103 round 2: explicit freeze button and frozen strip (R16 / S103-I)

Base: `main` at `05f556c` (= live). Ruling S103-I (2026-10-30 21:05 IST, `claude/rulings_s103.md`). TD-S97-NEW-19.

Paste everything below the line into Lovable, on `main`.

---

Make exactly the 5 replacements below, in exactly one file: `src/components/AppShell.tsx`. Each OLD text appears in that file
exactly once; replace it with the NEW text verbatim.

Rules:
- Change nothing else. Do not touch any other file, any formatter, any data read (`supabase.from(...)`), any hook, any query option.
- Commit directly to `main` with the message: `S103-I: freeze is an explicit header button (no Space key) and a full-width strip says since when`.

### R1. state — remember when the freeze began

OLD:
```
  const [frozen, setFrozen] = useState(false);
```
NEW:
```
  const [frozen, setFrozen] = useState(false);
  const [frozenSince, setFrozenSince] = useState<Date | null>(null);
```

### R2. the effect that pauses and resumes polling also stamps the time

OLD:
```
    onlineManager.setOnline(!frozen);
    if (!frozen) refetchAll();
```
NEW:
```
    onlineManager.setOnline(!frozen);
    setFrozenSince(frozen ? new Date() : null);
    if (!frozen) refetchAll();
```

### R3. remove the Space key handler (freezing is no longer a bare key press)

OLD:
```
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (e.code === "Space") { e.preventDefault(); setFrozen((f) => !f); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

```
NEW: (delete the whole block above, leaving no replacement text and no blank-line pile-up)

### R4. the header control is always visible and toggles

OLD:
```
  const Frozen = frozen && (
    <button onClick={() => setFrozen(false)} title="Space to resume"
      className="rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.1em]"
      style={{ border: "1px solid var(--sel)", color: "var(--sel)" }}>frozen</button>
  );
```
NEW:
```
  const Frozen = (
    <button onClick={() => setFrozen((f) => !f)} title={frozen ? "Resume live updates" : "Freeze updates (pause polling)"}
      className="rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.1em]"
      style={{ border: "1px solid var(--sel)", color: "var(--sel)" }}>{frozen ? "resume" : "freeze"}</button>
  );
```

### R5. a full-width strip while frozen

OLD:
```
      <StaleStrip />
```
NEW:
```
      <StaleStrip />
      {frozen && (
        <div className="w-full px-4 py-1.5 text-[12px]" style={{ background: "var(--alert-bg)", color: "var(--alert-fg)" }}>
          frozen since {frozenSince ? frozenSince.toLocaleTimeString("en-GB", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit" }) : "—"} · data not updating
        </div>
      )}
```

---

## Operator notes (not for Lovable)

- **Effect:** the header always shows a small `freeze` button (`resume` while frozen). While frozen, a full-width strip under the header reads `frozen since hh:mm · data not updating` (IST). The Space bar no longer freezes anything (it also scrolls the page, which is why a stray press froze the board unseen on 10-23: both symbols stuck at 11:10, a reload fixed it). Polling, refetch and every query are untouched.
- **Reads before promote (staging, Chrome):** (1) header shows `freeze`; Space does nothing. (2) Click `freeze` → button reads `resume`, strip appears with the clock time in IST; a second tab on the same page keeps its data. (3) Click `resume` → strip gone, data refreshes at once. (4) Narrow window (< 1024 px): the same button sits beside the symbol toggle.
- **Guard:** `mv_lovable_guard_s103r16.sh 05f556c` (allowlist = this one file; no new data read; fingerprint: `frozenSince` ×≥3, `data not updating`, no `e.code === "Space"`).
- Closes TD-S97-NEW-19 on the next live read. R36 closes as read, no change (S103-I).
