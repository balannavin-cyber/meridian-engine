#!/usr/bin/env bash
# mv_lovable_guard_s103.sh — round copy of mv_lovable_guard.sh v2 for S103 round 1 (S103-A Health token scale, S103-C Context skew on expiry day).
# Differences from v2, and only these: allowlist = src/pages/Health.tsx, src/marketview/state.ts, src/marketview/sections.tsx;
# NO data read may be added; round fingerprint below. Never pushes, never touches live.
#   bash ~/mv_lovable_guard_s103.sh 30998f2
#   MV_GUARD_NOBUILD=1 bash ...   (checks only)
set -euo pipefail
BASE="${1:?usage: mv_lovable_guard_s103.sh <BASE_SHA>}"
TREE="${MV_TREE:-$HOME/meridian-connect}"
cd "$TREE"
git fetch -q origin
HEAD_SHA=$(git rev-parse --short origin/main)
echo "== base $BASE  ->  origin/main $HEAD_SHA   (S103 round 1: S103-A / S103-C)"
git merge-base --is-ancestor "$BASE" origin/main || { echo "FAIL: $BASE is not an ancestor of origin/main"; exit 1; }
echo "== commits:"; git log --format='   %h %an  %s' "$BASE"..origin/main
[ -n "$(git rev-list "$BASE"..origin/main)" ] || { echo "FAIL: no new commits since $BASE"; exit 1; }
ALLOW='src/pages/Health.tsx|src/marketview/state.ts|src/marketview/sections.tsx'
fail=0; npaths=0
echo "== changed paths:"
while IFS=$'\t' read -r st path rest; do
  p="${rest:-$path}"; echo "   $st $p"; npaths=$((npaths+1))
  printf '%s\n' "$p" | grep -qxE "$ALLOW" || { echo "   FAIL: outside allowlist -> $p"; fail=1; }
done < <(git diff --name-status "$BASE" origin/main)
[ "$npaths" = 3 ] && echo "   ok   exactly 3 paths" || { echo "   FAIL: $npaths paths changed (expected 3)"; fail=1; }
ADDED=$(git diff "$BASE" origin/main | grep -E '^\+[^+]' || true)
REMOVED=$(git diff "$BASE" origin/main | grep -E '^-[^-]' || true)
chk() { local label="$1" re="$2" text="${3-$ADDED}"; local hits; hits=$(printf '%s\n' "$text" | grep -nE "$re" || true)
  if [ -n "$hits" ]; then echo "   FAIL: $label"; printf '%s\n' "$hits" | head -5 | sed 's/^/      /'; fail=1; else echo "   ok   $label"; fi; }
echo "== added-line checks:"
chk "no data read added" 'supabase\.(from|rpc|channel|storage|functions)|createClient|fetch\(|\.from\("'
chk "no credentials" 'eyJ[A-Za-z0-9_-]{10,}|service_role|SUPABASE_(URL|ANON|SERVICE)|VITE_SUPABASE|sk_(live|test)_|pk_(live|test)_'
chk "no vanna/charm (L78-1)" '\b([Vv][Aa][Nn][Nn][Aa]|[Cc][Hh][Aa][Rr][Mm])\b'
chk "no formatter changed" '(function|const) (fmtNum|fmtSigned|fmtPct|crLakh|lad|fmtCr|statusFor|ageMinutes)\b' "$REMOVED"
echo "== round fingerprint (the tree at origin/main):"
H=$(git show origin/main:src/pages/Health.tsx); ST=$(git show origin/main:src/marketview/state.ts); SX=$(git show origin/main:src/marketview/sections.tsx)
n=$(printf '%s\n' "$H" | grep -c 'statusFor(tokenProbeAge, 1440)'); [ "$n" = 1 ] && echo "   ok   token tile on the 1440-min scale" || { echo "   FAIL: $n of 1 statusFor(tokenProbeAge, 1440)"; fail=1; }
chk "the 30-minute token test is gone" 'tokenProbeAge <= 30' "$H"
n=$(printf '%s\n' "$SX" | grep -c 'SKIPPED_EXPIRY'); [ "$n" = 2 ] && echo "   ok   2 SKIPPED_EXPIRY branches in sections.tsx" || { echo "   FAIL: $n of 2 SKIPPED_EXPIRY in sections.tsx"; fail=1; }
n=$(printf '%s\n' "$ST" | grep -c 'ivNextSkew98'); [ "$n" = 2 ] && echo "   ok   ivNextSkew98 defined and returned in state.ts" || { echo "   FAIL: $n of 2 ivNextSkew98 in state.ts"; fail=1; }
n=$(printf '%s\n' "$SX" | grep -c 'ivNextSkew98'); [ "$n" -ge 1 ] && echo "   ok   ivNextSkew98 rendered in sections.tsx" || { echo "   FAIL: ivNextSkew98 not rendered"; fail=1; }
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
