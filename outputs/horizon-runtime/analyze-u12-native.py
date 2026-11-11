#!/usr/bin/env python3
"""Summarize valid U12/U13 runs by case and arm; refused packs never contribute FPS."""
import json
from pathlib import Path
import statistics
import sys


def usable(run):
    return bool(run.get("valid")) and (not run["case"].startswith("n-") or run.get("loaded") is True)


def aggregate(summary):
    # A retry replaces its own round only; retain all independent rounds and arms.
    latest = {(r["case"], r.get("arm", "r3-v4"), r.get("round", 1)): r for r in summary["results"]}
    groups = {}
    for (case, arm, rnd), run in latest.items():
        group = groups.setdefault((case, arm), {"case": case, "arm": arm, "runs": [], "valid": [], "paired_pct": []})
        group["runs"].append(run)
        if not usable(run):
            continue
        group["valid"].append(run)
        ref = latest.get(("makeup", arm, rnd))
        avg = (run.get("static") or {}).get("avg_fps")
        ref_avg = ((ref or {}).get("static") or {}).get("avg_fps")
        if case != "makeup" and ref is not None and usable(ref) and avg and ref_avg:
            group["paired_pct"].append((avg / ref_avg - 1) * 100)
    return list(groups.values())


def spread(values, spec=".1f"):
    values = [v for v in values if v is not None]
    if not values:
        return "n/a"
    median = format(statistics.median(values), spec)
    return median if len(values) == 1 else f"{median} [{format(min(values), spec)}, {format(max(values), spec)}]"


def render(summary):
    rows = ["| case | arm | valid/rounds | loaded | static avg | static 1% low | paired vs MakeUp % | flight avg | flight 1% low | footprint peak MB | swap peak M | note |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for group in aggregate(summary):
        case, arm, runs, valid = (group[k] for k in ("case", "arm", "runs", "valid"))
        def phase(name, metric):
            return spread([(r.get(name) or {}).get(metric) for r in valid])
        loaded_values = {r.get("loaded") for r in runs}
        loaded = "ref" if case == "makeup" else ("yes" if loaded_values == {True} else "no" if loaded_values == {False} else "mixed/unknown")
        notes = list(dict.fromkeys((r.get("error") or "; ".join(r.get("refusal_lines") or []))
                                   for r in runs if not usable(r)))
        note = "; ".join(n for n in notes if n)[:160].replace("|", "/").replace("\n", " ")
        footprint = [(r.get("memory") or {}).get("footprint_peak_kb") for r in valid]
        footprint = [v / 1024 for v in footprint if v is not None]
        swap = [(r.get("memory") or {}).get("swap_peak_M") for r in valid]
        rows.append(f"| {case} | {arm} | {len(valid)}/{len(runs)} | {loaded} | {phase('static', 'avg_fps')} | "
                    f"{phase('static', 'low_1pct_fps')} | {spread(group['paired_pct'])} | {phase('flight', 'avg_fps')} | "
                    f"{phase('flight', 'low_1pct_fps')} | {spread(footprint, '.0f')} | {spread(swap, '.0f')} | {note} |")
    skipped = summary.get("skipped", [])
    return "\n".join(["# Native shader comparison", "", "Values are median [minimum, maximum] across valid rounds; a single round shows one value.",
                      "Paired percentages use the MakeUp reference from the same arm and round. Refused/unloaded packs have no FPS metrics.",
                      "", *rows, "", f"Planned rounds skipped after a hopeless/unloaded result: {len(skipped)}.",
                      "Screenshot paths and per-pass timing lines are retained in the JSON results.", ""])


def main():
    path = Path(sys.argv[1])
    out = render(json.loads(path.read_text()))
    path.with_suffix(".tables.md").write_text(out)
    print(out)


if __name__ == "__main__":
    main()
