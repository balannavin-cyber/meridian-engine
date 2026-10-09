#!/usr/bin/env bash
# mv_lovable_guard.sh v2 — run on the box AFTER Lovable has pushed, BEFORE anything is built.
# Checks every commit Lovable added on top of BASE against the S92 safeguards, then (only if all pass)
# fast-forwards ~/meridian-connect and builds /staging/. It never touches live and never pushes.
#
#   bash mv_lovable_guard.sh <BASE_SHA>                    layout-only pass: no new data reads at all
#   bash mv_lovable_guard.sh <BASE_SHA> <view_name>        one data pass: src/lib/board.ts may change, and the ONLY
#                                                          new supabase read allowed is .from("<view_name>"), once
#
# FAILS (exit 1, nothing built) if Lovable's net diff:
#   1. touches any path outside the allowlist (src/pages/Board.tsx, src/components/board/**, roadmap.md,
#      + src/lib/board.ts only when a view is named)
#   2. touches .env*, lockfiles, package.json, vite/ts/tailwind/eslint config, index.html, other src/lib/**, supabase/**, *.sql
#   3. adds a data read other than the one named view (supabase.from/.rpc/.channel/.storage/.functions, createClient, fetch()
#   4. adds anything that looks like a credential (JWT, service_role, SUPABASE key names, sk_/pk_ tokens) — case-sensitive
#   5. adds the words vanna or charm in any capitalisation (parity ruling L78-1)
#   6. fails strict tsc, or the build fails (pipefail)
set -euo pipefail
BASE="${1:?usage: mv_lovable_guard.sh <BASE_SHA> [view_name]}"
VIEW="${2:-}"
cd ~/meridian-connect
git fetch -q origin
HEAD_SHA=$(git rev-parse --short origin/main)
echo "== base $BASE  ->  origin/main $HEAD_SHA   ${VIEW:+(one read allowed: $VIEW)}"
git merge-base --is-ancestor "$BASE" origin/main || { echo "FAIL: $BASE is not an ancestor of origin/main (history rewritten?)"; exit 1; }
echo "== commits:"; git log --format='   %h %an  %s' "$BASE"..origin/main
[ -n "$(git rev-list "$BASE"..origin/main)" ] || { echo "FAIL: no new commits since $BASE"; exit 1; }

fail=0
echo "== changed paths:"
while IFS=$'\t' read -r st path rest; do
  p="${rest:-$path}"; echo "   $st $p"
  ok=0
  case "$p" in src/pages/Board.tsx|src/components/board/*|roadmap.md) ok=1 ;; esac
  [ -n "$VIEW" ] && [ "$p" = "src/lib/board.ts" ] && ok=1
  [ "$ok" = 1 ] || { echo "   FAIL: outside allowlist -> $p"; fail=1; }
  case "$p" in
    .env*|*.sql|supabase/*|package.json|bun.lock|package-lock.json|vite.config.*|tsconfig*|tailwind.config.*|eslint.config.*|index.html|components.json)
      echo "   FAIL: forbidden path -> $p"; fail=1 ;;
    src/lib/*) [ -n "$VIEW" ] && [ "$p" = "src/lib/board.ts" ] || { echo "   FAIL: forbidden path -> $p"; fail=1; } ;;
  esac
done < <(git diff --name-status "$BASE" origin/main)

ADDED=$(git diff "$BASE" origin/main | grep -E '^\+[^+]' || true)
chk() { local label="$1" re="$2" text="${3-$ADDED}"; local hits; hits=$(printf '%s\n' "$text" | grep -nE "$re" || true)
  if [ -n "$hits" ]; then echo "   FAIL: $label"; printf '%s\n' "$hits" | head -5 | sed 's/^/      /'; fail=1; else echo "   ok   $label"; fi; }
echo "== added-line checks:"
READS='supabase\.(from|rpc|channel|storage|functions)|createClient|fetch\('
if [ -n "$VIEW" ]; then
  OTHER=$(printf '%s\n' "$ADDED" | grep -E "$READS" | grep -vF "supabase.from(\"$VIEW\")" || true)
  chk "no data reads other than $VIEW" '.' "$OTHER"
  n=$(printf '%s\n' "$ADDED" | grep -cF "supabase.from(\"$VIEW\")" || true)
  if [ "$n" = 1 ]; then echo "   ok   exactly one read of $VIEW"; else echo "   FAIL: $n added reads of $VIEW (expected 1)"; fail=1; fi
else
  chk "no new data reads" "$READS"
fi
chk "no credentials"           'eyJ[A-Za-z0-9_-]{10,}|service_role|SUPABASE_(URL|ANON|SERVICE)|VITE_SUPABASE|sk_(live|test)_|pk_(live|test)_'
chk "no vanna/charm (L78-1)"   '\b([Vv][Aa][Nn][Nn][Aa]|[Cc][Hh][Aa][Rr][Mm])\b'
[ "$fail" = 0 ] || { echo "== GUARD FAILED — nothing built. Paste this output to Claude."; exit 1; }

echo "== guard passed; fast-forward local tree and build /staging/"
git status --porcelain | grep -v '^??' && { echo "FAIL: local tracked changes present"; exit 1; } || true
git merge -q --ff-only origin/main
npx tsc --noEmit -p tsconfig.json
npx vite build --base=/staging/ --outDir /tmp/mv-staging-build --emptyOutDir 2>&1 | tail -3
sudo rsync -a --delete /tmp/mv-staging-build/ /var/www/marketview-staging/
echo "== STAGING DEPLOYED $(git rev-parse --short HEAD) — live untouched, nothing pushed"
git diff --stat "$BASE" HEAD | tail -1
