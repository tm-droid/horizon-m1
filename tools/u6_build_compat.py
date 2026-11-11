#!/usr/bin/env python3
"""U6: build Horizon-Tanush-Compat-2026-11-10.zip (pack-side fixes only).

Contents, all derived from the effective jems in the live pack stack:
  salmon.jem            drop the three empty placeholder entries (fin_back_1, fin_back_2, tail):
                        no boxes, no submodels, no animation refers to them.
  cow/cold_cow/warm_cow.jem
                        add empty stub nodes mushroom1..3 (same tree spots as cow_baby) so FA's
                        shared cow_animations.jpm targets resolve. Stubs have no boxes: no visual change.
  lantern children      iron_chain / lantern_hanging / soul_lantern_hanging with the extra texture keys
                        Better Lanterns templates need (copied from Codex's lantern-compat-f42-r1).
"""
import copy, json, sys, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import u6_cem_resolve as r

OUT = r.HOME / "resourcepacks" / "Horizon-Tanush-Compat-2026-11-10.zip"
LANT = Path.home() / "Developer/Horizon/outputs/horizon-native/lantern-compat-f42-r1/lantern-compat.zip"
CEM = "assets/minecraft/optifine/cem/"
EMPTY = ("fin_back_1", "fin_back_2", "tail")


def dump(o):
    return json.dumps(o, indent=2).encode()


def stub(name):
    return {"id": name, "translate": [0, 0, 0]}


def find(node, ident):
    if node.get("id") == ident:
        return node
    for s in node.get("submodels", []):
        got = find(s, ident)
        if got:
            return got


def main():
    files = r.stack(r.HOME, [])
    out = {}
    pack, zf, n = files[CEM + "salmon.jem"]
    j = json.loads(zf.read(n))
    keep = []
    for m in j["models"]:
        if m.get("part") in EMPTY and not m.get("boxes") and not m.get("submodels") and not m.get("model"):
            continue
        keep.append(m)
    assert len(keep) == len(j["models"]) - 3, "salmon placeholders changed"
    j["models"] = keep
    out[CEM + "salmon.jem"] = dump(j)
    for cow in ("cow", "cold_cow", "warm_cow"):
        pack, zf, n = files[CEM + cow + ".jem"]
        j = json.loads(zf.read(n))
        body = next(m for m in j["models"] if m.get("id") == "body")
        head2, rot = find(body, "head2"), find(body, "rotation")
        assert head2 and rot, cow
        if not find(body, "mushroom1"):
            head2.setdefault("submodels", []).append(stub("mushroom1"))
            rot.setdefault("submodels", []).append(stub("mushroom2"))
            rot["submodels"].append(stub("mushroom3"))
        out[CEM + cow + ".jem"] = dump(j)
    with zipfile.ZipFile(LANT) as lz:
        for name in lz.namelist():
            if name.endswith(("iron_chain.json", "lantern_hanging.json")):
                out[name] = lz.read(name)
    out["pack.mcmeta"] = dump({"pack": {"pack_format": 97, "min_format": 97, "max_format": 97,
        "description": "Tanush compat 2026-11-10: salmon/cow CEM stubs, Better Lanterns texture keys"}})
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for k in sorted(out):
            z.writestr(zipfile.ZipInfo(k, (1980, 1, 1, 0, 0, 0)), out[k], zipfile.ZIP_DEFLATED)
    print(OUT, len(out), "files")


main()
