#!/usr/bin/env python3
"""Write a dependency-free Rust test file from a TRANSFORMED workspace (no cargo needed).

    python3 -I standalone_tests.py WORKSPACE OUT.rs
    rustc --edition 2021 --test OUT.rs -o OUT && ./OUT

Copies native_emissive.rs's table/mappings/optifine_table/table_cached and the
`emissive_lookup_tests` module verbatim; only the include_str! path is made absolute.
The real `cargo test -p horizon-client-render native_emissive` still has to run after the build.
"""
import sys
from pathlib import Path

workspace, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
src = workspace / "crates/horizon-client-render/src"
text = (src / "native_emissive.rs").read_text()


def fn(sig):
    i = text.index(sig)
    return text[text.rfind("\n\n", 0, i) + 2:text.index("\n}\n", i) + 3]


head = "use std::collections::BTreeMap;\npub const MAX: usize = 128;\nconst NATIVE: usize = 32;\npub const CUTOUT: u32 = 1 << 31;\n"
body = "\n".join(fn(s) for s in ("pub fn table<'a>(", "pub fn mappings<'a>(", "pub fn optifine_table(", "pub fn table_cached<'a>("))
tests = text[text.index("#[cfg(test)]\nmod emissive_lookup_tests"):].replace(
    'include_str!("terrain.wgsl")', f'include_str!("{src}/terrain.wgsl")')
out.write_text(head + body + "\n" + tests)
