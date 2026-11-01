#!/usr/bin/env bash
# mv_lovable_guard_s103r20.sh — round copy of mv_lovable_guard_s103r16.sh for S103 round 3 (R20 / S103-J: previous close from v_close_print).
# Differences from the round-1 guard, and only these: allowlist = src/lib/board.ts (exactly 1 path); exactly ONE data read may be added and it must be .from("v_close_print");
# round fingerprint below. Never pushes, never touches live.
#   bash ~/mv_lovable_guard_s103r20.sh 05f556c
#   MV_GUARD_NOBUILD=1 bash ...   (checks only)
set -euo pipefail
BASE="${1:?usage: mv_lovable_guard_s103r20.sh <BASE_SHA>}"
TREE="${MV_TREE:-$HOME/meridian-connect}"
cd "$TREE"
git fetch -q origin
HEAD_SHA=$(git rev-parse --short origin/main)
echo "== base $BASE  ->  origin/main $HEAD_SHA   (S103 round 3: R20 / S103-J)"
git merge-base --is-ancestor "$BASE" origin/main || { echo "FAIL: $BASE is not an ancestor of origin/main"; exit 1; }
echo "== commits:"; git log --format='   %h %an  %s' "$BASE"..origin/main
[ -n "$(git rev-list "$BASE"..origin/main)" ] || { echo "FAIL: no new commits since $BASE"; exit 1; }
ALLOW='src/lib/board.ts'
fail=0; npaths=0
echo "== changed paths:"
while IFS=$'\t' read -r st path rest; do
  p="${rest:-$path}"; echo "   $st $p"; npaths=$((npaths+1))
  printf '%s\n' "$p" | grep -qxE "$ALLOW" || { echo "   FAIL: outside allowlist -> $p"; fail=1; }
done < <(git diff --name-status "$BASE" origin/main)
[ "$npaths" = 1 ] && echo "   ok   exactly 1 path" || { echo "   FAIL: $npaths paths changed (expected 1)"; fail=1; }
ADDED=$(git diff "$BASE" origin/main | grep -E '^\+[^+]' || true)
REMOVED=$(git diff "$BASE" origin/main | grep -E '^-[^-]' || true)
chk() { local label="$1" re="$2" text="${3-$ADDED}"; local hits; hits=$(printf '%s\n' "$text" | grep -nE "$re" || true)
  if [ -n "$hits" ]; then echo "   FAIL: $label"; printf '%s\n' "$hits" | head -5 | sed 's/^/      /'; fail=1; else echo "   ok   $label"; fi; }
echo "== added-line checks:"
chk "no rpc/channel/storage/functions/createClient/fetch added" 'supabase\.(rpc|channel|storage|functions)|createClient|fetch\('
n=$(printf '%s\n' "$ADDED" | grep -cE '\.from\(' || true)
m=$(printf '%s\n' "$ADDED" | grep -cE '\.from\("v_close_print"\)' || true)
[ "$n" = 1 ] && [ "$m" = 1 ] && echo "   ok   exactly one added .from( and it is v_close_print" || { echo "   FAIL: added .from( count $n, of which v_close_print $m (expected 1 and 1)"; fail=1; }
chk "no credentials" 'eyJ[A-Za-z0-9_-]{10,}|service_role|SUPABASE_(URL|ANON|SERVICE)|VITE_SUPABASE|sk_(live|test)_|pk_(live|test)_'
chk "no vanna/charm (L78-1)" '\b([Vv][Aa][Nn][Nn][Aa]|[Cc][Hh][Aa][Rr][Mm])\b'
chk "no polling option added" 'refetchInterval|staleTime|refetchOnWindowFocus|refetchIntervalInBackground'
chk "no formatter changed" '(function|const) (fmtNum|fmtSigned|fmtPct|istAt|statusFor|ageMinutes)\b' "$REMOVED"
echo "== round fingerprint (the tree at origin/main):"
A=$(git show origin/main:src/lib/board.ts)
n=$(printf '%s\n' "$A" | grep -c 'v_close_print'); [ "$n" -ge 1 ] && echo "   ok   v_close_print present ($n lines)" || { echo "   FAIL: v_close_print not found"; fail=1; }
n=$(printf '%s\n' "$A" | grep -c 'order("close_rank"'); [ "$n" = 1 ] && echo "   ok   ordered by close_rank once" || { echo "   FAIL: $n of 1 order(close_rank)"; fail=1; }
chk "the old 16:00-only read is gone" 'istAt\(prev, "16:00"\)' "$A"
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
