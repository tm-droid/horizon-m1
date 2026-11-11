#!/usr/bin/env python3
"""Scale the per-frame mesh-upload allowance (Chunk Updates / Upload Budget / unbudgeted time slice) by recent frame cost.

Source transform for a caller-owned f42 workspace. Anchored edits live in edits.json. Stacks on the r2 stage (after emissive-bsearch, pass-merge, shadow-dedup).

Library use (build-m1-performance-r2.py style):
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
NEW_FILES = {}


def render(relative, source):
    """Apply this transform's edits to `source`. Every anchor must match exactly once. A file
    byte-identical to the reviewed base (f42 + cloud-prep + shadow-scratch) must also produce the
    reviewed output hash; a file already changed by another reviewed transform only needs its
    anchors."""
    entry = SPEC["files"][relative]
    digest = hashlib.sha256(source).hexdigest()
    text = source.decode("utf-8")
    for index, edit in enumerate(entry["edits"]):
        if text.count(edit["new"]) and not text.count(edit["old"]):
            raise ValueError(f"{relative}: edit {index} already applied")
        if text.count(edit["old"]) != 1:
            raise ValueError(f"{relative}: edit {index} anchor found {text.count(edit['old'])} times, need 1")
        text = text.replace(edit["old"], edit["new"], 1)
    text += entry["append"]
    output = text.encode("utf-8")
    if digest == entry["base_sha256"] and hashlib.sha256(output).hexdigest() != entry["base_output_sha256"]:
        raise ValueError(f"{relative}: output differs from reviewed bytes")
    return output


def write_atomic(target, data, mode=0o644):
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".u6-", delete=False) as handle:
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
    for relative, data in outputs.items():
        target = workspace / relative
        write_atomic(target, data, target.stat().st_mode & 0o777)
    record = {"schema": 1, "engine_revision": REVISION, "workspace": str(workspace),
              "output_sha256": {r: hashlib.sha256(d).hexdigest() for r, d in outputs.items()},
              "runtime_verified": False, "compiled": False}
    with args.record.open("x") as handle:
        json.dump(record, handle, indent=2)
        handle.write("\n")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
