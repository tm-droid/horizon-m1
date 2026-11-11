#!/usr/bin/env python3
"""Create a fresh source-only f42 checkout copy; never patch the input checkout."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

COMMIT = "f42ef42ef6ceccb3c6a20bea2481d87949a51c81"
BEFORE = "4c7f8650070be17789d500aa86dd013fed9ddbcd0dc754d953f0208acb442cd8"
AFTER = "819c426566a24f6511d8b9794e01e008b6cdb5bdeed46cb07d76030336f02006"
TARGET = Path("crates/horizon-client/src/mobs/cem.rs")
HERE = Path(__file__).resolve().parent

# Exact f42 replacements, kept here alongside the reviewable unified diff.
EDITS = [
    ('fn vanilla_part(model: &str, part: &str) -> String {\n',
     'fn vanilla_part(model: &str, part: &str) -> String {\n'
     '    // Resolve exact baby exceptions before the existing adult-family normalization.\n'
     '    if (model, part) == ("villager_baby", "bodywear") {\n'
     '        return "bb_main".into();\n'
     '    }\n'
     '    let model = model.replace("_baby", "");\n'
     '    let model = model.as_str();\n'),
    ('    let renamed: Option<String> = match (model, part) {\n',
     '    let renamed: Option<String> = match (model, part) {\n'
     '        ("guardian" | "elder_guardian", "body") => Some("head".into()),\n'
     '        ("wolf" | "wolf_armor", "mane") => Some("upper_body".into()),\n'
     '        ("happy_ghast_harness", "body") => Some("harness".into()),\n'
     '        ("puffer_fish_small", "tail") => Some("back_fin".into()),\n'
     '        ("puffer_fish_small", "eye_right") => Some("right_eye".into()),\n'
     '        ("puffer_fish_small", "eye_left") => Some("left_eye".into()),\n'
     '        ("tropical_fish_pattern_a" | "tropical_fish_pattern_b", "fin_top") => {\n'
     '            Some("top_fin".into())\n'
     '        }\n'
     '        ("salmon" | "salmon_small" | "salmon_large", "fin_back_1") => {\n'
     '            Some("top_front_fin".into())\n'
     '        }\n'
     '        ("salmon" | "salmon_small" | "salmon_large", "fin_back_2") => {\n'
     '            Some("top_back_fin".into())\n'
     '        }\n'
     '        ("salmon" | "salmon_small" | "salmon_large", "tail") => Some("back_fin".into()),\n'
     '        ("horse_armor" | "skeleton_horse_armor", "neck") => Some("head_parts".into()),\n'
     '        ("horse_armor" | "skeleton_horse_armor", "mouth") => Some("upper_mouth".into()),\n'),
    ('        let model = name.replace("_baby", "");\n',
     '        let model = name;\n'),
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def render(original):
    if digest(original) != BEFORE:
        raise ValueError("source drift: cem.rs does not match pinned f42 bytes")
    result = original.decode("utf-8")
    for old, new in EDITS:
        if result.count(old) != 1:
            raise ValueError("patch context is not unique")
        result = result.replace(old, new, 1)
    patched = result.encode("utf-8")
    if digest(patched) != AFTER:
        raise ValueError("patched bytes do not match reviewed candidate")
    return patched


def verify_checkout(source):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(source), *args], text=True).strip()
    if git("rev-parse", "HEAD") != COMMIT:
        raise ValueError("checkout is not pinned f42 commit")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("checkout must be clean, including untracked files")


def prepare(source, output):
    source = Path(source).resolve(strict=True)
    requested_output = Path(output).absolute()
    # lexists also catches dangling symlinks; resolving first would hide them.
    if requested_output.exists() or requested_output.is_symlink():
        raise ValueError("output must not exist")
    output = requested_output.resolve()
    allowed = (HERE.parents[1] / "horizon-source-candidates", Path("/private/tmp"))
    if not any(output.is_relative_to(root) and output != root for root in allowed):
        raise ValueError("output must be a fresh child of outputs/horizon-source-candidates or /private/tmp")
    if output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("source and output must not overlap")
    target = source / TARGET
    if target.resolve() != target or not target.is_file():
        raise ValueError("source cem.rs must be a regular file with no symlink parents")
    original = target.read_bytes()
    patched = render(original)
    verify_checkout(source)
    # Copy tracked source and licenses into a new directory, without build output or git state.
    def ignore(path, names):
        return [name for name in (".git", "target") if Path(path) == source and name in names]
    shutil.copytree(source, output, symlinks=True, ignore=ignore)
    (output / TARGET).write_bytes(patched)
    diff = "".join(difflib.unified_diff(
        original.decode().splitlines(True), patched.decode().splitlines(True),
        fromfile="a/" + TARGET.as_posix(), tofile="b/" + TARGET.as_posix()))
    provenance = {
        "upstream_commit": COMMIT, "source": str(source), "output": str(output),
        "path": TARGET.as_posix(), "before_sha256": digest(original),
        "after_sha256": digest(patched), "patch_sha256": digest(diff.encode()),
        "status": "source-only candidate; no build, activation or runtime parity claim",
    }
    (output / "cem-binding-candidate.patch").write_text(diff)
    (output / "cem-binding-candidate.json").write_text(json.dumps(provenance, indent=2) + "\n")
    return provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.source_root, args.output_dir), indent=2))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"refused: {error}\n")


if __name__ == "__main__":
    main()
