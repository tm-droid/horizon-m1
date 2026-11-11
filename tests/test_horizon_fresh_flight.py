"""Fresh-flight evidence checks; no game, compiler or original save access."""
import importlib.util
from pathlib import Path
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("horizon_offline_fresh", ROOT / "tools/horizon-offline-test.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class FreshCorridorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.world = Path(self.temp.name)
        self.regions = self.world / "dimensions/minecraft/overworld/region"
        self.regions.mkdir(parents=True)

    def region(self, entries=(), size=12288):
        data = bytearray(size)
        for slot, offset, count in entries:
            data[slot * 4:slot * 4 + 4] = ((offset << 8) | count).to_bytes(4, "big")
        path = self.regions / "r.8.8.mca"
        path.write_bytes(data)
        return path

    def test_negative_chunk_coordinates_use_floor_and_region_local_slots(self):
        self.assertEqual(set(probe.fresh_corridor_chunks((-16, 95, -16), (0, 95, 0), margin=0)),
                         {(-1, -1), (-1, 0), (0, -1), (0, 0)})
        # Chunk(-1,-1) is slot1023 of region(-1,-1), not region(0,0).
        path = self.regions / "r.-1.-1.mca"
        data = bytearray(12288)
        data[4092:4096] = (513).to_bytes(4, "big")
        path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "already contains terrain"):
            probe.verify_fresh_corridor(self.world, [(-1, -1)])

    def test_absent_regions_and_empty_headers_are_fresh(self):
        self.assertTrue(probe.verify_fresh_corridor(self.world, [(256, 256)])["stored_corridor_absent_before_launch"])
        self.region(size=8192)
        check = probe.verify_fresh_corridor(self.world, [(256, 256)])
        self.assertEqual(sum(row["exists"] for row in check["region_headers"]), 1)
        self.assertEqual(check["chunks_checked"], 1)

    def test_existing_corridor_rejected_but_unrelated_slots_allowed(self):
        self.region([(1, 2, 1)])
        probe.verify_fresh_corridor(self.world, [(256, 256)])
        self.region([(0, 2, 1)])
        with self.assertRaisesRegex(ValueError, "already contains terrain"):
            probe.verify_fresh_corridor(self.world, [(256, 256)])

    def test_malformed_and_overlapping_location_tables_rejected(self):
        for entries, size in [([], 4096), ([], 8193), ([(1, 0, 1)], 12288),
                              ([(1, 2, 0)], 12288), ([(1, 3, 1)], 12288),
                              ([(1, 2, 1), (2, 2, 1)], 12288)]:
            with self.subTest(entries=entries, size=size):
                self.region(entries, size)
                with self.assertRaisesRegex(ValueError, "Malformed"):
                    probe.verify_fresh_corridor(self.world, [(256, 256)])

    def test_legacy_region_and_external_data_cannot_hide_existing_terrain(self):
        legacy = self.world / "region"
        legacy.mkdir()
        self.region([(0, 2, 1)]).rename(legacy / "r.8.8.mca")
        with self.assertRaisesRegex(ValueError, "already contains terrain"):
            probe.verify_fresh_corridor(self.world, [(256, 256)])
        (legacy / "r.8.8.mca").unlink()
        (self.regions / "c.256.256.mcc").write_bytes(b"orphan")
        with self.assertRaisesRegex(ValueError, "external chunk"):
            probe.verify_fresh_corridor(self.world, [(256, 256)])


class ConcurrentSamplingTests(unittest.TestCase):
    def test_status_is_sampled_while_deferred_flight_is_running(self):
        started, finish = threading.Event(), threading.Event()
        count = 0

        def ctl(*args, timeout):
            nonlocal count
            if args[0] == "fly":
                self.assertEqual(args[1:7], (*probe.FRESH_FROM, *probe.FRESH_TO))
                self.assertEqual(args[-1], "raw")
                started.set()
                if not finish.wait(1):
                    raise AssertionError("status was not sampled concurrently")
                return {"avg_fps": 42, "frame_ms": [20, 30], "cpu_ms": [2, 3], "gpu_ms": [17, 25]}
            self.assertEqual(args, ("status",))
            self.assertTrue(started.wait(1))
            count += 1
            if count == 2:
                finish.set()
            return {"streaming": {"decorating": count}, "pending_uploads": 3}

        phase = {}
        probe.sampled_fresh_flight(ctl, phase, interval=0.001)
        self.assertGreaterEqual(len(phase["status_timeline"]), 2)
        self.assertEqual(phase["measurement"]["frame_ms"], [20, 30])
        self.assertEqual(phase["measurement"]["cpu_ms"], [2, 3])
        self.assertEqual(phase["measurement"]["gpu_ms"], [17, 25])
        for sample in phase["status_timeline"]:
            self.assertLessEqual(sample["requested_seconds"], sample["received_seconds"])
        self.assertLessEqual(phase["request_started_seconds"], phase["wall_seconds"])

    def test_hopeless_threshold_preserves_boundary(self):
        self.assertTrue(probe.fresh_flight_hopeless({"avg_fps": 14.99}))
        self.assertFalse(probe.fresh_flight_hopeless({"avg_fps": 15}))


if __name__ == "__main__":
    unittest.main()
