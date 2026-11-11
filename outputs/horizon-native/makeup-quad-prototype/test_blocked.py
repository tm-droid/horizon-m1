import hashlib
from pathlib import Path
import subprocess
import sys
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


class BlockedDraftTest(unittest.TestCase):
    def test_no_unsafe_pack_can_be_built(self):
        source=ROOT/'instances/Tanush-26.3/minecraft/shaderpacks/MakeUp-UltraFast-9.6.zip'
        packs=ROOT/'outputs/horizon-runtime/game/shaderpacks'
        expected={source:'71319ea5d0ad114143ef1c334890e315dbf1eeb2318d6bc35f3e5021fb3c8ba8',
                  packs/'MakeUp-M1-HalfRes.zip':'bccebddd85c1e19926cc882c386ff3aa45e0104be3c3814ac21fa05ab6271ac8',
                  packs/'MakeUp-M1-HalfRes-r2.zip':'fb8872de0fd2c2bb901d6e892bee81855e507dbaeb5e3d2b5bc0401723f9643b'}
        result=subprocess.run([sys.executable,str(HERE/'build.py')],capture_output=True,text=True)
        self.assertEqual(result.returncode,1)
        self.assertIn('BLOCKED:',result.stderr)
        self.assertIn('#error M1_QUAD_DRAFT_BLOCKED', (HERE/'quad_cloud.glsl').read_text())
        self.assertFalse((packs/'MakeUp-M1-Quad.zip').exists())
        self.assertFalse((packs/'MakeUp-M1-Quad.zip.txt').exists())
        for path,digest in expected.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),digest,str(path))


if __name__=='__main__':
    unittest.main()
