"""Carry inert Java-mod assets into a resource pack; never port Java behavior."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import zipfile

from horizon_converter_packs import PackSafetyError, _hash_file, inspect_pack

TARGET_REVISION = "e6e12d40c522b8f5ee8740dd861c96689023737a"
STATUS = "assets-only-runtime-unverified"


def _json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def _license_path(name):
    leaf = PurePosixPath(name).name.lower()
    return (leaf.startswith(("license", "licence", "copying", "notice", "copyright"))
            or any(part.lower() in ("licenses", "licences", "license", "licence") for part in PurePosixPath(name).parts[:-1]))


def _zip_info(name):
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.compress_type = zipfile.ZIP_STORED
    return info


def carry_mod_assets(jar: Path, dest: Path) -> dict:
    """Create an exact fresh ZIP, or return no-assets without creating output."""
    jar, dest = Path(jar), Path(dest)
    if jar.is_symlink():
        raise PackSafetyError("Source JAR must not be a symlink")
    source = jar.resolve(strict=True)
    target = dest.absolute()
    resolved_target = target.resolve()
    if source == resolved_target or source in resolved_target.parents or resolved_target in source.parents:
        raise PackSafetyError("Source and destination must not overlap")
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    if not source.is_file():
        raise PackSafetyError("Source must be a JAR archive")
    report = inspect_pack(source)
    records = report["files"]
    code = [r for r in records if r["path"].lower().endswith(".class")]
    nested = [r for r in records if r["path"].lower().endswith(".jar")]
    assets = [r for r in records if r["path"].startswith("assets/")
              and not r["path"].lower().endswith((".class", ".jar"))]
    data = [r for r in records if r["path"].startswith("data/")]
    summary = {"source": str(source), "source_sha256": report["sha256"],
               "asset_count": len(assets), "omitted_code_count": len(code),
               "omitted_data_count": len(data), "omitted_nested_jar_count": len(nested),
               "review_required": True, "manual_activation_required": True,
               "manual_ordering_required": True}
    findings = [f for f in report["findings"] if f.get("path", "").startswith("assets/")]
    source_metadata = [r["path"] for r in records if r["path"] == "pack.mcmeta"]
    omitted_overlay_paths = [r["path"] for r in records if "/assets/" in r["path"]
                             and not r["path"].startswith("assets/")]
    if source_metadata:
        findings.append({"code": "omitted_source_pack_metadata", "severity": "review",
                         "evidence": "pack.mcmeta", "review_required": True,
                         "reason": "Original root pack metadata is preserved as evidence, but its pack-level semantics are not applied to the generated layer.",
                         "next_action": "Review source-metadata/pack.mcmeta and preserve required semantics before enabling this layer."})
        for original_finding in report["findings"]:
            if original_finding.get("path") != "pack.mcmeta":
                continue
            if original_finding["code"] in ("pack_filter", "pack_overlays"):
                section = original_finding["code"].removeprefix("pack_")
                findings.append({"code": "omitted_source_" + section, "severity": "review",
                                 "evidence": "pack.mcmeta", "review_required": True,
                                 "reason": f"Source {section} semantics are omitted; {len(omitted_overlay_paths)} nested overlay asset files are not carried.",
                                 "next_action": "Preserve source filter/overlay semantics and required overlay assets before enabling this layer."})
            elif original_finding["code"] in ("invalid_json", "metadata_limit"):
                findings.append(original_finding)
    if omitted_overlay_paths:
        findings.append({"code": "omitted_overlay_assets", "severity": "review",
                         "evidence": omitted_overlay_paths, "review_required": True,
                         "reason": "Nested asset roots are omitted; they may implement source pack overlays.",
                         "next_action": "Review these source paths and preserve required overlay behavior before enabling this layer."})
    summary["omitted_overlay_asset_count"] = len(omitted_overlay_paths)
    summary["omitted_overlay_asset_paths"] = omitted_overlay_paths
    if not assets:
        return {**summary, "status": "no-assets", "destination": None, "findings": findings}
    namespaces = sorted({r["path"].split("/")[1] for r in assets if len(r["path"].split("/")) >= 3})
    for namespace in namespaces:
        findings.append({"code": "minecraft_overrides" if namespace == "minecraft" else "namespace_review",
                         "severity": "review", "evidence": f"assets/{namespace}/", "review_required": True,
                         "reason": "Overrides vanilla resources; ordering changes the result." if namespace == "minecraft" else "Namespace ownership and referenced registrations are not verified.",
                         "next_action": "Review namespace references and activate this layer manually in the intended order."})
    for record in assets:
        name = record["path"]
        if name.endswith(".mcmeta") or len(name.split("/")) < 3:
            findings.append({"code": "preserved_asset_metadata_review", "severity": "review",
                             "evidence": name, "review_required": True,
                             "reason": "Asset metadata/path is preserved verbatim; target interpretation is unverified.",
                             "next_action": "Review the original metadata and path before manual activation."})
    selected = {r["path"]: r for r in assets}
    licenses = [r for r in records if _license_path(r["path"])
                and not r["path"].lower().endswith((".class", ".jar"))]
    copies = {name: name for name in selected}
    copies.update({"source-licenses/" + r["path"]: r["path"] for r in licenses})
    copies.update({"source-metadata/" + name: name for name in source_metadata})
    provenance = {
        "status": STATUS, "source_name": source.name, "source_sha256": report["sha256"],
        "target_revision": TARGET_REVISION, "target_resource_format": [97, 1],
        "entries": records, "carried_assets": [r["path"] for r in assets],
        "preserved_licenses": [r["path"] for r in licenses],
        "preserved_source_metadata": source_metadata,
        "omitted_overlay_asset_count": len(omitted_overlay_paths),
        "omitted_overlay_asset_paths": omitted_overlay_paths,
        "omitted_code_count": len(code), "omitted_data_count": len(data),
        "omitted_nested_jar_count": len(nested), "findings": findings,
        "manual_activation_required": True, "manual_ordering_required": True,
        "limitations": ["No Java behavior, entrypoints or block/item/entity registrations are converted.",
                        "No data/ gameplay content is converted.",
                        "Asset metadata and namespaces are preserved without upgrading or validating runtime parity.",
                        "Activate and order every generated resource-pack layer explicitly; this is not a full mod port."],
    }
    generated = {
        "pack.mcmeta": _json_bytes({"pack": {"description": f"Assets carried from {source.name}; no Java behavior",
                                             "min_format": [97, 1], "max_format": [97, 1]}}),
        "conversion-provenance.json": _json_bytes(provenance),
    }
    expected = {name: {"size": len(value), "sha256": hashlib.sha256(value).hexdigest()}
                for name, value in generated.items()}
    source_records = {r["path"]: r for r in records}
    expected.update({name: source_records[original] for name, original in copies.items()})
    created = False
    try:
        with target.open("xb") as output:
            created = True
            with zipfile.ZipFile(source) as original, zipfile.ZipFile(output, "w") as converted:
                for name in sorted([*copies, *generated]):
                    info = _zip_info(name)
                    if name in generated:
                        converted.writestr(info, generated[name])
                    else:
                        with original.open(copies[name]) as input_stream, converted.open(info, "w", force_zip64=True) as output_stream:
                            shutil.copyfileobj(input_stream, output_stream)
        copied = inspect_pack(target)
        actual = {r["path"]: {"size": r["size"], "sha256": r["sha256"]} for r in copied["files"]}
        proof = {name: {"size": r["size"], "sha256": r["sha256"]} for name, r in expected.items()}
        if actual != proof or _hash_file(source) != report["sha256"]:
            raise PackSafetyError("Source or carried content changed during conversion")
    except BaseException:
        if created:
            target.unlink()
        raise
    return {**summary, "status": STATUS, "destination": str(target),
            "sha256": copied["sha256"], "content_sha256": copied["content_sha256"],
            "assets_byte_preserved": True, "license_count": len(licenses),
            "namespaces": namespaces, "findings": findings}
