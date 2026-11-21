#!/bin/zsh
# Horizon M1 one-line installer. Paste into Terminal:
#   zsh -c "$(curl -fsSL https://raw.githubusercontent.com/tm-droid/horizon-m1/main/install.sh)"
# Downloads the latest release zip, checks its SHA-256, unzips it to a temporary folder and runs
# "Install Horizon M1.command" from there. Files fetched with curl carry no quarantine flag, so macOS
# shows no "unidentified developer" warning. Run the same line again to update; worlds are kept.
# Optional: HM1_LOOK=1|2|3 HM1_MODE=1|2 HM1_NAME=<player> answer the installer's questions,
# HM1_ZIP=<path to a downloaded Horizon-M1 zip> skips the download.
set -eu

REPO="tm-droid/horizon-m1"
die() { print -P "%F{red}%BError:%b%f $*" >&2; exit 1; }

[[ "$(uname -m)" == arm64 ]] || die "Horizon M1 is for Apple Silicon Macs (M1/M2/M3/M4) only."
FREE_KB=$(df -k "$HOME" | awk 'NR==2 {print $4}')
(( FREE_KB > 3 * 1024 * 1024 )) || die "Horizon M1 needs about 3 GB of free disk space. Free some up, then run this again."

TMP=$(mktemp -d "${TMPDIR:-/tmp}/horizon-m1.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

if [[ -n "${HM1_ZIP:-}" ]]; then
  ZIP="$HM1_ZIP"
  [[ -f "$ZIP" ]] || die "No file at $ZIP"
else
  print -P "%B==>%b Looking up the latest Horizon M1 release"
  JSON=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest") \
    || die "Could not reach GitHub. Check your internet connection, then run this again."
  # "<zip url> <sha256>" of the release's zip; GitHub computes the digest itself when the file is uploaded.
  # JavaScript for Automation parses the JSON (built into macOS, unlike python3 on Macs without developer tools).
  read -r URL WANT <<<"$(/usr/bin/osascript -l JavaScript -e 'function run(a) {
    const z = JSON.parse(a[0]).assets.find(x => x.name.endsWith(".zip"));
    return z ? z.browser_download_url + " " + (z.digest || "").replace(/^sha256:/, "") : "";
  }' "$JSON")" || true
  [[ -n "${URL:-}" ]] || die "The latest release has no zip. Download it by hand: https://github.com/$REPO/releases/latest"
  ZIP="$TMP/${URL:t}"
  print -P "%B==>%b Downloading ${URL:t} (about 210 MB)"
  curl -fL# -o "$ZIP" "$URL" || die "The download failed. Run this again."
  GOT=$(shasum -a 256 "$ZIP" | awk '{print $1}')
  [[ -n "$WANT" && "$WANT" == "$GOT" ]] || die "The download is damaged (checksum mismatch). Run this again."
  print -P "%B==>%b Checksum OK"
fi

print -P "%B==>%b Unzipping"
ditto -x -k "$ZIP" "$TMP/unzipped" || die "Could not unzip ${ZIP:t}."
INST=("$TMP"/unzipped/*/"Install Horizon M1.command"(N))
(( ${#INST} == 1 )) || die "The zip has no installer in it."
zsh "$INST[1]"
