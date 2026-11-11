"""Namespace reachability and the opt-in v4 prune; synthetic migrations only, no game or runtime access."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import horizon_converter_packs as packs
import horizon_converter_prune as prune

PNG = b"\x89PNG fixture "


def blockstate(model):
    return json.dumps({"variants": {"": {"model": model}}})


class PruneTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.src = self.root / "v3"
        (self.src / "resourcepacks").mkdir(parents=True)
        (self.src / "mod-asset-packs").mkdir()
        self.zip(self.src / "mod-asset-packs/mod-0001.zip", {"assets/carried/models/block/x.json": "{}"})
        base = {"pack.mcmeta": json.dumps({"pack": {"pack_format": 75, "description": "a"}})}
        shadowed = {"assets/minecraft/textures/entity/dead%02d.png" % i: PNG + bytes([i]) for i in range(30)}
        a = dict(base)
        a.update({
            "assets/minecraft/blockstates/rail.json": blockstate("priv:block/rail"),
            "assets/priv/models/block/rail.json": json.dumps({"textures": {"all": "priv:block/rail"}}),
            "assets/priv/textures/block/rail.png": PNG + b"base",
            "assets/priv/textures/block/rail_e.png": PNG + b"glow",
            "assets/priv/textures/block/unused.png": PNG + b"unused",
            "assets/deadmod/models/block/x.json": json.dumps({"textures": {"all": "priv:block/rail"}}),
            "assets/deadmod/textures/block/x.png": PNG + b"dead",
            "assets/deadmod/optifine/ctm/x/connect.properties": "matchBlocks=deadmod:x\n",
            "assets/deadmod/lang/en_us.json": json.dumps({"block.deadmod.x": "X"}),
            "assets/langns/lang/en_us.json": json.dumps({"block.deadmod.x": "X", "item.minecraft.stick": "Stick"}),
            "assets/skyns/optifine/sky/world0/sky1.properties": "source=skyns:day.png\n",
            "assets/skyns/day.png": PNG + b"sky",
            "assets/minecraft/textures/entity/keep.png": PNG + b"keep",
        })
        a.update(shadowed)
        b = dict(base)
        b.update({"assets/minecraft/textures/entity/dead%02d.png" % i: PNG + b"new" + bytes([i]) for i in range(30)})
        self.zip(self.src / "resourcepacks/a.zip", a)
        self.zip(self.src / "resourcepacks/b.zip", b)
        entries = [{"order": 0, "selection": "vanilla", "staged": False}]
        for order, name in ((1, "a.zip"), (2, "b.zip")):
            report = packs.inspect_pack(self.src / "resourcepacks" / name)
            report.update({"order": order, "selection": "file/" + name, "staged": True, "status": "preserved",
                           "staging": {"destination": str(self.src / "resourcepacks" / name), "sha256": report["sha256"],
                                       "content_sha256": report["content_sha256"], "file_count": report["file_count"],
                                       "byte_preserved": True}})
            entries.append(report)
        (self.src / "manifest.json").write_text(json.dumps({"resourcepacks": entries, "status": "prepared"}))
        (self.src / "upstream-plan.json").write_text(json.dumps({"cmd": [str(self.src)]}))
        self.before = self.digest_tree(self.src)

    def zip(self, path, members):
        with zipfile.ZipFile(path, "w") as archive:
            for name, data in members.items():
                archive.writestr(name, data)

    def digest_tree(self, root):
        return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(root.rglob("*")) if p.is_file()}

    def test_reachability(self):
        ns = prune.analyze(self.src)["namespaces"]
        self.assertTrue(ns["priv"]["reachable"])
        self.assertFalse(ns["deadmod"]["reachable"])
        self.assertTrue(ns["langns"]["reachable"], "lang file with a vanilla key is merged globally")
        self.assertTrue(ns["skyns"]["reachable"])
        self.assertNotIn("carried", ns)
        self.assertEqual(self.digest_tree(self.src), self.before, "analysis must be read-only")

    def test_derive_removes_only_dead_namespace_and_trim_files(self):
        dest = self.root / "v4"
        record = prune.derive(self.src, dest, min_free=0)
        self.assertEqual(self.digest_tree(self.src), self.before, "source migration untouched")
        manifest = json.loads((dest / "manifest.json").read_text())
        names = {n for e in manifest["resourcepacks"] if "files" in e for n in (f["path"] for f in e["files"])}
        self.assertFalse([n for n in names if "/deadmod/" in n])
        self.assertIn("assets/priv/textures/block/unused.png", names)
        with zipfile.ZipFile(dest / "resourcepacks/a.zip") as archive:
            self.assertEqual(set(archive.namelist()) - {n for n in archive.namelist() if n.endswith("/")}, {
                n for n in names if n in archive.namelist()} | {n for n in archive.namelist() if not n.endswith("/") and n not in names})
            self.assertIsNone(archive.testzip())
            self.assertFalse([n for n in archive.namelist() if "deadmod" in n or "entity/dead" in n])
        entry = next(e for e in manifest["resourcepacks"] if e.get("name") == "a.zip")
        again = packs.inspect_pack(dest / "resourcepacks/a.zip")
        self.assertEqual(entry["sha256"], again["sha256"])
        self.assertEqual(entry["content_sha256"], again["content_sha256"])
        self.assertTrue(entry["staging"]["destination"].startswith(str(dest)))
        self.assertEqual(manifest["resourcepacks"][2]["staging"]["destination"], str(dest / "resourcepacks/b.zip"))
        self.assertEqual(self.digest_tree(self.src)["resourcepacks/b.zip"], self.digest_tree(dest)["resourcepacks/b.zip"])
        changes = manifest["v4_changes"]
        listed = {p for item in changes["removed"] for p in item["paths"]}
        self.assertEqual(len(listed), changes["removed_file_count"])
        self.assertIn("assets/deadmod/models/block/x.json", listed)
        self.assertEqual(sum(1 for p in listed if "entity/dead" in p), 30)
        self.assertTrue(all(item["reason"] for item in changes["removed"]))
        self.assertEqual(changes["effective_map_check"]["changed_or_lost_in_kept_namespaces"], 0)
        self.assertEqual(record["removed_file_count"], changes["removed_file_count"])
        self.assertIn(str(dest), (dest / "upstream-plan.json").read_text())

    def test_strict_mode_drops_unreached_private_files(self):
        dest = self.root / "v4s"
        prune.derive(self.src, dest, prune_unreached_files=True, min_free=0)
        with zipfile.ZipFile(dest / "resourcepacks/a.zip") as archive:
            names = set(archive.namelist())
        self.assertNotIn("assets/priv/textures/block/unused.png", names)
        self.assertIn("assets/priv/textures/block/rail.png", names)
        self.assertIn("assets/priv/textures/block/rail_e.png", names, "emissive overlay follows its reached base")

    def test_refuses_existing_destination_and_low_disk(self):
        dest = self.root / "v4"
        dest.mkdir()
        with self.assertRaises(FileExistsError):
            prune.derive(self.src, dest, min_free=0)
        with self.assertRaises(OSError):
            prune.derive(self.src, self.root / "other", min_free=1 << 62)
        self.assertFalse((self.root / "other").exists())

    def test_default_converter_still_requires_game_dir(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools/horizon-convert.py"), "--output", str(self.root / "o")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--game-dir", result.stderr)


if __name__ == "__main__":
    unittest.main()
