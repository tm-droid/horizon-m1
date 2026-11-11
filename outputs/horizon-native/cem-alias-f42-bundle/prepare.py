#!/usr/bin/env python3
"""Check exact source bytes and create a fresh combined bundle input. Never build."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
COMMIT = "f42ef42ef6ceccb3c6a20bea2481d87949a51c81"
SOURCE_SHA = "4c7f8650070be17789d500aa86dd013fed9ddbcd0dc754d953f0208acb442cd8"
TARGET = Path("crates/horizon-client/src/mobs/cem.rs")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    entries = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"bundle symlink refused: {path}")
        if path.is_file():
            entries[path.relative_to(root).as_posix()] = sha(path)
    return entries


def prepare(source_root, zoom_bundle, output_dir):
    source = Path(source_root).resolve(strict=True) / TARGET
    if source.resolve() != source or sha(source) != SOURCE_SHA:
        raise ValueError("source guard failed: exact unmodified f42 cem.rs required")
    zoom = Path(zoom_bundle).resolve(strict=True)
    candidate = HERE / "bundle"
    provenance = json.loads((HERE / "provenance.json").read_text())
    candidate_hashes = inventory(candidate)
    if candidate_hashes != provenance["bundle_sha256"]:
        raise ValueError("candidate bundle differs from recorded provenance")
    zoom_manifest = json.loads((zoom / "horizon-native.json").read_text())
    if zoom_manifest.get("id") != "zoom" or zoom_manifest.get("hooks") != 1:
        raise ValueError("expected existing hook-only Zoom bundle")
    zoom_hashes = inventory(zoom)
    requested = Path(output_dir).absolute()
    if requested.exists() or requested.is_symlink():
        raise ValueError("combined output must not exist")
    output = requested.resolve()
    if not any(output.is_relative_to(root) and output != root
               for root in (HERE, Path("/private/tmp"))):
        raise ValueError("combined output must be below this candidate directory or /private/tmp")
    for input_root in (zoom, candidate, Path(source_root).resolve()):
        if output.is_relative_to(input_root) or input_root.is_relative_to(output):
            raise ValueError("combined output must not overlap inputs")
    output.mkdir(parents=True)
    shutil.copytree(candidate, output / "cem_alias_f42")
    shutil.copytree(zoom, output / "zoom")
    record = {"horizon_revision": COMMIT, "cem_rs_sha256": SOURCE_SHA,
              "candidate": candidate_hashes, "zoom": zoom_hashes,
              "status": "combined source input only; plan/apply/build/runtime pending"}
    (output / "combined-input-provenance.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--zoom-bundle", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.source_root, args.zoom_bundle, args.output_dir), indent=2))
    except (OSError, ValueError) as error:
        parser.exit(1, f"refused: {error}\n")


if __name__ == "__main__":
    main()
