#!/usr/bin/env bash
# mv_lovable_guard_s102b.sh — round copy of mv_lovable_guard.sh v2 for S102 / ADR-032 D1 round 2 (legacy pages, rescale ruled 2026-10-30 09:43 IST).
# Differences from v2, and only these: allowlist = src/lib/queries.ts, src/marketview/sections.tsx; data reads only of
# v_gamma_metrics_1pct / v_gex_strike_snapshots_1pct; round fingerprint below. Never pushes, never touches live.
#   bash ~/mv_lovable_guard_s102b.sh 8326ed0
#   MV_GUARD_NOBUILD=1 bash ...   (checks only)
set -euo pipefail
BASE="${1:?usage: mv_lovable_guard_s102b.sh <BASE_SHA>}"
TREE="${MV_TREE:-$HOME/meridian-connect}"
cd "$TREE"
git fetch -q origin
HEAD_SHA=$(git rev-parse --short origin/main)
echo "== base $BASE  ->  origin/main $HEAD_SHA   (S102 round 2: legacy pages)"
git merge-base --is-ancestor "$BASE" origin/main || { echo "FAIL: $BASE is not an ancestor of origin/main"; exit 1; }
echo "== commits:"; git log --format='   %h %an  %s' "$BASE"..origin/main
[ -n "$(git rev-list "$BASE"..origin/main)" ] || { echo "FAIL: no new commits since $BASE"; exit 1; }
ALLOW='src/lib/queries.ts|src/marketview/sections.tsx'
VIEWS='v_gamma_metrics_1pct|v_gex_strike_snapshots_1pct'
fail=0; npaths=0
echo "== changed paths:"
while IFS=$'\t' read -r st path rest; do
  p="${rest:-$path}"; echo "   $st $p"; npaths=$((npaths+1))
  printf '%s\n' "$p" | grep -qxE "$ALLOW" || { echo "   FAIL: outside allowlist -> $p"; fail=1; }
done < <(git diff --name-status "$BASE" origin/main)
[ "$npaths" = 2 ] && echo "   ok   exactly 2 paths" || { echo "   FAIL: $npaths paths changed (expected 2)"; fail=1; }
ADDED=$(git diff "$BASE" origin/main | grep -E '^\+[^+]' || true)
REMOVED=$(git diff "$BASE" origin/main | grep -E '^-[^-]' || true)
chk() { local label="$1" re="$2" text="${3-$ADDED}"; local hits; hits=$(printf '%s\n' "$text" | grep -nE "$re" || true)
  if [ -n "$hits" ]; then echo "   FAIL: $label"; printf '%s\n' "$hits" | head -5 | sed 's/^/      /'; fail=1; else echo "   ok   $label"; fi; }
echo "== added-line checks:"
OTHER=$(printf '%s\n' "$ADDED" | grep -E 'supabase\.(rpc|channel|storage|functions)|createClient|fetch\(|\.from\("' | grep -vE "\.from\(\"($VIEWS)\"\)" || true)
chk "no data reads other than the two _1pct views" '.' "$OTHER"
chk "no credentials" 'eyJ[A-Za-z0-9_-]{10,}|service_role|SUPABASE_(URL|ANON|SERVICE)|VITE_SUPABASE|sk_(live|test)_|pk_(live|test)_'
chk "no vanna/charm (L78-1)" '\b([Vv][Aa][Nn][Nn][Aa]|[Cc][Hh][Aa][Rr][Mm])\b'
chk "no formatter changed (fmtNum / fmtSigned / fmtPct)" '(function|const) (fmtNum|fmtSigned|fmtPct)\b' "$REMOVED"
echo "== round fingerprint (the tree at origin/main):"
Q=$(git show origin/main:src/lib/queries.ts); SX=$(git show origin/main:src/marketview/sections.tsx)
chk "no read of raw gex_strike_snapshots in queries.ts" 'from\("gex_strike_snapshots"\)' "$Q"
chk "no gamma_metrics read selecting net_gex in queries.ts" '"[^"]*\bnet_gex\b[^"]*"' "$(printf '%s\n' "$Q" | grep -A1 'from("gamma_metrics")')"
chk "no '}k' mislabel left in sections.tsx" 'fmtNum\(s\.dampenTotal\)\}k' "$SX"
n=$(printf '%s\n' "$Q" | grep -cE 'from\("v_gex_strike_snapshots_1pct"\)'); [ "$n" = 3 ] && echo "   ok   3 strike reads on v_gex_strike_snapshots_1pct" || { echo "   FAIL: $n of 3 strike reads on the _1pct view"; fail=1; }
n=$(printf '%s\n' "$Q" | grep -cE 'from\("v_gamma_metrics_1pct"\)'); [ "$n" = 2 ] && echo "   ok   2 gamma reads on v_gamma_metrics_1pct" || { echo "   FAIL: $n of 2 gamma reads on the _1pct view"; fail=1; }
n=$(printf '%s\n' "$Q" | grep -cE 'net_gex: (\(data as any\)|r)\.net_gex_1pct|gex_cr: r\.gex_cr_1pct'); [ "$n" = 3 ] && echo "   ok   3 per-1 % mappings" || { echo "   FAIL: $n of 3 per-1 % mappings"; fail=1; }
n=$(printf '%s\n' "$SX" | grep -c 'Cr per 1 %'); [ "$n" = 4 ] && echo "   ok   4 'Cr per 1 %' labels" || { echo "   FAIL: $n of 4 'Cr per 1 %' labels"; fail=1; }
[ "$fail" = 0 ] || { echo "== GUARD FAILED — nothing built. Paste this output to Claude."; exit 1; }
[ -n "${MV_GUARD_NOBUILD:-}" ] && { echo "== GUARD PASSED (checks only; MV_GUARD_NOBUILD set, nothing built)"; exit 0; }
echo "== guard passed; fast-forward local tree and build /staging/"
git status --porcelain | grep -v '^??' && { echo "FAIL: local tracked changes present"; exit 1; } || true
git merge -q --ff-only origin/main
npx tsc --noEmit -p tsconfig.json
npx vite build --base=/staging/ --outDir /tmp/mv-staging-build --emptyOutDir 2>&1 | tail -3
sudo rsync -a --delete /tmp/mv-staging-build/ /var/www/marketview-staging/
echo "== STAGING DEPLOYED $(git rev-parse --short HEAD) — live untouched, nothing pushed"
git diff --stat "$BASE" HEAD | tail -1
