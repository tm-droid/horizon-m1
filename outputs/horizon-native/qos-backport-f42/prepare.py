#!/usr/bin/env python3
"""Backport horizon-rust/horizon 9cfac94b + 0f7f9db8: far terrain threads at utility QoS on macOS.

Source transform for a caller-owned f42 workspace. Data lives beside this script:
edits.json (anchored edits, input/output SHA256) and new-files/ (whole new source files).

Library use (build-m1-performance.py style):
    mod.render(relative, bytes) -> bytes      one existing file; composes with other mods
    mod.FILES / mod.NEW_FILES                 what it touches / adds
CLI:
    prepare.py --workspace DIR --record NEW.json    apply in place (never inside launcher caches)
"""
import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = json.loads((HERE / "edits.json").read_text())
REVISION = SPEC["revision"]
FILES = list(SPEC["files"])
NEW_FILES = {rel: (HERE / "new-files" / rel).read_text() for rel in SPEC["new_files"]}


def render(relative, source):
    """Apply this mod's edits to `source`. A file that is byte-identical to pristine f42 must
    produce the reviewed output hash; a file already changed by another reviewed mod (shared
    files, e.g. game.rs) only needs every anchor to match exactly once."""
    entry = SPEC["files"][relative]
    digest = hashlib.sha256(source).hexdigest()
    if not entry["shared"] and digest != entry["pristine_sha256"]:
        raise ValueError(f"{relative}: not pristine f42 (SHA256 {digest})")
    text = source.decode("utf-8")
    for index, edit in enumerate(entry["edits"]):
        if text.count(edit["old"]) != 1:
            raise ValueError(f"{relative}: edit {index} anchor found {text.count(edit['old'])} times, need 1")
        text = text.replace(edit["old"], edit["new"], 1)
    text += entry["append"]
    output = text.encode("utf-8")
    if digest == entry["pristine_sha256"] and hashlib.sha256(output).hexdigest() != entry["output_sha256"]:
        raise ValueError(f"{relative}: output differs from reviewed bytes")
    return output


def write_atomic(target, data, mode=0o644):
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".perf-mod-", delete=False) as handle:
        handle.write(data)
        temporary = Path(handle.name)
    try:
        temporary.chmod(mode)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True, help="Fresh provenance JSON path")
    args = parser.parse_args()
    workspace = args.workspace.resolve(strict=True)
    root = Path(__file__).resolve().parents[3]
    cache = root / "outputs/horizon-runtime/launcher-data/native"
    protected = (cache / "source", cache / "stage", cache / "patched",
                 root / "outputs/horizon-runtime/m1-performance/candidate-source")
    if any(workspace == path or workspace.is_relative_to(path) for path in protected):
        parser.error("Use a separate owned workspace, outside launcher caches and the candidate source")
    if args.record.exists() or args.record.is_symlink():
        parser.error("Provenance output already exists")
    if (workspace / ".horizon-revision").read_text().strip() != REVISION:
        parser.error("Workspace is not f42")
    outputs = {}
    for relative in FILES:
        target = workspace / relative
        if target.is_symlink() or not target.resolve().is_relative_to(workspace) or not target.is_file():
            parser.error(f"{relative} must be a regular workspace file")
        outputs[relative] = render(relative, target.read_bytes())
    for relative in NEW_FILES:
        target = workspace / relative
        if target.exists() or target.is_symlink():
            parser.error(f"{relative} already exists")
        outputs[relative] = NEW_FILES[relative].encode("utf-8")
    for relative, data in outputs.items():
        target = workspace / relative
        write_atomic(target, data, target.stat().st_mode & 0o777 if target.exists() else 0o644)
    record = {"schema": 1, "engine_revision": REVISION, "workspace": str(workspace),
              "output_sha256": {r: hashlib.sha256(d).hexdigest() for r, d in outputs.items()},
              "runtime_verified": False, "compiled": False}
    with args.record.open("x") as handle:
        json.dump(record, handle, indent=2)
        handle.write("\n")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
