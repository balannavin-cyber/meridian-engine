#!/usr/bin/env bash
# mv_promote_s103.sh — promote meridian-connect origin/main 05f556c (S103 round 1: S103-A / S103-C) to live.
# REFUSING BLOCK: without the single argument GO it only checks and prints what it would do. Never prints a rollback.
#   bash ~/mv_promote_s103.sh        (checks + plan, nothing changed)
#   bash ~/mv_promote_s103.sh GO     (checks, then backup -> diff -rq proof -> build -> promote -> retention)
set -euo pipefail
WANT=05f556c; PREV_JS=index-EtZmieBR.js; PREV_SHA=30998f2
MANUAL_SHA=ede04e14d990bf54e8eaf24f60e062c1ec423e6c6204591b0bbfea4f0d7c4481
TREE="$HOME/meridian-connect"; LIVE=/var/www/marketview; BAK="/var/www/marketview.bak-$PREV_SHA"; BUILD=/tmp/mv-live-build
cd "$TREE"; git fetch -q origin
HEAD_SHA=$(git rev-parse --short HEAD); ORIG=$(git rev-parse --short origin/main)
echo "== tree HEAD $HEAD_SHA  origin/main $ORIG  want $WANT"
[ "$HEAD_SHA" = "$WANT" ] && [ "$ORIG" = "$WANT" ] || { echo "REFUSED: tree/origin not at $WANT"; exit 1; }
[ -z "$(git status --porcelain | grep -v '^??')" ] || { echo "REFUSED: tracked changes present"; exit 1; }
echo "== live now:"; ls "$LIVE/assets/" | grep -E '^index-.*\.js$'
[ -f "$LIVE/assets/$PREV_JS" ] || { echo "REFUSED: live bundle is not $PREV_JS (live is not $PREV_SHA) — read live before naming anything"; exit 1; }
echo "   live manual.json: $(sha256sum "$LIVE/help/manual.json" | cut -c1-16)…"
echo "== backups now:"; ls -dt /var/www/marketview.bak-* /var/www/marketview.PRE_* 2>/dev/null | sed 's/^/   /'
[ -e "$BAK" ] && { echo "REFUSED: $BAK already exists — it must be created from live by this block"; exit 1; }
echo "== build $WANT for live (base /):"
npx tsc --noEmit -p tsconfig.json
npx vite build --base=/ --outDir "$BUILD" --emptyOutDir 2>&1 | tail -2
NEW_JS=$(ls "$BUILD/assets/" | grep -E '^index-.*\.js$'); echo "   new bundle $NEW_JS"
grep -q "/assets/$NEW_JS" "$BUILD/index.html" && ! grep -q '/staging/' "$BUILD/index.html" && echo "   ok   index.html references /assets/ at root" || { echo "REFUSED: index.html base is wrong"; exit 1; }
echo "$MANUAL_SHA  $BUILD/help/manual.json" | sha256sum -c - >/dev/null && echo "   ok   manual.json ede04e14… (v0.5, unchanged this round)" || { echo "REFUSED: manual.json differs"; exit 1; }
echo "== plan: cp -a $LIVE -> $BAK; diff -rq (must be identical); rsync $BUILD/ -> $LIVE/; keep newest 3 .bak-* + PRE_*"
[ "${1:-}" = "GO" ] || { echo "== DRY — nothing changed. Re-run with GO."; exit 0; }
sudo cp -a "$LIVE" "$BAK"
sudo diff -rq "$LIVE" "$BAK" && echo "   ok   $BAK ≡ live (diff -rq clean)" || { echo "FAIL: backup differs from live — NOT promoting"; exit 1; }
sudo rsync -a --delete "$BUILD/" "$LIVE/"
ls "$LIVE/assets/" | grep -qE "^$NEW_JS$" || { echo "FAIL: live does not carry $NEW_JS"; exit 1; }
echo "== LIVE = $WANT · assets/$NEW_JS · rollback target $BAK (≡ $PREV_SHA, proven)"
echo "== retention (S100-L): keep newest 3 .bak-* by mtime + every PRE_*"
for d in $(ls -dt /var/www/marketview.bak-* | tail -n +4); do echo "   delete $d"; sudo rm -rf "$d"; done
ls -dt /var/www/marketview.bak-* /var/www/marketview.PRE_* 2>/dev/null | sed 's/^/   keep   /'
