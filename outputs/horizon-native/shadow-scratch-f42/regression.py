#!/usr/bin/env python3
"""Check source transforms and generate standalone Rust checks from real code."""
import argparse
from pathlib import Path
import prepare

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "outputs/horizon-runtime/launcher-data/native/source" / prepare.REVISION / prepare.TARGET

RUST_PREFIX = r'''use std::collections::HashSet;
type SectionKey = (i32, i32, i32);
#[derive(Clone, Copy, Debug, PartialEq)]
struct Visible { key: SectionKey, slot: u32, origin: [f32; 3] }
#[derive(Default)]
struct Sections { boxed: Vec<Visible> }
impl Sections {
    fn visible(&self, _: (), _: i32, _: &(), _: impl Fn(SectionKey) -> bool,
               _: impl Fn(i32, i32) -> bool, out: &mut Vec<Visible>) {
        out.extend(self.boxed.iter().copied());
    }
}
#[derive(Default)]
struct Scratch { sections: Sections, shadow_boxed: Vec<Visible>, shadow_seen: HashSet<SectionKey> }
impl Scratch {
    fn merge(&mut self, mut shadow_visible: Vec<Visible>) -> Vec<Visible> {
        let (camera, radius, light) = ((), 12, ());
'''
RUST_SUFFIX = r'''
        shadow_visible
    }
}
fn reference(mut near: Vec<Visible>, boxed: Vec<Visible>) -> Vec<Visible> {
    let seen: HashSet<_> = near.iter().map(|s| s.key).collect();
    near.extend(boxed.into_iter().filter(|s| !seen.contains(&s.key)));
    near
}
fn section(key: i32, serial: u32) -> Visible {
    Visible { key: (key, -4, key * 3), slot: serial, origin: [key as f32, serial as f32, 0.0] }
}
#[test]
fn exact_sequences_across_camera_and_scene_changes() {
    let mut scratch = Scratch::default();
    let cases = [
        (vec![], vec![]),
        (vec![section(1, 1)], vec![section(1, 9), section(-2, 2)]),
        (vec![], vec![section(1, 3), section(1, 4)]),
        (vec![section(-9, 5), section(4, 6)], vec![section(4, 7), section(8, 8)]),
        (vec![], vec![]),
        (vec![section(8, 44)], vec![section(1, 45), section(-9, 46)]),
    ];
    for (near, boxed) in cases.into_iter().cycle().take(600) {
        scratch.sections.boxed = boxed.clone();
        assert_eq!(scratch.merge(near.clone()), reference(near, boxed));
        assert!(scratch.shadow_boxed.is_empty());
    }
}
#[test]
fn capacities_stop_growing_after_warmup() {
    let mut scratch = Scratch::default();
    let near: Vec<_> = (0..1024).map(|i| section(i, i as u32)).collect();
    scratch.sections.boxed = (512..2048).map(|i| section(i, i as u32)).collect();
    scratch.merge(near.clone());
    let capacity = (scratch.shadow_boxed.capacity(), scratch.shadow_seen.capacity());
    for _ in 0..300 {
        assert_eq!(scratch.merge(near.clone()), reference(near.clone(), scratch.sections.boxed.clone()));
        assert_eq!((scratch.shadow_boxed.capacity(), scratch.shadow_seen.capacity()), capacity);
    }
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rust-output", type=Path, required=True)
    args = parser.parse_args()
    source = SOURCE.read_bytes()
    patched, digest = prepare.transform(source)
    assert digest == prepare.PRISTINE_SHA256
    assert patched.decode().count(prepare.NEW_BODY) == 1
    assert patched.decode().count("self.shadow_visible = shadow_visible;") == source.decode().count("self.shadow_visible = shadow_visible;")
    try:
        prepare.transform(patched)
    except ValueError:
        pass
    else:
        raise AssertionError("Already patched source was accepted")
    try:
        prepare.transform(source + b"\n")
    except ValueError:
        pass
    else:
        raise AssertionError("Unreviewed source was accepted")
    # Exact changed body, with a minimal stand-in only for unchanged visibility collection.
    extracted = patched.decode().split(prepare.NEW_BODY, 1)
    assert len(extracted) == 2
    if args.rust_output.exists():
        raise SystemExit("Use a fresh Rust fixture output path")
    args.rust_output.write_text(RUST_PREFIX + prepare.NEW_BODY + RUST_SUFFIX)
    print("PASS source SHA, 3 unique transforms, repeat/drift refusal, early-return restores retained")
    print(f"Rust fixture written: {args.rust_output}; actual Rust execution remains a separate check")


if __name__ == "__main__":
    main()
