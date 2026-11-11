"""Static archive and numerical contract checks; intentionally no GPU/compiler."""
import hashlib
import importlib.util
import random
import re
import unittest
from zipfile import ZipFile

from pathlib import Path
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prototype', HERE / 'build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PrototypeTests(unittest.TestCase):
    def test_source_preserved_and_build_deterministic(self):
        before = hashlib.sha256(builder.SOURCE.read_bytes()).digest()
        output = builder.OUT.read_bytes()
        builder.build()
        self.assertEqual(hashlib.sha256(builder.SOURCE.read_bytes()).digest(), before)
        self.assertEqual(builder.OUT.read_bytes(), output)
        self.assertEqual(builder.OUT.with_suffix('.zip.txt').read_bytes(), builder.OPTIONS.read_bytes())

    def test_archive_graph_and_unmodified_entries(self):
        with ZipFile(builder.SOURCE) as original, ZipFile(builder.OUT) as candidate:
            self.assertIsNone(candidate.testzip())
            modified = {'shaders/world0/deferred.fsh', 'shaders/shaders.properties'}
            for n in original.namelist():
                if not n.endswith('/') and n not in modified:
                    self.assertEqual(candidate.read(n), original.read(n), n)
            names = set(candidate.namelist())
            for n in names:
                if n.endswith(('.glsl', '.vsh', '.fsh')):
                    for include in re.findall(rb'#include\s+"(/[^\"]+)"', candidate.read(n)):
                        self.assertIn('shaders' + include.decode(), names, (n, include))
            properties = candidate.read('shaders/shaders.properties').decode()
            sizes = re.findall(r'^size\.buffer\.(\w+)=(.*)$', properties, re.M)
            self.assertEqual(sizes, [('colortex8', '0.5 0.5'), ('colortex9', '0.5 0.5')])
            self.assertNotIn('scale.', properties)
            self.assertIn(b'DRAWBUFFERS:89', candidate.read('shaders/common/m1_half_fragment.glsl'))
            self.assertIn(b'DRAWBUFFERS:14', candidate.read('shaders/common/m1_upsample_fragment.glsl'))
            self.assertNotIn(b'gl_FragData', candidate.read('shaders/common/m1_evaluate.glsl'))
            self.assertIn(b'const int colortex8Format = RGBA16F;', candidate.read('shaders/common/m1_half_fragment.glsl'))
            self.assertIn(b'const int colortex9Format = R32F;', candidate.read('shaders/common/m1_half_fragment.glsl'))

    def test_affine_contract_preserves_full_resolution_source(self):
        # Independent reference to MakeUp's boost -> cloud mix -> AO sequence.
        # Same coefficients must transfer from a sampled sky to any sharp sky source.
        rng = random.Random(9106)
        for _ in range(2000):
            sample, source, cloud = [[rng.uniform(0, 50) for _ in range(3)] for _ in range(3)]
            boost, opacity, ao = rng.uniform(1, 1.3), rng.random(), rng.uniform(.3, 1)
            half_result = [(v * boost * (1-opacity) + c * opacity) * ao for v, c in zip(sample, cloud)]
            multiplier = boost * (1-opacity) * ao
            additive = [v - s * multiplier for v, s in zip(half_result, sample)]
            reconstructed = [v * multiplier + a for v, a in zip(source, additive)]
            reference = [(v * boost * (1-opacity) + c * opacity) * ao for v, c in zip(source, cloud)]
            for a, b in zip(reconstructed, reference):
                self.assertAlmostEqual(a, b, places=11)


if __name__ == '__main__':
    unittest.main()
