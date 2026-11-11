"""Read-only pack evidence and byte-preserving staging; no compatibility claims."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import unicodedata
import zipfile

MAX_FILES = 100_000
MAX_FILE_BYTES = 1024 ** 3
MAX_TOTAL_BYTES = 4 * 1024 ** 3
MAX_METADATA_BYTES = 4 * 1024 ** 2
MAX_COMPRESSION_RATIO = 1000


class PackSafetyError(ValueError):
    """The pack cannot be inspected or copied safely."""


def _safe_name(name):
    if not name or "\\" in name or "\x00" in name or name.startswith("/") or re.match(r"^[A-Za-z]:", name):
        raise PackSafetyError(f"Unsafe pack path: {name!r}")
    parts = name.rstrip("/").split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise PackSafetyError(f"Unsafe pack path: {name!r}")
    return "/".join(parts)


def _entries(path, archive):
    entries = []
    seen = set()
    total = 0
    candidates = archive.infolist() if archive else path.rglob("*")
    for entry in candidates:
        name = _safe_name(entry.orig_filename if archive else entry.relative_to(path).as_posix())
        # ZIP member names are case-sensitive; folders must also be safe to copy
        # onto case-insensitive, normalization-insensitive staging volumes.
        key = name if archive else unicodedata.normalize("NFC", name).casefold()
        if key in seen:
            raise PackSafetyError(f"Duplicate/colliding pack path: {name}")
        seen.add(key)
        mode = (entry.external_attr >> 16) if archive else entry.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise PackSafetyError(f"Symlink in pack: {name}")
        directory = entry.is_dir() if archive else stat.S_ISDIR(mode)
        if len(seen) > MAX_FILES:
            raise PackSafetyError("Pack entry count exceeds safety limit")
        if directory:
            continue
        if not archive and not stat.S_ISREG(mode):
            raise PackSafetyError(f"Nonregular pack file: {name}")
        if archive and stat.S_IFMT(mode) not in (0, stat.S_IFREG):
            raise PackSafetyError(f"Nonregular archive member: {name}")
        size = entry.file_size if archive else entry.lstat().st_size
        total += size
        if size > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
            raise PackSafetyError("Pack size exceeds safety limit")
        if archive and (entry.flag_bits & 1 or size > max(1, entry.compress_size) * MAX_COMPRESSION_RATIO):
            raise PackSafetyError(f"Encrypted or excessive compression ratio: {name}")
        entries.append((name, entry, size))
    # Files cannot also be parents under the source's path semantics.
    files = {name if archive else unicodedata.normalize("NFC", name).casefold()
             for name, _, _ in entries}
    for name in files:
        if any(str(p) in files for p in PurePosixPath(name).parents if str(p) != "."):
            raise PackSafetyError(f"File/directory path conflict: {name}")
    return sorted(entries)


def _open_file(path):
    return os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb")


def _hash_file(path):
    digest = hashlib.sha256()
    with _open_file(path) as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_pack(path: Path) -> dict:
    """Inventory a ZIP or directory. Unsafe members raise PackSafetyError."""
    path = Path(path)
    if path.is_symlink():
        raise PackSafetyError("Pack source must not be a symlink")
    path = path.resolve(strict=True)
    archive = None if path.is_dir() else zipfile.ZipFile(path)
    findings, inventory, metadata = [], [], {}
    categories, namespaces = {}, {}

    def finding(code, name, reason, action="Review this feature against the target renderer before enabling the pack."):
        findings.append({"code": code, "severity": "review", "evidence": name,
                         "path": name, "reason": reason, "next_action": action,
                         "review_required": True})

    try:
        entries = _entries(path, archive)
        aliases = {}
        for name, _, _ in entries:
            aliases.setdefault(unicodedata.normalize("NFC", name).casefold(), []).append(name)
        for names in aliases.values():
            if len(names) > 1:
                for name in names:
                    finding("path_alias_review", name,
                            f"Distinct ZIP paths share a case/normalization alias: {names!r}; all names and bytes are preserved.",
                            "Review target path handling before enabling; do not rename or merge these entries automatically.")
        for name, entry, expected_size in entries:
            digest, data, size = hashlib.sha256(), bytearray(), 0
            is_metadata = name.lower().endswith((".json", ".mcmeta", ".properties", ".jem", ".jpm"))
            with (archive.open(entry) if archive else _open_file(entry)) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    size += len(chunk)
                    if size > expected_size or size > MAX_FILE_BYTES:
                        raise PackSafetyError(f"File changed or exceeds safety limit: {name}")
                    digest.update(chunk)
                    if is_metadata and expected_size <= MAX_METADATA_BYTES:
                        data.extend(chunk)
            if size != expected_size:
                raise PackSafetyError(f"File changed during inspection: {name}")
            inventory.append({"path": name, "size": size, "sha256": digest.hexdigest()})
            parts = name.split("/")
            if "assets" in parts:
                idx = parts.index("assets")
                if len(parts) > idx + 2:
                    namespace, category = parts[idx + 1:idx + 3]
                    namespaces[namespace] = namespaces.get(namespace, 0) + 1
                    categories[category] = categories.get(category, 0) + 1
                    if category in ("models", "blockstates", "items", "font", "sounds", "lang", "shaders") or category == "sounds.json":
                        finding("asset_" + category.replace(".json", ""), name, f"Contains {category} assets requiring target-format review.")
            lower = name.lower()
            for token in ("optifine", "emf", "etf", "cit", "ctm", "random", "sky"):
                if token in [p.lower() for p in parts[:-1]]:
                    finding("feature_" + token, name, f"Path contains the {token} feature directory; check runtime parity for these exact assets.")
            if lower.endswith((".jem", ".jpm")):
                finding("custom_entity_model", name, "Contains a custom entity model file; check runtime parity for this model.")
            if not is_metadata:
                continue
            if expected_size > MAX_METADATA_BYTES:
                finding("metadata_limit", name, "Metadata exceeds the read limit and was not parsed.")
                continue
            if lower.endswith(".properties"):
                text = data.decode("utf-8", errors="replace")
                if "emissive" in lower or re.search(r"(?m)^\s*(?:suffix\.emissive|emissive)\s*[:=]", text):
                    finding("emissive_properties", name, "Emissive properties require renderer support review.")
                continue
            try:
                parsed = json.loads(data)
            except (ValueError, UnicodeError, RecursionError) as exc:
                finding("invalid_json", name, f"JSON could not be parsed: {exc}", "Repair or review the original metadata; no bytes were changed.")
                continue
            if parts[-1] == "pack.mcmeta":
                metadata[name] = parsed
                if name != "pack.mcmeta":
                    finding("nested_pack_metadata", name, "Pack metadata is nested; the intended archive root needs review.")
                if isinstance(parsed, dict):
                    for section in ("overlays", "filter"):
                        if section in parsed:
                            finding("pack_" + section, name, f"Pack declares a {section} section.")
            if "/font/" in lower and isinstance(parsed, dict):
                providers = parsed.get("providers")
                if isinstance(providers, list) and any(isinstance(provider, dict) and provider.get("type") in ("ttf", "minecraft:ttf") for provider in providers):
                    finding("truetype_font", name, "Font declares a TrueType provider; target support needs review.")
            if lower.endswith(".mcmeta") and "/textures/" in lower and isinstance(parsed, dict):
                texture = parsed.get("texture")
                if isinstance(texture, dict):
                    for flag in ("blur", "clamp"):
                        if flag in texture:
                            finding("texture_" + flag, name, f"Texture metadata declares a {flag} override.")
                animation = parsed.get("animation")
                if isinstance(animation, dict) and animation.get("interpolate") is True:
                    finding("texture_interpolation", name, "Animated texture requests interpolation.")
    finally:
        if archive:
            archive.close()
    content_hash = hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if "pack.mcmeta" not in metadata:
        finding("missing_pack_metadata", "pack.mcmeta", "No valid root pack.mcmeta was found.")
    return {"path": str(path), "source": str(path), "name": path.name,
            "kind": "folder" if path.is_dir() else "zip", "files": inventory,
            "file_count": len(inventory), "total_bytes": sum(f["size"] for f in inventory),
            "sha256": content_hash if path.is_dir() else _hash_file(path),
            "content_sha256": content_hash, "namespaces": dict(sorted(namespaces.items())),
            "category_counts": dict(sorted(categories.items())),
            "pack_mcmeta": metadata.get("pack.mcmeta"), "pack_metadata": metadata,
            "findings": findings, "review_required": bool(findings)}


def stage_pack(source: Path, dest: Path) -> dict:
    """Copy to an exact, fresh target and verify content; remove failed output."""
    source, dest = Path(source), Path(dest)
    report = inspect_pack(source)
    source = source.resolve(strict=True)
    dest = dest.absolute()
    resolved_dest = dest.resolve()
    if source == resolved_dest or source in resolved_dest.parents or resolved_dest in source.parents:
        raise PackSafetyError("Source and destination must not overlap")
    if dest.exists() or dest.is_symlink():
        raise FileExistsError(dest)
    created = False
    try:
        if report["kind"] == "zip":
            with dest.open("xb") as output:
                created = True
                with _open_file(source) as original:
                    shutil.copyfileobj(original, output)
        else:
            dest.mkdir()
            created = True
            for record in report["files"]:
                original = source / record["path"]
                # Resolve every parent before opening a file, rejecting intervening links.
                if any(p.is_symlink() for p in [original, *original.parents] if p != source.parent):
                    raise PackSafetyError(f"Symlink appeared during staging: {original}")
                target = dest / record["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                with _open_file(original) as stream, target.open("xb") as output:
                    shutil.copyfileobj(stream, output)
        copied = inspect_pack(dest)
        if copied["sha256"] != report["sha256"] or copied["content_sha256"] != report["content_sha256"]:
            raise PackSafetyError("Content changed during staging; output removed")
    except BaseException:
        if created:
            if report["kind"] == "folder":
                shutil.rmtree(dest)
            else:
                dest.unlink()
        raise
    return {"source": str(source), "destination": str(dest), "kind": report["kind"],
            "sha256": copied["sha256"], "content_sha256": copied["content_sha256"],
            "file_count": copied["file_count"], "byte_preserved": True,
            "review_required": report["review_required"]}
