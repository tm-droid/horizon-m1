#!/usr/bin/env python3
"""Write a dependency-free Rust test file for the run-splitting rule from a TRANSFORMED workspace.

    python3 -I standalone_tests.py WORKSPACE OUT.rs
    rustc --edition 2021 --test OUT.rs -o OUT && ./OUT

Copies `RunShape`, `run_lengths` and the `pass_merge_tests` module from pack_post.rs verbatim.
The GPU side (one wgpu pass for a run) is not covered: it needs the real build and image diffs.
"""
import sys
from pathlib import Path

workspace, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
text = (workspace / "crates/horizon-client-render/src/gfx/pack_post.rs").read_text()
a = text.index("/// What decides whether consecutive programs share")
b = text.index("impl Pass {", a)
tests = text[text.index("#[cfg(test)]\nmod pass_merge_tests"):].replace(
    "use super::{RunShape, run_lengths};", "use super::*;")
out.write_text(text[a:b] + "\n" + tests)
