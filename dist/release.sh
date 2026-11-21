#!/bin/zsh
# Publish a Horizon M1 build as a new GitHub release (tag m1-<short>, e.g. m1-daily7-fix3).
# Usage: zsh dist/release.sh [--dry-run] [TAG]   (default TAG: the launcher's selected version)
# Builds the zip with package.sh, writes the notes from dist/RELEASE.md + the CHANGELOG.md section of this
# build, shows the gh command and runs it only after you type y. --dry-run stops before anything is uploaded.
# The assets keep the same names in every release, so releases/latest/download/<name> always points at the
# newest build (install.sh and the Horizon M1 app's update check rely on that).
set -eu
D="${0:A:h}"; R="${D:h}"; OUT="$D/out"
DRY=0; [[ "${1:-}" == --dry-run ]] && { DRY=1; shift; }
L="$HOME/Library/Application Support/horizon-launcher"
TAG="${1:-$(/usr/bin/python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["selected"])' "$L/settings.json")}"
SHORT="${${TAG##*-m1-}%-*}"
REL="m1-$SHORT"
die() { print -u2 "release: $*"; exit 1; }

# The installer and install.sh that players download come from main: publish only what is committed and pushed.
if (( ! DRY )); then
  [[ -z "$(git -C "$R" status --porcelain)" ]] || die "commit your changes first"
  git -C "$R" fetch -q origin main
  [[ "$(git -C "$R" rev-parse HEAD)" == "$(git -C "$R" rev-parse origin/main)" ]] || die "push main first (HEAD != origin/main)"
  gh release view "$REL" -R tm-droid/horizon-m1 >/dev/null 2>&1 && die "release $REL already exists"
fi

# This build's changelog section: from "## <short>" up to the next "## ".
CHANGES=$(awk -v h="## $SHORT" '$0 == h {on=1; next} on && /^## / {exit} on' "$R/CHANGELOG.md")
[[ -n "${CHANGES//[[:space:]]/}" ]] || die "CHANGELOG.md has no '## $SHORT' section"

zsh "$D/package.sh" "$TAG"
SHA=$(awk '{print $1}' "$OUT/Horizon-M1.zip.sha256")
NOTES="$OUT/release-notes.md"
/usr/bin/python3 - "$D/RELEASE.md" "$NOTES" "$SHORT" "$TAG" "$SHA" "$CHANGES" <<'PY'
import sys
src, dst, short, tag, sha, changes = sys.argv[1:]
t = open(src).read()
for k, v in (("__SHORT__", short), ("__TAG__", tag), ("__SHA__", sha), ("__CHANGES__", changes.strip())):
    t = t.replace(k, v)
open(dst, "w").write(t)
PY

CMD=(gh release create "$REL" "$OUT/Horizon-M1.zip" "$OUT/Horizon-M1.zip.sha256" "$OUT/horizon-m1.json"
     -R tm-droid/horizon-m1 --title "Horizon M1 $SHORT" --notes-file "$NOTES" --latest)
print "\nNotes: $NOTES\nCommand: ${(q)CMD}"
(( DRY )) && { print "dry run: nothing uploaded"; exit 0; }
print -n "Publish $REL now? Type y: "; read -r a
[[ "$a" == y ]] || { print "Not published."; exit 0; }
"${CMD[@]}"
# Check what players will get: the latest manifest must name this build.
sleep 3
curl -fsSL https://github.com/tm-droid/horizon-m1/releases/latest/download/horizon-m1.json | grep -q "\"$TAG\"" \
  && print "OK: latest release is $REL" || print -u2 "warning: releases/latest does not serve $TAG yet"
