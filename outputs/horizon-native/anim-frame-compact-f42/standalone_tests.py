#!/usr/bin/env python3
"""Write a dependency-free Rust test file from a TRANSFORMED workspace (no cargo needed).

    python3 -I standalone_tests.py WORKSPACE OUT.rs
    rustc --edition 2021 --test OUT.rs -o OUT && ./OUT

First checks the workspace: every edit's new text is present exactly once and no old anchor is left.
Then copies `AnimationFrames` and `pack_animations` (sprites.rs) verbatim over a stand-in `SpriteAnimation`
and checks the pack / get round trip over a tiny lz4_flex stand-in.
The real `cargo test -p horizon-client-render sprites::animation_frames_tests` still has to run after the build.
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

text = (workspace / "crates/horizon-client-render/src/sprites.rs").read_text()
start = text.index("/// An animated sprite's frames at the array's layer size.")
end = text.index("/// What an animated sprite shows")
code = text[start:end]
STUB = "\nmod lz4_flex {\n    // Stand-in for the crate (RLE, same size-prepended framing): the logic under test is the holder's.\n    pub fn compress_prepend_size(i: &[u8]) -> Vec<u8> {\n        let mut o = (i.len() as u32).to_le_bytes().to_vec();\n        let mut k = 0;\n        while k < i.len() {\n            let v = i[k];\n            let mut n = 1;\n            while k + n < i.len() && i[k + n] == v && n < 255 { n += 1; }\n            o.push(n as u8);\n            o.push(v);\n            k += n;\n        }\n        o\n    }\n    pub fn decompress_size_prepended(i: &[u8]) -> Result<Vec<u8>, ()> {\n        if i.len() < 4 { return Err(()); }\n        let n = u32::from_le_bytes([i[0], i[1], i[2], i[3]]) as usize;\n        let mut o = Vec::new();\n        for c in i[4..].chunks(2) {\n            if c.len() < 2 { return Err(()); }\n            o.extend(std::iter::repeat(c[1]).take(c[0] as usize));\n        }\n        if o.len() == n { Ok(o) } else { Err(()) }\n    }\n}\n"
TESTS = r'''
fn sheet(native: u32, size: u32, frames: u32) -> Vec<Vec<u8>> {
    (0..frames).map(|f| (0..size * size).flat_map(|i| {
        let (x, y) = (i % size * native / size, i / size * native / size);
        [x as u8, y as u8, (f * 40 + x + y) as u8, 255]
    }).collect()).collect()
}
fn wait(s: &AnimationFrames) {
    let t = std::time::Instant::now();
    while s.raw.lock().unwrap().is_some() { assert!(t.elapsed().as_secs() < 10); std::thread::yield_now(); }
}
#[test]
fn round_trip_clones_and_claims() {
    let frames = sheet(16, 64, 5);
    let a = SpriteAnimation { frames: Arc::new(AnimationFrames::new(Arc::new(frames.clone()))) };
    let b = SpriteAnimation { frames: a.frames.clone() };
    assert_eq!(*a.frames.get(), frames);
    pack_animations(std::slice::from_ref(&a));
    pack_animations(std::slice::from_ref(&b)); // claimed: no second job
    wait(&a.frames);
    assert!(b.frames.raw.lock().unwrap().is_none());
    assert_eq!(*b.frames.get(), frames);
    assert_eq!(a.frames.lens.len(), 5);
}
#[test]
fn unequal_and_empty_lists() {
    let frames = vec![vec![1, 2, 3, 4], vec![], vec![9; 12]];
    let s = AnimationFrames::new(Arc::new(frames.clone()));
    s.pack();
    assert_eq!(*s.get(), frames);
    let n = AnimationFrames::new(Arc::new(Vec::new()));
    n.pack();
    assert!(n.get().is_empty());
}
#[test]
fn corrupt_packed_data_falls_back_to_zeroes() {
    let s = AnimationFrames::new(Arc::new(vec![vec![5; 8]]));
    *s.raw.lock().unwrap() = None;
    let _ = s.packed.set(vec![1, 2, 3]);
    assert_eq!(*s.get(), vec![vec![0u8; 8]]);
}
'''
head = "use std::sync::Arc;\nstruct SpriteAnimation { frames: Arc<AnimationFrames> }\n"
out.write_text(head + STUB + code + TESTS)
