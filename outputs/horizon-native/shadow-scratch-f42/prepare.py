#!/usr/bin/env python3
"""Apply the reviewed scratch-reuse transform to a caller-owned f42 workspace."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

REVISION = "f42ef42ef6ceccb3c6a20bea2481d87949a51c81"
TARGET = Path("crates/horizon-client-render/src/gfx.rs")
PRISTINE_SHA256 = "322fd525d024a8291754bd61049af2b59b9ec82a796a9e6c7939cca248e68bfd"
CLOUD_SHA256 = "629e22e9e41440b0453a157701e5e67c357b4bd757a8a83f3dfd3ad90ae92ee6"
ACCEPTED_INPUTS = {PRISTINE_SHA256: "pristine-f42", CLOUD_SHA256: "reviewed-cloud-prep-f42"}
EXPECTED_OUTPUTS = {
    PRISTINE_SHA256: "f98f27b034a2fe6bcdb6b08d1fa777b59da2eeda3cc17e9d131be5f0a6854963",
    CLOUD_SHA256: "b6bfa796c0c3b72c4298a07aa3429c0042e1b14efc99c2864a6f94bfebdc0a61",
}

OLD_FIELDS = "    shadow_visible: Vec<resident::Visible>,\n"
NEW_FIELDS = OLD_FIELDS + "    shadow_boxed: Vec<resident::Visible>,\n    shadow_seen: std::collections::HashSet<SectionKey>,\n"
OLD_INIT = "            shadow_visible: Vec::new(),\n"
NEW_INIT = OLD_INIT + "            shadow_boxed: Vec::new(),\n            shadow_seen: std::collections::HashSet::new(),\n"
OLD_BODY = """                let mut boxed = Vec::new();
                self.sections
                    .visible(camera, radius, &light, |_| true, |_, _| false, &mut boxed);
                let seen: std::collections::HashSet<_> =
                    shadow_visible.iter().map(|s| s.key).collect();
                shadow_visible.extend(boxed.into_iter().filter(|s| !seen.contains(&s.key)));"""
NEW_BODY = """                let boxed = &mut self.shadow_boxed;
                boxed.clear();
                self.sections
                    .visible(camera, radius, &light, |_| true, |_, _| false, boxed);
                let seen = &mut self.shadow_seen;
                seen.clear();
                seen.extend(shadow_visible.iter().map(|s| s.key));
                shadow_visible.extend(boxed.drain(..).filter(|s| !seen.contains(&s.key)));"""


def transform(source):
    digest = hashlib.sha256(source).hexdigest()
    if digest not in ACCEPTED_INPUTS:
        raise ValueError(f"Unreviewed or already patched gfx.rs SHA256: {digest}")
    text = source.decode("utf-8")
    for old, new in ((OLD_FIELDS, NEW_FIELDS), (OLD_INIT, NEW_INIT), (OLD_BODY, NEW_BODY)):
        if text.count(old) != 1:
            raise ValueError("Expected exactly one reviewed source anchor")
        text = text.replace(old, new, 1)
    output = text.encode("utf-8")
    if hashlib.sha256(output).hexdigest() != EXPECTED_OUTPUTS[digest]:
        raise ValueError("Transformed output differs from reviewed bytes")
    return output, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True, help="Fresh provenance JSON path")
    args = parser.parse_args()
    workspace = args.workspace.resolve(strict=True)
    root = Path(__file__).resolve().parents[3]
    cache = root / "outputs/horizon-runtime/launcher-data/native"
    protected = (cache / "source", cache / "stage", cache / "patched")
    if any(workspace == path or workspace.is_relative_to(path) for path in protected):
        parser.error("Use a separate owned workspace, outside launcher staging/source caches")
    target = workspace / TARGET
    if target.is_symlink() or not target.resolve().is_relative_to(workspace) or not target.is_file():
        parser.error("Target must be a regular workspace file")
    if target.stat().st_size > 2 * 1024 * 1024:
        parser.error("Unexpectedly large renderer source")
    if args.record.exists() or args.record.is_symlink():
        parser.error("Provenance output already exists")
    output, input_sha = transform(target.read_bytes())
    record = {
        "schema": 1, "engine_revision": REVISION, "target": str(TARGET),
        "workspace": str(workspace), "input_kind": ACCEPTED_INPUTS[input_sha],
        "input_sha256": input_sha, "output_sha256": hashlib.sha256(output).hexdigest(),
        "scope": "renderer-owned shadow visibility scratch allocation reuse",
        "runtime_verified": False,
    }
    # Replace only after validating every anchor. Preserve the original source mode.
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".shadow-scratch-", delete=False) as temporary:
        temporary.write(output)
        temporary_path = Path(temporary.name)
    try:
        temporary_path.chmod(target.stat().st_mode & 0o777)
        os.replace(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)
    with args.record.open("x") as handle:
        json.dump(record, handle, indent=2)
        handle.write("\n")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
