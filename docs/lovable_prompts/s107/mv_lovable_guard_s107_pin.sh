#!/usr/bin/env bash
# mv_lovable_guard_s107_pin.sh -- S107 pin switch + labels (operator rulings R2/R3/R4, 2026-11-25; Board commits caecef8, cba0695, 457fc99): check origin/main since BASE, then build /staging/.
# Modelled on docs/lovable_prompts/s103/mv_lovable_guard_s103r20.sh, plus the S104 proxy build settings and bundle audit.
# REVISION 2 (2026-11-25 evening). Revision 1 (commit a9b38bc) built WITHOUT the proxy settings: staging showed "no run" on every tile. Do not use revision 1.
# Never pushes, never touches live.
#   bash ~/mv_lovable_guard_s107_pin.sh 90cb618
#   MV_GUARD_NOBUILD=1 bash ~/mv_lovable_guard_s107_pin.sh 90cb618      (checks only)
# Run outside 08:30-15:40 IST on a trading day (it builds on the production box).
set -euo pipefail
BASE="${1:?usage: mv_lovable_guard_s107_pin.sh <BASE_SHA>}"
TREE="${MV_TREE:-$HOME/meridian-connect}"
cd "$TREE"
git fetch -q origin
HEAD_SHA=$(git rev-parse --short origin/main)
echo "== base $BASE  ->  origin/main $HEAD_SHA   (S107: Pin = gross pin, Net peak, legacy/experimental labels, manual v0.6)"
git merge-base --is-ancestor "$BASE" origin/main || { echo "FAIL: $BASE is not an ancestor of origin/main"; exit 1; }
echo "== commits:"; git log --format='   %h %an  %s' "$BASE"..origin/main
[ -n "$(git rev-list "$BASE"..origin/main)" ] || { echo "FAIL: no new commits since $BASE"; exit 1; }
ALLOW='src/lib/board\.ts|src/pages/Board\.tsx|src/pages/Home\.tsx|src/lib/read\.ts|src/components/board/LadderPanel\.tsx|src/components/board/PinFlowsBody\.tsx|src/components/NarrativeModal\.tsx|src/components/AmbientTrajectory\.tsx|src/marketview/sections\.tsx|public/help/manual\.json'
fail=0
echo "== changed paths:"
while IFS=$'\t' read -r st path rest; do
  p="${rest:-$path}"; echo "   $st $p"
  printf '%s\n' "$p" | grep -qxE "$ALLOW" || { echo "   FAIL: outside allowlist -> $p"; fail=1; }
done < <(git diff --name-status "$BASE" origin/main)
ADDED=$(git diff "$BASE" origin/main -- src | grep -E '^\+[^+]' || true)
chk() { local label="$1" re="$2" text="${3-$ADDED}"; local hits; hits=$(printf '%s\n' "$text" | grep -nE "$re" || true)
  if [ -n "$hits" ]; then echo "   FAIL: $label"; printf '%s\n' "$hits" | head -5 | sed 's/^/      /'; fail=1; else echo "   ok   $label"; fi; }
echo "== added-line checks (src only):"
chk "no rpc/channel/storage/functions/createClient/fetch added" 'supabase\.(rpc|channel|storage|functions)|createClient|fetch\('
chk "no direct .from( added (the pin read goes through latestBySymbol)" '\.from\('
chk "no credentials" 'eyJ[A-Za-z0-9_-]{10,}|service_role|SUPABASE_(URL|ANON|SERVICE)|VITE_SUPABASE|sk_(live|test)_|pk_(live|test)_'
chk "no polling option added" 'refetchInterval|staleTime|refetchOnWindowFocus|refetchIntervalInBackground'
echo "== round fingerprint (the tree at origin/main):"
B=$(git show origin/main:src/lib/board.ts)
n=$(printf '%s\n' "$B" | grep -c 'latestBySymbol("v_gex_pin_gross"'); [ "$n" = 1 ] && echo "   ok   one read of v_gex_pin_gross, through latestBySymbol" || { echo "   FAIL: $n reads of v_gex_pin_gross (expected 1)"; fail=1; }
P=$(git show origin/main:src/pages/Board.tsx)
printf '%s\n' "$P" | grep -q 'pinLegs === "call_only"' && echo "   ok   leg codes call_only / put_only" || { echo "   FAIL: leg codes not call_only/put_only"; fail=1; }
printf '%s\n' "$P" | grep -q 'experimental' && echo "   ok   Flip carries experimental" || { echo "   FAIL: experimental not found in Board.tsx"; fail=1; }
n=$( { git grep -c 'legacy, unvalidated' origin/main -- src || true; } | wc -l); [ "$n" -ge 5 ] && echo "   ok   'legacy, unvalidated' present in $n src files" || { echo "   FAIL: 'legacy, unvalidated' in only $n src files (expected at least 5)"; fail=1; }
printf '%s\n' "$P" | grep -q 'Net peak' && echo "   ok   Net peak present" || { echo "   FAIL: Net peak not found"; fail=1; }
n=$( { git grep -n 'γ-conc\|γ-CONC' origin/main -- src || true; } | { grep -vE ':[0-9]+:[[:space:]]*//' || true; } | wc -l); [ "$n" = 0 ] && echo "   ok   no γ-conc left in src (code comments excepted)" || { echo "   FAIL: γ-conc still on $n src lines"; fail=1; }
for f in src/pages/TapeFlowBook.tsx src/lib/tapePin.ts src/lib/tapeClient.ts src/lib/queries.ts; do
  git diff --quiet "$BASE" origin/main -- "$f" && echo "   ok   unchanged: $f" || { echo "   FAIL: changed: $f"; fail=1; }
done
MV=$(git show origin/main:public/help/manual.json | python3 -c 'import json,sys; print(json.load(sys.stdin).get("manual_version",""))')
case "$MV" in v0.6*) echo "   ok   manual.json is $MV";; *) echo "   FAIL: manual.json is '$MV' (expected v0.6: run s107_manual_v06.sh, commit, push)"; fail=1;; esac
[ "$fail" = 0 ] || { echo "== GUARD FAILED -- nothing built. Paste this output to Claude."; exit 1; }
[ -n "${MV_GUARD_NOBUILD:-}" ] && { echo "== GUARD PASSED (checks only; MV_GUARD_NOBUILD set, nothing built)"; exit 0; }
echo "== guard passed; fast-forward local tree and build /staging/"
git status --porcelain | grep -v '^??' && { echo "FAIL: local tracked changes present"; exit 1; } || true
git merge -q --ff-only origin/main
npx tsc --noEmit -p tsconfig.json
# S104 (CLAUDE.md rule 26): the bundle must read through our own domain. The shell variables beat the committed .env.
VITE_SUPABASE_URL=https://marketview.meridianalpha.in VITE_SUPABASE_ANON_KEY=proxy npx vite build --base=/staging/ --outDir /tmp/mv-staging-build --emptyOutDir 2>&1 | tail -3
if grep -rlqE "kilmcowcikwdhvdxwofi|eyJ[A-Za-z0-9_-]{20,}" "/tmp/mv-staging-build/assets/"; then echo "FAIL: bundle holds the project ref or a JWT-shaped string"; exit 1; else echo "   ok   bundle audit: no project ref, no JWT-shaped string"; fi
grep -rlqF "marketview.meridianalpha.in" "/tmp/mv-staging-build/assets/" && echo "   ok   bundle reads through our own domain" || { echo "FAIL: own domain not in bundle"; exit 1; }
for m in 'of band gross' 'Net peak' 'v_gex_pin_gross' 'legacy, unvalidated' 'experimental'; do
  grep -rlqF "$m" /tmp/mv-staging-build/assets/ --include='*.js' && echo "   ok   marker in built assets: $m" || { echo "FAIL: marker not in any assets/*.js: $m"; exit 1; }
done
sudo rsync -a --delete /tmp/mv-staging-build/ /var/www/marketview-staging/
echo "== STAGING DEPLOYED $(git rev-parse --short HEAD) -- live untouched, nothing pushed"
git diff --stat "$BASE" HEAD | tail -1
