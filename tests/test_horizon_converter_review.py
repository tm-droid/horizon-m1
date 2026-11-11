import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from horizon_converter_review import appearance_contract, classify_mod, group_findings, walk_reports


class ReviewTests(unittest.TestCase):
    def test_grouping_retains_every_line_with_bounded_samples(self):
        items = [{"subject": "mod-1", "code": "native-port-required", "severity": "warning",
                  "evidence": {"categories": ["input-reference"], "name": f"key{i}"}} for i in range(100)]
        items.append({"subject": "file/font.zip", "code": "font_ttf", "severity": "review"})
        grouped = group_findings(items, {"mod-1": classify_mod({"id": "zoomify"})})
        self.assertEqual(len(grouped), 2)
        self.assertEqual(sorted(line for group in grouped for line in group["raw_evidence_lines"]), list(range(1, 102)))
        inputs = next(g for g in grouped if g["feature"] == "input")
        self.assertEqual(inputs["finding_count"], 100)
        self.assertEqual(len(inputs["evidence_samples"]), 5)

    def test_errors_take_priority_and_keep_blocking_action(self):
        groups = group_findings([{"subject": "mod-1", "code": "FAILED", "severity": "error",
                                  "next_action": "Fix broken archive"}], {"mod-1": classify_mod({"id": "sodium"})})
        self.assertEqual(groups[0]["priority"], 0)
        self.assertEqual(groups[0]["status"], "blocked")

    def test_optimizer_classification_does_not_discard_features(self):
        for mod in ["sodium", "lithium", "ferritecore"]:
            row = classify_mod({"id": mod})
            self.assertEqual(row["role"], "java-engine-optimizer")
            self.assertTrue(row["java_installation_unchanged"])
            self.assertTrue(row["feature_review_required"])
            self.assertFalse(row["native_equivalence_verified"])
        for mod in ["iris", "entity_model_features", "entity_texture_features"]:
            self.assertEqual(classify_mod({"id": mod})["role"], "appearance-feature")

    def test_nested_traversal_keeps_chain_evidence(self):
        report = {"id": "root", "nested_jars": [{"report": {"id": "child", "archive_chain": ["a.jar"]}}]}
        self.assertEqual([r["id"] for r in walk_reports(report)], ["root", "child"])

    def test_appearance_contract_preserves_order_and_unverified_status(self):
        selected = ["vanilla", "file/B.zip", "file/A.zip"]
        packs = [{"selection": name, "order": i, "findings": []} for i, name in enumerate(selected)]
        contract = appearance_contract(selected, packs, None, [])
        self.assertEqual(contract["resourcepack_selection"], selected)
        self.assertEqual([p["selection"] for p in contract["layers"]], selected[1:])
        self.assertFalse(contract["runtime_visual_parity_verified"])


if __name__ == "__main__":
    unittest.main()
