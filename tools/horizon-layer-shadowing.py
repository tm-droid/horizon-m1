#!/usr/bin/env python3
"""Read-only layer shadowing / duplicate audit for a Horizon converter migration.

usage: python3 -I horizon-layer-shadowing.py <migration dir> [--json out.json] [--md table.md]

Inputs (never modified): <dir>/manifest.json (per-file path/size/sha256 of every staged resource pack),
<dir>/resourcepacks/*.zip (only read for CEM .jem -> .jpm references), <dir>/mod-asset-packs/mod-NNNN.zip
and <dir>/mods/mod-NNNN.json (names).

Layer order: manifest `resourcepacks[].order` ascending; HIGHER order wins (the options.txt convention: last
pack on top). Carried mod-asset packs form one tier below every resource pack, above vanilla (vanilla files are
not in the manifest, so shadowing of vanilla is not modelled).

Safety rules (conservative, path-level only):
 - a layer with pack.mcmeta `filter`, overlay directories that hold files, or nested sub-packs is REVIEW;
 - merged resource types (lang, sounds.json, atlases, font) never count as shadowed;
 - DROP = every file is shadowed or byte-identical to what lies beneath (verified: effective path->sha256 map
   is identical before/after the simulated removal).
"""
import argparse
import collections
import json
import os
import re
import sys
import zipfile
import hashlib

EMISSIVE_CAP = 96   # MAX(128) - NATIVE(32): native_emissive::load_optifine stops here
EMISSIVE_MAX = 128
MERGED = re.compile(r"^assets/[^/]+/(lang/[^/]+\.json|sounds\.json|atlases/.+\.json|font/.+\.json)$")
CEM = re.compile(r"^assets/[^/]+/(?:optifine|emf)/cem/.+\.(jem|jpm)$")
FAMILIES = {
    "ores": re.compile(r"(?:^|[/_])ores?(?:[/_.]|$)|_ore(?:[_/.]|$)|ingot|nugget|raw_(?:iron|gold|copper)|ancient_debris"),
    "ctm": re.compile(r"/optifine/ctm/"),
    "lanterns": re.compile(r"lantern"),
    "torches": re.compile(r"torch"),
    "flower_pots": re.compile(r"flower_pot|potted_"),
}


def has_key(o, key):
    if isinstance(o, dict):
        return key in o or any(has_key(v, key) for v in o.values())
    if isinstance(o, list):
        return any(has_key(v, key) for v in o)
    return False


def overlay_dirs(meta):
    out = set()
    if isinstance(meta, dict):
        for k, v in meta.items():
            if k == "overlays" and isinstance(v, dict):
                for e in v.get("entries", []):
                    if isinstance(e, dict) and e.get("directory"):
                        out.add(e["directory"])
            else:
                out |= overlay_dirs(v)
    elif isinstance(meta, list):
        for v in meta:
            out |= overlay_dirs(v)
    return out


def sha256_zip(zf, name):
    h = hashlib.sha256()
    with zf.open(name) as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_layers(d):
    man = json.load(open(os.path.join(d, "manifest.json")))
    layers = []
    for e in man["resourcepacks"]:
        if "files" not in e:
            continue  # vanilla placeholder
        meta = e.get("pack_metadata", {})
        odirs = overlay_dirs(meta)
        root, other, merged = {}, [], {}
        for f in e["files"]:
            p = f["path"]
            if p.startswith("assets/"):
                (merged if MERGED.match(p) else root)[p] = (f["sha256"], f["size"])
            elif p in ("pack.mcmeta", "pack.png") or p.upper().startswith(("LICENSE", "README")):
                continue
            elif p.split("/")[0] in odirs:
                other.append(("overlay", p, f["size"]))
            elif "/assets/" in p:
                other.append(("nested", p, f["size"]))
        layers.append({
            "order": e["order"], "name": e["name"], "root": root, "merged": merged, "other": other,
            "filter": has_key(meta, "filter") or has_key(meta, "block"),
            "overlay_files": sum(1 for o in other if o[0] == "overlay"),
            "nested_files": sum(1 for o in other if o[0] == "nested"),
            "overlay_dirs": sorted(odirs), "dest": (e.get("staging") or {}).get("destination"),
        })
    layers.sort(key=lambda l: l["order"])
    return man, layers


def load_mods(d):
    out = []
    mdir = os.path.join(d, "mod-asset-packs")
    if not os.path.isdir(mdir):
        return out
    for fn in sorted(os.listdir(mdir)):
        if not fn.endswith(".zip"):
            continue
        zp = os.path.join(mdir, fn)
        name = fn[:-4]
        try:
            j = json.load(open(os.path.join(d, "mods", name + ".json")))
            name = "%s (%s)" % (j.get("name") or j.get("id"), fn[:-4])
        except Exception:
            pass
        files = {}
        with zipfile.ZipFile(zp) as zf:
            for i in zf.infolist():
                if i.filename.startswith("assets/") and not i.is_dir():
                    files[i.filename] = i.file_size
        out.append({"zip": zp, "name": name, "files": files})
    return out


def simulate(layers, mods, hashes_mod, eligible):
    """Bottom-up removal; each removal keeps the effective path->hash map unchanged. Returns {layer idx: set(paths)}
    and {mod idx: set(paths)}. `eligible(layer)` says whether that layer may lose files."""
    provs = collections.defaultdict(list)  # path -> [(order, hash, layer_ref)] ; mods order 0
    for mi, m in enumerate(mods):
        for p in m["files"]:
            provs[p].append([0, None, ("m", mi)])
    for li, l in enumerate(layers):
        for p, (h, s) in l["root"].items():
            provs[p].append([l["order"], h, ("l", li)])
    removed = {("l", i): set() for i in range(len(layers))}
    removed.update({("m", i): set() for i in range(len(mods))})
    alive = {p: sorted(v, key=lambda x: x[0]) for p, v in provs.items()}
    # mods first (lowest), then layers ascending
    todo = [("m", i) for i in range(len(mods))] + [("l", i) for i in range(len(layers))]
    for ref in todo:
        if ref[0] == "m":
            paths = list(mods[ref[1]]["files"])
            ok = True
        else:
            l = layers[ref[1]]
            paths = list(l["root"])
            ok = eligible(l)
        if not ok:
            continue
        for p in paths:
            lst = alive[p]
            idx = next(i for i, x in enumerate(lst) if x[2] == ref)
            above = lst[idx + 1:] if ref[0] == "l" else [x for x in lst[idx + 1:] if x[2][0] == "l"]
            if above:                        # a resource-pack file above remains -> dead (mod-vs-mod order is unknown)
                lst.pop(idx)
                removed[ref].add(p)
                continue
            if ref[0] == "l" and idx > 0:    # top provider: removable if the next lower one is identical
                below = lst[idx - 1]
                bh = below[1]
                if bh is None:
                    bh = hashes_mod(p, below[2][1])
                if bh == lst[idx][1]:
                    lst.pop(idx)
                    removed[ref].add(p)
    return removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--json")
    ap.add_argument("--md")
    a = ap.parse_args()
    d = os.path.abspath(a.dir)
    man, layers = load_layers(d)
    mods = load_mods(d)
    mod_hash_cache = {}
    zfs = {}

    def hashes_mod(path, mi):
        k = (mi, path)
        if k not in mod_hash_cache:
            zp = mods[mi]["zip"]
            zf = zfs.get(zp) or zfs.setdefault(zp, zipfile.ZipFile(zp))
            mod_hash_cache[k] = sha256_zip(zf, path)
        return mod_hash_cache[k]

    # --- provider index
    prov = collections.defaultdict(list)  # path -> [(order, layer idx, hash)]
    for li, l in enumerate(layers):
        for p, (h, s) in l["root"].items():
            prov[p].append((l["order"], li, h))
    modprov = collections.defaultdict(list)
    for mi, m in enumerate(mods):
        for p in m["files"]:
            modprov[p].append(mi)
    for v in prov.values():
        v.sort()

    def review_reason(l):
        r = []
        if l["filter"]:
            r.append("pack.mcmeta filter")
        if l["overlay_files"]:
            r.append("%d overlay files (%s)" % (l["overlay_files"], ",".join(l["overlay_dirs"][:4])))
        if l["nested_files"]:
            r.append("%d nested sub-pack files" % l["nested_files"])
        return "; ".join(r)

    pot = simulate(layers, mods, hashes_mod, lambda l: True)
    conf = simulate(layers, mods, hashes_mod, lambda l: not review_reason(l))

    # --- effective map
    eff = {}
    for p, v in prov.items():
        eff[p] = (v[-1][1], v[-1][2])
    for p, ms in modprov.items():
        if p not in eff:
            hs = {hashes_mod(p, mi) for mi in ms} if len(ms) > 1 else {None}
            eff[p] = (-1, None if len(hs) == 1 else "conflict")

    def eff_after(removed):
        pr = collections.defaultdict(list)
        for li, l in enumerate(layers):
            for p, (h, s) in l["root"].items():
                if p not in removed[("l", li)]:
                    pr[p].append((l["order"], h))
        mp = {}
        for mi, m in enumerate(mods):
            for p in m["files"]:
                if p not in removed[("m", mi)]:
                    mp.setdefault(p, []).append(mi)
        out = {}
        for p, v in pr.items():
            out[p] = max(v)[1]
        for p, ms in mp.items():
            if p not in out:
                out[p] = hashes_mod(p, ms[0])
        return out

    def eff_before():
        out = {}
        for p, v in prov.items():
            out[p] = v[-1][2]
        for p, ms in modprov.items():
            if p not in out:
                out[p] = hashes_mod(p, ms[0])
        return out

    before = eff_before()
    verified = {}
    for tag, rem in (("potential", pot), ("confirmed", conf)):
        aft = eff_after(rem)
        verified[tag] = (aft == before)
        if aft != before:
            print("MISMATCH", tag, [(k, before.get(k), aft.get(k)) for k in set(before) | set(aft) if before.get(k) != aft.get(k)][:5], file=sys.stderr)

    # --- trim dirs
    def trim_dirs(l, removed):
        F = list(l["root"]) + list(l["merged"])
        R = removed
        sel = []
        for depth in range(3, 8):
            groups = collections.defaultdict(list)
            for p in F:
                segs = p.split("/")[:-1]
                if len(segs) >= depth:
                    groups["/".join(segs[:depth])].append(p)
            for g, ps in groups.items():
                if any(g == s or g.startswith(s + "/") for s, _ in sel):
                    continue
                if all(p in R for p in ps):
                    sel.append((g, len(ps)))
        covered = set()
        for g, n in sel:
            covered.update(p for p in l["root"] if p.startswith(g + "/"))
        return sel, covered

    # --- per-layer stats
    rows = []
    for li, l in enumerate(layers):
        ref = ("l", li)
        files = l["root"]
        total_b = sum(s for h, s in files.values())
        dead = {p for p in files if any(o > l["order"] for o, _, _ in prov[p]) or
                False}
        dead_b = sum(files[p][1] for p in dead)
        ident = set()
        for p in files:
            lower = [x for x in prov[p] if x[0] < l["order"]]
            if lower:
                if lower[-1][2] == files[p][0]:
                    ident.add(p)
            elif p in modprov:
                hs = {hashes_mod(p, mi) for mi in modprov[p]}
                if hs == {files[p][0]}:
                    ident.add(p)
        ident_only = ident - dead
        rr = review_reason(l)
        R = pot[ref]
        rem_b = sum(files[p][1] for p in R)
        sel, covered = trim_dirs(l, R)
        cov_b = sum(files[p][1] for p in covered)
        rows.append({
            "order": l["order"], "name": l["name"], "files": len(files) + len(l["merged"]), "root_files": len(files),
            "bytes": total_b,
            "merged_files": len(l["merged"]), "overlay_files": l["overlay_files"],
            "nested_files": l["nested_files"], "filter": l["filter"],
            "dead_files": len(dead), "dead_pct": round(100.0 * len(dead) / (len(files) + len(l["merged"])), 1) if files else 0.0,
            "dead_bytes": dead_b, "identical_to_lower_not_dead": len(ident_only),
            "identical_to_lower_bytes": sum(files[p][1] for p in ident_only),
            "removable_files": len(R), "removable_bytes": rem_b,
            "removable_pct": round(100.0 * len(R) / (len(files) + len(l["merged"])), 1) if files else 0.0,
            "confirmed_removable_files": len(conf[ref]),
            "confirmed_removable_bytes": sum(files[p][1] for p in conf[ref]),
            "trim_dirs": [{"dir": g, "files": n} for g, n in sorted(sel)],
            "trim_dirs_covered_files": len(covered), "trim_dirs_covered_bytes": cov_b,
            "needs_manual_review": rr, "overlay_dirs": l["overlay_dirs"],
        })
    # --- emissive
    sfx = "_e"
    eff_files = {p: v for p, v in eff.items()}
    bases = []
    for p in eff_files:
        m = re.match(r"^assets/([^/]+)/textures/block/(.+)\.png$", p)
        if m and not m.group(2).endswith(sfx):
            bases.append((False, "%s:block/%s" % (m.group(1), m.group(2)), p[:-4] + sfx + ".png", p))
        elif re.match(r"^assets/[^/]+/optifine/ctm/.+\.png$", p) and not p.endswith(sfx + ".png"):
            bases.append((True, p[:-4], p[:-4] + sfx + ".png", p))
    bases.sort(key=lambda x: (x[0], x[1]))
    # identical-pixel bases share an atlas layer -> no overlay (known sprites only)
    shared = collections.Counter(eff_files[b[3]][1] for b in bases)
    pairs, dropped, shared_skip = [], [], []
    n_eff_e = sum(1 for p in eff_files if p.endswith(sfx + ".png") and "/textures/block/" in p or
                  (p.endswith(sfx + ".png") and "/optifine/ctm/" in p))
    for is_tile, name, ov, bp in bases:
        if ov not in eff_files:
            continue
        if shared[eff_files[bp][1]] > 1:
            shared_skip.append(ov)
            continue
        (pairs if len(pairs) < EMISSIVE_CAP else dropped).append((ov, bp, is_tile))
    emis = collections.OrderedDict()
    for lst, key in ((pairs, "kept"), (dropped, "dropped")):
        for ov, bp, tile in lst:
            li_ = eff_files[ov][0]
            nm = layers[li_]["name"] if li_ >= 0 else "mod-tier"
            e = emis.setdefault(nm, {"kept": 0, "dropped": 0, "ctm_kept": 0, "ctm_dropped": 0})
            e[key] += 1
            if tile:
                e["ctm_" + key] += 1
    # dead emissive files per layer (shadowed _e)
    emis_dead = collections.Counter()
    for li, l in enumerate(layers):
        for p in l["root"]:
            if p.endswith(sfx + ".png") and prov[p][-1][1] != li:
                emis_dead[l["name"]] += 1
    first_dropped = dropped[0][0] if dropped else None

    # --- orphan namespaces: pack assets for namespaces that neither vanilla nor any carried mod provides.
    # Horizon does not run Java mods, so these resources cannot be reached (assumption, flagged).
    mod_ns = {p.split("/")[1] for m in mods for p in m["files"]}
    keep_ns = mod_ns | {"minecraft", "realms"}
    orphan = collections.OrderedDict()
    orphan_paths = set()
    for li, l in enumerate(layers):
        o = collections.defaultdict(lambda: [0, 0])
        for p, (h, sz) in list(l["root"].items()) + list(l["merged"].items()):
            ns = p.split("/")[1]
            if ns not in keep_ns:
                o[ns][0] += 1
                o[ns][1] += sz
                orphan_paths.add(p)
        if o:
            orphan[l["name"]] = {k: {"files": v[0], "bytes": v[1]} for k, v in sorted(o.items())}
    pairs2 = []
    for is_tile, name, ov, bp in bases:
        if ov in eff_files and shared[eff_files[bp][1]] <= 1 and bp.split("/")[1] in keep_ns:
            pairs2.append(ov)
    emis_no_orphan = {"pairs_loaded": min(len(pairs2), EMISSIVE_CAP), "pairs_eligible": len(pairs2),
                      "pairs_dropped": max(0, len(pairs2) - EMISSIVE_CAP), "headroom": max(0, EMISSIVE_CAP - len(pairs2))}
    # --- CEM
    cem_rows = []
    cem_paths = {p for p in prov if CEM.match(p)}
    cem_layers = collections.OrderedDict()
    for li, l in enumerate(layers):
        mine = [p for p in l["root"] if CEM.match(p)]
        if not mine:
            continue
        won = [p for p in mine if prov[p][-1][1] == li]
        jem = [p for p in mine if p.endswith(".jem")]
        jem_won = [p for p in jem if prov[p][-1][1] == li]
        cem_layers[l["name"]] = {
            "order": l["order"], "files": len(mine), "jem": len(jem), "jem_won": len(jem_won),
            "jem_overridden": len(jem) - len(jem_won), "won": len(won),
            "entirely_overridden": len(won) == 0, "jem_entirely_overridden": bool(jem) and not jem_won,
        }
    # jem -> jpm cross-layer provenance for winning jems
    mixed = []
    zfp = {}
    for p in sorted(cem_paths):
        if not p.endswith(".jem"):
            continue
        li = prov[p][-1][1]
        l = layers[li]
        try:
            zp = os.path.join(d, "resourcepacks", os.path.basename(l["dest"] or ""))
            zf = zfp.get(zp) or zfp.setdefault(zp, zipfile.ZipFile(zp))
            doc = json.loads(zf.read(p).decode("utf-8", "replace"))
        except Exception:
            continue
        base = p.rsplit("/", 1)[0]
        for mdl in doc.get("models", []) if isinstance(doc, dict) else []:
            ref = mdl.get("model") if isinstance(mdl, dict) else None
            if not ref or not ref.endswith(".jpm"):
                continue
            cand = base + "/" + ref if not ref.startswith("assets/") else ref
            cand = os.path.normpath(cand).replace(os.sep, "/")
            if cand in prov and prov[cand][-1][1] != li:
                mixed.append({"jem": p, "jem_layer": l["name"], "jpm": cand, "jpm_layer": layers[prov[cand][-1][1]]["name"]})
    # --- families
    fam = {}
    for fname, rx in FAMILIES.items():
        per = collections.OrderedDict()
        for li, l in enumerate(layers):
            mine = [p for p in l["root"] if rx.search(p)]
            if mine:
                per[l["name"]] = {"files": len(mine), "winning": sum(1 for p in mine if prov[p][-1][1] == li),
                                  "bytes": sum(l["root"][p][1] for p in mine)}
        shared_paths = sum(1 for p, v in prov.items() if rx.search(p) and len(v) > 1)
        fam[fname] = {"layers": per, "paths_in_multiple_layers": shared_paths}
    # ctm dir (block id) vs texture/block name overlap across layers (functional overlap)
    ctm_names = collections.defaultdict(set)
    tex_names = collections.defaultdict(set)
    for li, l in enumerate(layers):
        for p in l["root"]:
            m = re.match(r"^assets/[^/]+/optifine/ctm/(?:.+/)?([^/]+)/[^/]+\.(?:png|properties)$", p)
            if m:
                ctm_names[m.group(1)].add(l["name"])
            m = re.match(r"^assets/[^/]+/textures/block/([^/]+)\.png$", p)
            if m:
                tex_names[m.group(1)].add(l["name"])
    func = collections.Counter()
    for n, ls in ctm_names.items():
        for t in tex_names.get(n, ()):
            for c in ls:
                if c != t:
                    func[(c, t)] += 1
    fam["ctm_vs_block_texture_functional_overlap"] = [
        {"ctm_layer": c, "block_texture_layer": t, "block_names": n} for (c, t), n in func.most_common(15)]

    # --- mods
    mod_rows = []
    for mi, m in enumerate(mods):
        files = m["files"]
        dead = [p for p in files if p in prov]
        ident = [p for p in dead if hashes_mod(p, mi) == prov[p][-1][2]]
        mod_rows.append({
            "name": m["name"], "files": len(files), "bytes": sum(files.values()),
            "shadowed_by_resourcepack": len(dead), "shadowed_bytes": sum(files[p] for p in dead),
            "identical_to_winning_resourcepack_file": len(ident),
            "winning_packs": sorted({layers[prov[p][-1][1]]["name"] for p in dead}),
        })
    dup_rp = collections.Counter()
    for m in mod_rows:
        for w in m["winning_packs"]:
            dup_rp[w] += 1
    mod_dead_conf = sum(len(v) for k, v in conf.items() if k[0] == "m")

    # --- verdicts
    for r, l in zip(rows, layers):
        files = len(l["root"])
        fully = r["removable_files"] == files and r["merged_files"] == 0 and files > 0
        if r["needs_manual_review"]:
            r["verdict"] = "REVIEW"
            r["reason"] = r["needs_manual_review"] + "; root tree %.0f%% removable" % r["removable_pct"]
        elif fully:
            r["verdict"] = "DROP"
            r["reason"] = "100%% %s" % ("shadowed" if r["dead_files"] == files else "shadowed or byte-identical to lower")
        elif r["removable_bytes"] >= 100 * 1024 or r["removable_files"] >= 25:
            r["verdict"] = "TRIM"
            r["reason"] = "%d files / %.2f MB removable" % (r["removable_files"], r["removable_bytes"] / 1e6)
        else:
            r["verdict"] = "KEEP"
            r["reason"] = "%.1f%% removable" % r["removable_pct"] if r["removable_files"] else "no overlap"
        r["emissive"] = emis.get(r["name"], {"kept": 0, "dropped": 0, "ctm_kept": 0, "ctm_dropped": 0})
        r["emissive_dead_files"] = emis_dead.get(r["name"], 0)
        r["cem"] = cem_layers.get(r["name"])

    res = {
        "migration": d, "layers": rows, "mod_packs": mod_rows,
        "mod_packs_summary": {
            "count": len(mods), "files": sum(m["files"] for m in mod_rows), "bytes": sum(m["bytes"] for m in mod_rows),
            "packs_with_shadowed_files": sum(1 for m in mod_rows if m["shadowed_by_resourcepack"]),
            "shadowed_files": sum(m["shadowed_by_resourcepack"] for m in mod_rows),
            "shadowed_bytes": sum(m["shadowed_bytes"] for m in mod_rows),
            "identical_files": sum(m["identical_to_winning_resourcepack_file"] for m in mod_rows),
            "fully_shadowed_packs": [m["name"] for m in mod_rows if m["files"] and m["shadowed_by_resourcepack"] == m["files"]],
            "resourcepacks_overriding_mod_assets": dict(dup_rp),
        },
        "emissive": {
            "cap": EMISSIVE_CAP, "max": EMISSIVE_MAX, "suffix": sfx,
            "effective_block_and_ctm_e_files": n_eff_e, "pairs_kept": len(pairs), "pairs_dropped": len(dropped),
            "skipped_shared_base": len(shared_skip), "headroom": EMISSIVE_CAP - len(pairs),
            "first_dropped": first_dropped,
            "per_layer": emis, "if_orphan_namespaces_removed": emis_no_orphan, "dead_e_files_per_layer": dict(emis_dead),
            "assumption": "blocks (ns:block/name) sorted before CTM tiles (path), each by name, first 96 loaded; "
                          "vanilla base sprites assumed present; shared-pixel exclusion only among known pack files",
        },
        "cem": {"layers": cem_layers, "jem_files_effective": sum(1 for p in cem_paths if p.endswith('.jem')),
                "jpm_files_effective": sum(1 for p in cem_paths if p.endswith('.jpm')),
                "jem_jpm_cross_layer_refs": mixed[:60], "jem_jpm_cross_layer_ref_count": len(mixed)},
        "families": fam, "orphan_namespaces": orphan,
        "orphan_total": {"files": sum(v["files"] for o in orphan.values() for v in o.values()),
                         "bytes": sum(v["bytes"] for o in orphan.values() for v in o.values())},
        "savings": {
            "verified_effective_map_unchanged": verified,
            "confirmed_removable_files": sum(r["confirmed_removable_files"] for r in rows),
            "confirmed_removable_bytes": sum(r["confirmed_removable_bytes"] for r in rows),
            "potential_removable_files": sum(r["removable_files"] for r in rows),
            "potential_removable_bytes": sum(r["removable_bytes"] for r in rows),
            "mod_pack_removable_files_confirmed": mod_dead_conf,
            "layers_total": len(rows), "total_bytes": sum(r["bytes"] for r in rows),
            "drop": [r["name"] for r in rows if r["verdict"] == "DROP"],
            "trim": [r["name"] for r in rows if r["verdict"] == "TRIM"],
            "review": [r["name"] for r in rows if r["verdict"] == "REVIEW"],
        },
    }
    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
        json.dump(res, open(a.json, "w"), indent=1, default=list)
    if a.md:
        with open(a.md, "w") as f:
            f.write("| # | layer | files | % shadowed | dead MB | removable MB | emissive kept/dropped | CEM (jem won/total) | verdict | reason |\n")
            f.write("|--:|---|--:|--:|--:|--:|--:|---|---|---|\n")
            for r in rows:
                c = r["cem"]
                cs = "%d/%d%s" % (c["jem_won"], c["jem"], " ALL-OVERRIDDEN" if c["jem_entirely_overridden"] else "") if c else "-"
                e = r["emissive"]
                f.write("| %d | %s | %d | %.1f | %.2f | %.2f | %d/%d | %s | %s | %s |\n" % (
                    r["order"], r["name"].replace("|", "/"), r["files"], r["dead_pct"], r["dead_bytes"] / 1e6,
                    r["removable_bytes"] / 1e6, e["kept"], e["dropped"], cs, r["verdict"], r["reason"].replace("|", "/")))
    s = res["savings"]
    print("layers=%d DROP=%d TRIM=%d REVIEW=%d | confirmed %.1f MB / potential %.1f MB of %.1f MB | verified=%s" % (
        len(rows), len(s["drop"]), len(s["trim"]), len(s["review"]), s["confirmed_removable_bytes"] / 1e6,
        s["potential_removable_bytes"] / 1e6, s["total_bytes"] / 1e6, verified))
    e = res["emissive"]
    print("emissive: kept=%d dropped=%d headroom=%d (e files %d, shared-skip %d)" % (
        e["pairs_kept"], e["pairs_dropped"], e["headroom"], e["effective_block_and_ctm_e_files"], e["skipped_shared_base"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
