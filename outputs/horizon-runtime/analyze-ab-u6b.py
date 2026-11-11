#!/usr/bin/env python3
"""Paired ABBA analysis: consecutive runs form a (control, candidate) pair; median of paired deltas + bootstrap 95% CI.
Run with a python that has numpy+PIL for the optional scene diff (python3.13 framework)."""
import json, random, statistics as st, sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent
tag = sys.argv[1]
data = json.loads((RUNTIME / f"m1-performance-matrix-{tag}.json").read_text())
runs = [r for r in data["results"] if r.get("valid")]
# (path, label, higher_is_better)
M = [("avg_fps", "avg FPS", True), ("low_1pct_fps", "1% low FPS", True), ("p99_ms", "p99 frame ms", False),
     ("gpu.avg_ms", "GPU ms avg", False), ("cpu.avg_ms", "CPU ms avg", False)]


def get(r, phase, path):
    v = r[phase]
    for k in path.split("."):
        v = v[k]
    return v


def boot(xs, n=10000):
    rnd = random.Random(1)
    meds = sorted(st.median(rnd.choices(xs, k=len(xs))) for _ in range(n))
    return meds[int(.025 * n)], meds[int(.975 * n)]


def pairs(case):
    rs = sorted((r for r in runs if r["case"] == case), key=lambda r: r["index"])
    out = []
    for i in range(0, len(rs) - 1, 2):
        a, b = rs[i], rs[i + 1]
        if {a["role"], b["role"]} == {"control", "candidate"}:
            out.append((a, b) if a["role"] == "control" else (b, a))
    return out


def verdict(lo, hi, higher):
    if lo > 0 or hi < 0:
        good = (lo > 0) == higher
        return "WIN" if good else "REGRESSION"
    return "NO EFFECT"


res = {}
for case in sorted({r["case"] for r in runs}):
    ps = pairs(case)
    res[case] = {"pairs": len(ps), "metrics": {}}
    rows = [(f"{ph}.{p}", f"{ph} {lab}", ph, p, hb) for ph in ("static", "flight") for p, lab, hb in M]
    for key, lab, ph, p, hb in rows:
        d = [get(k, ph, p) - get(c, ph, p) for c, k in ps]
        cm = st.median(get(c, ph, p) for c, _ in ps); km = st.median(get(k, ph, p) for _, k in ps)
        lo, hi = boot(d)
        res[case]["metrics"][key] = {"label": lab, "control_median": cm, "cand_median": km, "delta_median": st.median(d),
                                     "ci95": [lo, hi], "verdict": verdict(lo, hi, hb), "n": len(d)}
    for key in ("flight_full_settle_seconds", "swap_delta_M"):
        d = [k[key] - c[key] for c, k in ps if c.get(key) is not None and k.get(key) is not None]
        if d:
            lo, hi = boot(d)
            res[case]["metrics"][key] = {"label": key, "delta_median": st.median(d), "ci95": [lo, hi],
                                         "verdict": verdict(lo, hi, False), "n": len(d),
                                         "control_median": st.median(c[key] for c, _ in ps if c.get(key) is not None),
                                         "cand_median": st.median(k[key] for _, k in ps if k.get(key) is not None)}
    # control-vs-control and cand scene diff
    try:
        import numpy as np
        from PIL import Image
        ld = lambda r: np.asarray(Image.open(Path(r["result"]).parent / "scene.png").convert("RGB"), dtype=np.int16)
        ctl = [r for r in runs if r["case"] == case and r["role"] == "control"]
        cand = [r for r in runs if r["case"] == case and r["role"] == "candidate"]
        dif = lambda a, b: 100 * float((np.abs(ld(a) - ld(b)).max(axis=2) > 0).mean())
        res[case]["scene_diff_pct"] = {"ctl_vs_cand": dif(ctl[0], cand[0]), "ctl_vs_ctl": dif(ctl[0], ctl[1]) if len(ctl) > 1 else None}
    except Exception as e:
        res[case]["scene_diff_pct"] = repr(e)
(RUNTIME / f"m1-performance-matrix-{tag}-paired.json").write_text(json.dumps(res, indent=1))
for case, v in res.items():
    print(f"== {case} pairs={v['pairs']} scene={v['scene_diff_pct']}")
    for k, m in v["metrics"].items():
        print(f"  {m['label']:34s} ctl {m['control_median']:9.3f} cand {m['cand_median']:9.3f} d {m['delta_median']:+8.3f} CI [{m['ci95'][0]:+.3f},{m['ci95'][1]:+.3f}] {m['verdict']}")
