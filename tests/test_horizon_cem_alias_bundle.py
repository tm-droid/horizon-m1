"""Source-only partial native alias candidate; no Cargo or game tests."""
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "outputs/horizon-native/cem-alias-f42-bundle"
SPEC = importlib.util.spec_from_file_location("cem_alias_prepare", BUNDLE / "prepare.py")
PREPARE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREPARE)


class AliasBundleTests(unittest.TestCase):
    def test_pins_schema_and_recorded_bytes(self):
        record = json.loads((BUNDLE / "provenance.json").read_text())
        self.assertEqual(PREPARE.inventory(BUNDLE / "bundle"), record["bundle_sha256"])
        self.assertEqual(PREPARE.inventory(BUNDLE / "provenance"), record["evidence_sha256"])
        manifest = (BUNDLE / "bundle/horizon-mixin.toml").read_text()
        self.assertIn('horizon_revision = "' + PREPARE.COMMIT + '"', manifest)
        self.assertIn('target = "horizon_client_lib::mobs::cem::vanilla_part"', manifest)
        self.assertIn('kind = "HEAD"\ncancellable = true', manifest)
        self.assertIn('{ name = "model", ty = "&str", value = "model" }', manifest)
        self.assertIn('{ name = "part", ty = "&str", value = "part" }', manifest)
        self.assertFalse((BUNDLE / "bundle/horizon-native.json").exists())
        self.assertEqual(PREPARE.sha(BUNDLE / "provenance/cem.rs"), PREPARE.SOURCE_SHA)

    def test_target_follows_pinned_cargo_module_topology(self):
        # Derive the defining crate from Cargo's lib entry, not source directory name
        # or the `extern crate self as horizon_client` alias inside client_lib.rs.
        topology = BUNDLE / "provenance/topology"
        record = json.loads((BUNDLE / "provenance.json").read_text())
        for relative, evidence in record["topology_sources"].items():
            self.assertEqual(PREPARE.sha(topology / relative), evidence["sha256"])
            self.assertIn(PREPARE.COMMIT, evidence["url"])
        library = topology / "crates/horizon-client-lib/Cargo.toml"
        cargo = library.read_text()
        package_section = cargo.split("[package]", 1)[1].split("\n[", 1)[0]
        lib_section = cargo.split("[lib]", 1)[1].split("\n[", 1)[0]
        package = re.search(r'^name\s*=\s*"([^"]+)"', package_section, re.M).group(1)
        lib_path = re.search(r'^path\s*=\s*"([^"]+)"', lib_section, re.M).group(1)
        entry = (library.parent / lib_path).resolve()
        self.assertTrue(entry.is_relative_to(topology.resolve()))
        self.assertRegex(entry.read_text(), r"(?m)^pub mod mobs;")
        mobs = entry.parent / "mobs.rs"
        self.assertRegex(mobs.read_text(), r"(?m)^pub mod cem;")
        cem_path = mobs.parent / "mobs/cem.rs"
        self.assertEqual(cem_path.relative_to(topology.resolve()), PREPARE.TARGET)
        self.assertRegex((BUNDLE / "provenance/cem.rs").read_text(), r"(?m)^fn vanilla_part\(")
        derived = package.replace("-", "_") + "::mobs::cem::vanilla_part"
        target = re.search(r'^target\s*=\s*"([^"]+)"',
                           (BUNDLE / "bundle/horizon-mixin.toml").read_text(), re.M).group(1)
        self.assertEqual(target, derived)
        reexport = topology / "crates/horizon-client/src/lib.rs"
        self.assertIn("pub use horizon_client_lib::*;", reexport.read_text())
        self.assertNotRegex(reexport.read_text(), r"(?m)^pub mod mobs;")
        self.assertNotEqual(target, "horizon_client::mobs::cem::vanilla_part")

    def test_prepare_guards_and_unchanged_inputs(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
            root = Path(temporary)
            source = root / "source"
            target = source / PREPARE.TARGET
            target.parent.mkdir(parents=True)
            original = (BUNDLE / "provenance/cem.rs").read_bytes()
            target.write_bytes(original)
            zoom = ROOT / "outputs/horizon-native/zoom-f42-candidate/bundle"
            zoom_before = PREPARE.inventory(zoom)
            candidate_before = PREPARE.inventory(BUNDLE / "bundle")
            output = root / "combined"
            record = PREPARE.prepare(source, zoom, output)
            self.assertEqual(record["zoom"], zoom_before)
            self.assertEqual(PREPARE.inventory(zoom), zoom_before)
            self.assertEqual(PREPARE.inventory(BUNDLE / "bundle"), candidate_before)
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual(PREPARE.inventory(output / "zoom"), zoom_before)
            self.assertEqual(PREPARE.inventory(output / "cem_alias_f42"), candidate_before)
            with self.assertRaisesRegex(ValueError, "must not exist"):
                PREPARE.prepare(source, zoom, output)
            target.write_bytes(original + b"\n")
            with self.assertRaisesRegex(ValueError, "source guard"):
                PREPARE.prepare(source, zoom, root / "drift")
            target.write_bytes(original)
            with self.assertRaisesRegex(ValueError, "below this candidate"):
                PREPARE.prepare(source, zoom, ROOT / "outputs/horizon-runtime/unwanted-alias-input")

    @unittest.skipUnless(shutil.which("rustc"), "rustc required for helper assertions")
    def test_actual_helper_control_flow(self):
        helper = (BUNDLE / "bundle/aliases.rs").read_text()
        positives = [("guardian", "body", "head"), ("elder_guardian", "body", "head"),
                     ("wolf", "mane", "upper_body"), ("wolf_armor", "mane", "upper_body"),
                     ("happy_ghast_harness", "body", "harness"),
                     ("puffer_fish_small", "tail", "back_fin"),
                     ("puffer_fish_small", "eye_right", "right_eye"),
                     ("puffer_fish_small", "eye_left", "left_eye")]
        for model in ("salmon", "salmon_small", "salmon_large"):
            positives += [(model, "fin_back_1", "top_front_fin"),
                          (model, "fin_back_2", "top_back_fin"), (model, "tail", "back_fin")]
        positives += [(m, "fin_top", "top_fin") for m in ("tropical_fish_pattern_a", "tropical_fish_pattern_b")]
        for model in ("horse_armor", "skeleton_horse_armor"):
            positives += [(model, "neck", "head_parts"), (model, "mouth", "upper_mouth")]
        negatives = [("villager", "bodywear"), ("villager_baby", "bodywear"),
                     ("piglin", "jacket"), ("piglin_baby", "jacket"),
                     ("wolf_baby", "mane"), ("wolf_collar", "mane"),
                     ("happy_ghast", "body"), ("puffer_fish_big", "tail"),
                     ("puffer_fish_medium", "eye_left"), ("cod", "fin_top"),
                     ("tropical_fish_a", "fin_top"), ("horse", "neck"),
                     ("zombie_horse_armor", "neck"), ("guardian", "body2"),
                     ("guardian", "spine1"), ("salmon", "body"), ("cow", "mane")]
        checks = [f'assert_eq!(audited_part_aliases({json.dumps(m)}, {json.dumps(p)}), core::ops::ControlFlow::Break(String::from({json.dumps(v)})));' for m, p, v in positives]
        checks += [f'assert_eq!(audited_part_aliases({json.dumps(m)}, {json.dumps(p)}), core::ops::ControlFlow::Continue(()));' for m, p in negatives]
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
            source = Path(temporary) / "helper.rs"
            binary = Path(temporary) / "helper"
            source.write_text(helper + "\nfn main() {\n" + "\n".join(checks) + "\n}\n")
            subprocess.run(["rustc", "--edition=2021", str(source), "-o", str(binary)], check=True, capture_output=True)
            subprocess.run([str(binary)], check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
