#!/usr/bin/env python3
"""Create the U13 M1 variants, preserving every non-manifest ZIP entry byte-for-byte."""
from pathlib import Path
import re
import tomllib
import zipfile

PACKS = Path(__file__).resolve().parents[1] / "horizon-native-packs"
VARIANTS = (
    ("montarc-1.1.1.hshader", "montarc-m1.hshader", "montarcm1", "Montarc M1", 96.0),
    ("daybreak-0.1.1.hshader", "daybreak011-m1.hshader", "daybreakm1", "Daybreak M1", 80.0),
)


def replace_once(pattern, replacement, text):
    result, count = re.subn(pattern, replacement, text, count=1, flags=re.M)
    if count != 1:
        raise ValueError(f"Missing expected manifest field: {pattern}")
    return result


def manifest_variant(text, ident, name, distance):
    text = replace_once(r'^id = "[^"]+"$', f'id = "{ident}"', text)
    text = replace_once(r'^name = "[^"]+"$', f'name = "{name}"', text)
    text = replace_once(r'^resolution = 2048$', 'resolution = 1536', text)
    text = replace_once(r'^distance = (128|96)\.0$', f'distance = {distance}', text)
    if ident == "montarcm1":
        text = replace_once(r'(id = "shadow_samples"\n(?:(?!\[\[options\]\]).*\n)*?default = )"Medium"$',
                            r'\1"Low"', text)
    manifest = tomllib.loads(text)
    assert manifest["id"] == ident and manifest["shadow"]["resolution"] == 1536
    assert manifest["shadow"]["distance"] == distance
    if ident == "montarcm1":
        options = {option["id"]: option for option in manifest["options"]}
        assert options["shadow_samples"]["default"] == "Low"
        assert options["reflections"]["default"] is True and options["fxaa"]["default"] is True
    return text.encode()


def main():
    for source, target, ident, name, distance in VARIANTS:
        with zipfile.ZipFile(PACKS / source) as original:
            entries = {entry.filename: original.read(entry) for entry in original.infolist()}
            entries["horizon-shaders.toml"] = manifest_variant(
                entries["horizon-shaders.toml"].decode(), ident, name, distance)
            with zipfile.ZipFile(PACKS / target, "w") as variant:
                variant.comment = original.comment
                for entry in original.infolist():
                    variant.writestr(entry, entries[entry.filename])
        with zipfile.ZipFile(PACKS / target) as variant:
            assert variant.namelist() == list(entries)
            assert all(variant.read(entry) == data for entry, data in entries.items())
        print(f"{target}: id={ident}, shadow=1536/{distance:g}; all other entries preserved")


if __name__ == "__main__":
    main()
