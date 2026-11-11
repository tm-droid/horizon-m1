#!/usr/bin/env python3
"""Audit the current installed inputs and stage the exact daily pack order for probes."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

from horizon_converter_packs import inspect_pack

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "outputs/horizon-runtime"
GAME = RUNTIME / "game"
V4 = ROOT / "outputs/horizon-converter/2026-11-05-Tanush-f42-v4"
JAVA = ROOT / "instances/Tanush-26.3/minecraft/mods"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    snapshot = out / "snapshot"
    (snapshot / "resourcepacks").mkdir(parents=True, exist_ok=True)
    settings = dict(line.split(":", 1) for line in (GAME / "options.txt").read_text().splitlines() if ":" in line)
    selection = json.loads(settings["resourcePacks"])
    version = json.loads((RUNTIME / "launcher-data/settings.json").read_text())["selected"]
    native = json.loads((RUNTIME / "launcher-data/versions" / version / "native-mods.json").read_text())
    porter = {item["id"]: item for item in json.loads((V4 / "porting-index.json").read_text())}
    packs, layers = [], defaultdict(list)
    for layer, entry in enumerate(selection):
        if entry == "vanilla":
            continue
        name = entry.removeprefix("file/")
        if entry == name or Path(name).name != name:
            raise ValueError(f"Unexpected pack selection {entry!r}")
        source = GAME / "resourcepacks" / name
        row = {"layer": layer, "name": name}
        try:
            pack = inspect_pack(source)
            row.update(archive_read="pass", sha256=pack["sha256"], members=pack["file_count"],
                       categories=pack["category_counts"],
                       findings=dict(Counter(f["code"] for f in pack["findings"])),
                       overlays=bool((pack["pack_mcmeta"] or {}).get("overlays")))
            for asset in pack["files"]:
                if asset["path"].startswith("assets/"):
                    layers[asset["path"]].append(name)
            dest = snapshot / "resourcepacks" / name
            if not dest.exists():
                shutil.copyfile(source, dest)
            if sha(dest) != row["sha256"] or sha(source) != row["sha256"]:
                raise ValueError("Pack bytes changed during snapshot")
        except (OSError, ValueError, zipfile.BadZipFile) as error:
            row.update(archive_read="failed", error=str(error))
        packs.append(row)

    warnings = []
    for line in (GAME / "logs/latest.log").read_text(errors="replace").splitlines():
        match = re.search(r"Horizon: custom entity model (assets/[^:]+): (missing assets/\S+)", line)
        if match:
            model, missing = match.groups()
            warnings.append({"model": model, "missing": missing.removeprefix("missing "),
                             "root_path_pack_candidates": layers.get(model, [])})
    mods = []
    for path in sorted(JAVA.iterdir()):
        if not path.name.endswith((".jar", ".jar.disabled")):
            continue
        row = {"file": path.name, "enabled_in_java": path.suffix == ".jar"}
        try:
            if path.is_symlink():
                raise ValueError("Symlink")
            row["sha256"] = sha(path)
            with zipfile.ZipFile(path) as archive:
                bad = archive.testzip()
                if bad:
                    raise zipfile.BadZipFile(f"CRC failed for {bad}")
                row["archive_read"] = "pass"
                if "fabric.mod.json" in archive.namelist():
                    raw = archive.read("fabric.mod.json")
                    try:
                        meta = json.loads(raw)
                    except json.JSONDecodeError:
                        row["metadata"] = "requires lenient JSON string control characters"
                        meta = json.loads(raw, strict=False)
                    row.update(id=meta.get("id"), version=meta.get("version"), name=meta.get("name"))
                else:
                    row["metadata"] = "no root Fabric descriptor"
            if item := porter.get(row.get("id")):
                task = json.loads((V4 / item["task"]).read_text())
                row.update(porter_task=item["task_id"], porter_classification=task["classification"],
                           porter_source_matches=row["sha256"] == task["source_sha256"],
                           porter_scan_complete=item["scan_coverage"]["complete"])
        except (OSError, ValueError, zipfile.BadZipFile) as error:
            if row.get("archive_read") == "pass":
                row["metadata_error"] = str(error)
            else:
                row.update(archive_read="failed", error=str(error))
        mods.append(row)
    winner_counts = Counter(owners[-1] for owners in layers.values())
    for pack in packs:
        pack["root_path_wins"] = winner_counts[pack["name"]]
    audit = {"selected_native_version": version, "compiled_native_mods": native["mods"],
             "resourcepack_selection": selection, "packs": packs, "java_mods": mods,
             "observed_missing_model_imports": warnings,
             "text_shader_rejected_in_daily_log": "the resource pack's text shader is not used" in
                (GAME / "logs/latest.log").read_text(errors="replace"),
             "scope": "Archive and metadata checks. Root path wins are candidate layer order, without overlay/filter evaluation."}
    write_json(out / "inventory.json", audit)
    if all(row["archive_read"] == "pass" for row in packs):
        write_json(snapshot / "manifest.json", {"resourcepack_selection": selection,
                   "snapshot_sha256": {row["name"]: row["sha256"] for row in packs}})
    print(json.dumps({"packs": len(packs), "pack_passes": sum(row["archive_read"] == "pass" for row in packs),
          "java_mods": len(mods), "jar_passes": sum(row["archive_read"] == "pass" for row in mods),
          "porter_source_matches": sum(row.get("porter_source_matches", False) for row in mods),
          "missing_model_imports": len(warnings), "compiled_native_mods": len(native["mods"])}))


if __name__ == "__main__":
    main()
