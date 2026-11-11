import contextlib
import hashlib
import importlib.util
import io
import json
import lzma
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("horizon_cli", TOOLS / "horizon-convert.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def archive(path, members):
    with zipfile.ZipFile(path, "w") as out:
        for name, value in members.items():
            out.writestr(name, json.dumps(value) if isinstance(value, dict) else value)


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.game = self.root / "instance/minecraft"
        for name in ("mods", "resourcepacks", "shaderpacks", "config"):
            (self.game / name).mkdir(parents=True)
        self.selected = ["vanilla", "file/second.zip", "file/first.zip"]
        self.set_options(self.selected)
        for name in ("first.zip", "second.zip"):
            archive(self.game / "resourcepacks" / name, {
                "pack.mcmeta": {"pack": {"description": name, "min_format": [97, 1], "max_format": [97, 1]}},
                "assets/minecraft/lang/en_us.json": {"test": name},
            })
        archive(self.game / "mods/example.jar", {"fabric.mod.json": {
            "schemaVersion": 1, "id": "example", "name": "Example", "version": "1.0",
            "depends": {"fabricloader": ">=0.19.5"}}, "assets/example/lang/en_us.json": {"key": "value"}})
        archive(self.game / "mods/disabled.jar.disabled", {"fabric.mod.json": {"id": "disabled"}})
        self.out = self.root / "migration"

    def set_options(self, selected):
        (self.game / "options.txt").write_text("resourcePacks:" + json.dumps(selected) + "\nrenderDistance:12\n")

    def run_cli(self, stage=False, runtime_manifest=None, carry_assets=False):
        with contextlib.redirect_stdout(io.StringIO()):
            return cli.run(self.game, self.out, stage, carry_assets, runtime_manifest)

    def manifest(self):
        return json.loads((self.out / "manifest.json").read_text())

    def runtime_record(self, revision=cli.REVISION, api=153, **overrides):
        record = {"runtime_revision": revision, "native_hooks_api": api,
                  "hook_api_evidence": {"url": f"https://github.com/horizon-rust/horizon/blob/{revision}/crates/horizon-client/src/game/native_hooks.rs",
                                        "verification": "verified"},
                  "assetdigest": {"sha256": "a" * 64, "status": "declared-verified"}, "status": "installed"}
        record.update(overrides)
        path = self.root / "runtime-record.json"
        path.write_text(json.dumps(record))
        return path

    def runtime_issues(self):
        return {item.get("issue") for item in
                (json.loads(line) for line in (self.out / "raw-review-queue.jsonl").read_text().splitlines())
                if item.get("code") == "RUNTIME_PROVENANCE_REVIEW"}

    def test_full_preparation_preserves_order_bytes_and_source(self):
        before = {str(p): p.read_bytes() for p in self.game.rglob("*") if p.is_file()}
        self.assertEqual(self.run_cli(True), 0)
        manifest = self.manifest()
        self.assertEqual(manifest["resourcepack_selection"], self.selected)
        self.assertEqual([p["selection"] for p in manifest["resourcepacks"]], self.selected)
        self.assertEqual(manifest["active_mod_count"], 1)
        self.assertEqual(manifest["disabled_mods"], ["disabled.jar.disabled"])
        self.assertTrue(manifest["source_unchanged"])
        self.assertFalse(manifest["java_behavior_converted"])
        self.assertFalse(manifest["runtime_visual_parity_verified"])
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.game.rglob("*") if p.is_file()})
        for name in ("first.zip", "second.zip"):
            self.assertEqual((self.out / "resourcepacks" / name).read_bytes(), (self.game / "resourcepacks" / name).read_bytes())
        graph = json.loads((self.out / "dependency-graph.json").read_text())
        self.assertEqual(graph["edges"][0]["to"], "fabricloader")
        self.assertTrue((self.out / "tasks/mod-0001.json").exists())

    def test_no_staging_or_execution_by_default(self):
        self.assertEqual(self.run_cli(), 0)
        self.assertFalse((self.out / "resourcepacks").exists())
        plan = json.loads((self.out / "upstream-plan.json").read_text())
        self.assertFalse(plan["executed"])
        self.assertNotIn("port", [part for argv in plan["commands"] for part in argv])
        self.assertEqual(plan["commands"][1][-1], "--offline")

    def test_absent_runtime_is_explicit_not_inferred_from_research(self):
        self.assertEqual(self.run_cli(), 0)
        provenance = self.manifest()["runtime_provenance"]
        self.assertEqual(provenance["status"], "runtime-unspecified")
        self.assertIsNone(provenance["selected_runtime"])
        self.assertFalse(provenance["native_compatibility_verified"])
        self.assertIn("runtime-unspecified", self.runtime_issues())
        task = json.loads((self.out / "tasks/mod-0001.json").read_text())
        self.assertEqual(task["runtime_provenance"]["status"], "runtime-unspecified")

    def test_matching_source_record_still_does_not_prove_runtime_compatibility(self):
        path = self.runtime_record()
        self.assertEqual(self.run_cli(runtime_manifest=path), 0)
        provenance = self.manifest()["runtime_provenance"]
        self.assertEqual(provenance["status"], "research-source-match-runtime-unverified")
        self.assertTrue(provenance["revision_matches_research"])
        self.assertTrue(provenance["host_api_matches_research"])
        self.assertTrue(provenance["hook_api_evidence_complete"])
        self.assertFalse(provenance["native_compatibility_verified"])
        self.assertEqual(provenance["input_manifest"]["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(provenance["selected_runtime"]["assetdigest"]["status"], "declared-verified")
        self.assertEqual(json.loads((self.out / "runtime-provenance.json").read_text()), provenance)
        self.assertIn("native-runtime-validation-pending", self.runtime_issues())

    def test_different_runtime_retains_research_and_allows_asset_exports(self):
        revision = "c9d474dd9116e84c243f8992d75c11314df56f06"
        path = self.runtime_record(revision, 80)
        self.assertEqual(self.run_cli(True, path, True), 0)
        manifest = self.manifest()
        provenance = manifest["runtime_provenance"]
        research = "e6e12d40c522b8f5ee8740dd861c96689023737a"
        self.assertEqual(provenance["status"], "requires-target-hook-review")
        self.assertEqual(provenance["selected_runtime"]["runtime_revision"], revision)
        self.assertEqual(provenance["research"], {"horizon_revision": research, "native_hooks_api": 153})
        self.assertEqual(manifest["horizon_revision"], research)
        self.assertFalse(provenance["native_compatibility_verified"])
        self.assertTrue(manifest["source_unchanged"])
        self.assertTrue({"research-revision-differs", "research-host-api-differs"} <= self.runtime_issues())
        task = json.loads((self.out / "tasks/mod-0001.json").read_text())
        plan = json.loads((self.out / "upstream-plan.json").read_text())
        self.assertEqual(task["target"]["horizon_revision"], research)
        self.assertEqual(plan["revision"], research)
        self.assertEqual(plan["runtime_provenance"]["selected_runtime_revision"], revision)
        self.assertFalse(plan["selected_runtime_commands_verified"])
        for name in ("first.zip", "second.zip"):
            self.assertEqual((self.out / "resourcepacks" / name).read_bytes(), (self.game / "resourcepacks" / name).read_bytes())
        with zipfile.ZipFile(self.game / "mods/example.jar") as source, zipfile.ZipFile(self.out / "mod-asset-packs/mod-0001.zip") as carried:
            self.assertEqual(source.read("assets/example/lang/en_us.json"), carried.read("assets/example/lang/en_us.json"))
        hooks = cli.candidate_hooks({"classes": [{"source_entry": "sample/Input.class",
                                    "relevant_references": [{"categories": ["input-reference"]}]}]})
        self.assertIn(f"/blob/{research}/", hooks[0]["source"])
        self.assertEqual(hooks[0]["source_host_native_hooks_api"], 153)
        self.assertIsNone(hooks[0]["minimum_required_hooks_api"])
        self.assertEqual(hooks[0]["selected_runtime_validation"], "unverified")

    def test_boolean_verification_marker_is_declaration_not_native_validation(self):
        path = self.runtime_record(hook_api_evidence={
            "url": f"https://raw.githubusercontent.com/horizon-rust/horizon/{cli.REVISION}/crates/horizon-client/src/game/native_hooks.rs",
            "verification": True})
        provenance, reviews = cli.runtime_provenance(path)
        self.assertTrue(provenance["hook_api_evidence_complete"])
        self.assertFalse(provenance["native_compatibility_verified"])
        self.assertEqual(reviews[0]["issue"], "native-runtime-validation-pending")

    def test_runtime_source_url_requires_revision_in_supported_route(self):
        revision = cli.REVISION
        source = "crates/horizon-client/src/game/native_hooks.rs"
        pinned = [f"https://github.com/horizon-rust/horizon/blob/{revision}/{source}#L1050",
                  f"https://github.com/horizon-rust/horizon/raw/{revision}/{source}",
                  f"https://raw.githubusercontent.com/horizon-rust/horizon/{revision}/{source}",
                  f"https://api.github.com/repos/horizon-rust/horizon/contents/{source}?ref={revision}"]
        mutable = [f"https://github.com/horizon-rust/horizon/blob/main/{source}?sha={revision}",
                   f"https://github.com/horizon-rust/horizon/blob/main/{source}#{revision}",
                   f"https://raw.githubusercontent.com/horizon-rust/horizon/main/{source}?ref={revision}",
                   f"https://raw.githubusercontent.com/horizon-rust/horizon/main/{source}#{revision}",
                   f"https://api.github.com/repos/horizon-rust/horizon/contents/{source}?sha={revision}",
                   f"https://api.github.com/repos/horizon-rust/horizon/contents/{source}?ref=main#{revision}",
                   f"https://api.github.com/repos/horizon-rust/horizon/contents/{source}?ref={revision}&ref=main"]
        for url in pinned + mutable:
            with self.subTest(url=url):
                path = self.runtime_record(hook_api_evidence={"url": url, "verification": "verified"})
                provenance, reviews = cli.runtime_provenance(path)
                self.assertEqual(provenance["hook_api_evidence_complete"], url in pinned)
                self.assertFalse(provenance["native_compatibility_verified"])
                self.assertEqual(provenance["status"], "research-source-match-runtime-unverified"
                                 if url in pinned else "runtime-evidence-incomplete")
                self.assertEqual(any(item["issue"] == "runtime-hook-evidence-incomplete" for item in reviews),
                                 url in mutable)

    def test_newer_staged_runtime_is_not_relabelled_or_blanket_rejected(self):
        revision = "f42ef42ef6ceccb3c6a20bea2481d87949a51c81"
        path = self.runtime_record(revision, 359, status="staged-not-prepared",
                                   runtime_release="nightly-2026-11-03-f42ef42", executed_game=False)
        provenance, reviews = cli.runtime_provenance(path)
        self.assertEqual(provenance["status"], "requires-target-hook-review")
        self.assertEqual(provenance["research"]["native_hooks_api"], 153)
        self.assertEqual(provenance["selected_runtime"]["native_hooks_api"], 359)
        self.assertEqual(provenance["selected_runtime"]["status"], "staged-not-prepared")
        self.assertFalse(provenance["selected_runtime"]["executed_game"])
        self.assertFalse(provenance["native_compatibility_verified"])
        api_review = next(item for item in reviews if item["issue"] == "research-host-api-differs")
        self.assertIn("not a rejection", api_review["reason"])

    def test_missing_or_unverified_api_evidence_is_review_not_asset_blocker(self):
        cases = [{"native_hooks_api": None}, {"native_hooks_api": True}, {"hook_api_evidence": None},
                 {"hook_api_evidence": {"url": f"https://github.com/horizon-rust/horizon/blob/{cli.REVISION}/crates/horizon-client/src/game/native_hooks.rs",
                                        "verification": "unverified"}},
                 {"hook_api_evidence": {"url": "https://github.com/horizon-rust/horizon/blob/main/crates/horizon-client/src/game/native_hooks.rs",
                                        "verification": True}}]
        for i, overrides in enumerate(cases):
            with self.subTest(overrides=overrides):
                self.out = self.root / f"migration-evidence-{i}"
                path = self.runtime_record(**overrides)
                self.assertEqual(self.run_cli(True, path), 0)
                provenance = self.manifest()["runtime_provenance"]
                self.assertEqual(provenance["status"], "runtime-evidence-incomplete")
                self.assertFalse(provenance["hook_api_evidence_complete"])
                self.assertIn("runtime-hook-evidence-incomplete", self.runtime_issues())
                self.assertEqual((self.out / "resourcepacks/first.zip").read_bytes(), (self.game / "resourcepacks/first.zip").read_bytes())

    def test_unreadable_runtime_record_does_not_stop_source_asset_preparation(self):
        path = self.root / "missing-runtime.json"
        self.assertEqual(self.run_cli(True, path), 0)
        self.assertEqual(self.manifest()["runtime_provenance"]["status"], "runtime-evidence-incomplete")
        self.assertIn("runtime-manifest-unreadable", self.runtime_issues())
        self.assertTrue(self.manifest()["source_unchanged"])
        self.assertTrue((self.out / "resourcepacks/first.zip").exists())

    def test_missing_pack_is_blocker_not_silent_drop(self):
        self.set_options(["file/missing.zip"])
        self.assertEqual(self.run_cli(True), 2)
        self.assertEqual(self.manifest()["resourcepacks"][0]["status"], "blocked")
        self.assertTrue(self.manifest()["source_unchanged"])

    def test_unsafe_selection_and_source_output_overlap_rejected(self):
        for name in ("file/../outside.zip", "file/a/b.zip", "file/C:\\outside.zip"):
            self.set_options([name])
            with self.assertRaises(ValueError):
                self.run_cli(True)
            self.assertFalse(self.out.exists())
        self.set_options(self.selected)
        with self.assertRaises(ValueError):
            cli.run(self.game, self.game / "output", False)
        with self.assertRaises(ValueError):
            cli.run(self.game, self.game.parent, False)

    def test_existing_output_not_overwritten(self):
        self.out.mkdir()
        sentinel = self.out / "keep.txt"
        sentinel.write_text("keep")
        with self.assertRaises(ValueError):
            self.run_cli()
        self.assertEqual(sentinel.read_text(), "keep")

    def test_active_shader_and_override_preserved(self):
        shader = self.game / "shaderpacks/Mellow.zip"
        archive(shader, {"shaders/shaders.properties": "screen=TEST\n", "shaders/final.fsh": "void main(){}"})
        shader.with_name("Mellow.zip.txt").write_text("SMAA=true\n")
        (self.game / "config/iris.properties").write_text("enableShaders=true\nshaderPack=Mellow.zip\n")
        self.assertEqual(self.run_cli(True), 0)
        self.assertEqual((self.out / "shader-source/Mellow.zip").read_bytes(), shader.read_bytes())
        self.assertEqual((self.out / "shader-source/Mellow.zip.txt").read_text(), "SMAA=true\n")
        self.assertEqual(self.manifest()["shader"]["status"], "shader-runtime-parity-unverified")

    def test_source_change_invalidates_output(self):
        original = cli.analyze_mod

        def mutate(path):
            result = original(path)
            (self.game / "options.txt").write_text("resourcePacks:[]\n")
            return result

        with patch.object(cli, "analyze_mod", side_effect=mutate):
            self.assertEqual(self.run_cli(), 2)
        self.assertFalse(self.manifest()["source_unchanged"])
        self.assertEqual(self.manifest()["status"], "incomplete")

    def test_missing_fabric_metadata_still_gets_manual_task(self):
        archive(self.game / "mods/example.jar", {"not-fabric.txt": "manual"})
        self.assertEqual(self.run_cli(), 0)
        self.assertTrue((self.out / "tasks/mod-0001.json").exists())
        self.assertIn("JAVA_PORT_REVIEW", (self.out / "review-queue.jsonl").read_text())

    def test_corrupt_pack_and_mod_report_incomplete(self):
        (self.game / "resourcepacks/first.zip").write_bytes(b"broken zip")
        (self.game / "mods/example.jar").write_bytes(b"broken jar")
        self.assertEqual(self.run_cli(), 2)
        self.assertEqual(self.manifest()["status"], "incomplete")
        self.assertEqual(self.manifest()["resourcepacks"][2]["status"], "blocked")

    def test_fifo_and_oversized_sources_rejected_before_hashing(self):
        fifo = self.game / "mods/blocked.jar"
        os.mkfifo(fifo)
        with self.assertRaises(ValueError):
            self.run_cli()
        self.assertFalse(self.out.exists())
        fifo.unlink()
        with patch.object(cli, "MAX_SOURCE_FILE", 1):
            with self.assertRaises(ValueError):
                self.run_cli()

    def test_lzma_member_failure_becomes_blocked_layer(self):
        original = cli.inspect_pack

        def corrupt(path):
            if path.name == "first.zip":
                raise lzma.LZMAError("corrupt compression stream")
            return original(path)

        with patch.object(cli, "inspect_pack", side_effect=corrupt):
            self.assertEqual(self.run_cli(), 2)
        self.assertEqual(self.manifest()["resourcepacks"][2]["status"], "blocked")

    def test_mod_asset_conversion_integrated_with_manual_tasks(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.run(self.game, self.out, False, True), 0)
        manifest = self.manifest()
        self.assertEqual(manifest["mod_assets_carried"], 1)
        task = json.loads((self.out / "tasks/mod-0001.json").read_text())
        self.assertEqual(task["asset_carry"]["status"], "assets-only-runtime-unverified")
        with zipfile.ZipFile(self.out / "mod-asset-packs/mod-0001.zip") as pack:
            self.assertIn("assets/example/lang/en_us.json", pack.namelist())
            self.assertNotIn("fabric.mod.json", pack.namelist())

    def test_missing_active_shader_creates_priority_zero_blocker(self):
        (self.game / "config/iris.properties").write_text("enableShaders=true\nshaderPack=missing.zip\n")
        self.assertEqual(self.run_cli(), 2)
        tasks = [json.loads(line) for line in (self.out / "review-queue.jsonl").read_text().splitlines()]
        blocker = next(t for t in tasks if "SHADER_SCAN_OR_STAGE_FAILED" in t["codes"])
        self.assertEqual(blocker["priority"], 0)
        self.assertEqual(blocker["status"], "blocked")

    def test_source_settings_and_grouped_queue_are_auditable(self):
        config = self.game / "config/zoomify.json"
        config.write_text('{"zoomKey": "c", "factor": 4}')
        self.assertEqual(self.run_cli(), 0)
        manifest = self.manifest()
        self.assertIn("config/zoomify.json", manifest["source_before"])
        self.assertEqual((self.out / "source-settings/config/zoomify.json").read_bytes(), config.read_bytes())
        raw = (self.out / "raw-review-queue.jsonl").read_text().splitlines()
        tasks = [json.loads(line) for line in (self.out / "review-queue.jsonl").read_text().splitlines()]
        self.assertEqual(sorted(n for t in tasks for n in t["raw_evidence_lines"]), list(range(1, len(raw) + 1)))
        appearance = json.loads((self.out / "appearance-contract.json").read_text())
        self.assertFalse(appearance["runtime_visual_parity_verified"])

    def test_f42_preflights_use_effective_pack_order_and_preserve_source_bytes(self):
        revision = "f42ef42ef6ceccb3c6a20bea2481d87949a51c81"
        self.set_options(self.selected)
        with (self.game / "options.txt").open("a") as stream:
            stream.write("version:5023\nfov:0.625\ncloudRange:64\n")
        gamma = self.game / "config/gammautils.json"
        gamma.write_text('{"gamma":{"value":15.0},"resetOnClose":false}')
        prefix = "assets/minecraft/optifine/cem/"
        archive(self.game / "resourcepacks/second.zip", {
            "pack.mcmeta": {"pack": {"description": "lower", "pack_format": 97}},
            prefix + "chest.jem": {"models": [{"part": "root", "model": "anim.jpm"}]},
            prefix + "anim.jpm": {"animations": [{"root.rx": "height_above_ground"}]},
        })
        archive(self.game / "resourcepacks/first.zip", {
            "pack.mcmeta": {"pack": {"description": "higher", "pack_format": 97}},
            prefix + "anim.jpm": {"animations": [{"root.rx": "fluid_depth_up"}]},
        })
        before = {str(path): path.read_bytes() for path in self.game.rglob("*") if path.is_file()}
        self.assertEqual(self.run_cli(True, self.runtime_record(revision, 359)), 0)
        settings = json.loads((self.out / "native-settings-candidate.json").read_text())
        self.assertEqual(settings["fields"]["fov"]["typed_value"], 95)
        self.assertIn("fov:0.625\n", (self.out / "native-options-candidate.txt").read_text())
        self.assertNotIn("gamma:", settings["candidate_text"])
        self.assertTrue(any(gap["code"] == "brightness-modifier-runtime-review" for gap in settings["gaps"]))
        self.assertEqual((self.out / "source-settings/config/gammautils.json").read_bytes(), gamma.read_bytes())
        cem = json.loads((self.out / "native-cem-preflight.json").read_text())
        reads = {item["matched"] for item in cem["findings"] if item["rule"] == "cem.stubbed-parameter-read"}
        self.assertEqual(reads, {"fluid_depth_up"})
        self.assertFalse(cem["runtime_parity_verified"])
        self.assertEqual(before, {str(path): path.read_bytes() for path in self.game.rglob("*") if path.is_file()})
        for name in ("first.zip", "second.zip"):
            self.assertEqual((self.out / "resourcepacks" / name).read_bytes(), (self.game / "resourcepacks" / name).read_bytes())
        raw = [json.loads(line) for line in (self.out / "raw-review-queue.jsonl").read_text().splitlines()]
        self.assertTrue(any(item["code"] == "NATIVE_CEM_REVIEW" and item["evidence_file"] == "native-cem-preflight.json" for item in raw))


if __name__ == "__main__":
    unittest.main()
