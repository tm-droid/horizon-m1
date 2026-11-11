#!/usr/bin/env python3
"""Write a dependency-free Rust test file from a TRANSFORMED workspace (no cargo needed).

    python3 -I standalone_tests.py WORKSPACE OUT.rs
    rustc --edition 2021 --test OUT.rs -o OUT && ./OUT

First checks the workspace: every edit's new text is present exactly once and no old anchor is left.
Then copies `SpritePixels` (assets.rs) verbatim
and checks the pack / get round trip over a tiny lz4_flex stand-in.
The real `cargo test -p horizon-client-render assets::sprite_pixels_tests` still has to run after the build.
"""
import sys
from pathlib import Path

workspace, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
import json

spec = json.loads((Path(__file__).resolve().parent / "edits.json").read_text())
for relative, entry in spec["files"].items():
    text = (workspace / relative).read_text()
    for index, edit in enumerate(entry["edits"]):
        assert text.count(edit["new"]) == 1, f"{relative}: edit {index} result not found exactly once"
        assert text.count(edit["old"]) == 0 or edit["old"] in edit["new"], f"{relative}: edit {index} old anchor left"

text = (workspace / "crates/horizon-client-render/src/assets.rs").read_text()
start = text.index("pub struct SpritePixels(")
end = text.index("fn invalid(message: &str)")
code = text[start:end]
STUB = "\nmod lz4_flex {\n    // Stand-in for the crate (RLE, same size-prepended framing): the logic under test is the holder's.\n    pub fn compress_prepend_size(i: &[u8]) -> Vec<u8> {\n        let mut o = (i.len() as u32).to_le_bytes().to_vec();\n        let mut k = 0;\n        while k < i.len() {\n            let v = i[k];\n            let mut n = 1;\n            while k + n < i.len() && i[k + n] == v && n < 255 { n += 1; }\n            o.push(n as u8);\n            o.push(v);\n            k += n;\n        }\n        o\n    }\n    pub fn decompress_size_prepended(i: &[u8]) -> Result<Vec<u8>, ()> {\n        if i.len() < 4 { return Err(()); }\n        let n = u32::from_le_bytes([i[0], i[1], i[2], i[3]]) as usize;\n        let mut o = Vec::new();\n        for c in i[4..].chunks(2) {\n            if c.len() < 2 { return Err(()); }\n            o.extend(std::iter::repeat(c[1]).take(c[0] as usize));\n        }\n        if o.len() == n { Ok(o) } else { Err(()) }\n    }\n}\n"
TESTS = r'''
fn wait(s: &SpritePixels) {
    let t = std::time::Instant::now();
    while s.0.raw.lock().unwrap().is_some() { assert!(t.elapsed().as_secs() < 10); std::thread::yield_now(); }
}
#[test]
fn lab_pbr_maps_round_trip() {
    let normals: Vec<u8> = (0..16 * 16 * 3).flat_map(|i| if i % 7 == 0 { [120, 130, 250, 255] } else { [128, 128, 255, 255] }).collect();
    let specular: Vec<u8> = (0..16 * 16 * 3).flat_map(|i| [(i * 3 % 251) as u8, (i % 97) as u8, 0, 255]).collect();
    for map in [normals, specular] {
        let s = SpritePixels::new(map.clone());
        assert_eq!(*s.get(), map);
        s.pack();
        wait(&s);
        assert_eq!(*s.get(), map);
        assert_eq!(s.len(), map.len());
    }
}
#[test]
fn absent_maps_stay_empty() {
    let none = SpritePixels::new(Vec::new());
    assert!(none.is_empty());
    none.pack();
    assert!(none.get().is_empty());
    assert!(none.0.packed.get().is_none());
}
'''
out.write_text("use std::sync::Arc;\n" + STUB + code + TESTS)
