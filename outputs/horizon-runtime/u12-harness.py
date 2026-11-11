#!/usr/bin/env python3
"""Wrapper: runs tools/horizon-offline-test.py unchanged, with native .hshader packs registered as extra --case values.
The harness stages SHADERS[case] from the Java instance's shaderpacks/ or game/shaderpacks/ into the profile and
selects it with `pickedShaderPack:<file>` in horizon-graphics.txt (run-u12-native-packs.py clones the files there)."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NATIVE = {"n-meridian": "meridian-26.3.1.hshader", "n-meridian-compat": "meridian_compat-26.3.1.hshader",
          "n-daybreak011": "daybreak-0.1.1.hshader", "n-daybreak020": "daybreak-0.2.0.hshader",
          "n-montarc": "montarc-1.1.1.hshader", "n-montarc-m1": "montarc-m1.hshader",
          "n-daybreak011-m1": "daybreak011-m1.hshader"}
spec = importlib.util.spec_from_file_location("horizon_offline_test", ROOT / "tools/horizon-offline-test.py")
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)
harness.SHADERS.update(NATIVE)
harness.SHADERS["makeup-m1"] = "MakeUp-M1-HalfRes.zip"
harness.SHADERS["makeup-m1r2"] = "MakeUp-M1-HalfRes-r2.zip"
raise SystemExit(harness.main())
