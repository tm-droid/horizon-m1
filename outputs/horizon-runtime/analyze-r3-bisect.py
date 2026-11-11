#!/usr/bin/env python3
"""Paired by-round analysis for run-r3-bisect.py output. Needs numpy + PIL (framework python)."""
import itertools
import json
from pathlib import Path
import sys

import numpy as np

METRICS = [("avg_fps", "avg fps", lambda b: b["avg_fps"]),
           ("low_1pct_fps", "1% low fps", lambda b: b["low_1pct_fps"]),
           ("p99_ms", "p99 ms", lambda b: b["p99_ms"]),
           ("gpu_p99_ms", "GPU p99 ms", lambda b: b["gpu"]["p99_ms"]),
           ("cpu_p99_ms", "CPU p99 ms", lambda b: b["cpu"]["p99_ms"])]
PAIRS = {"makeup": [("r3", "control"), ("r3noqos", "control"), ("r3", "r3noqos")],
         "packs": [("r3", "r2"), ("r3noqos", "r2"), ("r3", "r3noqos")]}
RNG = np.random.default_rng(20261106)


def boot_ci(deltas, n=10000):
    d = np.asarray(deltas, float)
    if len(d) < 2:
        return (float("nan"), float("nan"))
    med = np.median(RNG.choice(d, size=(n, len(d)), replace=True), axis=1)
    return tuple(np.percentile(med, [2.5, 97.5]))


def load(path):
    summary = json.loads(Path(path).read_text())
    runs = {}
    for r in summary["results"]:
        if r.get("valid"):
            runs[(r["case"], r["arm"], r["round"])] = r  # later attempt wins
    return summary, runs


def paired(runs, case, a, b, getter):
    rounds = sorted({k[2] for k in runs if k[0] == case})
    out = []
    for rnd in rounds:
        ra, rb = runs.get((case, a, rnd)), runs.get((case, b, rnd))
        if ra and rb:
            out.append((getter(ra), getter(rb)))
    return out


def fmt(x, nd=2):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:+.{nd}f}"


def table(runs, case, phase_label, extract):
    lines = [f"| {case} {phase_label} | pair | n | median delta | 95% CI (bootstrap median) | mean delta | base median | delta % | rounds A>B |",
             "|---|---|---|---|---|---|---|---|---|"]
    for key, name, fn in METRICS:
        for a, b in PAIRS[case]:
            pr = paired(runs, case, a, b, lambda r: fn(extract(r)))
            if not pr:
                continue
            d = np.array([x - y for x, y in pr])
            base = float(np.median([y for _, y in pr]))
            lo, hi = boot_ci(d)
            lines.append(f"| {name} | {a} - {b} | {len(d)} | {fmt(np.median(d))} | [{fmt(lo)}, {fmt(hi)}] | {fmt(d.mean())} | "
                         f"{base:.2f} | {fmt(100 * np.median(d) / base, 1)}% | {int((d > 0).sum())}/{len(d)} |")
    return lines


def mem_table(runs):
    lines = ["| case | pair | n | footprint peak delta MB (median) | CI | RSS peak delta MB (median) | swap_peak delta M (median) |",
             "|---|---|---|---|---|---|---|"]
    for case in PAIRS:
        for a, b in PAIRS[case]:
            for label, g, div in (("fp", lambda r: (r.get("memory") or {}).get("footprint_peak_kb"), 1024),):
                fp = paired(runs, case, a, b, g)
                rs = paired(runs, case, a, b, lambda r: (r.get("memory") or {}).get("rss_peak_kb"))
                sw = paired(runs, case, a, b, lambda r: (r.get("memory") or {}).get("swap_peak_M"))
                def dl(pr, div=1):
                    return np.array([(x - y) / div for x, y in pr if x is not None and y is not None])
                f, r_, s = dl(fp, 1024), dl(rs, 1024), dl(sw)
                if not len(f) and not len(r_):
                    continue
                lo, hi = boot_ci(f) if len(f) else (float("nan"),) * 2
                lines.append(f"| {case} | {a} - {b} | {max(len(f), len(r_))} | {fmt(np.median(f) if len(f) else None, 1)} | "
                             f"[{fmt(lo, 1)}, {fmt(hi, 1)}] | {fmt(np.median(r_) if len(r_) else None, 1)} | "
                             f"{fmt(np.median(s) if len(s) else None, 1)} |")
    return lines


def visual(runs):
    from PIL import Image
    lines = []
    bands = 6
    for case in PAIRS:
        imgs = {}
        for (c, arm, rnd), r in runs.items():
            if c != case:
                continue
            p = Path(r["result"]).parent / "scene.png"
            if p.is_file():
                im = Image.open(p).convert("L")
                im = im.resize((im.width // 4, im.height // 4))
                imgs[(arm, rnd)] = np.asarray(im, float)
        if not imgs:
            continue

        def band_diff(x, y):
            h = x.shape[0] // bands
            return [float(np.abs(x[i * h:(i + 1) * h] - y[i * h:(i + 1) * h]).mean()) for i in range(bands)]
        same = [band_diff(imgs[p], imgs[q]) for p, q in itertools.combinations(sorted(imgs), 2) if p[0] == q[0]]
        lines.append(f"**{case}** mean abs gray diff per horizontal band (top to bottom), 0-255 scale.")
        lines.append("")
        lines.append("| comparison | " + " | ".join(f"band {i + 1}" for i in range(bands)) + " | verdict |")
        lines.append("|---|" + "---|" * (bands + 1))
        spread = np.mean(same, axis=0) if same else np.zeros(bands)
        spread_max = np.max(same, axis=0) if same else np.zeros(bands)
        lines.append("| same-arm spread (mean of all within-arm pairs) | " + " | ".join(f"{v:.2f}" for v in spread) + " | baseline |")
        arms = sorted({k[0] for k in imgs})
        for a, b in itertools.combinations(arms, 2):
            cross = [band_diff(imgs[p], imgs[q]) for p in imgs for q in imgs if p[0] == a and q[0] == b]
            m = np.mean(cross, axis=0)
            flag = [i + 1 for i in range(bands) if m[i] > 1.5 * spread[i] + 0.25 and m[i] > spread_max[i]]
            lines.append(f"| {a} vs {b} | " + " | ".join(f"{v:.2f}" for v in m) + " | " +
                         ("DIFFERS in band " + ",".join(map(str, flag)) if flag else "within same-arm spread") + " |")
        lines.append("")
    return lines


def main():
    summary, runs = load(sys.argv[1])
    out = [f"## Auto-generated tables ({summary.get('tag')}, finished {summary.get('finished')}, "
           f"complete={summary.get('complete')}, aborted={summary.get('aborted')})", "",
           f"Valid runs: {len(runs)} of {len(summary['plan'])} planned; r3noqos present: {summary.get('has_r3noqos')}", ""]
    for case in PAIRS:
        out += table(runs, case, "static", lambda r: r["static"]) + [""]
        out += table(runs, case, "flight", lambda r: r["flight"]) + [""]
    out += ["### Memory", ""] + mem_table(runs) + ["", "### Visual (scene.png)", ""]
    try:
        out += visual(runs)
    except Exception as error:  # noqa: BLE001
        out += [f"visual analysis failed: {error!r}"]
    out += ["### Per-run raw", "", "| case | arm | round | static avg | static 1% | static p99 | static GPU p99 | flight avg | flight 1% | flight p99 | fp peak MB | swap Mbefore->after |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for (case, arm, rnd), r in sorted(runs.items()):
        s, f, m = r["static"], r["flight"], r.get("memory") or {}
        fp = m.get("footprint_peak_kb")
        out.append(f"| {case} | {arm} | {rnd} | {s['avg_fps']:.1f} | {s['low_1pct_fps']:.1f} | {s['p99_ms']:.1f} | {s['gpu']['p99_ms']:.1f} | "
                   f"{f['avg_fps']:.1f} | {f['low_1pct_fps']:.1f} | {f['p99_ms']:.1f} | {'n/a' if not fp else f'{fp / 1024:.0f}'} | "
                   f"{r.get('swap_before_M')}->{r.get('swap_after_M')} |")
    text = "\n".join(out) + "\n"
    target = Path(sys.argv[1]).with_suffix(".tables.md")
    target.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
