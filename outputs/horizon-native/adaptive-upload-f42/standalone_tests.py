#!/usr/bin/env python3
"""Write a dependency-free Rust test file from a TRANSFORMED workspace (no cargo needed).

    python3 -I standalone_tests.py WORKSPACE OUT.rs
    rustc --edition 2021 --test OUT.rs -o OUT && ./OUT

Copies the `mod adaptive_upload { .. }` block (logic plus its unit tests, std only) out of game.rs.
Includes a closed-loop settle model asserting the adaptive drain never takes longer than the fixed one.
"""
import sys
from pathlib import Path

workspace, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
text = (workspace / "crates/horizon-client/src/game.rs").read_text()
start = text.index("mod adaptive_upload {")
start = text.rfind("\n\n", 0, start) + 2
end = text.index("\n}\n", text.index("fn flight_with_a_steady_queue")) + 3
out.write_text("#![allow(dead_code)]\n" + text[start:end] + "\nfn main() {}\n")
