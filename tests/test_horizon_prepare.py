import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location("horizon_prepare", Path(__file__).resolve().parents[1] / "tools/prepare-horizon.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "app.zip"
        self.dest = self.root / "staged"

    def test_regular_files_and_executable_permissions(self):
        with zipfile.ZipFile(self.archive, "w") as z:
            info = zipfile.ZipInfo("Horizon.app/Contents/MacOS/launcher")
            info.external_attr = 0o100755 << 16
            z.writestr(info, b"not executed")
        installer.extract_archive(self.archive, self.dest)
        binary = self.dest / "Horizon.app/Contents/MacOS/launcher"
        self.assertEqual(binary.read_bytes(), b"not executed")
        self.assertEqual(binary.stat().st_mode & 0o777, 0o755)
        with self.assertRaises(ValueError):
            installer.extract_archive(self.archive, self.dest)

    def test_unsafe_entries_do_not_create_destination(self):
        for name in ("../outside", "/absolute", "A/../../outside", "A\\outside", "A/./B"):
            with zipfile.ZipFile(self.archive, "w") as z:
                z.writestr(name, "bad")
            with self.assertRaises(ValueError):
                installer.extract_archive(self.archive, self.dest)
            self.assertFalse(self.dest.exists())

    def test_symlinks_and_case_collisions_block(self):
        with zipfile.ZipFile(self.archive, "w") as z:
            info = zipfile.ZipInfo("link")
            info.external_attr = 0o120777 << 16
            z.writestr(info, "../outside")
        with self.assertRaises(ValueError):
            installer.extract_archive(self.archive, self.dest)
        with zipfile.ZipFile(self.archive, "w") as z:
            z.writestr("A", "one")
            z.writestr("a", "two")
        with self.assertRaises(ValueError):
            installer.extract_archive(self.archive, self.dest)
        self.assertFalse(self.dest.exists())


if __name__ == "__main__":
    unittest.main()
