"""Build a read-only, version-qualified partial native options candidate.

This audits canonical scalar forms of selected Java26.3 options against f42's
file codec. It does not apply presets, execute Horizon, or establish visual parity.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import stat

REVISION = "f42ef42ef6ceccb3c6a20bea2481d87949a51c81"
DATA_VERSION = 5023
HOOKS_API = 359
MAX_BYTES = 4 * 1024 * 1024
SOURCE = f"https://github.com/horizon-rust/horizon/blob/{REVISION}"
CODEC_URL = SOURCE + "/crates/horizon-client-render/src/options_file.rs#L314"

# This is intentionally smaller than Horizon's entire options schema.
SPECS = {
    "fov": ("fov",),
    "fovEffectScale": ("unit-square",),
    "bobView": ("bool",),
    "mouseSensitivity": ("unit",),
    "gamma": ("unit",),
    "entityDistanceScaling": ("quarter",),
    "particles": ("int", 0, 2),
    "renderClouds": ("enum", ("false", "fast", "true")),
    "cloudRange": ("int", 2, 128),
    "graphicsPreset": ("enum", ("fast", "fancy", "fabulous", "custom")),
    "mipmapLevels": ("int", 0, 4),
    "entityShadows": ("bool",),
    "renderDistance": ("int", 2, 128),
    "simulationDistance": ("int", 5, 32),
    "maxFps": ("frame-limit",),
    "enableVsync": ("bool",),
}


def _read(path):
    path = Path(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise ValueError("Input must be a bounded regular file")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("Input exceeded its byte limit while reading")
    finally:
        os.close(descriptor)
    return data.decode("utf-8"), {"path": str(path.absolute()), "sha256": hashlib.sha256(data).hexdigest()}


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def _json(raw):
    def reject_constant(value):
        raise ValueError(f"Non-finite JSON number: {value}")
    def finite_float(raw_value):
        value = float(raw_value)
        if not math.isfinite(value):
            raise ValueError("Non-finite JSON number")
        return value
    return json.loads(raw, object_pairs_hook=_object, parse_constant=reject_constant, parse_float=finite_float)


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Only a finite canonical numeric scalar is audited here")
    return value


def _typed(key, raw):
    value = _json(raw)
    spec = SPECS[key]
    kind = spec[0]
    if kind == "bool":
        if type(value) is not bool:
            raise ValueError("Expected a JSON boolean")
    elif kind == "enum":
        if type(value) is not str or value not in spec[1]:
            raise ValueError("Expected a supported quoted enum name")
    elif kind in ("int", "frame-limit"):
        if type(value) is not int:
            raise ValueError("Expected a canonical integer")
        low, high = (10, 260) if kind == "frame-limit" else spec[1:]
        if not low <= value <= high:
            raise ValueError(f"Outside native validated range {low}..{high}")
        if kind == "frame-limit" and value % 10:
            raise ValueError("Native validation would quantize this frame cap to a multiple of10")
    else:
        value = _number(value)
        if kind == "fov":
            degrees = value * 40.0 + 70.0
            if not math.isfinite(degrees) or not 30 <= degrees <= 110:
                raise ValueError("FOV file values are normalized, not API degrees")
            if degrees != int(degrees):
                raise ValueError("Native FOV decoding would truncate a fractional degree")
            value = int(degrees)
        elif kind == "quarter":
            if not 0.5 <= value <= 5:
                raise ValueError("Outside native entity-distance range0.5..5")
            if int(value * 4) / 4 != value:
                raise ValueError("Native validation would quantize entity distance to quarter steps")
        else:
            if not 0 <= value <= 1 or (value == 0 and math.copysign(1, value) < 0):
                raise ValueError("Outside the native unsigned unit-double range")
            if kind == "unit-square" and math.sqrt(value) ** 2 != value:
                raise ValueError("Native square-root validation changes this floating-point value")
    return value


def build_settings_candidate(options_path, runtime_revision, *, gammautils_path=None):
    """Return candidate text/evidence/gaps; never write or launch anything.

    Unknown options are listed by key only. Missing or unaudited values are not
    replaced with defaults. Candidate raw values retain their original spelling;
    Horizon may serialize them differently on exit.
    """
    report = {
        "schema": 1,
        "rule_set": "java26.3-f42-canonical-options-v1",
        "runtime_revision": runtime_revision,
        "audited_revision": REVISION,
        "audited_native_hooks_api": HOOKS_API,
        "source": None,
        "source_version": None,
        "fields": {},
        "omitted_keys": [],
        "gaps": [],
        "candidate_text": None,
        "runtime_values_verified": False,
        "runtime_visual_parity_verified": False,
        "qualification": "Partial file-codec candidate only; not a complete settings migration or visual-parity certificate.",
    }

    def gap(code, reason, *, key=None, line=None):
        entry = {"code": code, "reason": reason, "severity": "review"}
        if key is not None:
            entry["key"] = key
        if line is not None:
            entry["source_line"] = line
        report["gaps"].append(entry)

    try:
        text, report["source"] = _read(options_path)
    except (OSError, ValueError) as exc:
        report["status"] = "source-unreadable"
        gap("settings-source-unreadable", str(exc))
        return report

    entries = {}
    duplicates = set()
    for number, line in enumerate(text.splitlines(), 1):
        if not line:
            continue
        if ":" not in line:
            gap("malformed-option-line", "No option/value separator; line was not interpreted", line=number)
            continue
        key, raw = line.split(":", 1)
        if not key or key.strip() != key:
            gap("malformed-option-key", "Empty or noncanonical option key", line=number)
            continue
        if key in entries:
            duplicates.add(key)
            gap("duplicate-option-key", "Ambiguous duplicate option; no value selected", key=key, line=number)
        else:
            entries[key] = (raw, number)

    version = entries.get("version")
    if version and "version" not in duplicates:
        try:
            parsed = _json(version[0])
            if type(parsed) is int:
                report["source_version"] = parsed
        except (ValueError, RecursionError):
            pass
    # Native version parsing uses Java's integer parser, not the JSON codec.
    # Audit only its canonical spelling, so JSON whitespace cannot mask a fixer fallback.
    source_supported = (report["source_version"] == DATA_VERSION and
                        version is not None and version[0] == str(DATA_VERSION))
    target_supported = runtime_revision == REVISION
    if not source_supported:
        gap("source-options-version-unverified", "Only explicit source version5023 is audited; no version was inserted or upgraded", key="version")
    if not target_supported:
        gap("target-options-codec-unverified", "This option contract is pinned to f42; no other runtime was relabeled as compatible")

    report["omitted_keys"] = sorted(set(entries) - set(SPECS) - {"version"})
    if report["omitted_keys"]:
        gap("settings-outside-audited-bridge", "Listed omitted keys are outside this bridge's coverage; this is not proof that Horizon lacks them")

    candidate = [f"version:{version[0]}"] if source_supported and target_supported else []
    for key in SPECS:
        if key not in entries:
            gap("source-option-missing", "No source value was provided; no native default was invented", key=key)
            continue
        raw, line = entries[key]
        field = {"raw": raw, "source_line": line, "evidence_url": CODEC_URL,
                 "runtime_value_verified": False, "status": "not-transferred"}
        report["fields"][key] = field
        if key in duplicates:
            continue
        if not (source_supported and target_supported):
            field["status"] = "codec-context-unverified"
            continue
        try:
            typed = _typed(key, raw)
        except (ValueError, OverflowError, RecursionError) as exc:
            gap("option-value-not-transferred", str(exc), key=key, line=line)
            continue
        field.update(status="candidate-verbatim", typed_value=typed, candidate_raw=raw)
        candidate.append(f"{key}:{raw}")

    if gammautils_path is not None:
        try:
            gamma_text, provenance = _read(gammautils_path)
            report["gammautils_evidence"] = {"source": provenance,
                                             "rendered_brightness_state_verified": False}
            config = _json(gamma_text)
            if not isinstance(config, dict):
                raise ValueError("GammaUtils configuration must be an object")
            gamma = config.get("gamma")
            summary = {key: gamma[key] for key in ("value", "defaultGamma", "toggledGamma", "resetOnClose")
                       if isinstance(gamma, dict) and key in gamma}
            report["gammautils_evidence"]["configured_gamma"] = summary
            gap("brightness-modifier-runtime-review", "GammaUtils configuration does not prove the last rendered brightness; native fullbright/shader equivalence needs comparison. No fullbright setting was enabled", key="gamma")
        except (OSError, ValueError, RecursionError) as exc:
            gap("brightness-modifier-evidence-unreadable", str(exc), key="gamma")

    if source_supported and target_supported:
        report["candidate_text"] = "\n".join(candidate) + "\n"
        report["status"] = "partial-candidate" if report["gaps"] else "candidate-awaits-runtime-validation"
    else:
        report["status"] = "codec-context-unverified"
    return report
