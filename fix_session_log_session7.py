p = "docs/session_notes/session_log.md"
s = open(p, encoding="utf-8").read()

old = "## Session log — v3 canonical one-liners (newest first)\n\n2026-04-22"
new_line = "2026-04-23 · `48d1b6e` · Session 7: breadth cascade root cause CLOSED (C-09 equity_intraday_last stale 27 days -> refresh_equity_intraday_last.py on AWS 09:05 IST cron) + TD-014 breadth writer instrumentation + runbook_update_kite_flow filled + CLAUDE.md v1.3 Rule 13 data contamination registry + C-10 OPEN Kite token propagation manual (Session 9 candidate) · PASS · docs_updated:yes"
new = "## Session log — v3 canonical one-liners (newest first)\n\n" + new_line + "\n2026-04-22"

assert old in s, "anchor text not found - session_log.md structure may have changed"
assert "2026-04-23" not in s.split("(newest first)")[1][:500], "Session 7 line already present - refusing duplicate insert"

open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, 1))
print("Inserted Session 7 one-liner at top of v3 canonical list")
