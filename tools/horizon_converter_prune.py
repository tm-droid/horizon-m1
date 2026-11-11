"""Opt-in v4 derivation: drop resource-pack namespaces nothing can reach, plus dead TRIM files.

`analyze` is read-only. `derive` clones an existing migration (APFS `cp -cR`), rewrites only the pack ZIPs
that lose files, re-inspects them with the converter's own `inspect_pack`, and records every removed path
and reason in `manifest.json` under `v4_changes`. Stdlib only; never touches the source migration, the
game instance or any runtime.

Reachability: vanilla (`minecraft`, `realms`) and carried-mod namespaces are live. A pack namespace that
neither provides is *reachable* only if a live file (or a file already reached) names it, or one of its
files is a self-root that Horizon reads regardless of namespace and that targets live content:
  - `optifine|mcpatcher/(sky|colormap|lightmap|anim|gui)/*.properties` (read from every namespace);
  - `optifine|mcpatcher/(ctm|cit)/*.properties` whose matchBlocks/matchTiles/items name a live id;
  - `lang/*.json` holding at least one key that does not name a dead namespace (lang merges globally).
Everything else in a namespace nobody references is unreachable. Decisions are per namespace; the file-level
count inside reachable namespaces is reported but never pruned.
"""
from __future__ import annotations

import collections
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import zipfile

from horizon_converter_packs import inspect_pack

MERGED = re.compile(r"^(lang/[^/]+\.json|sounds\.json|atlases/.+\.json|font/.+\.json)$")
TEXT_EXT = (".json", ".mcmeta", ".properties", ".jem", ".jpm", ".txt", ".fsh", ".vsh", ".glsl")
MAX_TEXT = 4 * 1024 * 1024
REF = re.compile(r"(?<![A-Za-z0-9_.\-])([a-z0-9_.\-]+):([A-Za-z0-9_./\-]+)")
FEATURE = re.compile(r"^(?:optifine|mcpatcher)/([a-z_]+)/")
ROOT_FEATURES = {"sky", "colormap", "lightmap", "anim", "gui"}
MATCH_KEYS = {"matchblocks", "matchtiles", "blocks", "items", "matchitems"}
DIRS = ("", "models/", "textures/", "sounds/", "blockstates/", "items/", "font/", "particles/", "equipment/",
        "atlases/", "texts/", "shaders/", "optifine/", "mcpatcher/")
EXTS = ("", ".json", ".png", ".png.mcmeta", ".ogg", ".properties", ".mcmeta", ".jem", ".jpm", ".txt")
MIN_FREE = 4 * 1024 ** 3
STRICT_DIRS = ("models/", "textures/", "blockstates/", "items/")


def overlay_dirs(meta):
    out = set()
    if isinstance(meta, dict):
        for key, value in meta.items():
            if key == "overlays" and isinstance(value, dict):
                for entry in value.get("entries", []):
                    if isinstance(entry, dict) and entry.get("directory"):
                        out.add(entry["directory"])
            else:
                out |= overlay_dirs(value)
    elif isinstance(meta, list):
        for value in meta:
            out |= overlay_dirs(value)
    return out


def _pack_source(directory, entry):
    return directory / "resourcepacks" / os.path.basename((entry.get("staging") or {})["destination"])


class _Reader:
    """Cached member reads from ZIPs (or folder packs)."""

    def __init__(self):
        self.zips = {}

    def read(self, source, raw):
        if source.is_dir():
            return (source / raw).read_bytes()
        archive = self.zips.get(source) or self.zips.setdefault(source, zipfile.ZipFile(source))
        return archive.read(raw)

    def close(self):
        for archive in self.zips.values():
            archive.close()


def _load(directory):
    directory = Path(directory).resolve()
    manifest = json.loads((directory / "manifest.json").read_text())
    packs = sorted((e for e in manifest["resourcepacks"] if "files" in e), key=lambda e: e["order"])
    records = []
    for index, entry in enumerate(packs):
        source = _pack_source(directory, entry)
        for item in entry["files"]:
            parts = item["path"].split("/")
            if "assets" not in parts:
                continue
            at = parts.index("assets")
            if len(parts) < at + 3:
                continue
            records.append({"tier": "pack", "layer": index, "pack": entry["name"], "raw": item["path"],
                            "ns": parts[at + 1], "rel": "/".join(parts[at + 2:]), "root": at == 0,
                            "size": item["size"], "sha": item["sha256"], "src": source})
    mod_dir = directory / "mod-asset-packs"
    if mod_dir.is_dir():
        for name in sorted(os.listdir(mod_dir)):
            if not name.endswith(".zip"):
                continue
            with zipfile.ZipFile(mod_dir / name) as archive:
                for info in archive.infolist():
                    parts = info.filename.split("/")
                    if parts[0] == "assets" and len(parts) >= 3 and not info.is_dir():
                        records.append({"tier": "mod", "layer": -1, "pack": name, "raw": info.filename,
                                        "ns": parts[1], "rel": "/".join(parts[2:]), "root": True,
                                        "size": info.file_size, "sha": None, "src": mod_dir / name})
    return directory, manifest, packs, records


def analyze(directory):
    """Per-namespace reachability. Read-only."""
    directory, manifest, packs, records = _load(directory)
    keep = {r["ns"] for r in records if r["tier"] == "mod"} | {"minecraft", "realms"}
    dead_ns = sorted({r["ns"] for r in records if r["tier"] == "pack"} - keep)
    dead_set = set(dead_ns)
    winner = {}
    for r in records:
        if r["tier"] == "pack" and r["root"] and not MERGED.match(r["rel"]):
            key = (r["ns"], r["rel"])
            winner[key] = max(winner.get(key, -1), r["layer"])

    def active(r):
        key = (r["ns"], r["rel"])
        if r["tier"] == "mod":
            return key not in winner
        if r["root"] and not MERGED.match(r["rel"]):
            return winner[key] == r["layer"]
        return True

    index = collections.defaultdict(list)
    for r in records:
        if r["ns"] in dead_set and r["tier"] == "pack":
            index[(r["ns"], r["rel"])].append(r)
    reached, evidence, queue = set(), collections.defaultdict(list), []
    reader = _Reader()
    texts = {}

    def text(r):
        if not r["rel"].lower().endswith(TEXT_EXT) or r["size"] > MAX_TEXT:
            return ""
        key = (r["src"], r["raw"])
        if key not in texts:
            try:
                texts[key] = reader.read(r["src"], r["raw"]).decode("utf-8", "replace")
            except (KeyError, OSError, zipfile.BadZipFile):
                texts[key] = ""
        return texts[key]

    def mark(ns, rel, why):
        if (ns, rel) in reached or (ns, rel) not in index:
            return False
        reached.add((ns, rel))
        if len(evidence[ns]) < 3:
            evidence[ns].append(why)
        queue.extend(index[(ns, rel)])
        if rel.endswith(".png"):   # animation sidecar, and the OptiFine emissive overlay found beside its base
            mark(ns, rel + ".mcmeta", why)
            if not rel.endswith("_e.png"):
                mark(ns, rel[:-4] + "_e.png", why)
        return True

    def follow(r):
        who = "%s:%s" % (r["pack"], r["raw"])
        for m in REF.finditer(text(r)):
            ns, rest = m.group(1), m.group(2).rstrip(".")
            if ns not in dead_set:
                continue
            for d in DIRS:
                for e in EXTS:
                    mark(ns, d + rest + e, "%s -> %s:%s" % (who, ns, rest))

    def drain():
        while queue:
            r = queue.pop()
            follow(r)

    try:
        for r in records:
            if r["ns"] in keep and active(r) and r["rel"].lower().endswith(TEXT_EXT):
                follow(r)
                drain()
        lang_dead = re.compile(r"(?:^|\.)(?:%s)(?:\.|$)" % "|".join(re.escape(n) for n in dead_ns)) if dead_ns else None
        for r in [x for x in records if x["ns"] in dead_set and x["tier"] == "pack"]:
            rel = r["rel"]
            m = FEATURE.match(rel)
            why = None
            if m and rel.endswith(".properties"):
                feature = m.group(1)
                if feature in ROOT_FEATURES:
                    why = "self-root: %s properties are read from every namespace" % feature
                elif feature in ("ctm", "cit"):
                    live = False
                    for line in text(r).splitlines():
                        k, eq, v = line.partition("=")
                        if eq and k.strip().lower() in MATCH_KEYS:
                            for tok in v.split():
                                ns, colon, rest = tok.partition(":")
                                if not colon or "=" in rest or ns in keep:
                                    live = True
                    if live:
                        why = "self-root: %s rule matches a live block/item" % feature
                        folder = rel.rsplit("/", 1)[0] + "/"
                        for (ns2, rel2) in list(index):
                            if ns2 == r["ns"] and rel2.startswith(folder) and "/" not in rel2[len(folder):]:
                                mark(ns2, rel2, "sibling of " + r["raw"])
            elif re.match(r"^lang/[^/]+\.json$", rel):
                try:
                    keys = json.loads(text(r)).keys()
                except (ValueError, AttributeError):
                    keys = ()
                if any(not (lang_dead and lang_dead.search(k)) for k in keys):
                    why = "self-root: lang file holds keys for live content"
            if why:
                mark(r["ns"], rel, "%s (%s)" % (why, r["raw"]))
            drain()
    finally:
        reader.close()

    namespaces = {}
    for ns in dead_ns:
        recs = [r for r in records if r["ns"] == ns and r["tier"] == "pack"]
        namespaces[ns] = {
            "reachable": any(k[0] == ns for k in reached),
            "files": len(recs), "bytes": sum(r["size"] for r in recs),
            "files_reached": sum(1 for r in recs if (ns, r["rel"]) in reached),
            "packs": sorted({r["pack"] for r in recs}), "evidence": evidence.get(ns, []),
        }
    unreachable = [{"pack": r["pack"], "path": r["raw"], "size": r["size"], "namespace": r["ns"]}
                   for r in records if r["tier"] == "pack" and namespaces.get(r["ns"], {}).get("reachable") is False]
    unreached = [{"pack": r["pack"], "path": r["raw"], "size": r["size"], "namespace": r["ns"]}
                 for r in records if r["tier"] == "pack" and namespaces.get(r["ns"], {}).get("reachable")
                 and (r["ns"], r["rel"]) not in reached and r["rel"].startswith(STRICT_DIRS)]
    return {"migration": str(directory), "live_namespaces": len(keep), "namespaces": namespaces,
            "unreachable_paths": unreachable, "unreached_in_reachable": unreached}


def _shadowing():
    spec = importlib.util.spec_from_file_location("horizon_layer_shadowing", Path(__file__).with_name("horizon-layer-shadowing.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def trim_candidates(directory):
    """Dead / byte-identical files of layers the shadowing audit labels TRIM (no overlays, filter or sub-packs)."""
    sh = _shadowing()
    directory = str(Path(directory).resolve())
    _, layers = sh.load_layers(directory)
    mods = sh.load_mods(directory)
    cache, zips = {}, {}

    def hashes_mod(path, mi):
        if (mi, path) not in cache:
            zp = mods[mi]["zip"]
            archive = zips.get(zp) or zips.setdefault(zp, zipfile.ZipFile(zp))
            cache[(mi, path)] = sh.sha256_zip(archive, path)
        return cache[(mi, path)]

    pot = sh.simulate(layers, mods, hashes_mod, lambda l: True)
    owners = collections.defaultdict(list)
    for l in layers:
        for p in l["root"]:
            owners[p].append((l["order"], l["name"]))
    out = []
    try:
        for index, l in enumerate(layers):
            if l["filter"] or l["overlay_files"] or l["nested_files"]:
                continue
            removable = pot[("l", index)]
            fully = len(removable) == len(l["root"]) and not l["merged"] and l["root"]
            size = sum(l["root"][p][1] for p in removable)
            if fully or not (size >= 100 * 1024 or len(removable) >= 25):
                continue
            for p in sorted(removable):
                higher = sorted(o for o in owners[p] if o[0] > l["order"])
                why = ("TRIM %s: shadowed by higher layer %s" % (l["name"], higher[-1][1]) if higher else
                       "TRIM %s: byte-identical to the next lower provider" % l["name"])
                out.append({"pack": l["name"], "path": p, "size": l["root"][p][1], "namespace": p.split("/")[1], "why": why})
    finally:
        for archive in zips.values():
            archive.close()
    return out


def effective_map(packs, mod_paths):
    """path -> sha256 for the highest pack providing it; `None` marks mod-tier-only paths."""
    eff = {}
    for entry in sorted(packs, key=lambda e: e["order"]):
        for item in entry["files"]:
            eff[item["path"]] = item["sha256"]
    for p in mod_paths:
        eff.setdefault(p, None)
    return eff


def _rewrite_zip(source, dest, drop):
    with zipfile.ZipFile(source) as zin, zipfile.ZipFile(dest, "x") as zout:
        infos = zin.infolist()
        parents = lambda name: {name.rsplit("/", k)[0] + "/" for k in range(1, name.count("/") + 1)}
        kept = set()
        for i in infos:
            if i.filename not in drop and not i.is_dir():
                kept |= parents(i.filename)
        gone = set()
        for name in drop:
            gone |= parents(name)
        for i in infos:
            if i.filename in drop or (i.is_dir() and i.filename in gone and i.filename not in kept):
                continue
            z = zipfile.ZipInfo(i.filename, i.date_time)
            z.compress_type, z.external_attr, z.create_system, z.comment = i.compress_type, i.external_attr, i.create_system, i.comment
            zout.writestr(z, zin.read(i), compress_type=i.compress_type)


def _swap_paths(value, pairs):
    if isinstance(value, str):
        for old, new in pairs:
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [_swap_paths(v, pairs) for v in value]
    if isinstance(value, dict):
        return {k: _swap_paths(v, pairs) for k, v in value.items()}
    return value


def _clone(source, dest):
    try:
        subprocess.run(["cp", "-cR", str(source), str(dest)], check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source, dest)


def derive(source, dest, prune_namespaces=True, prune_trim=True, prune_unreached_files=False, min_free=MIN_FREE):
    """Create migration `dest` from `source`. Returns the `v4_changes` record.

    `prune_unreached_files` (strict) also drops models/textures/blockstates/items that no live file reaches inside
    reachable pack-private namespaces (e.g. the thousands of rail models only dead mods referenced)."""
    source, dest = Path(source).resolve(strict=True), Path(dest).absolute()
    if dest.exists() or dest.is_symlink():
        raise FileExistsError(dest)
    if source == dest.resolve() or source in dest.resolve().parents or dest.resolve() in source.parents:
        raise ValueError("Source and destination must not overlap")
    analysis = analyze(source) if prune_namespaces else {"namespaces": {}, "unreachable_paths": [], "unreached_in_reachable": []}
    trims = trim_candidates(source) if prune_trim else []
    removal = collections.OrderedDict()   # pack -> {path: why}
    for item in analysis["unreachable_paths"]:
        info = analysis["namespaces"][item["namespace"]]
        removal.setdefault(item["pack"], {})[item["path"]] = (
            "namespace '%s' unreachable: not provided by vanilla or a carried mod and no live file references it" % item["namespace"], item["size"], "ns")
    if prune_unreached_files:
        for item in analysis["unreached_in_reachable"]:
            removal.setdefault(item["pack"], {}).setdefault(item["path"], (
                "strict: no live file references this model/texture/blockstate/item in namespace '%s'" % item["namespace"], item["size"], "strict"))
    for item in trims:
        removal.setdefault(item["pack"], {}).setdefault(item["path"], (item["why"], item["size"], "trim"))
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    by_name = {e["name"]: e for e in manifest["resourcepacks"] if "files" in e}
    need = sum(os.path.getsize(_pack_source(source, by_name[n])) for n in removal)
    free = shutil.disk_usage(dest.parent).free
    if free - need < min_free:
        raise OSError("Refusing: %d bytes free, %d needed for rewritten packs, %d required to stay free" % (free, need, min_free))
    pairs = [(str(source), str(dest))]
    before = effective_map([e for e in manifest["resourcepacks"] if "files" in e], [])
    _clone(source, dest)
    try:
        changed = {}
        for name, files in removal.items():
            entry = by_name[name]
            old = _pack_source(source, entry)
            new = _pack_source(dest, entry)
            drop = set(files)
            if old.is_dir():
                for rel in drop:
                    (new / rel).unlink()
            else:
                new.unlink()
                _rewrite_zip(old, new, drop)
            report = inspect_pack(new)
            changed[name] = (entry, report, old)
        for name, (entry, report, old) in changed.items():
            for key in ("files", "file_count", "total_bytes", "content_sha256", "sha256", "namespaces",
                        "category_counts", "findings", "review_required"):
                entry[key] = report[key]
            entry["v4_prune"] = {"v3_sha256": entry["staging"]["sha256"], "v3_file_count": entry["staging"]["file_count"],
                                 "removed_files": len(removal[name])}
            entry["staging"].update({"sha256": report["sha256"], "content_sha256": report["content_sha256"],
                                     "file_count": report["file_count"], "byte_preserved": False})
            entry["status"] = "pruned-v4-runtime-unverified"
        packs_after = [e for e in manifest["resourcepacks"] if "files" in e]
        after = effective_map(packs_after, [])
        removed_paths = {(n, p) for n, f in removal.items() for p in f}
        gone_ok = {p for f in removal.values() for p, (_, _, kind) in f.items() if kind != "trim"}
        mismatch, absent = [], 0
        mod_sha = _ModHasher(source)
        for path, sha in before.items():
            if after.get(path, "-") == sha:
                continue
            if path not in after and path in gone_ok:
                absent += 1
                continue
            if path not in after:
                got = mod_sha(path)   # trimmed file now served by a carried-mod pack
                if got == sha:
                    continue
            mismatch.append(path)
        mod_sha.close()
        extra = {p for p in after if p not in before}
        record = {
            "derived_from": str(source), "derived_from_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "tool": "horizon-convert --prune-unreachable-namespaces", "created_unix": int(time.time()),
            "unreachable_namespaces": {k: {"files": v["files"], "bytes": v["bytes"], "packs": v["packs"]}
                                       for k, v in sorted(analysis["namespaces"].items()) if not v["reachable"]},
            "reachable_namespaces": {k: {"files": v["files"], "bytes": v["bytes"], "evidence": v["evidence"]}
                                     for k, v in sorted(analysis["namespaces"].items()) if v["reachable"]},
            "removed_file_count": len(removed_paths),
            "removed_bytes": sum(s for f in removal.values() for _, s, _ in f.values()),
            "mode": "strict (also unreached files in reachable namespaces)" if prune_unreached_files else "namespace-level",
            "effective_map_check": {"paths_before": len(before), "paths_after": len(after), "removed_namespace_or_strict_paths": absent,
                                    "changed_or_lost_in_kept_namespaces": len(mismatch), "new_paths": len(extra),
                                    "examples": sorted(mismatch)[:5]},
            "review_queues_regenerated": False,
            "note": "review-queue.jsonl / raw-review-queue.jsonl are copied from the source and may cite removed paths.",
            "removed": [{"pack": n, "reason": why, "paths": sorted(p for p, (w, _, _) in f.items() if w == why)}
                        for n, f in removal.items() for why in sorted({w for w, _, _ in f.values()})],
        }
        if mismatch or extra:
            raise RuntimeError("Effective path->sha map changed outside removals: %s" % (sorted(mismatch)[:5] or sorted(extra)[:5]))
        manifest = _swap_paths(manifest, pairs)
        manifest["v4_changes"] = record
        (dest / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        for name in ("upstream-plan.json", "appearance-contract.json"):
            target = dest / name
            if target.is_file():
                text = target.read_text()
                for old, new in pairs:
                    text = text.replace(old, new)
                target.write_text(text)
        return record
    except BaseException:
        shutil.rmtree(dest, ignore_errors=True)
        raise


class _ModHasher:
    def __init__(self, directory):
        self.index = collections.defaultdict(list)
        self.zips = {}
        mod_dir = Path(directory) / "mod-asset-packs"
        if mod_dir.is_dir():
            for name in sorted(os.listdir(mod_dir)):
                if name.endswith(".zip"):
                    archive = zipfile.ZipFile(mod_dir / name)
                    self.zips[name] = archive
                    for n in archive.namelist():
                        self.index[n].append(name)

    def __call__(self, path):
        names = self.index.get(path)
        return hashlib.sha256(self.zips[names[0]].read(path)).hexdigest() if names else None

    def close(self):
        for archive in self.zips.values():
            archive.close()
