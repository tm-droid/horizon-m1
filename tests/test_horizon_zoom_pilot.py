"""Integrity checks for the pinned, inactive native Zoom source pilot."""
import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1] / "outputs/horizon-native/zoom-pilot"


class ZoomPilotSourceTests(unittest.TestCase):
    def test_baseline_and_source_match_recorded_hashes(self):
        status = json.loads((ROOT / "pilot-status.json").read_text())
        recorded = {entry["path"] for entry in status["source"]["files"]}
        for folder, field in (("upstream", "upstream_sha256"), ("source", "source_sha256")):
            actual = {p.relative_to(ROOT / folder).as_posix()
                      for p in (ROOT / folder).rglob("*") if p.is_file()
                      and "target" not in p.relative_to(ROOT / folder).parts}
            self.assertEqual(actual, recorded)
            for entry in status["source"]["files"]:
                data = (ROOT / folder / entry["path"]).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), entry[field])
                if folder == "upstream":
                    blob = b"blob " + str(len(data)).encode() + b"\0" + data
                    self.assertEqual(hashlib.sha1(blob).hexdigest(), entry["git_blob_sha1"])
        patch = (ROOT / status["tool_revision"]["patch"]).read_bytes()
        self.assertEqual(hashlib.sha256(patch).hexdigest(), status["tool_revision"]["sha256"])

    def test_only_runtime_is_changed_and_required_bundle_files_survive(self):
        status = json.loads((ROOT / "pilot-status.json").read_text())
        changed = [e["path"] for e in status["source"]["files"]
                   if e["upstream_sha256"] != e["source_sha256"]]
        self.assertEqual(changed, ["mixins/zoom/runtime.rs"])
        for path in ("Cargo.toml", "Cargo.lock", "LICENSE", "mixins/zoom/horizon-mixin.toml"):
            self.assertTrue((ROOT / "source" / path).is_file(), path)
        self.assertIn("MIT License", (ROOT / "source/LICENSE").read_text())
        self.assertFalse((ROOT / "source/horizon-native.json").exists())

    def test_injection_targets_and_helpers_have_pinned_contract_evidence(self):
        evidence = json.loads((ROOT / "hook-contract.json").read_text())
        self.assertEqual(evidence["api"], 153)
        self.assertEqual(evidence["revision"], "e6e12d40c522b8f5ee8740dd861c96689023737a")
        manifest = (ROOT / "source/mixins/zoom/horizon-mixin.toml").read_text()
        targets = re.findall(r'^target = ".*::(native_\w+)"$', manifest, re.M)
        self.assertEqual(len(targets), 6)
        declarations = {item["name"]: item["declaration"] for item in evidence["declarations"]}
        for name in targets:
            self.assertIn("fn " + name + "(", declarations[name])
        for helper in re.findall(r'^(?:helper|source) = "([^"]+)"$', manifest, re.M):
            self.assertTrue((ROOT / "source/mixins/zoom" / helper).is_file(), helper)
        engine = evidence["native_zoom_now"]["source"]
        self.assertIn("self.scoping()", engine)
        self.assertIn("finite(z.factor, 1.0, 10.0)", engine)

    def test_status_is_source_only_and_local(self):
        status = json.loads((ROOT / "pilot-status.json").read_text())
        self.assertFalse(status["active"])
        self.assertFalse(status["target"]["build_verified"])
        self.assertEqual(status["checks"]["game_build"], "not run")
        self.assertEqual(status["checks"]["game_launch"], "not run")
        self.assertEqual(status["checks"]["benchmarks"], "not run")
        self.assertTrue(status["explicit_gaps"])


if __name__ == "__main__":
    unittest.main()
