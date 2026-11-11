"""Audited source examples; no installed-game access or runtime execution."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("lantern_compat", ROOT / "tools/horizon-lantern-compat.py")
compat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compat)
FIXTURES = ROOT / "outputs/horizon-native/lantern-compat-source/fixtures"


class LanternCompatTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        self.pack = self.inputs / "lanterns.zip"
        self.assets = self.inputs / "assets"
        shutil.copytree(FIXTURES / "vanilla-assets", self.assets)
        self.write_pack()
        self.output = self.root / "candidate"

    def write_pack(self, changes=None):
        members = {path.relative_to(FIXTURES / "pack").as_posix(): path.read_bytes()
                   for path in (FIXTURES / "pack").rglob("*") if path.is_file()}
        members.update(changes or {})
        with zipfile.ZipFile(self.pack, "w") as archive:
            for name, data in members.items():
                archive.writestr(name, data)

    def build(self, **kwargs):
        return compat.build_overlay(kwargs.get("pack", self.pack),
                                    kwargs.get("assets", self.assets),
                                    kwargs.get("output", self.output))

    def test_actual_children_only_add_texture_bindings_and_preserve_sources(self):
        original_pack = self.pack.read_bytes()
        originals = {name: (self.assets / "minecraft/models/block" / name).read_bytes()
                     for name in compat.CHILD_HASHES}
        report = self.build()
        with zipfile.ZipFile(self.output / "lantern-compat.zip") as archive:
            self.assertEqual(set(archive.namelist()), {"pack.mcmeta", *[compat.MODEL + name for name in originals]})
            for name, original in originals.items():
                before = json.loads(original)
                after = json.loads(archive.read(compat.MODEL + name))
                expected = json.loads(original)
                source, added = ("texture", "chain") if name == "iron_chain.json" else ("lantern", "hanging_lantern")
                expected["textures"].update({added: before["textures"][source], "particle": before["textures"][source]})
                self.assertEqual(after, expected)
                self.assertEqual((self.assets / "minecraft/models/block" / name).read_bytes(), original)
                self.assertEqual((self.output / "source-evidence/vanilla/minecraft/models/block" / name).read_bytes(), original)
            metadata = json.loads(archive.read("pack.mcmeta"))["pack"]
            self.assertEqual([metadata[k] for k in ["pack_format", "min_format", "max_format"]], [97, 97, 97])
        self.assertEqual(self.pack.read_bytes(), original_pack)
        self.assertEqual(report["status"], "candidate-not-activated")
        self.assertFalse(report["runtime_visual_parity_verified"])
        self.assertEqual(len(report["changes"]), 3)

    def test_source_template_child_and_metadata_drift_refused_before_output(self):
        for name in compat.PACK_HASHES:
            with self.subTest(member=name):
                original = (FIXTURES / "pack" / name).read_bytes()
                self.write_pack({name: original + b" "})
                with self.assertRaisesRegex(ValueError, "Source drift"):
                    self.build()
                self.assertFalse(self.output.exists())
        self.write_pack()
        child = self.assets / "minecraft/models/block/iron_chain.json"
        child.write_bytes(child.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "Source drift"):
            self.build()
        self.assertFalse(self.output.exists())

    def test_new_child_override_and_duplicate_known_member_refused(self):
        self.write_pack({compat.MODEL + "iron_chain.json": b"{}"})
        with self.assertRaisesRegex(ValueError, "overrides a target child"):
            self.build()
        self.write_pack()
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.pack, "a") as archive:
                archive.writestr("pack.mcmeta", (FIXTURES / "pack/pack.mcmeta").read_bytes())
        with self.assertRaisesRegex(ValueError, "Expected one source member"):
            self.build()

    def test_fresh_disjoint_output_and_symlink_inputs(self):
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError, "fresh"):
            self.build()
        self.output.rmdir()
        with self.assertRaisesRegex(ValueError, "disjoint"):
            self.build(output=self.assets / "candidate")
        with self.assertRaisesRegex(ValueError, "disjoint"):
            self.build(output=self.inputs / "candidate")
        linked = self.root / "linked.zip"
        linked.symlink_to(self.pack)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            self.build(pack=linked)
        linked.unlink()
        linked.symlink_to(self.root / "missing", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            self.build(output=linked / "candidate")


if __name__ == "__main__":
    unittest.main()
