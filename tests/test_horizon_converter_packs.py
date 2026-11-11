"""Safety and content-proof fixtures; no installed packs or game access."""
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
import horizon_converter_packs as packs


class PackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def archive(self, entries, name="pack.zip"):
        path = self.root / name
        with zipfile.ZipFile(path, "w") as archive:
            for key, value in entries:
                archive.writestr(key, value)
        return path

    def test_inventory_and_evidence(self):
        source = self.archive([
            ("pack.mcmeta", json.dumps({"pack": {"pack_format": 75, "description": "original"}, "overlays": {"entries": []}, "filter": {}})),
            ("assets/minecraft/optifine/cem/cow.jem", "{}"),
            ("assets/minecraft/textures/block/fire.png.mcmeta", '{"animation":{"interpolate":true}}'),
            ("assets/minecraft/models/block/bad.json", "{"),
            ("assets/minecraft/optifine/emissive.properties", "suffix.emissive=_e"),
            ("assets/minecraft/textures/block/fire.png", b"\x89PNG untouched"),
            ("assets/minecraft/font/default.json", '{"providers":[{"type":"ttf","file":"test.ttf"}]}'),
            ("assets/minecraft/textures/gui/test.png.mcmeta", '{"texture":{"blur":false,"clamp":true}}'),
        ])
        report = packs.inspect_pack(source)
        codes = {f["code"] for f in report["findings"]}
        self.assertTrue({"custom_entity_model", "texture_interpolation", "invalid_json", "emissive_properties", "pack_overlays", "pack_filter", "truetype_font", "texture_blur", "texture_clamp"} <= codes)
        self.assertEqual(report["pack_mcmeta"]["pack"]["pack_format"], 75)
        self.assertEqual(report["namespaces"], {"minecraft": 7})
        self.assertEqual(report["files"], sorted(report["files"], key=lambda f: f["path"]))
        self.assertEqual(report["sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(report["content_sha256"], packs.inspect_pack(source)["content_sha256"])
        self.assertTrue(all({"code", "severity", "evidence", "reason", "next_action"} <= f.keys() for f in report["findings"]))

    def test_zip_staging_preserves_archive_bytes(self):
        source = self.archive([("pack.mcmeta", '{"pack":{"description":"no rewrite"}}'), ("other.bin", b"\x00\xff")])
        dest = self.root / "copy.zip"
        result = packs.stage_pack(source, dest)
        self.assertTrue(result["byte_preserved"])
        self.assertEqual(source.read_bytes(), dest.read_bytes())
        with self.assertRaises(FileExistsError):
            packs.stage_pack(source, dest)
        self.assertEqual(source.read_bytes(), dest.read_bytes())

    def test_nested_folder_copy_and_metadata(self):
        source = self.root / "folder"
        (source / "nested" / "assets" / "test" / "lang").mkdir(parents=True)
        (source / "nested" / "pack.mcmeta").write_bytes(b'{"pack":{"description":"nested"}}')
        (source / "nested" / "assets" / "test" / "lang" / "en_us.json").write_bytes(b'{"key":"value"}')
        before = packs.inspect_pack(source)
        self.assertIn("nested_pack_metadata", {f["code"] for f in before["findings"]})
        dest = self.root / "copy"
        result = packs.stage_pack(source, dest)
        self.assertEqual(before["content_sha256"], result["content_sha256"])
        self.assertEqual((source / "nested/pack.mcmeta").read_bytes(), (dest / "nested/pack.mcmeta").read_bytes())

    def test_unsafe_paths_and_collisions(self):
        for index, name in enumerate(("../escape", "/absolute", "C:/drive", "assets\\escape", "a/./b", "a//b")):
            with self.subTest(name=name):
                source = self.archive([(name, "unsafe")], f"bad{index}.zip")
                with self.assertRaises(packs.PackSafetyError):
                    packs.stage_pack(source, self.root / f"out{index}.zip")
                self.assertFalse((self.root / f"out{index}.zip").exists())
        for index, entries in enumerate(([('a', 'one'), ('a', 'two')], [('a', 'file'), ('a/b', 'child')], [('a/', ''), ('a', 'file')])):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                source = self.archive(entries, f"collision{index}.zip")
            with self.assertRaises(packs.PackSafetyError):
                packs.inspect_pack(source)

    def test_zip_case_and_normalization_aliases_preserved(self):
        source = self.archive([("A.class", b"upper"), ("a.class", b"lower"),
                               ("é", b"one"), ("e\u0301", b"two"),
                               ("Parent", b"file"), ("parent/child", b"child")])
        report = packs.inspect_pack(source)
        self.assertEqual(report["file_count"], 6)
        aliases = [f for f in report["findings"] if f["code"] == "path_alias_review"]
        self.assertEqual({f["path"] for f in aliases}, {"A.class", "a.class", "é", "e\u0301"})
        dest = self.root / "aliases.zip"
        packs.stage_pack(source, dest)
        self.assertEqual(source.read_bytes(), dest.read_bytes())

    def test_folder_staging_rejects_case_aliases(self):
        source = self.root / "case-folder"
        source.mkdir()
        (source / "A").write_bytes(b"upper")
        (source / "a").write_bytes(b"lower")
        if len(list(source.iterdir())) != 2:
            self.skipTest("Source filesystem cannot represent case aliases")
        dest = self.root / "case-copy"
        with self.assertRaises(packs.PackSafetyError):
            packs.stage_pack(source, dest)
        self.assertFalse(dest.exists())

    def test_symlink_archive_and_folder(self):
        link = zipfile.ZipInfo("link")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        source = self.archive([(link, "../outside")])
        with self.assertRaises(packs.PackSafetyError):
            packs.inspect_pack(source)
        folder = self.root / "folder"
        folder.mkdir()
        (folder / "link").symlink_to(source)
        with self.assertRaises(packs.PackSafetyError):
            packs.inspect_pack(folder)

    def test_overlap_and_limits(self):
        folder = self.root / "folder"
        folder.mkdir()
        (folder / "pack.mcmeta").write_text('{}')
        with self.assertRaises(packs.PackSafetyError):
            packs.stage_pack(folder, folder / "copy")
        with self.assertRaises(packs.PackSafetyError):
            packs.stage_pack(folder, self.root)
        with patch.object(packs, "MAX_FILES", 0):
            with self.assertRaises(packs.PackSafetyError):
                packs.inspect_pack(folder)
        source = self.archive([("pack.mcmeta", '{"pack":{"description":"long"}}')])
        with patch.object(packs, "MAX_METADATA_BYTES", 2):
            report = packs.inspect_pack(source)
            self.assertIn("metadata_limit", {f["code"] for f in report["findings"]})
        with patch.object(packs, "MAX_TOTAL_BYTES", 2):
            with self.assertRaises(packs.PackSafetyError):
                packs.inspect_pack(source)

    def test_failed_copy_is_removed(self):
        source = self.archive([("pack.mcmeta", '{}')])
        dest = self.root / "failed.zip"
        with patch.object(packs.shutil, "copyfileobj", side_effect=OSError("disk failure")):
            with self.assertRaisesRegex(OSError, "disk failure"):
                packs.stage_pack(source, dest)
        self.assertFalse(dest.exists())
        self.assertTrue(source.exists())


if __name__ == "__main__":
    unittest.main()
