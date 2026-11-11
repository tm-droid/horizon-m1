#!/usr/bin/env python3
"""Aggregate outputs/bench-2026-11-10/runs/*.json -> runs.csv + tables.md"""
import csv, json, statistics as st
from pathlib import Path

D = Path(__file__).resolve().parent
runs = [json.loads(p.read_text()) for p in sorted((D / "runs").glob("*.json"))]
runs = [r for r in runs if r.get("valid")]
runs.sort(key=lambda r: r["index"])
cols = ["index", "scenario", "build", "window", "avg_fps", "low1_fps", "p99_ms", "cpu_ms", "gpu_ms", "peak_rss_MB", "swap_delta_M", "idle_s", "thermal"]
rows = []
for r in runs:
    for w in ("static", "flight"):
        m = r[w]
        rows.append(dict(index=r["index"], scenario=r["scenario"], build=r["build"], window=w,
                         avg_fps=round(m["avg_fps"], 1), low1_fps=round(m["low_1pct_fps"], 1), p99_ms=round(m["p99_ms"], 2),
                         cpu_ms=round(m["cpu"]["avg_ms"], 2), gpu_ms=round(m["gpu"]["avg_ms"], 2),
                         peak_rss_MB=r["peak_rss_MB"], swap_delta_M=r["swap_delta_M"], idle_s=r["gate"]["idle_s"], thermal=r["gate"]["thermal"]))
with (D / "runs.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(rows)

out = ["## Per-run table\n", "| # | scenario | build | window | avg FPS | 1% low | p99 ms | CPU ms | GPU ms | peak RSS MB | swap d MB |", "|---|---|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    out.append(f"| {r['index']} | {r['scenario']} | {r['build']} | {r['window']} | {r['avg_fps']} | {r['low1_fps']} | {r['p99_ms']} | {r['cpu_ms']} | {r['gpu_ms']} | {r['peak_rss_MB']} | {r['swap_delta_M']} |")
out += ["", "## Medians per build (range = min-max of per-run values, n runs)\n",
        "| scenario | window | build | n | avg FPS med (min-max) | 1% low med (min-max) | CPU ms med | GPU ms med | peak RSS MB med | swap d MB med |", "|---|---|---|---|---|---|---|---|---|---|"]
summ = {}
for sc in ("packs", "makeup"):
    for wn in ("static", "flight"):
        for b in ("DAILY", "STOCK", "R11"):
            g = [r for r in rows if r["scenario"] == sc and r["window"] == wn and r["build"] == b]
            if not g:
                continue
            a = [x["avg_fps"] for x in g]; l = [x["low1_fps"] for x in g]
            summ[(sc, wn, b)] = (a, l)
            out.append(f"| {sc} | {wn} | {b} | {len(g)} | {st.median(a):.1f} ({min(a)}-{max(a)}) | {st.median(l):.1f} ({min(l)}-{max(l)}) | "
                       f"{st.median(x['cpu_ms'] for x in g):.2f} | {st.median(x['gpu_ms'] for x in g):.2f} | {st.median(x['peak_rss_MB'] for x in g):.0f} | {st.median(x['swap_delta_M'] for x in g):.0f} |")
out += ["", "## Noise band and DAILY vs others\n",
        "Noise = within-build spread of avg FPS (max-min, and half-range as +/-). Verdict: median difference larger than both builds' spreads.\n",
        "| scenario | window | DAILY-STOCK d med | DAILY-R11 d med | spread DAILY | spread STOCK | spread R11 | DAILY>STOCK beyond noise | DAILY>R11 beyond noise |", "|---|---|---|---|---|---|---|---|---|"]
for sc in ("packs", "makeup"):
    for wn in ("static", "flight"):
        try:
            d, s, r = (summ[(sc, wn, b)][0] for b in ("DAILY", "STOCK", "R11"))
        except KeyError:
            continue
        sp = [max(x) - min(x) for x in (d, s, r)]
        ds, dr = st.median(d) - st.median(s), st.median(d) - st.median(r)
        out.append(f"| {sc} | {wn} | {ds:+.1f} | {dr:+.1f} | {sp[0]:.1f} | {sp[1]:.1f} | {sp[2]:.1f} | "
                   f"{'yes' if ds > max(sp[0], sp[1]) else ('worse' if -ds > max(sp[0], sp[1]) else 'no')} | {'yes' if dr > max(sp[0], sp[2]) else ('worse' if -dr > max(sp[0], sp[2]) else 'no')} |")
(D / "tables.md").write_text("\n".join(out) + "\n")
print("\n".join(out[-24:]))
