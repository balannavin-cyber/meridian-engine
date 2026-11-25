#!/usr/bin/env bash
# mv_promote_s107_pin.sh -- promote meridian-connect origin/main (S107: Pin = gross pin, Net peak, legacy/experimental labels, manual v0.6) to live.
# Modelled on docs/lovable_prompts/s103/mv_promote_s103.sh, plus the S104 proxy build settings and bundle audit; deletes no backup.
# REVISION 2 (2026-11-25 evening) = the script as actually run for the promote of d7642c2 at about 18:08 IST. Revision 1 (commit a9b38bc) built WITHOUT the proxy settings and would have emptied the live Board. Do not use revision 1.
# BEFORE FIRST USE compare it with the most recent proven promote
# script on the box (~/mv_promote_s105_tape.sh): if that one has a step this one lacks, stop and tell Claude.
# REFUSING BLOCK: without GO it only checks and prints what it would do.
#   bash ~/mv_promote_s107_pin.sh <WANT_SHA>        (checks + plan, nothing changed)
#   bash ~/mv_promote_s107_pin.sh <WANT_SHA> GO     (checks, then backup -> diff -rq proof -> build -> promote -> retention)
# Preconditions it cannot check: the wrapper SQL is applied and 4a-4f passed; staging was looked at against live data.
set -euo pipefail
WANT="${1:?usage: mv_promote_s107_pin.sh <WANT_SHA> [GO]}"; PREV_JS=index-DcEq-HfE.js; PREV_SHA=90cb618
TREE="$HOME/meridian-connect"; LIVE=/var/www/marketview; BAK="/var/www/marketview.bak-$PREV_SHA"; BUILD=/tmp/mv-live-build
cd "$TREE"; git fetch -q origin
HEAD_SHA=$(git rev-parse --short HEAD); ORIG=$(git rev-parse --short origin/main)
echo "== tree HEAD $HEAD_SHA  origin/main $ORIG  want $WANT"
[ "$HEAD_SHA" = "$WANT" ] && [ "$ORIG" = "$WANT" ] || { echo "REFUSED: tree/origin not at $WANT"; exit 1; }
git merge-base --is-ancestor 457fc99 HEAD || { echo "REFUSED: HEAD does not contain 457fc99"; exit 1; }
[ -z "$(git status --porcelain | grep -v '^??')" ] || { echo "REFUSED: tracked changes present"; exit 1; }
echo "== live now:"; ls "$LIVE/assets/" | grep -E '^index-.*\.js$'
[ -f "$LIVE/assets/$PREV_JS" ] || { echo "REFUSED: live bundle is not $PREV_JS (live is not $PREV_SHA) -- read live before naming anything"; exit 1; }
echo "   live manual.json: $(sha256sum "$LIVE/help/manual.json" | cut -c1-16)..."
echo "== backups now:"; ls -dt /var/www/marketview.bak-* /var/www/marketview.PRE_* 2>/dev/null | sed 's/^/   /'
[ -e "$BAK" ] && { echo "REFUSED: $BAK already exists -- it must be created from live by this block"; exit 1; }
echo "== build $WANT for live (base /):"
npx tsc --noEmit -p tsconfig.json
VITE_SUPABASE_URL=https://marketview.meridianalpha.in VITE_SUPABASE_ANON_KEY=proxy npx vite build --base=/ --outDir "$BUILD" --emptyOutDir 2>&1 | tail -2
NEW_JS=$(ls "$BUILD/assets/" | grep -E '^index-.*\.js$'); echo "   new bundle $NEW_JS"
if grep -rlqE "kilmcowcikwdhvdxwofi|eyJ[A-Za-z0-9_-]{20,}" "$BUILD/assets/"; then echo "REFUSED: bundle holds the project ref or a JWT-shaped string"; exit 1; else echo "   ok   bundle audit: no project ref, no JWT-shaped string"; fi
grep -rlqF "marketview.meridianalpha.in" "$BUILD/assets/" && echo "   ok   bundle reads through our own domain" || { echo "REFUSED: own domain not in bundle"; exit 1; }
grep -q "/assets/$NEW_JS" "$BUILD/index.html" && ! grep -q '/staging/' "$BUILD/index.html" && echo "   ok   index.html references /assets/ at root" || { echo "REFUSED: index.html base is wrong"; exit 1; }
MV=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("manual_version",""))' "$BUILD/help/manual.json")
case "$MV" in v0.6*) echo "   ok   manual.json $MV";; *) echo "REFUSED: manual.json is '$MV', expected v0.6"; exit 1;; esac
for m in 'of band gross' 'Net peak' 'v_gex_pin_gross' 'legacy, unvalidated' 'experimental'; do
  grep -rlqF "$m" "$BUILD/assets/" --include='*.js' && echo "   ok   marker in built assets: $m" || { echo "REFUSED: marker not in any assets/*.js: $m"; exit 1; }
done
echo "== plan: cp -a $LIVE -> $BAK; diff -rq (must be identical); rsync $BUILD/ -> $LIVE/; no backup is deleted"
[ "${2:-}" = "GO" ] || { echo "== DRY -- nothing changed. Re-run with GO as the second argument."; exit 0; }
sudo cp -a "$LIVE" "$BAK"
sudo diff -rq "$LIVE" "$BAK" && echo "   ok   $BAK = live (diff -rq clean)" || { echo "FAIL: backup differs from live -- NOT promoting"; exit 1; }
sudo rsync -a --delete "$BUILD/" "$LIVE/"
ls "$LIVE/assets/" | grep -qE "^$NEW_JS$" || { echo "FAIL: live does not carry $NEW_JS"; exit 1; }
for m in 'of band gross' 'Net peak' 'v_gex_pin_gross' 'legacy, unvalidated' 'experimental'; do
  sudo grep -rlqF "$m" "$LIVE/assets/" --include='*.js' && echo "   ok   live marker: $m" || echo "   WARN: live marker missing: $m"
done
echo "== LIVE = $WANT · assets/$NEW_JS · rollback target $BAK (= $PREV_SHA, proven by diff -rq)"
echo "== backups (nothing is deleted by this script; pruning under S100-L is the operator's separate decision):"
ls -dt /var/www/marketview.bak-* /var/www/marketview.PRE_* 2>/dev/null | sed 's/^/   keep   /'
