#!/usr/bin/env python3
"""U6: re-resolve CEM part names and animation targets against the pack stack.

Read-only. Builds the effective file map from options.txt `resourcePacks` order (later wins,
root assets only, no pack overlays), then for each requested model lists:
  * `part` values that Horizon's `vanilla_part` + skeleton will not find (given a table of
    vanilla bones known from the nightly source / Codex's bone audit), and
  * animation targets (`name.rx` etc.) whose `name` is neither a jem/jpm id nor a `part` value.

Usage: u6_cem_resolve.py [--home DIR] [--extra OVERLAY.zip ...] [model ...]
`--extra` puts additional zips on top of the stack (to check an overlay before activating it).
"""
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

HOME = Path.home() / "Library/Application Support/horizon"
CEM_DIRS = ("assets/minecraft/optifine/cem/", "assets/minecraft/emf/cem/")
TARGET = re.compile(r"(?<![\w.])([A-Za-z_][\w]*)\.(tx|ty|tz|rx|ry|rz|sx|sy|sz|visible|visible_boxes)\b")
# Bones the engine does have, per docs/horizon-converter/cem-binding-gaps-2026-11-03.md
# (exported native nodes) for the models U6 touches. Names a jem `part` may take directly.
VANILLA = {
    "salmon": {"body_front", "body_back", "head", "left_fin", "right_fin", "top_front_fin",
               "top_back_fin", "back_fin", "root"},
    "cow": {"head", "body", "root", "left_hind_leg", "right_hind_leg", "left_front_leg",
            "right_front_leg"},
}
# the engine's own aliases (crates/horizon-client/src/mobs/cem.rs `vanilla_part`) as used here
ALIAS = {
    "salmon": {"fin_left": "left_fin", "fin_right": "right_fin"},
    "cow": {f"leg{i}": n for i, n in enumerate(
        ["right_hind_leg", "left_hind_leg", "right_front_leg", "left_front_leg"], 1)},
}


def pack_order(home):
    text = (home / "options.txt").read_text()
    line = next(l for l in text.splitlines() if l.startswith("resourcePacks:"))
    names = json.loads(line.split(":", 1)[1].replace("\\u0027", "'"))
    return [n[len("file/"):] for n in names if n.startswith("file/")]


def stack(home, extra):
    files = {}
    zips = [home / "resourcepacks" / n for n in pack_order(home)] + [Path(e) for e in extra]
    for z in zips:
        if not z.exists():
            continue
        zf = zipfile.ZipFile(z)
        for n in zf.namelist():
            if n.startswith(CEM_DIRS):
                files[n] = (z.name, zf, n)
    return files


def ids_and_parts(node, ids, parts):
    if "id" in node:
        ids.add(node["id"])
    if "part" in node:
        parts.add(node["part"])
    for sub in node.get("submodels", []):
        ids_and_parts(sub, ids, parts)


def analyse(model, files):
    for d in CEM_DIRS:
        key = f"{d}{model}.jem"
        if key in files:
            break
    else:
        return None
    pack, zf, name = files[key]
    jem = json.loads(zf.read(name))
    ids, parts, expr = set(), set(), []
    anims = list(jem.get("animations", []))
    for entry in jem["models"]:
        ids_and_parts(entry, ids, parts)
        anims += entry.get("animations", [])
        carrier = entry.get("model")
        if carrier:
            ckey = name.rsplit("/", 1)[0] + "/" + carrier
            if ckey in files:
                cj = json.loads(files[ckey][1].read(files[ckey][2]))
                anims += cj.get("animations", [])
                for sub in cj.get("models", []):
                    ids_and_parts(sub, ids, parts)
            else:
                expr.append(f"missing carrier {carrier}")
    targets = set()
    for a in anims:
        for k, v in a.items():
            for m in TARGET.finditer(k + " " + str(v)):
                targets.add(m.group(1))
    base = model.replace("_baby", "")
    known = VANILLA.get(base, set())
    unresolved_parts = sorted(
        p for p in parts
        if known and ALIAS.get(base, {}).get(p, p) not in known and p not in ids - {p})
    reserved = {"var", "varb", "this", "render", "part"}
    unknown_targets = sorted(t for t in targets if t not in ids and t not in parts and t not in reserved
                             and ALIAS.get(base, {}).get(t, t) not in known)
    return {"pack": pack, "parts_not_in_skeleton": unresolved_parts,
            "targets_without_bone": unknown_targets, "problems": expr}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", default=str(HOME))
    ap.add_argument("--extra", action="append", default=[])
    ap.add_argument("models", nargs="*",
                    default=["salmon", "cow", "cold_cow", "warm_cow", "cow_baby", "cold_cow_baby",
                             "warm_cow_baby", "mooshroom", "creeper_charge"])
    a = ap.parse_args()
    files = stack(Path(a.home), a.extra)
    bad = 0
    for m in a.models:
        r = analyse(m, files)
        if r is None:
            print(f"{m}: no jem in stack")
            continue
        flag = r["parts_not_in_skeleton"] or r["targets_without_bone"] or r["problems"]
        bad += bool(flag)
        print(f"{m} [{r['pack']}]: parts_not_in_skeleton={r['parts_not_in_skeleton']} "
              f"targets_without_bone={r['targets_without_bone']} problems={r['problems']}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
