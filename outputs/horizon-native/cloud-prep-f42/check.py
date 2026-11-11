#!/usr/bin/env python3
"""Verify reviewed edits; optionally compile the actual guard with GPU-free Rust stubs."""
import argparse
import importlib.util
from pathlib import Path
import re
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cloud_prepare", HERE / "prepare.py")
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


def check(source, rustc):
    rendered = {}
    for name in patch.SPEC["files"]:
        original = (source / name).read_bytes()
        rendered[name] = patch.render(name, original).decode()
        try:
            patch.render(name, original + b"\n")
        except ValueError:
            pass
        else:
            raise AssertionError("Source drift was accepted")
    gfx = rendered["crates/horizon-client-render/src/gfx.rs"]
    post = rendered["crates/horizon-client-render/src/gfx/pack_post.rs"]
    guard = re.search(r"        let iris_clouds = frame.title\n.*?        let native_clouds = .*?;\n", gfx, re.S).group()
    query = re.search(r"    pub fn clouds_off\(&self\) -> bool \{\n.*?\n    \}", post, re.S).group()
    assert "let clouds_off = post.clouds_off;" in post
    assert "            hides_clouds,\n            clouds_off," in post
    assert gfx.index(guard) < gfx.index("self.cloud_mesh.prepare(input)")
    rust = r'''
// MIT License. Guard excerpt from Horizon; copyright 2026 Ludovic Marie and contributors.
struct Native { vanilla_clouds: bool }
struct Post { clouds_off: bool, has_cloud_program: bool }
impl Post {
QUERY
}
struct Frame { title: bool }
struct Renderer { native: Option<Native>, pack_post: Option<((), Option<Post>)> }
impl Renderer {
    fn prepares_cloud_mesh(&self, frame: &Frame) -> bool {
GUARD
        native_clouds
    }
}
fn main() {
    let mut cases = 0;
    for title in [false, true] {
        for native in [None, Some(false), Some(true)] {
            // absent slot, failed/unloaded post, ordinary pack, clouds=off,
            // and real gbuffers_clouds programs with each declaration.
            for pack in [None, Some(None), Some(Some((false, false))),
                         Some(Some((true, false))), Some(Some((false, true))),
                         Some(Some((true, true)))] {
                let renderer = Renderer {
                    native: native.map(|vanilla_clouds| Native { vanilla_clouds }),
                    pack_post: pack.map(|p| ((), p.map(|(clouds_off, has_cloud_program)| Post {
                        clouds_off, has_cloud_program,
                    }))),
                };
                let suppressed = matches!(pack, Some(Some((true, _)))) && !title;
                let expected = native != Some(false) && !suppressed;
                assert_eq!(renderer.prepares_cloud_mesh(&Frame { title }), expected);
                // An actual cloud program still receives the native geometry.
                if matches!(pack, Some(Some((false, true)))) && native != Some(false) {
                    assert!(renderer.prepares_cloud_mesh(&Frame { title }));
                }
                if let Some((_, Some(p))) = &renderer.pack_post {
                    let _ = p.has_cloud_program;
                }
                cases += 1;
            }
        }
    }
    println!("cloud guard: {cases} cases passed");
}
'''.replace("QUERY", query).replace("GUARD", guard)
    if rustc:
        with tempfile.TemporaryDirectory(prefix="horizon-cloud-guard-") as directory:
            path = Path(directory)
            (path / "check.rs").write_text(rust)
            subprocess.run([str(rustc), "--edition=2021", str(path / "check.rs"), "-o", str(path / "check")], check=True)
            subprocess.run([str(path / "check")], check=True)
    print("Reviewed two-file transforms and source-drift rejection passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--rustc", type=Path, help="Compile the extracted guard under a queued verification turn")
    args = parser.parse_args()
    check(args.source, args.rustc)
