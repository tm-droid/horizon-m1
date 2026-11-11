#!/usr/bin/env python3
"""Summarise m1-performance-matrix-<tag>.json into per case/build stats, noise, and scene.png diffs."""
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np
from PIL import Image

RUNTIME = Path(__file__).resolve().parent
tag = sys.argv[1] if len(sys.argv) > 1 else "r2"
data = json.loads((RUNTIME / f"m1-performance-matrix-{tag}.json").read_text())
runs = [r for r in data["results"] if r.get("valid")]

METRICS = [("avg_fps", "avg FPS", None), ("low_1pct_fps", "1% low FPS", None), ("p99_ms", "p99 ms", None),
           ("cpu", "CPU ms (avg)", "avg_ms"), ("gpu", "GPU ms (avg)", "avg_ms")]
HIGHER_BETTER = {"avg_fps", "low_1pct_fps"}


def value(run, phase, key, sub):
    v = run[phase][key]
    return v[sub] if sub else v


def rng(xs):
    return max(xs) - min(xs)


out = {"cases": {}}
for case in sorted({r["case"] for r in runs}):
    out["cases"][case] = {}
    for phase in ("static", "flight"):
        for key, label, sub in METRICS:
            row = {}
            for role in ("control", "candidate"):
                xs = [value(r, phase, key, sub) for r in runs if r["case"] == case and r["role"] == role]
                row[role] = {"n": len(xs), "median": st.median(xs), "min": min(xs), "max": max(xs), "values": xs}
            noise = max(rng(row["control"]["values"]), rng(row["candidate"]["values"]))
            delta = row["candidate"]["median"] - row["control"]["median"]
            row["delta"] = delta
            row["delta_pct"] = 100 * delta / row["control"]["median"] if row["control"]["median"] else None
            row["noise_spread"] = noise
            row["significant"] = abs(delta) > noise
            better = (delta > 0) == (key in HIGHER_BETTER)
            row["direction"] = "better" if better else "worse"
            out["cases"][case][f"{phase}.{key}"] = row
    for key in ("flight_full_settle_seconds", "flight_settle_seconds"):
        row = {}
        for role in ("control", "candidate"):
            xs = [r[key] for r in runs if r["case"] == case and r["role"] == role and r.get(key) is not None]
            row[role] = {"n": len(xs), "median": st.median(xs), "min": min(xs), "max": max(xs), "values": xs}
        noise = max(rng(row["control"]["values"]), rng(row["candidate"]["values"]))
        row["delta"] = row["candidate"]["median"] - row["control"]["median"]
        row["noise_spread"] = noise
        row["significant"] = abs(row["delta"]) > noise
        out["cases"][case][key] = row
    out["cases"][case]["swap_used_M"] = [
        (r["index"], r["role"], r["gate"]["swap"].split("used = ")[1].split("M")[0]) for r in runs if r["case"] == case]

# visual parity
def load(r):
    return np.asarray(Image.open(Path(r["result"]).parent / "scene.png").convert("RGB"), dtype=np.int16)


visual = {}
for case in sorted({r["case"] for r in runs}):
    ctl = [r for r in runs if r["case"] == case and r["role"] == "control"]
    cand = [r for r in runs if r["case"] == case and r["role"] == "candidate"]

    def diff(a, b):
        d = np.abs(load(a) - load(b)).max(axis=2)
        return {"pixels_differ_pct": 100 * float((d > 0).mean()), "pixels_over_8_of_255_pct": 100 * float((d > 8).mean()),
                "mean_abs_channel_diff": float(np.abs(load(a) - load(b)).mean())}

    visual[case] = {
        "control_vs_candidate": diff(ctl[0], cand[0]),
        "all_pairs_control_vs_candidate_pct": [diff(a, b)["pixels_differ_pct"] for a in ctl for b in cand],
        "control_vs_control_baseline": diff(ctl[0], ctl[1]),
        "candidate_vs_candidate_baseline": diff(cand[0], cand[1]),
    }
out["visual"] = visual
(RUNTIME / f"m1-performance-matrix-{tag}-analysis.json").write_text(json.dumps(out, indent=1))

for case, rows in out["cases"].items():
    print(f"== {case}")
    for name, row in rows.items():
        if name == "swap_used_M":
            print("  swap", row)
            continue
        c, d = row["control"], row["candidate"]
        sig = "SIG" if row["significant"] else "ns"
        print(f"  {name:28s} ctl {c['median']:.3f} [{c['min']:.3f}-{c['max']:.3f}]  cand {d['median']:.3f} "
              f"[{d['min']:.3f}-{d['max']:.3f}]  delta {row['delta']:+.3f} noise {row['noise_spread']:.3f} {sig}"
              f" {row.get('direction', '')}")
print(json.dumps(visual, indent=1))
