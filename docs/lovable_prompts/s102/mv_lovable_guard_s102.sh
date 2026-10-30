#!/usr/bin/env bash
# mv_lovable_guard_s102.sh — round copy of mv_lovable_guard.sh v2 for S102 / ADR-032 D1 (Γ sizes per 1 % move).
# Differences from v2, and only these: the allowlist is the seven paths of this round; data reads are allowed only of the
# seven *_1pct views (any number of them); and the round's own fingerprint is checked (no unsuffixed read of a rescaled
# source survives in the seven files; no formatter is touched). Everything else is v2: never pushes, never touches live.
#
#   bash ~/mv_lovable_guard_s102.sh <BASE_SHA>          (BASE = 27c0e17, the commit /staging/ and live were built from)
#   MV_GUARD_NOBUILD=1 bash ...                         (checks only — used to rehearse the guard on a clone)
set -euo pipefail
BASE="${1:?usage: mv_lovable_guard_s102.sh <BASE_SHA>}"
TREE="${MV_TREE:-$HOME/meridian-connect}"
cd "$TREE"
git fetch -q origin
HEAD_SHA=$(git rev-parse --short origin/main)
echo "== base $BASE  ->  origin/main $HEAD_SHA   (S102 round: seven _1pct views)"
git merge-base --is-ancestor "$BASE" origin/main || { echo "FAIL: $BASE is not an ancestor of origin/main (history rewritten?)"; exit 1; }
echo "== commits:"; git log --format='   %h %an  %s' "$BASE"..origin/main
[ -n "$(git rev-list "$BASE"..origin/main)" ] || { echo "FAIL: no new commits since $BASE"; exit 1; }

ALLOW='src/lib/board.ts|src/lib/terrain.ts|src/lib/read.ts|src/pages/Board.tsx|src/pages/Home.tsx|src/pages/Lab3D.tsx|src/components/board/LadderPanel.tsx'
VIEWS='v_gex_abs_exposure_1pct|v_gex_net_gamma_river_1pct|v_gex_strike_terrain_1pct|v_gex_greeks_l2_net_1pct|v_gex_greeks_l2_strike_1pct|v_gex_strike_snapshots_1pct|v_gamma_metrics_1pct'
fail=0
echo "== changed paths:"
npaths=0
while IFS=$'\t' read -r st path rest; do
  p="${rest:-$path}"; echo "   $st $p"; npaths=$((npaths+1))
  printf '%s\n' "$p" | grep -qxE "$ALLOW" || { echo "   FAIL: outside allowlist -> $p"; fail=1; }
done < <(git diff --name-status "$BASE" origin/main)
[ "$npaths" = 7 ] && echo "   ok   exactly 7 paths" || { echo "   FAIL: $npaths paths changed (expected 7)"; fail=1; }

ADDED=$(git diff "$BASE" origin/main | grep -E '^\+[^+]' || true)
chk() { local label="$1" re="$2" text="${3-$ADDED}"; local hits; hits=$(printf '%s\n' "$text" | grep -nE "$re" || true)
  if [ -n "$hits" ]; then echo "   FAIL: $label"; printf '%s\n' "$hits" | head -5 | sed 's/^/      /'; fail=1; else echo "   ok   $label"; fi; }
echo "== added-line checks:"
READS='supabase\.(from|rpc|channel|storage|functions)|createClient|fetch\('
OTHER=$(printf '%s\n' "$ADDED" | grep -E "$READS" | grep -vE "supabase\.from\(\"($VIEWS)\"\)" || true)
chk "no data reads other than the seven _1pct views" '.' "$OTHER"
chk "no credentials"         'eyJ[A-Za-z0-9_-]{10,}|service_role|SUPABASE_(URL|ANON|SERVICE)|VITE_SUPABASE|sk_(live|test)_|pk_(live|test)_'
chk "no vanna/charm (L78-1)" '\b([Vv][Aa][Nn][Nn][Aa]|[Cc][Hh][Aa][Rr][Mm])\b'
REMOVED=$(git diff "$BASE" origin/main | grep -E '^-[^-]' || true)
chk "no formatter changed (crLakh / lad / fmtCr / lak)" '(const (crLakh|lad|fmtCr|lak) =)' "$REMOVED"
echo "== round fingerprint (the tree at origin/main):"
for f in src/lib/board.ts src/lib/terrain.ts src/lib/read.ts src/pages/Board.tsx src/pages/Home.tsx src/pages/Lab3D.tsx src/components/board/LadderPanel.tsx; do
  git show "origin/main:$f" > "/tmp/mvg_s102_$(basename "$f")"
done
T=/tmp/mvg_s102_
left=$( { grep -nE 'latestBySymbol\("v_gex_abs_exposure",|from\("v_gex_net_gamma_river"\)|from\("v_gex_strike_terrain"\)|"v_gex_greeks_l2_net"|from\("v_gex_greeks_l2_strike"\)' ${T}board.ts ${T}terrain.ts || true;
          grep -nE 'abs\?\.(net|abs)_gex_cr\)' ${T}Board.tsx ${T}Home.tsx ${T}read.ts || true;
          grep -nE 'fl\("(net_gex_drift_(time_cr_per_day|iv_cr_per_volpt)|gross_strike_gex_drift_(time|iv))"\)' ${T}Board.tsx || true;
          grep -nE 'unit definition pending|unit pending' ${T}Board.tsx ${T}LadderPanel.tsx ${T}Lab3D.tsx || true; } )
chk "no unsuffixed read or 'unit pending' label left in the seven files" '.' "$left"
n1=$(cat ${T}board.ts ${T}terrain.ts | grep -oE "\"($VIEWS)\"" | sort -u | wc -l)
[ "$n1" = 7 ] && echo "   ok   all seven _1pct views referenced" || { echo "   FAIL: $n1 of 7 _1pct views referenced"; fail=1; }
rm -f /tmp/mvg_s102_*
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
