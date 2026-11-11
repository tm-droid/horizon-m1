import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from horizon_converter_settings import build_settings_candidate, REVISION, MAX_BYTES


CURRENT = {
    "version": "5023", "fov": "0.625", "fovEffectScale": "1.0", "bobView": "true",
    "mouseSensitivity": "0.5", "entityDistanceScaling": "1.0", "particles": "0",
    "renderClouds": '"true"', "cloudRange": "64", "graphicsPreset": '"custom"',
    "mipmapLevels": "4", "entityShadows": "true", "renderDistance": "12",
    "simulationDistance": "8", "maxFps": "60", "enableVsync": "false",
}


class NativeSettingsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.options = self.root / "options.txt"
        self.gamma = self.root / "gammautils.json"
        self.write_options()

    def write_options(self, **changes):
        values = dict(CURRENT)
        for key, value in changes.items():
            if value is None:
                values.pop(key, None)
            else:
                values[key] = value
        self.options.write_text("\n".join(f"{key}:{value}" for key, value in values.items()) + "\n")

    def build(self, **kwargs):
        return build_settings_candidate(self.options, REVISION, **kwargs)

    def gap_keys(self, report, code):
        return {gap.get("key") for gap in report["gaps"] if gap["code"] == code}

    def test_current_values_transfer_verbatim_with_fov_file_api_distinction(self):
        original = self.options.read_bytes()
        report = self.build()
        self.assertEqual(report["fields"]["fov"]["typed_value"], 95)
        self.assertEqual(report["fields"]["fov"]["candidate_raw"], "0.625")
        for key, raw in CURRENT.items():
            self.assertIn(f"{key}:{raw}\n", report["candidate_text"])
        self.assertEqual(report["fields"]["renderClouds"]["typed_value"], "true")
        self.assertEqual(report["fields"]["cloudRange"]["typed_value"], 64)
        self.assertFalse(report["runtime_visual_parity_verified"])
        self.assertFalse(report["runtime_values_verified"])
        self.assertEqual(self.options.read_bytes(), original)
        self.assertEqual(report["source"]["sha256"], hashlib.sha256(original).hexdigest())

    def test_missing_gamma_is_not_replaced_or_fullbright_enabled(self):
        self.gamma.write_text(json.dumps({"gamma": {"value": 15.0, "resetOnClose": False}}))
        original = self.gamma.read_bytes()
        report = self.build(gammautils_path=self.gamma)
        self.assertNotIn("gamma:", report["candidate_text"])
        self.assertNotIn("fullbright", report["candidate_text"])
        self.assertIn("gamma", self.gap_keys(report, "source-option-missing"))
        self.assertIn("gamma", self.gap_keys(report, "brightness-modifier-runtime-review"))
        self.assertFalse(report["gammautils_evidence"]["rendered_brightness_state_verified"])
        self.assertEqual(self.gamma.read_bytes(), original)

    def test_invalid_gamma_and_quantized_caps_are_omitted_not_clamped(self):
        self.write_options(gamma="15.0", maxFps="125", entityDistanceScaling="1.1")
        report = self.build()
        self.assertEqual(self.gap_keys(report, "option-value-not-transferred"),
                         {"gamma", "maxFps", "entityDistanceScaling"})
        for key in ("gamma", "maxFps", "entityDistanceScaling"):
            self.assertNotIn(f"{key}:", report["candidate_text"])

    def test_api_fov_degrees_are_invalid_file_values(self):
        self.write_options(fov="95")
        report = self.build()
        self.assertIn("fov", self.gap_keys(report, "option-value-not-transferred"))
        self.assertNotIn("fov:", report["candidate_text"])

    def test_fractional_degree_fov_is_not_quietly_truncated(self):
        self.write_options(fov="0.63")
        report = self.build()
        self.assertIn("fov", self.gap_keys(report, "option-value-not-transferred"))

    def test_missing_wrong_or_non_integer_version_emits_no_candidate(self):
        for value in (None, "5022", "5023.0", "5023 ", "true", '"5023"'):
            with self.subTest(value=value):
                self.write_options(version=value)
                report = self.build()
                self.assertIsNone(report["candidate_text"])
                self.assertEqual(report["status"], "codec-context-unverified")
                self.assertFalse(any("typed_value" in item for item in report["fields"].values()))

    def test_unknown_runtime_is_not_relabelled_f42(self):
        report = build_settings_candidate(self.options, "c9d474dd9116e84c243f8992d75c11314df56f06")
        self.assertIsNone(report["candidate_text"])
        self.assertNotEqual(report["runtime_revision"], report["audited_revision"])

    def test_duplicate_option_never_chooses_a_value(self):
        self.options.write_text(self.options.read_text() + "fov:0.0\n")
        report = self.build()
        self.assertIn("fov", self.gap_keys(report, "duplicate-option-key"))
        self.assertNotIn("fov:", report["candidate_text"])

    def test_duplicate_version_prevents_candidate(self):
        self.options.write_text(self.options.read_text() + "version:5023\n")
        self.assertIsNone(self.build()["candidate_text"])

    def test_malformed_nonfinite_wrong_types_and_wrapping_ids_are_visible(self):
        self.write_options(fov="NaN", mouseSensitivity="1e999", bobView="1", particles="-1",
                           graphicsPreset='"not-real"', renderClouds='"invalid"')
        self.options.write_text(self.options.read_text() + "no separator\n")
        report = self.build()
        self.assertEqual(self.gap_keys(report, "option-value-not-transferred"),
                         {"fov", "mouseSensitivity", "bobView", "particles", "graphicsPreset", "renderClouds"})
        self.assertTrue(any(item["code"] == "malformed-option-line" for item in report["gaps"]))

    def test_unsigned_unit_negative_zero_is_not_accepted(self):
        self.write_options(gamma="-0.0")
        self.assertIn("gamma", self.gap_keys(self.build(), "option-value-not-transferred"))

    def test_unsupported_options_are_listed_not_copied_or_claimed_unsupported_native(self):
        self.write_options(ao="true", lastServer='"private.example"')
        report = self.build()
        self.assertEqual(report["omitted_keys"], ["ao", "lastServer"])
        self.assertNotIn("private.example", json.dumps(report))
        self.assertNotIn("ao:", report["candidate_text"])

    def test_duplicate_or_malformed_modifier_json_does_not_claim_brightness(self):
        for raw in ('{"gamma":{"value":1,"value":15}}', '{"gamma":{"value":1e999}}', '{broken', '[]'):
            with self.subTest(raw=raw):
                self.gamma.write_text(raw)
                report = self.build(gammautils_path=self.gamma)
                self.assertIn("gamma", self.gap_keys(report, "brightness-modifier-evidence-unreadable"))
                self.assertIsNotNone(report["candidate_text"])

    def test_missing_oversized_and_non_regular_sources_are_bounded(self):
        self.assertIsNone(build_settings_candidate(self.root / "missing", REVISION)["candidate_text"])
        self.options.write_bytes(b"x" * (MAX_BYTES + 1))
        self.assertEqual(self.build()["status"], "source-unreadable")
        self.assertEqual(build_settings_candidate(self.root, REVISION)["status"], "source-unreadable")


if __name__ == "__main__":
    unittest.main()
