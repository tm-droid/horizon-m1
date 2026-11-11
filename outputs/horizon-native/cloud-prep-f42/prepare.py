#!/usr/bin/env python3
"""Prepare a fresh, independently identified f42 control or cloud-fix source tree."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
SPEC = json.loads((HERE / "patch-spec.json").read_text())
EXCLUDED = {".git", ".local", "target"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def render(path, original):
    rule = SPEC["files"][path]
    if digest(original) != rule["before_sha256"]:
        raise ValueError(f"Reviewed source drift: {path}")
    text = original.decode("utf-8")
    for old, new in rule["edits"]:
        if text.count(old) != 1:
            raise ValueError(f"Nonunique patch context: {path}")
        text = text.replace(old, new, 1)
    output = text.encode("utf-8")
    if digest(output) != rule["after_sha256"]:
        raise ValueError(f"Unexpected patched bytes: {path}")
    return output


def inventory(root):
    result = {}
    for directory, directories, files in os.walk(root, followlinks=False):
        directory = Path(directory)
        if directory == root:
            directories[:] = [name for name in directories if name not in EXCLUDED]
            files = [name for name in files if name not in EXCLUDED]
        for name in directories + files:
            path = directory / name
            relative = path.relative_to(root)
            if path.is_symlink():
                raise ValueError(f"Source symlinks require separate review: {relative}")
            if path.is_file():
                result[str(relative)] = digest(path.read_bytes())
            elif not path.is_dir():
                raise ValueError(f"Nonregular source entry: {relative}")
    return result


def prepare(source, output, mode):
    source = source.resolve(strict=True)
    requested = output.absolute()
    if requested.exists() or requested.is_symlink():
        raise ValueError("Output must be fresh")
    output = requested.resolve()
    if not output.is_relative_to(HERE) or output == HERE:
        raise ValueError("Output must be an owned child of the cloud-prep-f42 directory")
    if output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("Source and output must not overlap")
    if (source / ".horizon-revision").read_text().strip() != SPEC["engine_revision"]:
        raise ValueError("Source is not the pinned f42 snapshot")
    patched = {name: render(name, (source / name).read_bytes()) for name in SPEC["files"]}
    before = inventory(source)
    shutil.copytree(source, output, ignore=lambda path, names: EXCLUDED if Path(path) == source else ())
    copied = inventory(output)
    if before != copied or inventory(source) != before:
        raise ValueError("Source changed or copy differs; incomplete output must not be built")
    if mode == "patched":
        for name, data in patched.items():
            (output / name).write_bytes(data)
    after = inventory(output)
    expected = dict(before)
    if mode == "patched":
        expected.update({name: rule["after_sha256"] for name, rule in SPEC["files"].items()})
    if after != expected:
        raise ValueError("Unexpected output changes; incomplete output must not be built")
    record = {
        "engine_revision": SPEC["engine_revision"], "mode": mode,
        "source": str(source), "source_files": before, "output_files": after,
        "patch_spec_sha256": digest((HERE / "patch-spec.json").read_bytes()),
        "patch_sha256": digest((HERE / "cloud-prep.patch").read_bytes()),
        "source_unchanged": True, "changed_files": [name for name in after if after[name] != before[name]],
        "build_verified": False, "runtime_verified": False,
    }
    (output / "cloud-prep-provenance.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=["control", "patched"], required=True)
    args = parser.parse_args()
    result = prepare(args.source, args.output, args.mode)
    print(json.dumps({key: result[key] for key in ("mode", "source_unchanged", "changed_files")}))
