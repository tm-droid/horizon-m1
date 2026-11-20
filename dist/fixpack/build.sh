#!/bin/sh
# Zips Horizon-Texture-Fixes/ into out/Horizon-Texture-Fixes.zip (pack.mcmeta at the zip root).
set -eu
cd "$(dirname "$0")"
mkdir -p out
rm -f out/Horizon-Texture-Fixes.zip
(cd Horizon-Texture-Fixes && find . -name .DS_Store -prune -o -type f -print | sed 's|^\./||' | LC_ALL=C sort | zip -X -q ../out/Horizon-Texture-Fixes.zip -@)
unzip -tq out/Horizon-Texture-Fixes.zip
ls -l out/Horizon-Texture-Fixes.zip
