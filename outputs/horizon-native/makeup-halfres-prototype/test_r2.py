"""R2 archive isolation and numerical equivalence, no compiler or GPU."""
import hashlib
import math
import random
import unittest
from zipfile import ZipFile

import build
import build_r2


class R2Tests(unittest.TestCase):
    def test_r2_deterministic_and_r1_unchanged(self):
        r1_hash = hashlib.sha256(build.OUT.read_bytes()).hexdigest()
        self.assertEqual(r1_hash, 'bccebddd85c1e19926cc882c386ff3aa45e0104be3c3814ac21fa05ab6271ac8')
        first = build_r2.OUT.read_bytes()
        build_r2.build()
        self.assertEqual(build_r2.OUT.read_bytes(), first)
        self.assertEqual(hashlib.sha256(build.OUT.read_bytes()).hexdigest(), r1_hash)
        self.assertEqual(build_r2.OUT.with_suffix('.zip.txt').read_bytes(), build.OPTIONS.read_bytes())
        with ZipFile(build.OUT) as r1, ZipFile(build_r2.OUT) as r2:
            self.assertEqual(set(r1.namelist()), set(r2.namelist()))
            changed = {n for n in r1.namelist() if r1.read(n) != r2.read(n)}
            self.assertEqual(changed, {'M1-PROTOTYPE.md', 'shaders/common/m1_upsample_fragment.glsl'})
            self.assertIsNone(r2.testzip())

    def test_vector_gates_match_original_scalar_rules(self):
        rng = random.Random(729)
        near, far = .05, 384.
        def ld(d):
            return 2*near / (far+near-d*(far-near))
        for _ in range(10000):
            depth = rng.choice([rng.random(), 1.0, .56, .559999])
            guides = [rng.choice([depth, rng.random(), 1.0, .56]) for _ in range(4)]
            distance = ld(depth)*far*.5
            reference = all((ld(depth) > .9999) == (ld(g) > .9999)
                            and (depth < .56) == (g < .56)
                            and abs(ld(g)*far*.5-distance) <= max(.02,distance*.01)
                            for g in guides)
            sky = [ld(g) > .9999 for g in guides]
            hand = [g < .56 for g in guides]
            vector = ((all(sky) if ld(depth) > .9999 else not any(sky))
                      and (all(hand) if depth < .56 else not any(hand))
                      and all(abs(ld(g)*far*.5-distance) <= max(.02,distance*.01) for g in guides))
            self.assertEqual(reference, vector)

    def test_equal_depth_hardware_bilinear_contract_and_borders(self):
        # Reference full r1 manual-tap accumulation against separable bilinear
        # filtering, including one-pixel and odd framebuffer-derived sizes.
        rng = random.Random(812)
        for full_size in [(1, 1), (3, 5), (2560, 1600), (2559, 1599)]:
            width, height = [max(1, math.floor(v*.5)) for v in full_size]
            for uv in [(0, 0), (1, 1), (.000001, .999999)] + [(rng.random(),rng.random()) for _ in range(100)]:
                x, y = uv[0]*width-.5, uv[1]*height-.5
                ox, oy = math.floor(x), math.floor(y)
                bx, by = x-ox, y-oy
                def value(ix, iy):
                    ix, iy = min(width-1,max(0,ix)), min(height-1,max(0,iy))
                    return math.sin(ix*3.7+iy*.3)*50
                a,b,c,d = value(ox,oy),value(ox+1,oy),value(ox,oy+1),value(ox+1,oy+1)
                weights = [(1-bx)*(1-by),bx*(1-by),(1-bx)*by,bx*by]
                manual = sum(v*w for v,w in zip([a,b,c,d],weights))/sum(weights)
                hardware = ((1-bx)*a+bx*b)*(1-by)+((1-bx)*c+bx*d)*by
                self.assertAlmostEqual(manual, hardware, places=11)


if __name__ == '__main__':
    unittest.main()
