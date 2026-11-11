"""Small declarative CEM fixtures; never access an installed game or pack."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import horizon_converter_cem as cem

BASE = "assets/minecraft/optifine/cem/"
EMF = "assets/minecraft/emf/cem/"


def model(expr="age", target="body.rx", **entry):
    return {"models": [{"part": "body", "id": "body", "animations": [{target: expr}], **entry}]}


class CemTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sequence = 0

    def pack(self, entries, *, metadata=None):
        self.sequence += 1
        path = self.root / f"pack{self.sequence}.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("pack.mcmeta", json.dumps(metadata or {"pack": {"description": "fixture"}}))
            for name, value in entries.items():
                if not name.startswith("assets/"):
                    name = BASE + name
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                archive.writestr(name, value)
        return path

    def analyze(self, packs, revision=cem.REVISION, **kwargs):
        return cem.analyze_cem_packs(packs, revision, **kwargs)

    def rules(self, report):
        return [item["rule"] for item in report["findings"]]

    def gaps(self, report):
        return {item["code"] for item in report["coverage_gaps"]}

    def test_exact_expression_reads_and_source_bytes(self):
        path = self.pack({"cow.jem": model("if(is_child, height_above_ground, fluid_depth_up)")})
        before = path.read_bytes()
        result = self.analyze([path])
        self.assertEqual({f["matched"] for f in result["findings"]}, cem.STUBS)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(result["packs"][0]["sha256"], hashlib.sha256(before).hexdigest())
        self.assertFalse(result["runtime_parity_verified"])
        self.assertTrue(all(not f["binding_verified"] for f in result["findings"]))
        self.assertTrue(all(cem.REVISION in f["native_source"] for f in result["findings"]))

    def test_qualified_substrings_and_function_names_are_not_bare_reads(self):
        path = self.pack({"cow.jem": model("var.height_above_ground + fluid_depth_up_extra + custom:height_above_ground + height_above_ground()")})
        self.assertEqual(self.analyze([path])["findings"], [])

    def test_metadata_and_unconsumed_placements_are_not_expressions(self):
        doc = model()
        doc["credit"] = "height_above_ground render.shadow_size"
        doc["animations"] = [{"body.rx": "height_above_ground"}]
        doc["models"][0]["animations"] = [{"#comment": "fluid_depth_up", "credit": "height_above_ground"}]
        doc["models"][0]["submodels"] = [{"animations": [{"body.tx": "fluid_depth_up"}]}]
        result = self.analyze([self.pack({"cow.jem": doc})])
        self.assertEqual(result["findings"], [])
        self.assertTrue({"root-animation-scope", "nested-consumption-unverified"} <= self.gaps(result))

    def test_render_writes_not_reads_or_wrong_namespaces(self):
        doc = model()
        doc["models"][0]["animations"] = [{"render.shadow_size": 0.5, "body.visible": True,
                                              "var.render": 1, "body.rx": "render.shadow_size",
                                              "render.foo.bar": "age"}]
        result = self.analyze([self.pack({"cow.jem": doc})])
        writes = [f for f in result["findings"] if f["rule"] == "cem.render-property-write-unused"]
        self.assertEqual([f["matched"] for f in writes], ["render.shadow_size"])

    def test_unsupported_quoted_expression_is_a_gap_not_a_token_scan(self):
        result = self.analyze([self.pack({"cow.jem": model('print("height_above_ground")')})])
        self.assertEqual(result["findings"], [])
        self.assertIn("expression-lexical-scope", self.gaps(result))

    def test_cross_pack_import_and_shared_evidence_consumers(self):
        low = self.pack({"shared.jpm": {"animations": [{"body.rx": "height_above_ground"}]}})
        high = self.pack({name: {"models": [{"part": "body", "model": "shared.jpm"}]}
                          for name in ["cow.jem", "pig.jem"]})
        result = self.analyze([low, high])
        self.assertEqual(result["unresolved_dependencies"], [])
        self.assertEqual(len(result["findings"]), 1)
        finding = result["findings"][0]
        self.assertEqual(finding["source"]["pack"], str(low))
        self.assertEqual({c["model"] for c in finding["consumers"]}, {"cow", "pig"})
        self.assertTrue(all(len(c["chain"]) == 2 for c in finding["consumers"]))

    def test_later_pack_overrides_import_without_flagging_shadowed_bytes(self):
        low = self.pack({"shared.jpm": {"animations": [{"body.rx": "height_above_ground"}]}})
        high = self.pack({"shared.jpm": {"animations": [{"body.rx": "age"}]},
                          "cow.jem": {"models": [{"part": "body", "model": "shared.jpm"}]}})
        result = self.analyze([low, high])
        self.assertEqual(result["findings"], [])
        self.assertTrue(any(r["pack"] == str(low) for r in result["shadowed_resources"]))

    def test_own_empty_or_null_animations_mask_import(self):
        for masked in ([], None):
            with self.subTest(masked=masked):
                path = self.pack({"shared.jpm": {"animations": [{"body.rx": "height_above_ground"}]},
                                  "cow.jem": {"models": [{"part": "body", "model": "shared.jpm", "animations": masked}]}})
                self.assertEqual(self.analyze([path])["findings"], [])

    def test_first_earlier_base_id_wins(self):
        doc = {"models": [{"id": "base", "part": "body", "animations": []},
                          {"id": "base", "part": "body", "animations": [{"body.rx": "height_above_ground"}]},
                          {"part": "body", "baseId": "base"}]}
        result = self.analyze([self.pack({"cow.jem": doc})])
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual([c["model_index"] for c in result["findings"][0]["consumers"]], [1])

    def test_missing_base_id_remains_visible(self):
        result = self.analyze([self.pack({"cow.jem": model(baseId="later")})])
        self.assertIn("base-id-unresolved", self.gaps(result))

    def test_external_chest_animations_not_chest_boat_prefix(self):
        doc = {"models": [{"part": "base", "model": "animations.jpm"}]}
        result = self.analyze([self.pack({"animations.jpm": {"animations": [{"base.rx": "age"}]},
                                          "chest.jem": doc, "chest_boat.jem": doc})])
        findings = [f for f in result["findings"] if f["rule"] == "cem.block-entity-animation-not-applied"]
        self.assertEqual(len(findings), 1)
        self.assertEqual([c["model"] for c in findings[0]["consumers"]], ["chest"])
        self.assertEqual(findings[0]["source"]["path"], BASE + "animations.jpm")

    def test_bed_and_cart_use_other_renderers_without_consuming_jem_animations(self):
        lower = self.pack({"minecart.jem": model("age")})
        upper = self.pack({"minecart.jem": model("height_above_ground"),
                           "chest_minecart.jem": model("render.shadow_size"),
                           "hopper_minecart.jem": {"models": []},
                           "hopper_minecart.properties": "models.1=2",
                           "bed.jem": model("age"),
                           "minecart_helper.jem": model("age")})
        for budget in (0, cem.MAX_TOTAL_WORK):
            with self.subTest(budget=budget), patch.object(cem, "MAX_TOTAL_WORK", budget):
                result = self.analyze([lower, upper])
                findings = {item["matched"]: item for item in result["findings"]}
                self.assertEqual({stem: item["rule"] for stem, item in findings.items()},
                                 {"bed": "cem.bed-model-not-applied", "minecart": "cem.minecart-model-not-applied",
                                  "chest_minecart": "cem.minecart-model-not-applied",
                                  "hopper_minecart": "cem.minecart-model-not-applied"})
                self.assertEqual(findings["minecart"]["source"]["pack"], str(upper))
                self.assertEqual(findings["bed"]["consumers"][0]["renderer"], "terrain-block-model")
        self.assertEqual(self.analyze([upper], revision="different")["findings"], [])

    def test_selector_rule_number_is_not_model_index(self):
        path = self.pack({"villager.jem": model(), "villager.properties": "models.104=1\nmodels.2=1 1\nmodels.3=1-1\n"})
        self.assertNotIn("cem.alternate-model-selection", self.rules(self.analyze([path])))

    def test_block_entity_part_and_alias_uncertainty_are_not_confirmed_consumption(self):
        path = self.pack({"chest.jem": model(part="not_a_chest_part"),
                          "book.jem": model(part="pages_right"),
                          "enchanting_book.jem": {"models": []},
                          "lectern_book.jem": {"models": []}})
        result = self.analyze([path])
        self.assertNotIn("cem.block-entity-animation-not-applied", self.rules(result))
        self.assertTrue({"block-entity-part-unverified", "block-entity-alias-binding-unverified"} <= self.gaps(result))

    def test_book_fallback_is_selected_per_native_consumer(self):
        for preferred, expected in (("enchanting_book", "lectern_book"),
                                    ("lectern_book", "book")):
            with self.subTest(preferred=preferred):
                result = self.analyze([self.pack({"book.jem": model(part="root"),
                                                  preferred + ".jem": {"models": []}})])
                findings = [f for f in result["findings"]
                            if f["rule"] == "cem.block-entity-animation-not-applied"]
                self.assertEqual(len(findings), 1)
                self.assertEqual(findings[0]["consumers"][0]["native_block_entity_targets"], [expected])

    def test_root_is_native_supported_for_all_block_entity_targets(self):
        for stem in ("banner_base", "banner_flag", "banner", "conduit", "decorated_pot", "book"):
            with self.subTest(stem=stem):
                result = self.analyze([self.pack({stem + ".jem": model(part="root")})])
                self.assertIn("cem.block-entity-animation-not-applied", self.rules(result))
                self.assertNotIn("block-entity-part-unverified", self.gaps(result))

    def test_banner_fallback_does_not_bind_a_base_part_to_flag_consumer(self):
        result = self.analyze([self.pack({"banner.jem": model(part="stand"),
                                          "banner_base.jem": {"models": []}})])
        self.assertNotIn("cem.block-entity-animation-not-applied", self.rules(result))
        self.assertIn("block-entity-alias-binding-unverified", self.gaps(result))

    def test_alternate_selector_values_and_large_ranges_are_not_expanded(self):
        path = self.pack({"happy_ghast.jem": model(),
                          "happy_ghast.properties": "models.1=104\nmodels.2=1-2147483647\nnames.1=opaque condition\n"})
        result = self.analyze([path])
        choices = [f for f in result["findings"] if f["rule"] == "cem.alternate-model-selection"]
        self.assertEqual(len(choices), 2)
        self.assertEqual(choices[1]["matched"], [[1, 2147483647]])
        self.assertTrue(all(f["impact"] == "conditional" for f in choices))

    def test_selector_invalid_duplicates_and_continuations_are_gaps(self):
        for text, code in [("models.1=0", "properties-selector-unverified"),
                           ("models.1=2-1", "properties-selector-unverified"),
                           ("models.1=1\nmodels.1=2", "properties-duplicate-selector"),
                           ("models\\.1=2", "properties-syntax-unverified"),
                           ("names.1=abc\\\nmodels.1=2", "properties-syntax-unverified")]:
            with self.subTest(text=text):
                result = self.analyze([self.pack({"cow.jem": model(), "cow.properties": text})])
                self.assertNotIn("cem.alternate-model-selection", self.rules(result))
                self.assertIn(code, self.gaps(result))

    def test_native_emf_and_flat_candidate_priority(self):
        path = self.pack({BASE + "cow.jem": model("height_above_ground"),
                          EMF + "cow/cow.jem": model("fluid_depth_up"), EMF + "cow.jem": model()})
        result = self.analyze([path])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["models"][0]["source"]["path"], EMF + "cow.jem")

    def test_preferred_strict_parse_failure_does_not_invent_native_fallback(self):
        path = self.pack({EMF + "cow.jem": "{/* native parser unknown */}", BASE + "cow.jem": model("height_above_ground")})
        result = self.analyze([path])
        self.assertEqual(result["findings"], [])
        self.assertIn("parse-fallback-unverified", self.gaps(result))

    def test_missing_unsafe_and_nested_refs_are_not_recursive_native_imports(self):
        for ref in ("absent.jpm", "../outside.jpm"):
            result = self.analyze([self.pack({"cow.jem": model(model=ref)})])
            self.assertEqual(result["findings"], [])
            self.assertTrue({"unresolved-model-dependency", "model-reference-unverified"} & self.gaps(result))
        result = self.analyze([self.pack({"cow.jem": model(model="outer.jpm"),
                                          "outer.jpm": {"model": "inner.jpm"},
                                          "inner.jpm": {"animations": [{"body.rx": "height_above_ground"}]}})])
        self.assertIn("nested-import-unverified", self.gaps(result))
        self.assertEqual(result["findings"], [])

    def test_duplicate_json_keys_are_coverage_gaps(self):
        path = self.pack({"cow.jem": '{"models": [], "models": []}'})
        result = self.analyze([path])
        self.assertIn("strict-json-scope", self.gaps(result))
        self.assertEqual(result["findings"], [])

    def test_distinct_path_budget_is_not_discounted_by_content_hash(self):
        doc = {"models": [{"part": "body", "model": ref} for ref in ["one.jpm", "two.jpm"]]}
        imported = {"animations": [{"body.rx": "age"}]}
        root_size = len(json.dumps(doc).encode())
        imported_size = len(json.dumps(imported).encode())
        path = self.pack({"cow.jem": doc, "one.jpm": imported, "two.jpm": imported})
        with patch.object(cem, "MAX_MODEL_BYTES", root_size + imported_size):
            result = self.analyze([path])
        self.assertIn("analysis-model-byte-limit", self.gaps(result))
        self.assertEqual(result["models"][0]["native_distinct_path_bytes"], root_size + 2 * imported_size)

    def test_repeated_cached_animation_work_is_still_bounded(self):
        doc = {"models": [{"part": "body", "model": "shared.jpm"} for _ in range(3)]}
        path = self.pack({"cow.jem": doc, "shared.jpm": {"animations": [{"body.rx": "age + " + "1" * 100}]}})
        with patch.object(cem, "MAX_WORK", 180):
            result = self.analyze([path])
        self.assertIn("analysis-animation-limit", self.gaps(result))
        self.assertEqual(result["models"][0]["effective_assignment_occurrences"], 1)

    def test_rejected_targets_and_nonobjects_charge_work_before_filtering(self):
        for animations in ([0] * 1000, [{"unknown": "age"}] * 1000,
                           [{"#comment": "age"}] * 1000):
            with self.subTest(first=animations[0]):
                doc = {"models": [{"part": "body", "model": "shared.jpm"} for _ in range(1024)]}
                path = self.pack({"cow.jem": doc, "shared.jpm": {"animations": animations}})
                with patch.object(cem, "MAX_WORK", 100):
                    result = self.analyze([path])
                self.assertIn("analysis-animation-limit", self.gaps(result))
                self.assertLessEqual(result["counts"]["analysis_work_units"], 100)
                self.assertEqual(result["models"][0]["effective_assignment_occurrences"], 0)

    def test_raw_expression_cutoff_precedes_target_filtering(self):
        # Each rejected target is still one expression seen by compile_animation.
        animations = [{"x": 0}] * 4096 + [{"body.rx": "height_above_ground"}]
        path = self.pack({"cow.jem": {"models": [{"part": "body", "animations": animations}]}})
        result = self.analyze([path])
        self.assertNotIn("cem.stubbed-parameter-read", self.rules(result))
        self.assertIn("native-expression-limit", self.gaps(result))
        self.assertEqual(result["models"][0]["raw_expression_occurrences"], 4096)

    def test_raw_expression_cutoff_spans_inherited_applications(self):
        doc = {"models": [{"part": "body", "model": "shared.jpm"} for _ in range(5)] +
                         [{"part": "body", "animations": [{"body.rx": "height_above_ground"}]}]}
        path = self.pack({"cow.jem": doc, "shared.jpm": {"animations": [{"x": 0}] * 1024}})
        result = self.analyze([path])
        self.assertNotIn("cem.stubbed-parameter-read", self.rules(result))
        self.assertIn("native-expression-limit", self.gaps(result))
        self.assertEqual(result["models"][0]["raw_expression_occurrences"], 4096)

    def test_read_and_root_limits_stay_visible(self):
        path = self.pack({"cow.jem": model("height_above_ground"), "pig.jem": model("fluid_depth_up")})
        with patch.object(cem, "MAX_TOTAL_BYTES", 2):
            result = self.analyze([path])
        self.assertIn("analysis-read-limit", self.gaps(result))
        self.assertFalse(result["resource_view_verified"])
        with patch.object(cem, "MAX_ROOTS", 1):
            result = self.analyze([path])
        self.assertIn("analysis-root-limit", self.gaps(result))
        self.assertEqual(result["counts"]["skipped_models"], 1)
        with patch.object(cem, "MAX_TOTAL_WORK", 1):
            result = self.analyze([path])
        self.assertIn("analysis-global-work-limit", self.gaps(result))

    def test_unknown_runtime_and_overlays_do_not_become_clean_certificates(self):
        path = self.pack({"cow.jem": model("height_above_ground")}, metadata={"pack": {}, "overlays": {"entries": [{"directory": "overlay"}]}})
        result = self.analyze([path], revision="c9" * 20)
        self.assertEqual(result["status"], "target_capabilities_unverified")
        self.assertEqual(result["findings"], [])
        self.assertIn("pack-view-semantics-unverified", self.gaps(result))
        self.assertFalse(result["resource_view_verified"])

    def test_unsupported_folder_and_conflicting_zip_are_visible(self):
        result = self.analyze([self.root])
        self.assertIn("pack-catalogue-incomplete", self.gaps(result))
        path = self.root / "duplicate.zip"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(BASE + "cow.jem", "{}")
                archive.writestr(BASE + "cow.jem", "{}")
        result = self.analyze([path])
        self.assertIn("pack-catalogue-incomplete", self.gaps(result))


if __name__ == "__main__":
    unittest.main()
