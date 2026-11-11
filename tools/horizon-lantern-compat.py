#!/usr/bin/env python3
"""Generate a private, unactivated overlay for one audited lantern texture gap."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import zipfile

REVISION = "f42ef42ef6ceccb3c6a20bea2481d87949a51c81"
MODEL = "assets/minecraft/models/block/"
PACK_HASHES = {
    "pack.mcmeta": "a4be1fb6933f9e366052d935f39195a035baed080c123a9a51bfba6304041689",
    MODEL + "template_chain.json": "7d000a44fe4ecaa06ce61bf52ca9768be0b5c55eebc9fca424b3344ef06defd1",
    MODEL + "template_hanging_lantern.json": "3a53bd00983f6621e54dd7a36b1132754e576a4296bfa7208924289708861c26",
    MODEL + "template_lantern.json": "99130fee5affc4484099fe45a017a5ffd6e97020defb929bc33d760b49d49841",
}
CHILD_HASHES = {
    "iron_chain.json": "cd7a73bd8de9eab3524deca354c6efe8c04f892e91bf1e7631a8660e1b4d4003",
    "lantern_hanging.json": "ff097344ea76b118a25ea4c2e389d6c07933fca340775621a4860bcc92b94d28",
    "soul_lantern_hanging.json": "11bb739808c76200f3d0d30aa08e3cc6083fa3355b236879facc9c9e8a869e28",
}
MAX_MEMBER = 512 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(path):
    path = Path(path).absolute()
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise ValueError(f"Symlink path refused: {path}")
    return path.resolve()


def regular_bytes(path, limit):
    path = canonical(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError(f"Expected bounded regular input: {path}")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError(f"Input exceeds byte bound: {path}")
        return data
    finally:
        os.close(descriptor)


def guarded(data, expected, name):
    if digest(data) != expected:
        raise ValueError(f"Source drift; manual review required: {name}")
    return data


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def build_overlay(pack, vanilla_assets, output):
    """Output a fresh directory; leave pack order and original files untouched."""
    pack, assets, output = map(canonical, (pack, vanilla_assets, output))
    if output.exists():
        raise ValueError("Output must be a fresh directory")
    for source in (pack.parent, assets):
        if output.is_relative_to(source) or source.is_relative_to(output):
            raise ValueError("Output must be disjoint from source pack directory and assets")
    pack_bytes = regular_bytes(pack, 64 * 1024 * 1024)
    evidence = {}
    with zipfile.ZipFile(io.BytesIO(pack_bytes)) as archive:
        members = archive.infolist()
        if len(members) > 10_000:
            raise ValueError("Pack entry bound exceeded")
        # These children must still come from the guarded vanilla snapshot.
        if any(entry.filename in {MODEL + name for name in CHILD_HASHES} for entry in members):
            raise ValueError("Pack now overrides a target child; manual review required")
        for name, expected in PACK_HASHES.items():
            matches = [entry for entry in members if entry.filename == name]
            if len(matches) != 1:
                raise ValueError(f"Expected one source member: {name}")
            entry = matches[0]
            mode = entry.external_attr >> 16
            if (entry.file_size > MAX_MEMBER or entry.flag_bits & 1 or
                    stat.S_IFMT(mode) not in (0, stat.S_IFREG)):
                raise ValueError(f"Unsafe or oversized source member: {name}")
            evidence[name] = guarded(archive.read(entry), expected, name)
    metadata = json.loads(evidence["pack.mcmeta"])
    # Derive format97 from this exact audited pack, rather than guessing a version.
    pack_format = metadata["pack"]["pack_format"]
    files = {"pack.mcmeta": encode({"pack": {
        "pack_format": pack_format, "min_format": pack_format, "max_format": pack_format,
        "description": "Private Better Lanterns texture-key candidate; unverified",
    }})}
    changes = []
    for name, expected in CHILD_HASHES.items():
        relative = "minecraft/models/block/" + name
        original = guarded(regular_bytes(assets / relative, MAX_MEMBER), expected, relative)
        evidence["vanilla/" + relative] = original
        child = json.loads(original)
        textures = child["textures"]
        source_key, added_key = ("texture", "chain") if name == "iron_chain.json" else ("lantern", "hanging_lantern")
        textures[added_key] = textures[source_key]
        textures["particle"] = textures[source_key]
        target = MODEL + name
        files[target] = encode(child)
        changes.append({"path": target, "source_sha256": expected,
                        "output_sha256": digest(files[target]),
                        "added_texture_keys": [added_key, "particle"]})
    report = {
        "schema": 1, "status": "candidate-not-activated", "runtime_revision": REVISION,
        "pack": {"path": str(pack), "sha256": digest(pack_bytes)},
        "vanilla_assets": str(assets), "pack_format": pack_format,
        "source_members": {name: digest(data) for name, data in evidence.items()},
        "changes": changes, "runtime_visual_parity_verified": False,
        "gaps": ["Current ordered stack must retain the audited parent/child winners",
                 "Day/night iron-chain and hanging lantern fixture not rendered",
                 "Standing/copper lantern geometry and particles need control comparisons",
                 "No claim about Java/EMF behavior or other pack versions"],
    }
    output.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(output / "lantern-compat.zip", "x") as archive:
        for name, data in files.items():
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(entry, data)
    for name, data in evidence.items():
        destination = output / "source-evidence" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    report["overlay_sha256"] = digest((output / "lantern-compat.zip").read_bytes())
    (output / "provenance.json").write_bytes(encode(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--vanilla-assets", type=Path, required=True,
                        help="Prepared f42 assets/ root, containing minecraft/models/")
    parser.add_argument("--output", type=Path, required=True, help="Fresh disjoint output directory")
    args = parser.parse_args()
    try:
        report = build_overlay(args.pack, args.vanilla_assets, args.output)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Overlay refused; manual review required: {error}\n")
    print(json.dumps({"output": str(args.output), "status": report["status"],
                      "changes": len(report["changes"]), "runtime_visual_parity_verified": False}))


if __name__ == "__main__":
    main()
