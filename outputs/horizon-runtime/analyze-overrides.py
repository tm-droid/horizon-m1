#!/usr/bin/env python3
"""analyze-overrides.py TAG [TAG...]: paired deltas per arm vs nearest base runs (mean of adjacent bases in same tag/case),
or, with --rounds, vs same-round base. Prints median paired delta + bootstrap 95% CI."""
import json
import random
import statistics as st
import sys
from pathlib import Path

import numpy as np
from PIL import Image

RT = Path(__file__).resolve().parent
args = [a for a in sys.argv[1:] if not a.startswith("--")]
ROUNDS = "--rounds" in sys.argv
runs = []
for tag in args:
    runs += [r for r in json.loads((RT / f"overrides-matrix-{tag}.json").read_text())["results"] if r.get("valid")]

for r in runs:
    if not r.get("static"):
        r["static"] = json.loads((RT / "tests" / r["label"] / "result.json").read_text())["measurement"]

METRICS = [("static", "avg_fps"), ("static", "low_1pct_fps"), ("static", "p99_ms"),
           ("flight", "avg_fps"), ("flight", "low_1pct_fps"), ("flight", "p99_ms"), (None, "flight_full_settle_seconds")]


def val(r, m):
    ph, k = m
    return r[ph][k] if ph else r.get(k)


def boot(xs, n=5000):
    if len(xs) < 2:
        return None
    random.seed(1)
    meds = sorted(st.median(random.choices(xs, k=len(xs))) for _ in range(n))
    return meds[int(.025 * n)], meds[int(.975 * n)]


def scene(r):
    return np.asarray(Image.open(r["scene"]).convert("RGB"), dtype=np.int16)


def pairs(case_runs, arm):
    """(arm run, reference value list) with reference = mean of base runs adjacent in sequence within the same tag."""
    out = []
    for r in case_runs:
        if r["arm"] != arm:
            continue
        refs = [b for b in case_runs if b["arm"] == "base" and b["tag"] == r["tag"]]
        if ROUNDS:
            near = [b for b in refs if b.get("round") == r.get("round")]
        else:
            before = [b for b in refs if b["seq"] < r["seq"]]
            after = [b for b in refs if b["seq"] > r["seq"]]
            near = ([before[-1]] if before else []) + ([after[0]] if after else [])
        if near:
            out.append((r, near))
    return out


report = {}
for case in sorted({r["case"] for r in runs}):
    cr = [r for r in runs if r["case"] == case]
    report[case] = {}
    for arm in sorted({r["arm"] for r in cr} - {"base"}):
        ps = pairs(cr, arm)
        row = {"n_pairs": len(ps)}
        for m in METRICS:
            d = []
            for r, near in ps:
                if val(r, m) is None or any(val(b, m) is None for b in near):
                    continue
                d.append(val(r, m) - st.mean(val(b, m) for b in near))
            if d:
                row["/".join(x for x in m if x)] = {"med": round(st.median(d), 3), "ci": boot(d), "d": [round(x, 2) for x in d]}
        vis = []
        for r, near in ps:
            try:
                dd = np.abs(scene(r) - scene(near[0])).max(axis=2)
                vis.append([round(100 * float((dd > 8).mean()), 2), round(float(np.abs(scene(r) - scene(near[0])).mean()), 2)])
            except Exception:
                pass
        row["scene_diff_pct_vs_base"] = vis
        report[case][arm] = row
    bases = [r for r in cr if r["arm"] == "base"]
    try:
        bb = [[round(100 * float((np.abs(scene(a) - scene(b)).max(axis=2) > 8).mean()), 2), round(float(np.abs(scene(a) - scene(b)).mean()), 2)] for a, b in zip(bases, bases[1:])]
        report[case]["_base_vs_base_scene_diff_pct"] = bb
    except Exception:
        pass
    report[case]["_base_medians"] = {"/".join(x for x in m if x): round(st.median([val(b, m) for b in bases if val(b, m) is not None]), 2) for m in METRICS if bases}
print(json.dumps(report, indent=1))
