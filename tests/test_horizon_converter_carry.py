"""Local fixture tests for inert asset carry; never execute JAR contents."""
import hashlib
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from horizon_converter_carry import carry_mod_assets
from horizon_converter_packs import PackSafetyError


class CarryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def jar(self, entries, name="mod.jar"):
        source = self.root / name
        with zipfile.ZipFile(source, "w") as archive:
            for key, value in entries:
                archive.writestr(key, value)
        return source

    def test_carry_only_assets_with_source_proof_and_licenses(self):
        binary = b"\x89PNG\x00\xff original quality"
        source = self.jar([
            ("assets/example/textures/item/test.png", binary),
            ("assets/example/models/item/test.json", b'{"parent":"minecraft:item/generated"}'),
            ("assets/example/hidden.class", b"not converted"),
            ("assets/example/nested.jar", b"not converted"),
            ("data/example/recipes/test.json", b"{}"),
            ("Main.class", b"code"), ("META-INF/jars/dep.jar", b"nested"),
            ("fabric.mod.json", b'{"id":"example","entrypoints":{"main":["Main"]}}'),
            ("META-INF/LICENSE.txt", b"license original\r\n"),
            ("NOTICE", b"notice"),
        ])
        before = source.read_bytes()
        dest = self.root / "converted.zip"
        result = carry_mod_assets(source, dest)
        self.assertEqual(result["status"], "assets-only-runtime-unverified")
        self.assertEqual(result["asset_count"], 2)
        self.assertEqual(result["omitted_code_count"], 2)
        self.assertEqual(result["omitted_data_count"], 1)
        self.assertEqual(result["omitted_nested_jar_count"], 2)
        self.assertTrue(result["manual_activation_required"])
        self.assertTrue(result["manual_ordering_required"])
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(result["source_sha256"], hashlib.sha256(before).hexdigest())
        with zipfile.ZipFile(dest) as converted:
            self.assertEqual(converted.namelist(), sorted(converted.namelist()))
            self.assertEqual(converted.read("assets/example/textures/item/test.png"), binary)
            self.assertEqual(converted.read("source-licenses/META-INF/LICENSE.txt"), b"license original\r\n")
            self.assertTrue(all(not name.endswith((".class", ".jar")) and not name.startswith("data/") for name in converted.namelist()))
            self.assertNotIn("fabric.mod.json", converted.namelist())
            metadata = json.loads(converted.read("pack.mcmeta"))
            self.assertEqual(metadata["pack"]["min_format"], [97, 1])
            self.assertEqual(metadata["pack"]["max_format"], [97, 1])
            self.assertNotIn("pack_format", metadata["pack"])
            provenance = json.loads(converted.read("conversion-provenance.json"))
            self.assertEqual(provenance["source_sha256"], hashlib.sha256(before).hexdigest())
            records = {r["path"]: r for r in provenance["entries"]}
            self.assertEqual(records["assets/example/textures/item/test.png"]["sha256"], hashlib.sha256(binary).hexdigest())
            self.assertTrue(all(i.date_time == (1980, 1, 1, 0, 0, 0) for i in converted.infolist()))

    def test_vanilla_override_unknown_namespace_and_metadata_review(self):
        source = self.jar([("assets/minecraft/models/item/apple.json", b"{}"),
                           ("assets/unknown/textures/test.png.mcmeta", b'{"animation":{"interpolate":true}}'),
                           ("assets/unknown/models/bad.json", b"{")])
        result = carry_mod_assets(source, self.root / "output.zip")
        codes = {f["code"] for f in result["findings"]}
        self.assertTrue({"minecraft_overrides", "namespace_review", "texture_interpolation", "invalid_json"} <= codes)
        with zipfile.ZipFile(result["destination"]) as converted:
            self.assertEqual(converted.read("assets/unknown/models/bad.json"), b"{")

    def test_case_distinct_classes_and_libipn_assets_preserved(self):
        aliases = ["assets/libipn/libIPN-logo.png", "assets/libipn/libipn-logo.png"]
        source = self.jar([("A.class", b"upper code"), ("a.class", b"lower code"),
                           *[(name, b"same PNG bytes") for name in aliases]])
        result = carry_mod_assets(source, self.root / "libipn.zip")
        self.assertEqual(result["omitted_code_count"], 2)
        self.assertEqual(result["asset_count"], 2)
        findings = [f for f in result["findings"] if f["code"] == "path_alias_review"]
        self.assertEqual({f["path"] for f in findings}, set(aliases))
        with zipfile.ZipFile(result["destination"]) as converted:
            for name in aliases:
                self.assertEqual(converted.read(name), b"same PNG bytes")
            self.assertNotIn("A.class", converted.namelist())
            self.assertNotIn("a.class", converted.namelist())
            provenance = json.loads(converted.read("conversion-provenance.json"))
            self.assertEqual(provenance["carried_assets"], sorted(aliases))
            self.assertEqual([f for f in provenance["findings"] if f["code"] == "path_alias_review"], findings)

    def test_source_pack_metadata_preserved_and_semantics_flagged(self):
        metadata = b'{ "pack":{"pack_format":75}, "filter":{"block":[]}, "overlays":{"entries":[{"directory":"variant","formats":75}]} }\r\n'
        source = self.jar([("pack.mcmeta", metadata),
                           ("assets/example/base.json", b"{}"),
                           ("variant/assets/example/changed.json", b"{}"),
                           ("variant/assets/example/texture.png", b"PNG")])
        result = carry_mod_assets(source, self.root / "overlay.zip")
        codes = {f["code"] for f in result["findings"]}
        self.assertTrue({"omitted_source_pack_metadata", "omitted_source_filter", "omitted_source_overlays", "omitted_overlay_assets"} <= codes)
        self.assertEqual(result["omitted_overlay_asset_count"], 2)
        self.assertEqual(result["omitted_overlay_asset_paths"], ["variant/assets/example/changed.json", "variant/assets/example/texture.png"])
        with zipfile.ZipFile(result["destination"]) as converted:
            self.assertEqual(converted.read("source-metadata/pack.mcmeta"), metadata)
            self.assertNotIn("variant/assets/example/changed.json", converted.namelist())
            provenance = json.loads(converted.read("conversion-provenance.json"))
            self.assertEqual(provenance["preserved_source_metadata"], ["pack.mcmeta"])
            self.assertEqual(provenance["omitted_overlay_asset_count"], 2)
            self.assertEqual(json.loads(converted.read("pack.mcmeta"))["pack"]["min_format"], [97, 1])

    def test_no_assets_does_not_create_output(self):
        source = self.jar([("Main.class", b"code"), ("data/test/file.json", b"{}"), ("LICENSE", b"license")])
        dest = self.root / "none.zip"
        result = carry_mod_assets(source, dest)
        self.assertEqual(result["status"], "no-assets")
        self.assertIsNone(result["destination"])
        self.assertFalse(dest.exists())

    def test_reject_unsafe_duplicate_and_symlink_archives(self):
        link = zipfile.ZipInfo("assets/test/link")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        cases = [[("../escape", "bad")], [(link, "../outside")],
                 [("assets/test/a", "one"), ("assets/test/a", "two")]]
        for index, entries in enumerate(cases):
            with self.subTest(index=index), warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                source = self.jar(entries, f"bad{index}.jar")
                dest = self.root / f"bad{index}.zip"
                with self.assertRaises(PackSafetyError):
                    carry_mod_assets(source, dest)
                self.assertFalse(dest.exists())

    def test_no_overwrite_or_source_overlap(self):
        source = self.jar([("assets/test/file.txt", "asset")])
        with self.assertRaises(PackSafetyError):
            carry_mod_assets(source, source)
        with self.assertRaises(PackSafetyError):
            carry_mod_assets(source, self.root)
        dest = self.root / "existing.zip"
        dest.write_bytes(b"keep")
        with self.assertRaises(FileExistsError):
            carry_mod_assets(source, dest)
        self.assertEqual(dest.read_bytes(), b"keep")

    def test_output_is_deterministic(self):
        source = self.jar([("assets/test/z.bin", b"last"), ("assets/test/a.bin", b"first")])
        first, second = self.root / "first.zip", self.root / "second.zip"
        carry_mod_assets(source, first)
        carry_mod_assets(source, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_failed_copy_cleans_output(self):
        source = self.jar([("assets/test/file.bin", b"asset")])
        dest = self.root / "failed.zip"
        with patch("horizon_converter_carry.shutil.copyfileobj", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                carry_mod_assets(source, dest)
        self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
