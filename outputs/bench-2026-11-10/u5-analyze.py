#!/usr/bin/env python3
"""u5 aggregate: python3 u5-analyze.py SCENARIO GLOB... -> medians per build@variant, delta vs first group listed via BASE env."""
import glob, json, statistics as st, sys, collections
D = __import__("pathlib").Path(__file__).resolve().parent / "runs"
sc = sys.argv[1]
groups = collections.defaultdict(list)
for pat in sys.argv[2:]:
    for p in sorted(glob.glob(str(D / pat))):
        r = json.loads(open(p).read())
        if not r.get("valid") or r["scenario"] != sc:
            continue
        groups[r["build"]].append(r)
M = [("avg_fps", "avg"), ("low_1pct_fps", "1%low"), ("p99_ms", "p99")]
def val(r, w, k):
    return r[w][k]
def med(g, w, k):
    return st.median(val(r, w, k) for r in g)
def row(g):
    out = {}
    for w in ("static", "flight"):
        for k, n in M:
            out[(w, n)] = med(g, w, k)
        out[(w, "cpu")] = st.median(r[w]["cpu"]["avg_ms"] for r in g)
        out[(w, "gpu")] = st.median(r[w]["gpu"]["avg_ms"] for r in g)
    out["rss"] = st.median(r["peak_rss_MB"] for r in g)
    return out
base = None
import os
bn = os.environ.get("BASE")
for b, g in groups.items():
    o = row(g)
    if b == bn:
        base = o
for b, g in groups.items():
    o = row(g)
    s = f"{b:22s} n={len(g)} "
    for w in ("static", "flight"):
        s += f"| {w[:2]} " + " ".join(f"{n}={o[(w,n)]:.1f}" for _, n in M) + f" cpu={o[(w,'cpu')]:.2f} gpu={o[(w,'gpu')]:.2f} "
    s += f"| rss={o['rss']:.0f}"
    print(s)
    if base and b != bn:
        d = []
        for w in ("static", "flight"):
            for _, n in M:
                d.append(f"{w[:2]}{n}{(o[(w,n)]/base[(w,n)]-1)*100:+.1f}%")
        d.append(f"rss{(o['rss']/base['rss']-1)*100:+.1f}%")
        print("   d vs base: " + " ".join(d))
