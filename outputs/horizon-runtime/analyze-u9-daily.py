#!/usr/bin/env python3
"""Paired by-round analysis for run-u9-daily.py output. Needs numpy + PIL (framework python).

  analyze-u9-daily.py <u9-daily-TAG.json>     tables -> <json>.tables.md
  analyze-u9-daily.py --ore-assets            asset-level v3 vs v4 ore/emissive overlay diff (no game needed)
"""
import itertools
import json
from pathlib import Path
import sys
import zipfile

import numpy as np

METRICS = [("avg fps", lambda b: b["avg_fps"]), ("1% low fps", lambda b: b["low_1pct_fps"]),
           ("p99 ms", lambda b: b["p99_ms"]), ("GPU p99 ms", lambda b: b["gpu"]["p99_ms"]),
           ("CPU p99 ms", lambda b: b["cpu"]["p99_ms"])]
SHADER_PAIR = [("r3-v4", "ctrl-v4")]
PAIRS = {"makeup": [("daily", "baseline"), ("daily-cull", "daily"), ("daily-cull", "baseline"), ("trim", "daily")],
         "packs": [("daily", "baseline")],
         "mellow": SHADER_PAIR, "miniature": SHADER_PAIR, "complementary": SHADER_PAIR,
         "ilikvanilla": SHADER_PAIR, "superduper": SHADER_PAIR, "sildurs": SHADER_PAIR, "bsl": SHADER_PAIR, "bliss": SHADER_PAIR, "unbound": SHADER_PAIR, "bakedpotato": SHADER_PAIR, "sildursdefault": SHADER_PAIR}
ORE_CASES = {"ores-makeup": ("r3-v4", "r3-v3"), "ores-packs": ("r3-v4", "r3-v3")}
RNG = np.random.default_rng(20261106)
ROOT = Path(__file__).resolve().parents[2]
MIGS = {"v3": ROOT / "outputs/horizon-converter/2026-11-04-Tanush-f42-v3",
        "v4": ROOT / "outputs/horizon-converter/2026-11-05-Tanush-f42-v4"}


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
    out = []
    for rnd in sorted({k[2] for k in runs if k[0] == case}):
        ra, rb = runs.get((case, a, rnd)), runs.get((case, b, rnd))
        if ra and rb:
            try:
                out.append((getter(ra), getter(rb)))
            except (KeyError, TypeError):
                pass
    return out


def fmt(x, nd=2):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:+.{nd}f}"


def table(runs, case, phase, extract):
    lines = [f"| {case} {phase} | pair | n | median delta | 95% CI (bootstrap median) | mean delta | base median | delta % | rounds A>B |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name, fn in METRICS:
        for a, b in PAIRS[case]:
            pr = paired(runs, case, a, b, lambda r: fn(extract(r)))
            if not pr:
                continue
            d = np.array([x - y for x, y in pr])
            base = float(np.median([y for _, y in pr]))
            lo, hi = boot_ci(d)
            pct = 100 * np.median(d) / base if base else float("nan")
            lines.append(f"| {name} | {a} - {b} | {len(d)} | {fmt(np.median(d))} | [{fmt(lo)}, {fmt(hi)}] | {fmt(d.mean())} | "
                         f"{base:.2f} | {fmt(pct, 1)}% | {int((d > 0).sum())}/{len(d)} |")
    return lines


def mem_table(runs):
    lines = ["| case | pair | n | footprint peak delta MB (median) | CI | RSS peak delta MB (median) | swap_peak delta M (median) |",
             "|---|---|---|---|---|---|---|"]
    for case in PAIRS:
        for a, b in PAIRS[case]:
            def get(key):
                return paired(runs, case, a, b, lambda r: (r.get("memory") or {})[key])

            def dl(pr, div=1):
                return np.array([(x - y) / div for x, y in pr if x is not None and y is not None])
            f, r_, s = dl(get("footprint_peak_kb"), 1024), dl(get("rss_peak_kb"), 1024), dl(get("swap_peak_M"))
            if not len(f) and not len(r_):
                continue
            lo, hi = boot_ci(f) if len(f) else (float("nan"),) * 2
            lines.append(f"| {case} | {a} - {b} | {max(len(f), len(r_))} | {fmt(np.median(f) if len(f) else None, 1)} | "
                         f"[{fmt(lo, 1)}, {fmt(hi, 1)}] | {fmt(np.median(r_) if len(r_) else None, 1)} | "
                         f"{fmt(np.median(s) if len(s) else None, 1)} |")
    return lines


def gray(path, shrink=4):
    from PIL import Image
    im = Image.open(path).convert("L")
    return np.asarray(im.resize((im.width // shrink, im.height // shrink)), float)


def visual(runs):
    lines = []
    bands = 6
    for case in PAIRS:
        imgs = {}
        for (c, arm, rnd), r in runs.items():
            p = Path(r["result"]).parent / "scene.png"
            if c == case and p.is_file():
                imgs[(arm, rnd)] = gray(p)
        if not imgs:
            continue

        def band_diff(x, y):
            h = x.shape[0] // bands
            return [float(np.abs(x[i * h:(i + 1) * h] - y[i * h:(i + 1) * h]).mean()) for i in range(bands)]
        same = [band_diff(imgs[p], imgs[q]) for p, q in itertools.combinations(sorted(imgs), 2) if p[0] == q[0]]
        lines += [f"**{case}** mean abs gray diff per horizontal band (top to bottom), 0-255.", "",
                  "| comparison | " + " | ".join(f"band {i + 1}" for i in range(bands)) + " | verdict |",
                  "|---|" + "---|" * (bands + 1)]
        spread = np.mean(same, axis=0) if same else np.zeros(bands)
        spread_max = np.max(same, axis=0) if same else np.zeros(bands)
        lines.append("| same-arm spread (mean of within-arm pairs) | " + " | ".join(f"{v:.2f}" for v in spread) + " | baseline |")
        for a, b in itertools.combinations(sorted({k[0] for k in imgs}), 2):
            cross = [band_diff(imgs[p], imgs[q]) for p in imgs for q in imgs if p[0] == a and q[0] == b]
            m = np.mean(cross, axis=0)
            flag = [i + 1 for i in range(bands) if m[i] > 1.5 * spread[i] + 0.25 and m[i] > spread_max[i]]
            lines.append(f"| {a} vs {b} | " + " | ".join(f"{v:.2f}" for v in m) + " | " +
                         ("DIFFERS in band " + ",".join(map(str, flag)) if flag else "within same-arm spread") + " |")
        lines.append("")
    return lines


def ore_glow(runs):
    """v4 vs v3 on the dark ore wall: 3 rows x 8 columns luminance grid over the centre of scene.png.

    Ore wall is 8 blocks wide, 3 high, centred on the camera. The grid is approximate (centre 80% x 70%),
    so read it as relative glow per ore slot, and open scene.png to confirm.
    """
    names = {0: ["diamond", "deepslate_diamond", "redstone(lit)", "deepslate_redstone(lit)", "emerald", "deepslate_emerald", "lapis", "deepslate_lapis"],
             1: ["gold", "deepslate_gold", "iron", "deepslate_iron", "copper", "deepslate_copper", "coal", "deepslate_coal"],
             2: ["nether_quartz", "nether_gold", "ancient_debris", "glowstone", "magma", "sea_lantern", "redstone(unlit)", "deepslate_redstone(unlit)"]}
    lines = []
    for case, (new, old) in ORE_CASES.items():
        rn, ro = runs.get((case, new, 1)), runs.get((case, old, 1))
        if not (rn and ro):
            continue
        pn, po = (Path(r["result"]).parent / "scene.png" for r in (rn, ro))
        if not (pn.is_file() and po.is_file()):
            lines.append(f"{case}: scene.png missing")
            continue
        gn, go = gray(pn, 2), gray(po, 2)
        h, w = gn.shape
        y0, y1, x0, x1 = int(h * 0.15), int(h * 0.85), int(w * 0.1), int(w * 0.9)

        def grid(g):
            sub = g[y0:y1, x0:x1]
            gh, gw = sub.shape[0] // 3, sub.shape[1] // 8
            return np.array([[sub[r * gh:(r + 1) * gh, c * gw:(c + 1) * gw].mean() for c in range(8)] for r in range(3)])
        a, b = grid(gn), grid(go)
        lines += [f"**{case}** mean luminance per ore slot, {new} (A) vs {old} (B); delta = A - B (0-255). "
                  f"Global mean abs diff {np.abs(gn - go).mean():.2f}.", "",
                  "| row | slot | ore | A | B | delta | verdict |", "|---|---|---|---|---|---|---|"]
        for r in range(3):
            for c in range(8):
                d = a[r, c] - b[r, c]
                verdict = "GLOW LOST" if d < -8 else ("GLOW GAINED" if d > 8 else "same")
                lines.append(f"| {r + 1} | {c + 1} | {names[r][c]} | {a[r, c]:.1f} | {b[r, c]:.1f} | {d:+.1f} | {verdict} |")
        lines.append("")
    return lines


def ore_assets():
    """Which ore-ish emissive (_e.png / emissive.properties) files each migration's packs ship."""
    found = {}
    for mig, directory in MIGS.items():
        files = set()
        for pack in sorted((directory / "resourcepacks").glob("*.zip")):
            try:
                with zipfile.ZipFile(pack) as z:
                    for name in z.namelist():
                        low = name.lower()
                        if "ore" in low.rsplit("/", 1)[-1] or "/ores/" in low or "debris" in low:
                            if low.endswith("_e.png") or low.endswith("emissive.properties") or low.endswith("_s.png"):
                                files.add((pack.name, name))
            except zipfile.BadZipFile:
                pass
        found[mig] = files
    lost, gained = sorted(found["v3"] - found["v4"]), sorted(found["v4"] - found["v3"])
    out = [f"ore emissive overlays: v3={len(found['v3'])} v4={len(found['v4'])} lost_in_v4={len(lost)} gained_in_v4={len(gained)}", ""]
    by_pack = {}
    for pack, name in lost:
        by_pack.setdefault(pack, []).append(name)
    for pack, names in by_pack.items():
        ns = sorted({n.split("/")[1] if n.startswith("assets/") else "?" for n in names})
        vanilla = sorted(n for n in names if n.startswith("assets/minecraft/"))
        out.append(f"- {pack}: {len(names)} lost, namespaces {ns}; minecraft-namespace lost: {len(vanilla)}")
        for n in vanilla[:30]:
            out.append(f"    {n}")
    mc_lost = [n for _, n in lost if n.startswith("assets/minecraft/")]
    out.append("")
    out.append("VERDICT: " + ("vanilla ore glow files differ v3->v4 (see list)" if mc_lost else
                              "no minecraft-namespace ore emissive file lost; only mod-namespace ore layers dropped"))
    return out


def main():
    if sys.argv[1:2] == ["--ore-assets"]:
        print("\n".join(ore_assets()))
        return
    summary, runs = load(sys.argv[1])
    out = [f"## Auto-generated tables ({summary.get('tag')}, finished {summary.get('finished')}, "
           f"complete={summary.get('complete')}, aborted={summary.get('aborted')})", "",
           f"Valid runs: {len(runs)} of {len(summary['plan'])} planned", ""]
    flagged = [f"{k[0]}/{k[1]}/{k[2]}" for k, r in runs.items() if r.get("loader_evidence_missing")]
    if flagged:
        out += ["Shader loader line not matched (run kept, verify manually): " + ", ".join(flagged), ""]
    for case in PAIRS:
        if any(k[0] == case for k in runs):
            out += table(runs, case, "static", lambda r: r["static"]) + [""]
            out += table(runs, case, "flight", lambda r: r["flight"]) + [""]
    out += ["### Memory", ""] + mem_table(runs) + ["", "### Visual (scene.png)", ""]
    try:
        out += visual(runs)
    except Exception as error:  # noqa: BLE001
        out += [f"visual analysis failed: {error!r}"]
    out += ["### Ore glow (v4 vs v3, r3 build)", ""]
    try:
        out += ore_glow(runs) or ["no complete ore pair"]
    except Exception as error:  # noqa: BLE001
        out += [f"ore analysis failed: {error!r}"]
    out += ["", "### Per-run raw", "",
            "| case | arm | round | static avg | static 1% | static p99 | static GPU p99 | flight avg | flight 1% | flight p99 | fp peak MB | swap Mbefore->after |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|"]

    def v(x, spec=".1f"):
        return "n/a" if x is None else format(x, spec)
    for (case, arm, rnd), r in sorted(runs.items()):
        s, f, m = r.get("static") or {}, r.get("flight") or {}, r.get("memory") or {}
        fp = m.get("footprint_peak_kb")
        out.append(f"| {case} | {arm} | {rnd} | {v(s.get('avg_fps'))} | {v(s.get('low_1pct_fps'))} | {v(s.get('p99_ms'))} | "
                   f"{v((s.get('gpu') or {}).get('p99_ms'))} | {v(f.get('avg_fps'))} | {v(f.get('low_1pct_fps'))} | {v(f.get('p99_ms'))} | "
                   f"{'n/a' if not fp else f'{fp / 1024:.0f}'} | {r.get('swap_before_M')}->{r.get('swap_after_M')} |")
    text = "\n".join(out) + "\n"
    Path(sys.argv[1]).with_suffix(".tables.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
