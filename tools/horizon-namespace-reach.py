#!/usr/bin/env python3
"""Read-only: which non-vanilla, non-carried-mod resource-pack namespaces can anything reach?

usage: python3 -I horizon-namespace-reach.py <migration dir> [--json out.json]
Stdlib only. Never modifies the migration. See horizon_converter_prune.py for the reachability rules.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from horizon_converter_prune import analyze  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--json")
    a = ap.parse_args()
    res = analyze(a.dir)
    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
        with open(a.json, "w") as f:
            json.dump(res, f, indent=1)
    rows = sorted(res["namespaces"].items(), key=lambda kv: -kv[1]["bytes"])
    for ns, v in rows:
        print("%-9s %-24s files=%-5d reached=%-5d MB=%-6.2f %s" % (
            "REACHABLE" if v["reachable"] else "dead", ns, v["files"], v["files_reached"], v["bytes"] / 1e6,
            "; ".join(v["evidence"][:1])[:150]))
    dead = [v for v in res["namespaces"].values() if not v["reachable"]]
    print("dead namespaces=%d files=%d MB=%.2f | reachable=%d" % (
        len(dead), sum(v["files"] for v in dead), sum(v["bytes"] for v in dead) / 1e6, len(rows) - len(dead)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
