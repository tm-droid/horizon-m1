"""Source-only candidate checks. Full engine/runtime acceptance is separate."""
import difflib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "outputs/horizon-native/cem-binding-f42"
SPEC = importlib.util.spec_from_file_location("cem_binding_candidate", BUNDLE / "apply.py")
CANDIDATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CANDIDATE)


class BindingPatchTests(unittest.TestCase):
    def original(self):
        return (BUNDLE / "upstream/cem.rs").read_bytes()

    def test_pinned_diff_and_provenance(self):
        original = self.original()
        changed = CANDIDATE.render(original)
        provenance = json.loads((BUNDLE / "provenance.json").read_text())
        self.assertEqual(CANDIDATE.digest(changed), provenance["after_sha256"])
        expected = "".join(difflib.unified_diff(
            original.decode().splitlines(True), changed.decode().splitlines(True),
            fromfile="a/" + CANDIDATE.TARGET.as_posix(),
            tofile="b/" + CANDIDATE.TARGET.as_posix()))
        self.assertEqual((BUNDLE / "cem-binding.patch").read_text(), expected)
        # Both replacement discovery/attachment and animation use the same exact name.
        self.assertIn("let model = name;", changed.decode())
        self.assertEqual(changed.decode().count("vanilla_part(&model,"), 3)
        self.assertNotIn("let model = name.replace", changed.decode())

    def test_source_drift_refused(self):
        with self.assertRaisesRegex(ValueError, "source drift"):
            CANDIDATE.render(self.original() + b"\n")

    def test_fresh_copy_preserves_input_and_license(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
            source = Path(temporary) / "source"
            target = source / CANDIDATE.TARGET
            target.parent.mkdir(parents=True)
            target.write_bytes(self.original())
            (source / "LICENSE").write_bytes((BUNDLE / "upstream/LICENSE").read_bytes())
            output = Path(temporary) / "candidate"
            with patch.object(CANDIDATE, "verify_checkout"):
                result = CANDIDATE.prepare(source, output)
            self.assertEqual(target.read_bytes(), self.original())
            self.assertEqual((output / CANDIDATE.TARGET).read_bytes(), CANDIDATE.render(self.original()))
            self.assertEqual((source / "LICENSE").read_bytes(), (output / "LICENSE").read_bytes())
            self.assertEqual(result["before_sha256"], CANDIDATE.BEFORE)
            with self.assertRaisesRegex(ValueError, "must not exist"):
                CANDIDATE.prepare(source, output)
            with self.assertRaisesRegex(ValueError, "overlap"):
                CANDIDATE.prepare(source, source / "new")

    def test_live_destination_and_symlinks_refused(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            with self.assertRaisesRegex(ValueError, "fresh child"):
                CANDIDATE.prepare(source, ROOT / "outputs/horizon-runtime/not-a-source-copy")
            output = Path(temporary) / "dangling"
            output.symlink_to(Path(temporary) / "absent")
            with self.assertRaisesRegex(ValueError, "must not exist"):
                CANDIDATE.prepare(source, output)

    def test_checkout_commit_and_dirty_refused(self):
        with patch.object(CANDIDATE.subprocess, "check_output", return_value="wrong\n"):
            with self.assertRaisesRegex(ValueError, "not pinned"):
                CANDIDATE.verify_checkout(Path("/unused"))
        with patch.object(CANDIDATE.subprocess, "check_output", side_effect=[CANDIDATE.COMMIT, " M crates/file.rs"]):
            with self.assertRaisesRegex(ValueError, "must be clean"):
                CANDIDATE.verify_checkout(Path("/unused"))

    @unittest.skipUnless(shutil.which("rustc"), "rustc required for actual resolver assertions")
    def test_actual_rust_resolver(self):
        # Compile the exact patched production function, without crates/game/native hooks.
        source = CANDIDATE.render(self.original()).decode()
        resolver = "fn vanilla_part(" + source.split("fn vanilla_part(", 1)[1].split("\nimpl CemLayer", 1)[0]
        cases = []
        for model in ("guardian", "elder_guardian"):
            cases.append((model, "body", "head"))
        for model in ("wolf", "wolf_armor"):
            cases.append((model, "mane", "upper_body"))
        cases += [("happy_ghast_harness", "body", "harness"),
                  ("puffer_fish_small", "tail", "back_fin"),
                  ("puffer_fish_small", "eye_right", "right_eye"),
                  ("puffer_fish_small", "eye_left", "left_eye")]
        for model in ("salmon", "salmon_small", "salmon_large"):
            cases += [(model, "fin_back_1", "top_front_fin"),
                      (model, "fin_back_2", "top_back_fin"), (model, "tail", "back_fin")]
        for model in ("tropical_fish_pattern_a", "tropical_fish_pattern_b"):
            cases.append((model, "fin_top", "top_fin"))
        for model in ("horse_armor", "skeleton_horse_armor"):
            cases += [(model, "neck", "head_parts"), (model, "mouth", "upper_mouth")]
        cases += [("villager_baby", "bodywear", "bb_main"),
                  ("villager", "bodywear", "jacket"),
                  ("villager_baby", "headwear2", "hat_rim"),
                  ("cow_baby", "leg1", "right_hind_leg"),
                  ("piglin_baby", "jacket", "jacket"),
                  ("piglin", "jacket", "jacket"),
                  ("puffer_fish_big", "tail", "tail"),
                  ("puffer_fish_medium", "eye_left", "eye_left"),
                  ("happy_ghast", "body", "body"), ("cow", "mane", "mane"),
                  ("wolf_collar", "mane", "mane"), ("horse", "neck", "head_parts"),
                  ("zombie_horse_armor", "neck", "neck"),
                  ("wandering_trader_baby", "bodywear", "jacket"),
                  ("villager_baby_armor", "bodywear", "bodywear"),
                  ("cod", "tail", "tail_fin"), ("guardian", "spine1", "spike0"),
                  ("guardian", "body2", "body2"), ("salmon", "body", "body")]
        assertions = "\n".join(f"assert_eq!(vanilla_part({json.dumps(m)}, {json.dumps(p)}), {json.dumps(v)});" for m, p, v in cases)
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
            path = Path(temporary) / "resolver.rs"
            path.write_text(resolver + "\nfn main() {\n" + assertions + "\n}\n")
            binary = Path(temporary) / "resolver"
            subprocess.run(["rustc", "--edition=2021", str(path), "-o", str(binary)], check=True, capture_output=True)
            subprocess.run([str(binary)], check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
