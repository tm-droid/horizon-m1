#!/usr/bin/env python3
"""Focused U13 checks; no client, compiler, queue, or device commands are run."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch
import sys
import zipfile

RUNTIME = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, RUNTIME / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUNNER = load("u13_runner", "run-u12-native-packs.py")
ANALYZER = load("u13_analyzer", "analyze-u12-native.py")
PREP = load("u13_prep", "prepare-u13-packs.py")


class U13Tests(unittest.TestCase):
    def test_case_arm_round_filter(self):
        cases = ["makeup", "n-montarc-m1", "n-daybreak011-m1"]
        matrix = RUNNER.plan(cases, "r3-v4-t", 3)
        self.assertEqual(matrix, [
            ("makeup", "r3-v4-t", 1),
            ("n-montarc-m1", "r3-v4-t", 1),
            ("n-daybreak011-m1", "r3-v4-t", 1),
            ("n-daybreak011-m1", "r3-v4-t", 2),
            ("n-montarc-m1", "r3-v4-t", 2),
            ("makeup", "r3-v4-t", 2),
            ("makeup", "r3-v4-t", 3),
            ("n-montarc-m1", "r3-v4-t", 3),
            ("n-daybreak011-m1", "r3-v4-t", 3),
        ])
        self.assertEqual(RUNNER.ARM_DEFS["r3-v4-t"][2], {"HORIZON_SHADER_PACK_TIMING": "1"})

    def test_validation_ignores_unselected_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "versions/r3").mkdir(parents=True)
            (root / "versions/r3/horizon-client").touch()
            (root / "v4").mkdir()
            for name in ("manifest.json", "native-settings-candidate.json", "wrapper.py", "montarc-m1.hshader"):
                (root / "v4" / name).touch()
            with patch.multiple(RUNNER, VERSIONS=root / "versions", BUILDS={"r3": "r3", "control": "missing"},
                                MIGRATIONS={"v4": root / "v4", "v3": root / "missing"},
                                NATIVE_DIR=root / "v4", HARNESS=root / "v4/wrapper.py"):
                self.assertEqual(RUNNER.input_problems(RUNNER.plan(["n-montarc-m1"], "r3-v4-t", 1)), [])
                problems = RUNNER.input_problems(RUNNER.plan(["n-montarc-m1"], "baseline", 1))
                self.assertTrue(any("control" in problem for problem in problems))
                self.assertTrue(any("v3" in problem for problem in problems))

    def test_trim_hash_uses_override_without_java_options(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "MakeUp-UltraFast-9.6.zip").write_bytes(b"archive")
            (root / "MakeUp-UltraFast-9.6.zip.txt").write_text("unrelated options")
            (root / "trim.txt").write_text("AOSTEPS=4\n")
            with patch.object(RUNNER, "TRIM_FILE", root / "trim.txt"), \
                    patch.object(RUNNER, "shader_source_dir", return_value=root), \
                    patch.object(RUNNER.REVIEW, "shader_hashes", side_effect=AssertionError("Java options read")):
                hashes = RUNNER.shader_hashes("makeup", "v4")
            self.assertEqual(hashes["options"], hashlib.sha256(b"AOSTEPS=4\n").hexdigest())

    def test_resume_rejects_changed_migration_manifest_or_native_settings(self):
        for changed in ("manifest.json", "native-settings-candidate.json"):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "manifest.json").write_text(json.dumps({"resourcepack_selection": ["vanilla"]}))
                (root / "native-settings-candidate.json").write_text('{}')
                (root / "versions/r3").mkdir(parents=True)
                (root / "versions/r3/horizon-client").write_bytes(b"binary")
                matrix = RUNNER.plan(["n-montarc-m1"], "r3-v4-t", 1)
                identity = RUNNER.migration_identity(root)
                summary = {"plan": [list(item) for item in matrix],
                           "binary_sha256": {"r3": RUNNER.R3.digest(root / "versions/r3/horizon-client")},
                           "shader_sha256": {"n-montarc-m1/v4": {"archive": "shader-hash"}},
                           "migration_identity": {"v4": identity}, "results": []}
                (root / "u12-native-resumetest.json").write_text(json.dumps(summary))
                if changed == "manifest.json":
                    (root / changed).write_text(json.dumps({"resourcepack_selection": ["vanilla", "file/new.zip"]}))
                else:
                    (root / changed).write_text('{"settings": "changed"}')
                self.assertNotEqual(RUNNER.migration_identity(root), identity)
                argv = ["runner", "--resume", "--tag", "resumetest", "--cases", "n-montarc-m1", "--arm", "r3-v4-t"]
                with patch.object(sys, "argv", argv), \
                        patch.multiple(RUNNER, RUNTIME=root, VERSIONS=root / "versions", BUILDS={"r3": "r3"},
                                       MIGRATIONS={"v4": root}), \
                        patch.object(RUNNER, "input_problems", return_value=[]), \
                        patch.object(RUNNER, "stage_native"), \
                        patch.object(RUNNER, "shader_hashes", return_value={"archive": "shader-hash"}), \
                        patch.object(RUNNER.subprocess, "Popen", side_effect=AssertionError("device command")):
                    self.assertEqual(RUNNER.main(), 2)
                self.assertEqual(json.loads((root / "u12-native-resumetest.json").read_text()), summary)

    def test_tags_separate_profiles(self):
        first = RUNNER.profile_label("u13a", "n-montarc-m1", "r3-v4-t", 1)
        second = RUNNER.profile_label("u13b", "n-montarc-m1", "r3-v4-t", 1)
        self.assertNotEqual(first, second)
        self.assertLessEqual(len(first), 60)
        self.assertNotEqual(first, RUNNER.profile_label("u13a", "n-montarc-m1", "r3-v4-t", 1, 2))

    def test_refusal_never_exposes_fallback_metrics(self):
        result = {"measurement": {"avg_fps": 100}, "shader_diagnostics": [
            "shader pack daybreak-0.2.0.hshader refused: TOML parse error"]}
        review, flags = RUNNER.review_cow(result, Path("unused"),
                                         {"selection": [], "manifest_hash": "unused"}, "n-daybreak020")
        self.assertFalse(flags["loaded"])
        self.assertNotIn("static", review)
        self.assertNotIn("flight", review)
        loaded = RUNNER.native_status(["shader pack montarcm1 1.1.1: Sky, Terrain, Colour in 42 ms"])
        self.assertTrue(loaded["loaded"])

    def test_refused_or_missing_makeup_loader_evidence_is_rejected(self):
        def review(result, profile, selection, manifest_hash, shader, *args):
            if shader is None:
                return {"static": {"avg_fps": 100}}  # A shader-off fallback would otherwise look fast.
            raise ValueError("No shader loader report showing active post programs")
        for diagnostics in ([], ["shader pack MakeUp-UltraFast-9.6.zip refused: invalid shader"]):
            with self.subTest(diagnostics=diagnostics):
                result = {"shader_requested": "MakeUp-UltraFast-9.6.zip", "shader_diagnostics": diagnostics}
                with patch.object(RUNNER.REVIEW, "review_result", side_effect=review) as check:
                    with self.assertRaisesRegex(ValueError, "No shader loader report"):
                        RUNNER.review_cow(result, Path("unused"),
                                          {"selection": [], "manifest_hash": "unused"}, "makeup")
                check.assert_called_once()
                self.assertIs(check.call_args.args[0], result)
                self.assertEqual(check.call_args.args[4], "MakeUp-UltraFast-9.6.zip")

    def test_valid_run_below_threshold_is_hopeless(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            path.write_text(json.dumps({"measurement": {"avg_fps": 14.9}}))
            self.assertTrue(RUNNER.hopeless({"valid": True, "result": str(path)}))
            path.write_text(json.dumps({"measurement": {"avg_fps": 15}}))
            self.assertFalse(RUNNER.hopeless({"valid": False, "result": str(path)}))

    def test_aggregation_pairs_same_arm_and_round_and_rejects_fallback(self):
        def run(case, arm, rnd, avg, **extra):
            return {"case": case, "arm": arm, "round": rnd, "valid": True,
                    "static": {"avg_fps": avg}, **extra}
        summary = {"results": [run("makeup", "a", 1, 20), run("makeup", "a", 2, 40),
                               run("n-montarc", "a", 1, 24, loaded=True),
                               run("n-montarc", "a", 2, 44, loaded=True),
                               run("makeup", "b", 1, 10),
                               run("n-montarc", "b", 1, 15, loaded=True),
                               run("n-daybreak020", "a", 1, 100, loaded=False)]}
        groups = {(g["case"], g["arm"]): g for g in ANALYZER.aggregate(summary)}
        self.assertEqual(len(groups[("n-montarc", "a")]["valid"]), 2)
        self.assertAlmostEqual(groups[("n-montarc", "a")]["paired_pct"][0], 20)
        self.assertAlmostEqual(groups[("n-montarc", "a")]["paired_pct"][1], 10)
        self.assertEqual(groups[("n-montarc", "b")]["paired_pct"], [50])
        self.assertEqual(groups[("n-daybreak020", "a")]["valid"], [])
        table = ANALYZER.render(summary)
        self.assertIn("34.0 [24.0, 44.0]", table)
        refused_row = next(line for line in table.splitlines() if line.startswith("| n-daybreak020"))
        self.assertNotIn("100", refused_row)

    def test_variants_change_only_intended_manifest_fields(self):
        for source, target, ident, name, distance in PREP.VARIANTS:
            with self.subTest(target=target), zipfile.ZipFile(PREP.PACKS / source) as original, \
                    zipfile.ZipFile(PREP.PACKS / target) as variant:
                self.assertEqual(original.namelist(), variant.namelist())
                for entry in original.namelist():
                    if entry != "horizon-shaders.toml":
                        self.assertEqual(original.read(entry), variant.read(entry), entry)
                expected = copy.deepcopy(tomllib.loads(original.read("horizon-shaders.toml").decode()))
                expected.update(id=ident, name=name)
                expected["shadow"].update(resolution=1536, distance=distance)
                if ident == "montarcm1":
                    next(o for o in expected["options"] if o["id"] == "shadow_samples")["default"] = "Low"
                self.assertEqual(tomllib.loads(variant.read("horizon-shaders.toml").decode()), expected)


if __name__ == "__main__":
    unittest.main()
