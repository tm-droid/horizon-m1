#!/usr/bin/env python3
"""Prepare a reviewable Horizon migration without changing the Java instance."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import lzma
import os
from pathlib import Path
import shutil
import stat
import sys
from urllib.parse import parse_qs, urlsplit
import zipfile
import zlib

from horizon_converter_mods import analyze_mod
from horizon_converter_packs import inspect_pack, stage_pack
from horizon_converter_carry import carry_mod_assets
from horizon_converter_review import appearance_contract, classify_mod, group_findings, walk_reports
from horizon_converter_cem import analyze_cem_packs
from horizon_converter_settings import build_settings_candidate

REVISION = "e6e12d40c522b8f5ee8740dd861c96689023737a"
RESEARCH_HOOKS_API = 153
SOURCE = f"https://github.com/horizon-rust/horizon/blob/{REVISION}"
MAX_CONFIG = 4 * 1024 * 1024
MAX_SOURCE_FILE = 1024 ** 3
MAX_SOURCE_TOTAL = 8 * 1024 ** 3
MAX_SOURCE_FILES = 100_000
SCAN_ERRORS = (ValueError, OSError, RuntimeError, zipfile.BadZipFile, zlib.error, lzma.LZMAError, EOFError)


@contextmanager
def source_open(path, cap):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > cap:
            raise ValueError(f"Source must be a bounded regular file: {path}")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            yield stream
    finally:
        os.close(descriptor)


def digest(path):
    h = hashlib.sha256()
    count = 0
    with source_open(path, MAX_SOURCE_FILE) as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            count += len(data)
            if count > MAX_SOURCE_FILE:
                raise ValueError(f"Source exceeded hash byte limit: {path}")
            h.update(data)
    return h.hexdigest()


def read_small(path):
    with source_open(path, MAX_CONFIG) as stream:
        data = stream.read(MAX_CONFIG + 1)
    if len(data) > MAX_CONFIG:
        raise ValueError(f"Configuration grew beyond byte limit: {path}")
    return data.decode("utf-8")


def inside(path, root):
    return path == root or root in path.parents


def local_child(root, name):
    """Selection strings are data, never shell or arbitrary filesystem paths."""
    if not name or name in (".", "..") or any(c in name for c in ("/", "\\", "\x00")):
        raise ValueError(f"Unsafe selected filename: {name!r}")
    candidate = root / name
    if candidate.is_symlink() or not inside(candidate.resolve(), root.resolve()):
        raise ValueError(f"Selected file escapes its source directory: {name!r}")
    return candidate


def options_selection(game):
    path = game / "options.txt"
    options = dict(line.split(":", 1) for line in read_small(path).splitlines() if ":" in line)
    selected = json.loads(options.get("resourcePacks", "[]"))
    if not isinstance(selected, list) or not all(isinstance(x, str) for x in selected):
        raise ValueError("resourcePacks must be a JSON list of strings")
    if len(selected) != len(set(selected)):
        raise ValueError("Duplicate selected resource packs; selection order is ambiguous")
    return selected


def shader_selection(game):
    path = game / "config/iris.properties"
    if not path.exists():
        return None
    props = {}
    for line in read_small(path).splitlines():
        if line.strip() and not line.lstrip().startswith(("#", "!")) and "=" in line:
            key, value = line.split("=", 1)
            props[key.strip()] = value.strip()
    if props.get("enableShaders", "false").lower() != "true":
        return None
    name = props.get("shaderPack")
    if not name:
        raise ValueError("Iris shaders enabled without a selected shaderPack")
    # Preserve properties with escapes as evidence; do not guess their decoding.
    return local_child(game / "shaderpacks", name)


def source_files(game, selected, shader):
    result = [game / "options.txt"]
    iris = game / "config/iris.properties"
    if iris.exists():
        result.append(iris)
    mods = game / "mods"
    if mods.is_symlink():
        raise ValueError("Symlinked mods directory is not supported")
    for path in mods.glob("*.jar"):
        result.append(path)
        if len(result) > MAX_SOURCE_FILES:
            raise ValueError("Source file-count limit exceeded")

    def add_tree(folder):
        for path in folder.rglob("*"):
            if path.is_file() or path.is_symlink() or not path.is_dir():
                result.append(path)
            if len(result) > MAX_SOURCE_FILES:
                raise ValueError("Source file-count limit exceeded")

    config = game / "config"
    if config.is_symlink():
        raise ValueError("Symlinked config directory is not supported")
    if config.exists():
        add_tree(config)

    for selection in selected:
        if selection.startswith("file/"):
            pack = local_child(game / "resourcepacks", selection[5:])
            if pack.is_dir():
                add_tree(pack)
            elif pack.exists():
                result.append(pack)
    if shader and shader.exists():
        if shader.is_dir():
            add_tree(shader)
        else:
            result.append(shader)
        sidecar = shader.with_name(shader.name + ".txt")
        if sidecar.exists():
            result.append(sidecar)
    total = 0
    for path in result:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or not inside(path.resolve(), game):
            raise ValueError(f"Source must be a regular file inside the game directory: {path}")
        total += info.st_size
        if info.st_size > MAX_SOURCE_FILE or total > MAX_SOURCE_TOTAL:
            raise ValueError("Source byte limit exceeded")
    return sorted(set(result))


def fingerprint(game, selected, shader):
    return {str(p.relative_to(game)): digest(p) for p in source_files(game, selected, shader)}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def finding(code, reason, action, severity="review", **extra):
    return dict(code=code, severity=severity, reason=reason, next_action=action, **extra)


def upstream_plan(game, output, jars, runtime=None):
    # Emit argv arrays only. Nothing downloaded, built or executed automatically.
    work = str(output / "upstream-work")
    binary = "horizon-port-pack"
    return {
        "revision": REVISION, "executed": False,
        "runtime_provenance": runtime_reference(runtime),
        "selected_runtime_commands_verified": False,
        "binary_requirement": "Build/verify horizon-port-pack from the pinned Horizon revision first.",
        "commands": [
            [binary, "import", str(game.parent), work],
            [binary, "inventory", work, "--offline"],
            [binary, "carry", work],
            [binary, "report", work],
        ],
        "single_mod_checks": [[binary, "check", str(jar), str(output / "upstream-checks" / f"mod-{i:04d}")]
                              for i, jar in enumerate(jars, 1)],
        "cautions": [
            "Do not use port --offline for a no-download workflow: its pipeline still fetches.",
            "carry can infer vanilla templates without oracle facts; review every guessed registration.",
            "Import may copy additional files; use a new work directory, never a live Horizon home.",
            "A check verdict or copied resource pack does not establish visual or behavior parity.",
            "These commands use the research revision, not automatically the selected runtime; reverify tool and native-port compatibility before use.",
        ],
        "schemas": {"coverage_status": ["ported", "partial", "not-yet", "not-needed"],
                    "check_verdict": ["works", "partly", "no"]},
    }


def dependency_graph(mods):
    ids = {m.get("id") for m in mods if isinstance(m.get("id"), str)}
    edges = []
    for mod in (node for root in mods for node in walk_reports(root)):
        metadata = mod.get("fabric") or {}
        dependencies = metadata.get("dependencies", {}) if isinstance(metadata, dict) else {}
        depends = dependencies.get("depends", {}) if isinstance(dependencies, dict) else {}
        if isinstance(depends, dict):
            for target, constraint in sorted(depends.items()):
                edges.append({"from": mod.get("id"), "to": target, "java_constraint": constraint,
                              "installed_top_level": target in ids, "archive_chain": mod.get("archive_chain", [])})
    return {"edges": edges, "qualification": "Java loader constraints are evidence, not Horizon dependencies; nested providers may satisfy an absent top-level ID."}


def candidate_hooks(report):
    verified = {
        "input-reference": ("native_key", "(&mut self, key: &str, pressed: bool)", 1792),
        "hud-reference": ("native_hud", "(&mut self, batch: &mut HudBatch, corners: &mut Corners)", 1698),
        "tick-callback-reference": ("native_tick", "(&mut self)", 1538),
    }
    result = []
    for category, (name, signature, line) in verified.items():
        evidence = []
        for node in walk_reports(report):
            for cls in node.get("classes", []):
                for ref in cls.get("relevant_references", []):
                    if category in ref.get("categories", []):
                        evidence.append({"source_entry": cls.get("source_entry"), "reference": ref,
                                         "archive_chain": node.get("archive_chain", [])})
        if evidence:
            result.append({"hook": name, "signature": signature, "status": "candidate-requires-semantic-review",
                           "source": SOURCE + f"/crates/horizon-client/src/game/native_hooks.rs#L{line}",
                           "source_revision": REVISION, "source_host_native_hooks_api": RESEARCH_HOOKS_API,
                           "minimum_required_hooks_api": None,
                           "selected_runtime_validation": "unverified",
                           "evidence": evidence[:30], "evidence_count": len(evidence),
                           "qualification": "A symbolic reference suggests a review area, not an equivalent implementation."})
    return result


def runtime_reference(runtime):
    runtime = runtime or {}
    selected = runtime.get("selected_runtime") or {}
    return {"file": "runtime-provenance.json", "status": runtime.get("status", "runtime-unspecified"),
            "selected_runtime_revision": selected.get("runtime_revision"),
            "native_compatibility_verified": False}


def pinned_runtime_source(url, revision):
    """Recognize immutable source routes, not revision text in incidental URL fields."""
    if not isinstance(url, str):
        return False
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    if parsed.scheme != "https":
        return False
    parts = parsed.path.strip("/").split("/")
    if parsed.netloc == "github.com":
        return (len(parts) > 4 and parts[:2] == ["horizon-rust", "horizon"] and
                parts[2] in ("blob", "raw") and parts[3] == revision)
    if parsed.netloc == "raw.githubusercontent.com":
        return (len(parts) > 3 and parts[:2] == ["horizon-rust", "horizon"] and
                parts[2] == revision)
    if parsed.netloc == "api.github.com":
        return (len(parts) > 4 and parts[:4] == ["repos", "horizon-rust", "horizon", "contents"] and
                parse_qs(parsed.query, keep_blank_values=True).get("ref") == [revision])
    return False


def runtime_provenance(path):
    """Record declared runtime evidence without relabeling research or executing it."""
    result = {"schema": 1, "research": {"horizon_revision": REVISION, "native_hooks_api": RESEARCH_HOOKS_API},
              "selected_runtime": None, "input_manifest": None, "status": "runtime-unspecified",
              "revision_matches_research": None, "host_api_matches_research": None,
              "hook_api_evidence_complete": False, "native_compatibility_verified": False,
              "qualification": "Research API is a host capability, not a per-port minimum. Source verification is declared by the input record; this converter does not fetch source, compile ports or test runtime behavior."}
    reviews = []

    def review(issue, reason):
        reviews.append(finding("RUNTIME_PROVENANCE_REVIEW", reason,
                               "Select the intended runtime, verify its source hooks and each port's required API/helpers, then compile and test the actual native package. Asset copies remain candidates.",
                               subject="runtime", scope="runtime-target", evidence_file="runtime-provenance.json", issue=issue))

    if path is None:
        review("runtime-unspecified", "No runtime manifest was supplied; the research pin is not evidence of the installed or selected runtime.")
        return result, reviews
    result["input_manifest"] = {"path": str(path.absolute()), "sha256": None}
    try:
        text = read_small(path)
        result["input_manifest"]["sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        selected = json.loads(text)
        if not isinstance(selected, dict):
            raise ValueError("Runtime manifest must be a JSON object")
    except (ValueError, OSError) as exc:
        result["status"] = "runtime-evidence-incomplete"
        review("runtime-manifest-unreadable", f"Runtime manifest could not be read as a bounded JSON object: {exc}")
        return result, reviews
    result["selected_runtime"] = selected
    revision = selected.get("runtime_revision")
    api = selected.get("native_hooks_api")
    revision_valid = isinstance(revision, str) and len(revision) == 40 and all(c in "0123456789abcdef" for c in revision)
    api_valid = type(api) is int and api > 0
    if not revision_valid:
        review("runtime-revision-missing", "The selected runtime needs its full lowercase 40-character source revision.")
    else:
        result["revision_matches_research"] = revision == REVISION
        if revision != REVISION:
            review("research-revision-differs", "The selected runtime differs from the research revision; candidate hook signatures, source links and upstream plans have not been reverified for it.")
    if not api_valid:
        review("runtime-hook-api-missing", "The selected runtime's host native-hooks API is missing or is not a positive integer.")
    else:
        result["host_api_matches_research"] = api == RESEARCH_HOOKS_API
        if api != RESEARCH_HOOKS_API:
            review("research-host-api-differs", "The selected host API differs from the research host API. This is a review requirement, not a rejection: the research API is not every port's minimum requirement.")
    evidence = selected.get("hook_api_evidence")
    evidence = evidence if isinstance(evidence, dict) else {}
    url = evidence.get("url")
    result["hook_api_evidence_complete"] = bool(revision_valid and api_valid and pinned_runtime_source(url, revision) and
                                               (evidence.get("verification") is True or evidence.get("verification") == "verified"))
    if not result["hook_api_evidence_complete"]:
        review("runtime-hook-evidence-incomplete", "Hook API evidence needs a source URL pinned to the selected revision and an explicit verification value of true or 'verified'.")
        result["status"] = "runtime-evidence-incomplete"
    elif result["revision_matches_research"] and result["host_api_matches_research"]:
        result["status"] = "research-source-match-runtime-unverified"
        review("native-runtime-validation-pending", "The declared runtime source/API matches the research, but no native port compilation or behavior compatibility is established.")
    else:
        result["status"] = "requires-target-hook-review"
    return result, reviews


def run(game, output, stage, carry_assets=False, runtime_manifest=None):
    game = game.resolve(strict=True)
    if not (game / "mods").is_dir() or not (game / "options.txt").is_file():
        raise ValueError("--game-dir must contain mods/ and options.txt")
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("Output must be a new directory; existing reports are never overwritten")
    if inside(output.resolve(), game) or inside(game, output.resolve()):
        raise ValueError("Output and source game directory must be disjoint")
    # Reject symlinked parents to avoid staging through an unexpected destination.
    if any(p.is_symlink() for p in [output, *output.parents]):
        raise ValueError("Symlinked output paths are not supported")
    runtime, runtime_reviews = runtime_provenance(runtime_manifest)
    selected = options_selection(game)
    shader = shader_selection(game)
    before = fingerprint(game, selected, shader)
    jars = sorted((game / "mods").glob("*.jar"))
    output.mkdir(parents=True, mode=0o700)
    (output / "mods").mkdir()
    (output / "tasks").mkdir()
    (output / "source-settings").mkdir()
    settings = []
    for relative, sha in before.items():
        name = Path(relative).name.lower()
        if relative == "options.txt" or (relative.startswith("config/") and name.startswith(
                ("iris.", "sodium", "entity_model_features", "entity_texture_features", "continuity", "zoomify", "gammautils"))):
            target = output / "source-settings" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(game / relative, target)
            if digest(target) != sha:
                raise ValueError(f"Settings changed while copying: {relative}")
            settings.append({"source": relative, "sha256": sha, "evidence": str(target.relative_to(output)),
                             "status": "source-semantics-not-translated"})
    if stage:
        (output / "resourcepacks").mkdir()
    if carry_assets:
        (output / "mod-asset-packs").mkdir()
    reports, packs, queue = [], [], list(runtime_reviews)
    incomplete = False
    for i, jar in enumerate(jars, 1):
        key = f"mod-{i:04d}"
        try:
            report = analyze_mod(jar)
        except SCAN_ERRORS as exc:
            incomplete = True
            report = {"path": str(jar), "name": jar.name, "sha256": before.get(str(jar.relative_to(game))),
                      "findings": [finding("MOD_SCAN_FAILED", str(exc), "Inspect this jar manually before porting.", "error")]}
        report["report_id"] = key
        if carry_assets:
            try:
                report["asset_carry"] = carry_mod_assets(jar, output / "mod-asset-packs" / f"{key}.zip")
            except SCAN_ERRORS as exc:
                incomplete = True
                report["asset_carry"] = {"status": "blocked", "error": str(exc)}
                report.setdefault("findings", []).append(finding("MOD_ASSET_CARRY_FAILED", str(exc),
                                                                "Review source assets; no candidate was accepted.", "error"))
        if any(item.get("severity") == "error" for node in walk_reports(report) for item in node.get("findings", [])):
            incomplete = True
        reports.append(report)
        write_json(output / "mods" / f"{key}.json", report)
        task = {
            "task_id": key, "source_name": jar.name, "source_sha256": report.get("sha256"),
            "mod_id": report.get("id"), "status": "needs-source-and-native-port-review",
            "evidence": f"mods/{key}.json", "workflow": "AGENT_WORKFLOW.md",
            "target": {"horizon_revision": REVISION, "native_hooks_api": RESEARCH_HOOKS_API,
                       "basis": "source-research; host API is not a per-port minimum"},
            "runtime_provenance": runtime_reference(runtime),
            "candidate_hooks": candidate_hooks(report),
            "asset_carry": report.get("asset_carry"),
            "classification": classify_mod(report),
            "config_candidates": [row for row in settings if row["source"] == "options.txt" or
                                  str(report.get("id") or "__unknown__").replace("_", "").lower() in
                                  Path(row["source"]).name.replace("_", "").lower()],
            "acceptance": ["Inspect original implementation and license; metadata/constant-pool references do not prove behavior.",
                           "Classify native built-in replacement, content carry, Rust logic, or unsupported behavior for every feature.",
                           "Reverify candidate hooks and required APIs/helpers against the selected runtime; compile the real native bundle against that runtime's source and mixin revisions.",
                           "Match config semantics, keybinds, assets and behavior; test visual parity before enabling.",
                           "Document unresolved features; do not mark partial code converted."],
        }
        write_json(output / "tasks" / f"{key}.json", task)
        for node in walk_reports(report):
            for item in node.get("findings", []):
                queue.append(dict(item, subject=key, evidence_file=f"mods/{key}.json",
                                  archive_chain=node.get("archive_chain", [])))
        for item in report.get("asset_carry", {}).get("findings", []):
            queue.append(dict(item, subject=key, scope="asset-carry", evidence_file=f"mods/{key}.json"))
        # Every Java code artifact retains a manual task even if the scanner found no recognized API.
        queue.append(finding("JAVA_PORT_REVIEW", "Fabric jars do not run in Horizon.",
                             f"Follow tasks/{key}.json; resolve code and dependency behavior explicitly.", subject=key))
    ordered_pack_paths = []
    for order, selection in enumerate(selected):
        row = {"selection": selection, "order": order, "staged": False}
        if selection == "vanilla":
            row["status"] = "horizon-built-in-assets-required"
        elif not selection.startswith("file/"):
            row["status"] = "java-mod-supplied-pack-review"
            queue.append(finding("MOD_SUPPLIED_PACK", selection,
                                 "Identify the supplying Java mod and preserve this layer when porting its assets.", subject=selection))
        else:
            try:
                pack = local_child(game / "resourcepacks", selection[5:])
                details = inspect_pack(pack)
                ordered_pack_paths.append(pack)
                row.update(details)
                row["status"] = "preserved-format-runtime-unverified"
                if stage:
                    row["staging"] = stage_pack(pack, output / "resourcepacks" / pack.name)
                    row["staged"] = True
                for item in details.get("findings", []):
                    queue.append(dict(item, subject=selection))
            except SCAN_ERRORS as exc:
                incomplete = True
                row.update(status="blocked", error=str(exc))
                queue.append(finding("PACK_SCAN_OR_STAGE_FAILED", str(exc), "Resolve this selected pack; preserve its exact layer position.", "error", subject=selection))
        packs.append(row)
    selected_revision = (runtime.get("selected_runtime") or {}).get("runtime_revision")
    native_settings = build_settings_candidate(game / "options.txt", selected_revision,
                                               gammautils_path=game / "config/gammautils.json" if (game / "config/gammautils.json").exists() else None)
    write_json(output / "native-settings-candidate.json", native_settings)
    if native_settings["candidate_text"] is not None:
        (output / "native-options-candidate.txt").write_text(native_settings["candidate_text"])
    for index, item in enumerate(native_settings["gaps"]):
        queue.append(finding("NATIVE_SETTINGS_REVIEW", item["reason"],
                             "Review the source value and selected runtime codec; compare effective values and appearance before applying the candidate.",
                             subject="instance-settings", scope="native-settings", key=item.get("key"),
                             evidence_file="native-settings-candidate.json", evidence_pointer=f"/gaps/{index}"))
    cem = analyze_cem_packs(ordered_pack_paths, selected_revision, scope_complete=False)
    write_json(output / "native-cem-preflight.json", cem)
    for index, item in enumerate(cem["findings"]):
        queue.append(finding("NATIVE_CEM_REVIEW", f"{item['rule']}: {item.get('matched')}",
                             "Inspect every consumer and native source evidence, then verify the combined pack stack; this finding does not prove a visible failure.",
                             subject="file/" + Path(item["source"]["pack"]).name, scope="native-cem", capability=item["rule"],
                             evidence_file="native-cem-preflight.json", evidence_pointer=f"/findings/{index}"))
    for index, item in enumerate(cem["coverage_gaps"]):
        queue.append(finding("NATIVE_CEM_COVERAGE", item["reason"],
                             "Resolve this preflight coverage gap before treating an empty finding list as meaningful; inspect the effective combined resource view.",
                             subject="selected-packs", scope="native-cem-coverage", issue=item["code"],
                             evidence_file="native-cem-preflight.json", evidence_pointer=f"/coverage_gaps/{index}"))
    shader_report = None
    if shader:
        try:
            shader_report = inspect_pack(shader)
            shader_report["status"] = "shader-runtime-parity-unverified"
            if stage:
                (output / "shader-source").mkdir()
                shader_report["staging"] = stage_pack(shader, output / "shader-source" / shader.name)
                sidecar = shader.with_name(shader.name + ".txt")
                if sidecar.exists():
                    shutil.copyfile(sidecar, output / "shader-source" / sidecar.name)
        except SCAN_ERRORS as exc:
            incomplete = True
            shader_report = {"path": str(shader), "status": "blocked", "error": str(exc)}
            queue.append(finding("SHADER_SCAN_OR_STAGE_FAILED", str(exc),
                                 "Resolve the selected shader before comparing appearance; no preserved shader is accepted.",
                                 "error", subject=shader.name))
        queue.append(finding("SHADER_PARITY", "Shader behavior and Iris overrides require runtime validation; see the shader preservation status in the manifest.",
                             "Test Mellow programs, SMAA, lighting, shadows and overrides on Horizon/Metal before claiming equivalent visuals.", subject=shader.name))
    after_selected = options_selection(game)
    after = fingerprint(game, after_selected, shader_selection(game))
    unchanged = before == after and selected == after_selected
    if not unchanged:
        incomplete = True
        queue.append(finding("SOURCE_CHANGED_DURING_RUN", "Source file inventory or hashes changed during conversion.",
                             "Keep this output provisional. Close the game/launcher and rerun into a fresh directory.", "error"))
    grouped = group_findings(queue, {m["report_id"]: classify_mod(m) for m in reports})
    manifest = {
        "schema": 2, "tool": "horizon-convert", "horizon_revision": REVISION,
        "runtime_provenance": runtime,
        "review_queue_format": "grouped-v1", "raw_review_queue_format": "findings-v1",
        "source_game_dir": str(game), "source_unchanged": unchanged, "source_before": before, "source_after": after,
        "status": "incomplete" if incomplete else "prepared-needs-review",
        "java_behavior_converted": False, "runtime_visual_parity_verified": False,
        "resourcepack_selection": selected, "resourcepacks": packs,
        "native_settings_candidate": {"file": "native-settings-candidate.json", "status": native_settings["status"],
                                      "candidate_file": "native-options-candidate.txt" if native_settings["candidate_text"] is not None else None,
                                      "runtime_visual_parity_verified": False},
        "native_cem_preflight": {"file": "native-cem-preflight.json", "status": cem["status"],
                                 "finding_count": len(cem["findings"]), "coverage_gap_count": len(cem["coverage_gaps"]),
                                 "runtime_visual_parity_verified": False},
        "shader": shader_report, "active_mod_count": len(reports),
        "disabled_mods": sorted(p.name for p in (game / "mods").glob("*.jar.disabled")),
        "review_count": len(grouped), "raw_finding_count": len(queue), "staged": stage,
        "nested_archives_inspected": sum(m.get("coverage", {}).get("nested_stats", {}).get("archives_inspected", 0) for m in reports),
        "mod_assets_carried": sum(m.get("asset_carry", {}).get("status") == "assets-only-runtime-unverified" for m in reports),
        "scan_coverage_incomplete": sum(not m.get("coverage", {}).get("complete", False) for m in reports),
        "target_sources": [SOURCE + "/docs/modpacks.md", SOURCE + "/docs/resource-packs.md", SOURCE + "/docs/native-mods.md"],
    }
    write_json(output / "manifest.json", manifest)
    write_json(output / "runtime-provenance.json", runtime)
    write_json(output / "appearance-contract.json", appearance_contract(selected, packs, shader_report, settings))
    write_json(output / "dependency-graph.json", dependency_graph(reports))
    write_json(output / "porting-index.json", [{"task_id": m["report_id"], "id": m.get("id"), "name": m.get("name"),
                                               "class_count": m.get("content", {}).get("classes"),
                                               "asset_count": m.get("content", {}).get("assets"),
                                               "nested_jar_count": len(m.get("nested_jars", [])),
                                               "scan_coverage": m.get("coverage"),
                                               "candidate_hooks": [h["hook"] for h in candidate_hooks(m)],
                                               "asset_carry": m.get("asset_carry", {}).get("status"),
                                               "task": f"tasks/{m['report_id']}.json"} for m in reports])
    write_json(output / "upstream-plan.json", upstream_plan(game, output, jars, runtime))
    with (output / "raw-review-queue.jsonl").open("w") as stream:
        for item in queue:
            stream.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    with (output / "review-queue.jsonl").open("w") as stream:
        for item in grouped:
            stream.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    (output / "AGENT_WORKFLOW.md").write_text(WORKFLOW)
    summary = ["# Horizon migration preparation", "", f"Status: **{manifest['status']}**. Source hashes unchanged: **{unchanged}**.", "",
               f"{len(reports)} active Java jars inspected; {len(packs)} resource-pack layers retained in selection order; {len(grouped)} grouped review tasks from {len(queue)} raw findings.", "",
               f"{manifest['mod_assets_carried']} resource-only mod asset candidates generated. Activate them only after reviewing namespace collisions and order; code/data behavior is omitted.", "",
               "Pack and shader copies preserve source bytes. No Java behavior was translated or executed. No Horizon runtime or visual parity has been verified.", "",
               f"Runtime provenance: **{runtime['status']}**. `runtime-provenance.json` separates the research pin from declared selected-runtime evidence; a source/API match is not runtime compatibility.", "",
               "`native-settings-candidate.json` records version-qualified option transfers and omissions; its optional text candidate is not activated. `native-cem-preflight.json` checks source-backed patterns over the selected file-pack layers, with consumer evidence and explicit coverage limits. Neither report establishes visual parity.", "",
               "Use `appearance-contract.json` for visual priorities/settings, `manifest.json` for pack order/fingerprints, `mods/` for code evidence, and `tasks/` for manual native ports. `review-queue.jsonl` groups unresolved work and references every line of `raw-review-queue.jsonl`.", "",
               "`upstream-plan.json` contains unexecuted argv arrays for Horizon's existing importer, offline inventory, content carry and reports. Review its caveats before running.", "",
               "Horizon supports many vanilla and OptiFine-style assets directly. Feature detections request parity checks; an extension directory alone does not prove lack of support.", ""]
    (output / "README.md").write_text("\n".join(summary))
    print(json.dumps({"output": str(output), "status": manifest["status"], "mods": len(reports),
                      "selected_layers": len(packs), "review_tasks": len(grouped), "raw_findings": len(queue), "source_unchanged": unchanged}))
    return 2 if incomplete else 0


WORKFLOW = f"""# Manual and assisted native port workflow

Research Horizon revision: `{REVISION}`; host native hooks API {RESEARCH_HOOKS_API}. This directory is a
review queue, not proof that the Java mods have been converted.

Read `runtime-provenance.json` for the separately selected runtime and remaining
verification gaps. The research host API is not every port's minimum API; do not
reject a port merely because another runtime's host API differs. Research hook
links and upstream plans are not automatically reverified for a selected runtime.

1. Pick one task from `tasks/`. Read its `mods/` evidence, original implementation,
   metadata, dependencies and license. Archive filenames and constant-pool references
   are observations; references can be unused. Nested jars need separate inspection.
2. Enumerate actual user-facing features and settings. Check Horizon's built-in
   functionality and native mods before reimplementing anything. Do not port Java
   renderer/GC optimizations mechanically into a different engine.
3. For content/assets use the pinned upstream `horizon-port-pack` tool and inspect
   every guessed block/item template, skipped file and registration. Preserve pack
   order; preserve all formats, animation expressions, models and shader overrides.
4. For code, inspect real Rust source hooks and the official native template. Known
   hooks include native_tick, native_hud and native_key in game/native_hooks.rs;
   these are game-source hooks, not an external stable Rust library. Confirm exact
   signatures and mixin schema at the pinned revisions. No fabricated APIs or no-op
   success stubs. Compile/test the actual native package before calling it ported.
5. Translate config semantics and defaults explicitly. Test input conflicts, network
   behavior, entity animation, audio and visuals with matching scenes. If a feature
   or hook is missing, produce a concrete upstream implementation task with source
   evidence and acceptance cases. Keep its status partial/blocked.
6. Record source hashes/revisions, changed files, exact checks and remaining gaps in
   a separate result next to the task. A person or agent can pick up unresolved flags
   from review-queue.jsonl; this tool does not send messages or launch agents.

Reference: {SOURCE}/docs/native-mods.md
Resource support: {SOURCE}/docs/resource-packs.md
Porting tool: {SOURCE}/docs/modpacks.md
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, help="Java game directory (required unless --prune-unreachable-namespaces)")
    parser.add_argument("--output", required=True, type=Path, help="Fresh disjoint output directory")
    parser.add_argument("--stage-packs", action="store_true", help="Copy selected packs and active shader intact; no live Horizon installation")
    parser.add_argument("--stage-mod-assets", action="store_true", help="Convert jar assets to resource-only candidate packs, with provenance and manual activation review")
    parser.add_argument("--runtime-manifest", type=Path, help="Optional declared runtime revision/API/evidence record; does not retarget research or prove compatibility")
    parser.add_argument("--prune-unreachable-namespaces", type=Path, metavar="SOURCE_MIGRATION",
                        help="Opt-in v4 mode: derive --output from an existing migration, dropping namespaces nothing can reach and dead TRIM files; no --game-dir or staging flags")
    parser.add_argument("--prune-unreached-files", action="store_true",
                        help="With --prune-unreachable-namespaces: also drop models/textures/blockstates/items nothing reaches inside reachable pack-private namespaces (strict)")
    args = parser.parse_args()
    if args.prune_unreachable_namespaces:
        from horizon_converter_prune import derive
        try:
            record = derive(args.prune_unreachable_namespaces, args.output, prune_unreached_files=args.prune_unreached_files)
        except (FileExistsError, ValueError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
            print(f"Prune failed: {exc}", file=sys.stderr)
            return 2
        print(json.dumps({"output": str(args.output), "removed_files": record["removed_file_count"],
                          "removed_bytes": record["removed_bytes"], "effective_map_check": record["effective_map_check"]}))
        return 0
    if not args.game_dir:
        parser.error("--game-dir is required")
    try:
        return run(args.game_dir, args.output, args.stage_packs, args.stage_mod_assets, args.runtime_manifest)
    except SCAN_ERRORS as exc:
        print(f"Migration preparation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
