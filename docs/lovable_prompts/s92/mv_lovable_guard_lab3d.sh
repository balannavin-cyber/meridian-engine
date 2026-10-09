#!/usr/bin/env bash
# mv_lovable_guard_lab3d.sh — ONE-TIME guard for the optional 3D view (ruling S92-J).
# Same contract as mv_lovable_guard.sh v2 (run on the box AFTER Lovable pushes, BEFORE anything is built;
# never pushes, never touches live), with exactly the exceptions S92-J grants and nothing more:
#
#   bash mv_lovable_guard_lab3d.sh <BASE_SHA>
#
# ALLOWED paths: src/pages/Lab3D.tsx (new), src/lib/terrain.ts (new), src/App.tsx (route only),
#   package.json + bun.lock / package-lock.json (dependency additions only), src/pages/Board.tsx,
#   src/components/board/** (entry links), roadmap.md.
# FAILS (exit 1, nothing built) if:
#   1. any other path changes; or .env*, supabase/**, *.sql, vite/ts/tailwind/eslint config, index.html,
#      src/lib/board.ts or any other src/lib/** (except terrain.ts) changes
#   2. package.json adds or changes anything except dependencies three, @react-three/fiber,
#      @react-three/drei, @types/three — or removes anything
#   3. src/App.tsx adds anything but a lazy import of ./pages/Lab3D and its <Route path="/board/3d">,
#      or imports Lab3D statically
#   4. any data read is added other than exactly ONE supabase.from("v_gex_strike_terrain"), or any
#      added line reads gex_strike_snapshots / trading_calendar, or adds .rpc/.channel/.storage/
#      .functions/createClient/fetch(
#   5. a credential pattern is added (case-sensitive), or vanna/charm in any case (L78-1)
#   6. strict tsc fails or the build fails (pipefail)
#   7. after the build, three.js is found in the entry chunk (it must load only when /board/3d opens)
set -euo pipefail
BASE="${1:?usage: mv_lovable_guard_lab3d.sh <BASE_SHA>}"
VIEW="v_gex_strike_terrain"
cd ~/meridian-connect
git fetch -q origin
HEAD_SHA=$(git rev-parse --short origin/main)
echo "== base $BASE  ->  origin/main $HEAD_SHA   (S92-J lab3d mode; one read allowed: $VIEW)"
git merge-base --is-ancestor "$BASE" origin/main || { echo "FAIL: $BASE is not an ancestor of origin/main"; exit 1; }
echo "== commits:"; git log --format='   %h %an  %s' "$BASE"..origin/main
[ -n "$(git rev-list "$BASE"..origin/main)" ] || { echo "FAIL: no new commits since $BASE"; exit 1; }

fail=0
echo "== changed paths:"
while IFS=$'\t' read -r st path rest; do
  p="${rest:-$path}"; echo "   $st $p"
  case "$p" in
    src/pages/Lab3D.tsx|src/lib/terrain.ts|src/App.tsx|package.json|bun.lock|package-lock.json|src/pages/Board.tsx|src/components/board/*|roadmap.md) ;;
    *) echo "   FAIL: outside S92-J allowlist -> $p"; fail=1 ;;
  esac
done < <(git diff --name-status "$BASE" origin/main)

chk() { local label="$1" re="$2" text="$3"; local hits; hits=$(printf '%s\n' "$text" | grep -nE "$re" || true)
  if [ -n "$hits" ]; then echo "   FAIL: $label"; printf '%s\n' "$hits" | head -5 | sed 's/^/      /'; fail=1; else echo "   ok   $label"; fi; }

echo "== package.json:"
PJ_ADD=$(git diff "$BASE" origin/main -- package.json | grep -E '^\+[^+]' || true)
PJ_DEL=$(git diff "$BASE" origin/main -- package.json | grep -E '^-[^-]' || true)
# a line that only gains a trailing comma shows as -/+ of the same text; strip commas before comparing
PJ_DEL_REAL=$(comm -23 <(printf '%s\n' "$PJ_DEL" | sed 's/^-//; s/,\s*$//' | sort) \
                       <(printf '%s\n' "$PJ_ADD" | sed 's/^+//; s/,\s*$//' | sort) | grep -v '^\s*$' || true)
chk "package.json removes nothing" '.' "$PJ_DEL_REAL"
PJ_NEW=$(comm -13 <(printf '%s\n' "$PJ_DEL" | sed 's/^-//; s/,\s*$//' | sort) \
                  <(printf '%s\n' "$PJ_ADD" | sed 's/^+//; s/,\s*$//' | sort) | grep -v '^\s*$' || true)
chk "package.json adds only three / @react-three/fiber / @react-three/drei / @types/three" \
    '.' "$(printf '%s\n' "$PJ_NEW" | grep -vE '^\s*"(three|@react-three/fiber|@react-three/drei|@types/three)"\s*:\s*"[~^]?[0-9][0-9.]*"\s*$' || true)"

echo "== src/App.tsx:"
APP_ADD=$(git diff "$BASE" origin/main -- src/App.tsx | grep -E '^\+[^+]' | sed 's/^+//' || true)
chk "App.tsx adds only the lazy Lab3D import and its /board/3d route" '.' \
    "$(printf '%s\n' "$APP_ADD" | grep -vE '^\s*$' \
       | grep -vE 'lazy\(\s*\(\)\s*=>\s*import\(\s*"\./pages/Lab3D"\s*\)\s*\)' \
       | grep -vE '<Route\s+path="/board/3d"' \
       | grep -vE '^\s*import\s*\{?[^}]*\b(lazy|Suspense)\b[^}]*\}?\s*from\s*"react";?\s*$' \
       | grep -vE '^\s*</?Suspense' || true)"
chk "Lab3D is not imported statically" '^\s*import\s+Lab3D\b' "$(git show origin/main:src/App.tsx)"

echo "== added-line checks (source files only; lockfiles excluded):"
ADDED=$(git diff "$BASE" origin/main -- . ':(exclude)bun.lock' ':(exclude)package-lock.json' | grep -E '^\+[^+]' || true)
READS='supabase\.(from|rpc|channel|storage|functions)|createClient|fetch\('
OTHER=$(printf '%s\n' "$ADDED" | grep -E "$READS" | grep -vF "supabase.from(\"$VIEW\")" || true)
chk "no data reads other than $VIEW" '.' "$OTHER"
n=$(printf '%s\n' "$ADDED" | grep -cF "supabase.from(\"$VIEW\")" || true)
if [ "$n" = 1 ]; then echo "   ok   exactly one read of $VIEW"; else echo "   FAIL: $n added reads of $VIEW (expected 1)"; fail=1; fi
chk "no raw-table reads in added lines" 'gex_strike_snapshots|trading_calendar' "$ADDED"
chk "no credentials" 'eyJ[A-Za-z0-9_-]{10,}|service_role|SUPABASE_(URL|ANON|SERVICE)|VITE_SUPABASE|sk_(live|test)_|pk_(live|test)_' "$ADDED"
chk "no vanna/charm (L78-1)" '\b([Vv][Aa][Nn][Nn][Aa]|[Cc][Hh][Aa][Rr][Mm])\b' "$ADDED"
chk "no credentials in lockfile" 'service_role|SUPABASE_(URL|ANON|SERVICE)|VITE_SUPABASE|sk_(live|test)_|pk_(live|test)_' \
    "$(git diff "$BASE" origin/main -- bun.lock package-lock.json | grep -E '^\+[^+]' || true)"
[ "$fail" = 0 ] || { echo "== GUARD FAILED — nothing built. Paste this output to Claude."; exit 1; }

echo "== guard passed; fast-forward, install (lockfile only), tsc, build /staging/"
git status --porcelain | grep -v '^??' && { echo "FAIL: local tracked changes present"; exit 1; } || true
git merge -q --ff-only origin/main
if [ -f bun.lock ] && command -v bun >/dev/null; then bun install --frozen-lockfile >/dev/null; else npm ci --silent; fi
npx tsc --noEmit -p tsconfig.json
npx vite build --base=/staging/ --outDir /tmp/mv-staging-build --emptyOutDir 2>&1 | tail -6
ENTRY=$(grep -oE 'assets/index-[A-Za-z0-9_-]+\.js' /tmp/mv-staging-build/index.html | head -1)
[ -n "$ENTRY" ] || { echo "FAIL: entry chunk not found in index.html"; exit 1; }
if grep -q 'WebGLRenderer' "/tmp/mv-staging-build/$ENTRY"; then
  echo "FAIL: three.js is in the entry chunk ($ENTRY) — Lab3D is not lazy-loaded. Nothing deployed."; exit 1
fi
echo "   ok   three.js absent from entry chunk $ENTRY ($(du -k "/tmp/mv-staging-build/$ENTRY" | cut -f1) KB)"
sudo rsync -a --delete /tmp/mv-staging-build/ /var/www/marketview-staging/
echo "== STAGING DEPLOYED $(git rev-parse --short HEAD) — live untouched, nothing pushed"
git diff --stat "$BASE" HEAD | tail -1
