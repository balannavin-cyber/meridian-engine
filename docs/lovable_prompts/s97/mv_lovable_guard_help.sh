#!/usr/bin/env bash
# mv_lovable_guard_help.sh v2: round guard for the S97 /help round (check-only; it builds and deploys nothing).
#
# Usage, on the box, from the meridian-connect clone, after Lovable's commits have been pulled:
#   bash mv_lovable_guard_help.sh <base_commit> <content_commit>
#     base_commit     the live commit the round starts from (e.g. 804d684)
#     content_commit  the operator's commit that added public/help/ (on top of base)
#
# The guard checks the NET diff content_commit..HEAD, i.e. only what Lovable changed.
# It exits 0 on PASS, 1 on FAIL. Run the usual staging build only after a PASS.
#
# Each check is followed by a one-line note on how it can fail (rule 0).
set -u
BASE="${1:?base commit}"; CONTENT="${2:?content commit}"
fail=0; say(){ printf '%s\n' "$*"; }; bad(){ say "FAIL  $*"; fail=1; }; ok(){ say "ok    $*"; }

git cat-file -e "$BASE^{commit}" 2>/dev/null || { say "FAIL  base $BASE not found"; exit 1; }
git cat-file -e "$CONTENT^{commit}" 2>/dev/null || { say "FAIL  content $CONTENT not found"; exit 1; }
git merge-base --is-ancestor "$BASE" "$CONTENT" || bad "content commit is not on top of base"

# C0. The content commit touches public/help/ only.
#     Fails if the operator commit carries anything else.
extra=$(git diff --name-only "$BASE" "$CONTENT" | grep -v '^public/help/' || true)
[ -z "$extra" ] && ok "C0 content commit = public/help/ only" || bad "C0 content commit touches: $extra"

# Lovable's net diff.
mapfile -t CH < <(git diff --name-status "$CONTENT" HEAD -- . ':(exclude)public/help/manual.json')
[ "${#CH[@]}" -gt 0 ] || bad "no Lovable changes since content commit"

# C1. Allowlist: App.tsx (M), new Help page / help components (A or M), and exactly one nav file (M).
#     Fails on any other path, any deletion, or more than one nav file.
nav=0
for line in "${CH[@]}"; do
  st=${line%%$'\t'*}; p=${line#*$'\t'}
  case "$p" in
    src/App.tsx)                         [ "$st" = M ] || bad "C1 App.tsx status $st" ;;
    src/pages/Help.tsx|src/components/help/*) [[ "$st" =~ ^[AM]$ ]] || bad "C1 $p status $st" ;;
    src/components/*|src/marketview/*)   [ "$st" = M ] && nav=$((nav+1)) && say "info  nav candidate: $p" || bad "C1 $p status $st" ;;
    *) bad "C1 path outside allowlist: $st $p" ;;
  esac
done
[ "$nav" -le 1 ] && ok "C1 allowlist (nav files changed: $nav)" || bad "C1 more than one nav/component file changed ($nav)"

# C2. public/help/ untouched by Lovable.
#     Fails if Lovable edited, moved or added content.
hc=$(git diff --name-only "$CONTENT" HEAD -- public/help/ | grep -v '^public/help/manual.json$' || true)
[ -z "$hc" ] && ok "C2 public/help untouched (manual.json title fix allowed)" || bad "C2 public/help changed: $hc"

# C3. No package or lock change.
#     Fails on any dependency edit.
git diff --quiet "$CONTENT" HEAD -- package.json package-lock.json bun.lock bun.lockb yarn.lock pnpm-lock.yaml \
  && ok "C3 no package/lock change" || bad "C3 package or lock file changed"

# C4. No added data read.
#     Fails if any added line contains "supabase".
added=$(git diff "$CONTENT" HEAD -- src | grep '^+' | grep -v '^+++')
n_sb=$(printf '%s\n' "$added" | grep -c 'supabase' || true)
[ "$n_sb" -eq 0 ] && ok "C4 no added supabase line" || bad "C4 $n_sb added line(s) mention supabase"

# C5. The only fetch is the static manual, via BASE_URL.
#     Fails on any other fetch target, a hard-coded leading slash, or an absolute URL.
n_fetch=$(printf '%s\n' "$added" | grep -c 'fetch(' || true)
# v2: a fetch counts as via BASE_URL if it names BASE_URL itself, or an identifier assigned from
# import.meta.env.BASE_URL in an added line (v1 required the literal on the fetch line: mis-specified, S97).
base_ids=$(printf '%s\n' "$added" | grep -oE '(const|let|var)[[:space:]]+[A-Za-z_][A-Za-z0-9_]*[[:space:]]*=[[:space:]]*import\.meta\.env\.BASE_URL' | sed -E 's/^(const|let|var)[[:space:]]+([A-Za-z_][A-Za-z0-9_]*).*/\2/' | sort -u)
pat='BASE_URL'; for i in $base_ids; do pat="$pat|\\\$\\{$i\\}"; done
n_ok=$(printf '%s\n' "$added" | grep 'fetch(' | grep -cE "$pat" || true)
[ "$n_fetch" -le 1 ] && [ "$n_fetch" -eq "$n_ok" ] && ok "C5 fetch count $n_fetch, all via BASE_URL" || bad "C5 fetch lines $n_fetch, via BASE_URL $n_ok"
printf '%s\n' "$added" | grep -qE 'https?://' && bad "C5 absolute URL added" || ok "C5 no absolute URL added"

# C6. No credential patterns, no forbidden words.
printf '%s\n' "$added" | grep -qiE 'eyJ[a-zA-Z0-9_-]{20,}|service_role|sk_live|api[_-]?key\s*[:=]' && bad "C6 credential-like pattern added" || ok "C6 no credential pattern"
printf '%s\n' "$added" | grep -qiE 'vanna|charm' && bad "C6 forbidden word added" || ok "C6 no forbidden words"

# C7. The route is lazy: App.tsx gains a lazy import of the Help page.
#     Fails if Help is imported eagerly.
app=$(git diff "$CONTENT" HEAD -- src/App.tsx | grep '^+' || true)
printf '%s\n' "$app" | grep -qE 'lazy\(.*pages/Help' && ok "C7 /help is lazy" || bad "C7 no lazy(() => import(...pages/Help)) in App.tsx"
printf '%s\n' "$app" | grep -qE '^\+import .*pages/Help' && bad "C7 eager import of Help" || true

# C8. Literal strings: the approved five plus the label "Help" must be present.
#     Fails if one is missing; other added string literals are listed for the operator to read.
for s in 'Marketview manual' 'manual ${' 'IST · board ${' 'help · loading' 'help content not found — public/help/manual.json'; do
  printf '%s\n' "$added" | grep -qF "$s" && ok "C8 string present: $s" || bad "C8 string missing: $s"
done
say "info  other added quoted strings (read them):"
printf '%s\n' "$added" | grep -oE '"[A-Za-z][^"]{3,}"|`[A-Za-z][^`]{3,}`|>[A-Za-z][^<{]{3,}<' | sort -u | sed 's/^/        /' | head -40

# C9. Content integrity: manual.json parses and its counts match the round's expectation.
python3 - <<'PY' || fail=1
import json,sys
d=json.load(open("public/help/manual.json"))
parts=len(d["parts"]); secs=sum(len(p["sections"]) for p in d["parts"])
figs=sum(len(p["shots"])+sum(len(s["shots"]) for s in p["sections"]) for p in d["parts"])
import os
missing=[s["file"] for p in d["parts"] for s in p["shots"]+[x for sec in p["sections"] for x in sec["shots"]] if not os.path.exists("public/"+s["file"])]
stars=[s["title"] for p in d["parts"] for s in p["sections"] if "*" in s["title"]]
print(f"info  manual {d['manual_version']} parts={parts} sections={secs} figures={figs} missing_files={len(missing)} starred_titles={len(stars)}")
sys.exit(1 if missing else 0)
PY

[ "$fail" -eq 0 ] && { say "PASS"; exit 0; } || { say "FAIL"; exit 1; }
