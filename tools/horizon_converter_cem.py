"""Bounded, read-only CEM review for a source-pinned Horizon runtime.

This detects known source-backed patterns, not complete CEM semantics or working ports.
Selected ZIPs are supplied from lowest to highest resource priority.
"""
from __future__ import annotations

import hashlib
import json
import lzma
import math
from pathlib import Path, PurePosixPath
import re
import zipfile
import zlib

from horizon_converter_packs import PackSafetyError, _entries, _hash_file

REVISION = "f42ef42ef6ceccb3c6a20bea2481d87949a51c81"
SOURCE = f"https://github.com/horizon-rust/horizon/blob/{REVISION}/crates/"
MAX_MEMBER_BYTES = 4 * 1024 ** 2
MAX_MODEL_BYTES = 4 * 1024 ** 2
MAX_TOTAL_BYTES = 64 * 1024 ** 2
MAX_MEMBERS = 8192
MAX_ROOTS = 512
MAX_DEPTH = 64
MAX_ENTRIES = 1024
MAX_WORK = 65536
MAX_TOTAL_WORK = 1_000_000
MAX_ANIMATIONS = 4096
MAX_SELECTOR_TOKENS = 1024
MAX_PACK_BYTES = 1024 ** 3
BASES = ("assets/minecraft/emf/cem/", "assets/minecraft/optifine/cem/")
MINECARTS = frozenset(("minecart", "chest_minecart", "furnace_minecart", "hopper_minecart",
                       "command_block_minecart", "spawner_minecart", "tnt_minecart"))
BLOCK_ENTITIES = frozenset("""chest chest_left chest_right trapped_chest trapped_chest_left
trapped_chest_right ender_chest shulker_box banner_base banner banner_flag head_skeleton
head_wither_skeleton head_zombie head_creeper head_dragon head_piglin head_player bell
enchanting_book book lectern_book conduit decorated_pot""".split())
BLOCK_PARTS = {
    **{name: frozenset(("root", "base", "lid", "knob")) for name in
       ("chest", "chest_left", "chest_right", "trapped_chest", "trapped_chest_left", "trapped_chest_right", "ender_chest")},
    "shulker_box": frozenset(("root", "base", "lid")),
    "banner_base": frozenset(("stand", "top")), "banner_flag": frozenset(("slate",)),
    "banner": frozenset(("stand", "top", "slate")),
    **{name: frozenset(("root", "head")) for name in
       ("head_skeleton", "head_wither_skeleton", "head_zombie", "head_creeper", "head_player")},
    "head_dragon": frozenset(("root", "head", "jaw")),
    "head_piglin": frozenset(("root", "head", "left_ear", "right_ear")),
    "bell": frozenset(("root", "body", "base")),
    **{name: frozenset(("root", "cover_right", "cover_left", "pages_right", "pages_left",
                       "flipping_page_right", "flipping_page_left", "book_spine"))
       for name in ("enchanting_book", "book", "lectern_book")},
    "conduit": frozenset(("base", "cage", "wind", "eye")),
    "decorated_pot": frozenset(("neck", "top", "bottom", "front", "back", "left", "right")),
}
# find_mut accepts root for every block-entity model, independently of mapped aliases.
BLOCK_PARTS = {name: parts | {"root"} for name, parts in BLOCK_PARTS.items()}
PARAMETERS = frozenset("""limb_swing limb_speed age head_yaw head_pitch swing_progress health
max_health hurt_time death_time pos_x pos_y pos_z rot_x rot_y id time day_time day_count
frame_time frame_counter dimension player_pos_x player_pos_y player_pos_z player_rot_x
player_rot_y rule_index anger_time anger_time_start distance move_forward move_strafing
height_above_ground fluid_depth fluid_depth_down fluid_depth_up is_aggressive is_alive
is_burning is_child is_glowing is_hurt is_in_hand is_in_item_frame is_in_ground is_in_gui
is_in_lava is_in_water is_invisible is_on_ground is_on_head is_on_shoulder is_ridden
is_riding is_sitting is_sneaking is_sprinting is_tamed is_wet is_climbing is_blocking
is_crawling is_jumping is_swimming is_right_handed is_swinging_right_arm
is_swinging_left_arm is_first_person_hand is_using_item is_holding_item_right
is_holding_item_left is_paused is_hovered is_player_first_person is_player_third_person
is_player_third_person_reversed""".split())
STUBS = frozenset(("height_above_ground", "fluid_depth_up"))
PART_PROPERTIES = frozenset("tx ty tz rx ry rz sx sy sz visible visible_boxes".split())
VARIABLES = frozenset(("var", "varb", "global_var", "global_varb"))
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.:]*")
RULE_SOURCES = {
    "cem.stubbed-parameter-read": SOURCE + "horizon-client/src/mobs/cem_anim.rs#L649",
    "cem.render-property-write-unused": SOURCE + "horizon-client/src/mobs/cem_anim.rs#L303",
    "cem.block-entity-animation-not-applied": SOURCE + "horizon-client-render/src/block_entity_cem.rs#L1",
    "cem.alternate-model-selection": SOURCE + "horizon-client/src/mobs/cem.rs#L222",
    "cem.bed-model-not-applied": SOURCE + "horizon-client-render/src/block_entity_render.rs#L845",
    "cem.minecart-model-not-applied": SOURCE + "horizon-client/src/game/minecarts.rs#L392",
}


def _pointer(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def _strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            key.encode("utf-8")
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value):
        raise ValueError(f"Non-JSON constant: {value}")

    def floating(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Nonfinite number is outside strict analysis")
        return number

    parsed = json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant, parse_float=floating)
    stack = [(parsed, 0)]
    while stack:
        value, depth = stack.pop()
        if depth > MAX_DEPTH:
            raise ValueError("JSON nesting exceeds analysis limit")
        if isinstance(value, str):
            value.encode("utf-8")
        if isinstance(value, dict):
            stack.extend((child, depth + 1) for child in value.values())
        elif isinstance(value, list):
            stack.extend((child, depth + 1) for child in value)
    return parsed


def analyze_cem_packs(ordered_paths, runtime_revision, *, scope_complete=False):
    """Return review evidence without extracting or changing any input pack.

    ZIP-only; unknown formats, binding aliases, overlays, lenient syntax and other
    deferred semantics remain explicit gaps. Findings are potential requirements,
    never a certificate that an animation compiles, binds or changes pixels.
    """
    report = {"schema": 1, "rule_set": "cem-preflight-f42-v2", "runtime_revision": runtime_revision,
              "capability_revision": REVISION, "status": "review-required", "packs": [],
              "scope_complete": bool(scope_complete), "scope_completeness_verified": False,
              "implicit_mod_resources_verified": False,
              "catalogued_prefixes": list(BASES),
              "resource_view_verified": True, "resource_winners": [], "shadowed_resources": [],
              "findings": [], "coverage_gaps": [], "unresolved_dependencies": [],
              "models": [], "counts": {"decoded_bytes": 0, "candidate_members": 0, "examined_models": 0,
                                         "skipped_models": 0, "analysis_work_units": 0},
              "runtime_parity_verified": False,
              "qualification": "Known source-backed patterns only. No full expression compilation, bone binding, native port, visual parity or performance is verified."}
    resources = {}
    parsed_cache = {}
    findings = {}
    gap_keys = set()
    occurrence_keys = {}
    consumer_keys = {}

    def provenance(resource):
        return {key: resource[key] for key in ("pack", "pack_index", "path", "sha256", "size")}

    def gap(code, reason, resource=None, pointer=None, **extra):
        item = {"code": code, "reason": reason, **extra}
        if resource is not None:
            item["source"] = provenance(resource)
        if pointer is not None:
            item["pointer"] = pointer
        signature = json.dumps(item, sort_keys=True)
        if signature not in gap_keys:
            gap_keys.add(signature)
            report["coverage_gaps"].append(item)

    def emit(rule, resource, pointer, consumer, *, matched=None, impact="potential"):
        key = (rule, resource["sha256"], pointer, str(matched))
        item = findings.setdefault(key, {"rule": rule, "impact": impact, "matched": matched,
                                        "source": provenance(resource), "pointer": pointer,
                                        "native_source": RULE_SOURCES[rule], "occurrences": [], "consumers": [],
                                        "binding_verified": False,
                                        "consumption": "candidate-not-runtime-verified",
                                        "resource_view_verified": report["resource_view_verified"]})
        occurrence = provenance(resource)
        occurrence_key = (resource["pack_index"], resource["path"])
        seen_occurrences = occurrence_keys.setdefault(key, set())
        if occurrence_key not in seen_occurrences:
            seen_occurrences.add(occurrence_key)
            item["occurrences"].append(occurrence)
        consumer_key = (consumer["root"], consumer["model"], consumer.get("model_index"), consumer.get("rule"))
        seen_consumers = consumer_keys.setdefault(key, set())
        if consumer_key not in seen_consumers:
            seen_consumers.add(consumer_key)
            item["consumers"].append(consumer)

    for pack_index, raw_path in enumerate(ordered_paths):
        path = Path(raw_path)
        pack = {"path": str(path.absolute()), "sha256": None, "priority": pack_index}
        report["packs"].append(pack)
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_PACK_BYTES:
                raise PackSafetyError("Only bounded regular ZIP packs are supported")
            pack["sha256"] = _hash_file(path)
            with zipfile.ZipFile(path) as archive:
                entries = _entries(path, archive)
                for name, entry, size in entries:
                    relevant = name == "pack.mcmeta" or (name.startswith(BASES) and name.endswith((".jem", ".jpm", ".properties")))
                    if not relevant:
                        continue
                    report["counts"]["candidate_members"] += 1
                    if (size > MAX_MEMBER_BYTES or report["counts"]["decoded_bytes"] + size > MAX_TOTAL_BYTES or
                            report["counts"]["candidate_members"] > MAX_MEMBERS):
                        report["resource_view_verified"] = False
                        gap("analysis-read-limit", "A relevant member exceeded the member/shared analysis budget.",
                            pack=pack["path"], path=name, size=size)
                        continue
                    with archive.open(entry) as stream:
                        data = stream.read(size + 1)
                    if len(data) != size:
                        raise PackSafetyError("Relevant member changed size")
                    report["counts"]["decoded_bytes"] += len(data)
                    if name == "pack.mcmeta":
                        try:
                            meta = _strict_json(data)
                            if not isinstance(meta, dict):
                                raise ValueError("Pack metadata is not an object")
                            if meta.get("filter") or meta.get("overlays", {}).get("entries"):
                                report["resource_view_verified"] = False
                                gap("pack-view-semantics-unverified", "Filters/format overlays are not applied by this scanner; resource winners are provisional.", pack=pack["path"])
                        except (ValueError, TypeError, AttributeError, RecursionError) as exc:
                            report["resource_view_verified"] = False
                            gap("pack-metadata-unparsed", f"Pack metadata could not establish the effective resource view: {exc}", pack=pack["path"])
                        continue
                    resource = {"pack": pack["path"], "pack_index": pack_index, "path": name,
                                "sha256": hashlib.sha256(data).hexdigest(), "size": size, "data": data}
                    if name in resources:
                        report["shadowed_resources"].append(provenance(resources[name]))
                    resources[name] = resource
            pack["sha256_after"] = _hash_file(path)
            if pack["sha256_after"] != pack["sha256"]:
                raise PackSafetyError("Pack changed during CEM inspection")
        except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, EOFError, zlib.error, lzma.LZMAError) as exc:
            report["resource_view_verified"] = False
            gap("pack-catalogue-incomplete", f"Pack could not be completely catalogued: {exc}", pack=pack["path"])

    report["resource_winners"] = [provenance(r) for _, r in sorted(resources.items())]
    if not scope_complete:
        gap("resource-scope-incomplete", "Dependencies unresolved here are unresolved in the provided scope, not proven globally missing.")
    gap("mob-bindings-unverified", "Mob layer aliases/fallback bindings and native expression compilation are not validated by this preflight.")
    if runtime_revision != REVISION:
        report["status"] = "target_capabilities_unverified"
        gap("target-capabilities-unverified", "The rule catalogue is pinned to f42; no known-gap facts are asserted for this other target.")
        return report

    def parse(resource):
        digest = resource["sha256"]
        if digest not in parsed_cache:
            try:
                parsed_cache[digest] = (_strict_json(resource["data"]), None)
            except (ValueError, RecursionError) as exc:
                parsed_cache[digest] = (None, str(exc))
        value, error = parsed_cache[digest]
        if error is not None or not isinstance(value, dict):
            gap("strict-json-scope", "Strict JSON analysis cannot establish native parsing/binding: " + (error or "not an object"), resource)
            return None
        return value

    def unsupported_nested(value, resource, pointer):
        stack = [(value, pointer)]
        work = 0
        while stack:
            work += 1
            if work > MAX_WORK:
                gap("analysis-nested-work-limit", "Nested scope inspection exceeded its work budget.", resource, pointer)
                return work
            node, here = stack.pop()
            if isinstance(node, dict):
                for key, child in node.items():
                    child_pointer = here + "/" + _pointer(key)
                    if key in ("animations", "model"):
                        gap("nested-consumption-unverified", "Nested animation/import placement is not treated as consumed native animation.", resource, child_pointer)
                    stack.append((child, child_pointer))
            elif isinstance(node, list):
                stack.extend((child, here + "/" + str(i)) for i, child in enumerate(node))
        return work

    # Native files.rs: EMF before OptiFine, flat before name/name.jem.
    roots = {}
    for base_index, base in enumerate(BASES):
        for name in sorted(resources):
            if not name.startswith(base) or not name.endswith(".jem"):
                continue
            rest = name[len(base):].split("/")
            if len(rest) == 1:
                stem, rank = rest[0][:-4], base_index * 2
            elif len(rest) == 2 and rest[1] == rest[0] + ".jem":
                stem, rank = rest[0], base_index * 2 + 1
            else:
                gap("root-form-unverified", "This JEM placement is not a supported native root form in this scanner.", resources[name])
                continue
            roots.setdefault(stem, []).append((rank, name))

    def animation_pairs(value, resource, pointer, charge, raw_remaining):
        if value is None:
            return [], 0, True
        if not isinstance(value, list):
            gap("animation-shape-unverified", "Animation value is not a list; native interpretation is not guessed.", resource, pointer)
            return [], 0, True
        pairs = []
        raw_count = 0
        for i, item in enumerate(value):
            # Native bake work includes rejected pairs and non-object items.
            if not charge(max(len(item), 1) if isinstance(item, dict) else 1):
                gap("analysis-animation-limit", "Animation traversal exhausted its work budget before target filtering.", resource, pointer)
                return [], raw_count, False
            if not isinstance(item, dict):
                gap("animation-shape-unverified", "Animation item is not an object.", resource, pointer + "/" + str(i))
                continue
            for target, expr in item.items():
                where = pointer + "/" + str(i) + "/" + _pointer(target)
                if not isinstance(expr, (str, int, float, bool)):
                    gap("animation-value-unverified", "Animation value is not a string or numeric/boolean constant.", resource, where)
                    continue
                if not charge(len(target) + (len(expr) if isinstance(expr, str) else 1)):
                    gap("analysis-animation-limit", "Animation text exhausted its work budget before target filtering.", resource, where)
                    return [], raw_count, False
                # The compiler counts raw bake-kept expressions before resolving targets.
                if raw_count >= raw_remaining:
                    gap("native-expression-limit", "Native compiler's raw expression cutoff leaves this and later expressions out.", resource, where)
                    return pairs, raw_count, False
                raw_count += 1
                if target.startswith(("#", "!")) or target in ("credit", "credits", "description"):
                    continue
                namespace, dot, prop = target.rpartition(".")
                valid_name = NAME.fullmatch(target) is not None
                recognized = (target in PARAMETERS or (valid_name and dot and prop and
                              (namespace in VARIABLES or namespace == "render" or prop in PART_PROPERTIES)))
                if not recognized:
                    gap("animation-target-unverified", "Assignment target/bone binding is outside this scanner's recognized target shapes.", resource, where)
                    continue
                pairs.append((target, expr, where))
        return pairs, raw_count, True

    for number, (stem, candidates) in enumerate(sorted(roots.items())):
        model_not_consumed = stem == "bed" or stem in MINECARTS
        if report["counts"]["analysis_work_units"] >= MAX_TOTAL_WORK and not model_not_consumed:
            report["counts"]["skipped_models"] += 1
            gap("analysis-global-work-limit", "Shared model analysis work budget reached.", model=stem)
            continue
        if number >= MAX_ROOTS:
            report["counts"]["skipped_models"] += 1
            gap("analysis-root-limit", "Candidate root analysis limit reached.", model=stem)
            continue
        candidates.sort()
        root_resource = resources[candidates[0][1]]
        root = parse(root_resource)
        # Strict-parser failure cannot establish that the native lenient parser falls back.
        if root is None:
            report["counts"]["skipped_models"] += 1
            gap("parse-fallback-unverified", "The preferred candidate's native parse result is unknown; lower candidates are not assumed active.", root_resource,
                candidates=[path for _, path in candidates])
            continue
        report["counts"]["examined_models"] += 1
        if root_resource["size"] > MAX_MODEL_BYTES:
            gap("analysis-model-byte-limit", "The root alone exceeds the per-model analysis byte budget.", root_resource)
            report["counts"]["skipped_models"] += 1
            continue
        model_report = {"name": stem, "source": provenance(root_resource), "consumers": [],
                        "native_distinct_path_bytes": root_resource["size"], "effective_assignment_occurrences": 0,
                        "raw_expression_occurrences": 0,
                        "binding_verified": False}
        report["models"].append(model_report)
        for _, path in candidates[1:]:
            report["shadowed_resources"].append({**provenance(resources[path]), "reason": "lower-priority same-name CEM candidate; preferred strict JSON parsed"})
        if "animations" in root:
            gap("root-animation-scope", "Root-level animations outside models[] are not treated as consumed.", root_resource, "/animations")
        entries = root.get("models", [])
        if not isinstance(entries, list):
            gap("model-shape-unverified", "models is not a list.", root_resource, "/models")
            continue
        if model_not_consumed:
            rule = "cem.bed-model-not-applied" if stem == "bed" else "cem.minecart-model-not-applied"
            renderer = "terrain-block-model" if stem == "bed" else "vanilla-minecart-model"
            consumer = {"model": stem, "root": root_resource["path"], "renderer": renderer}
            emit(rule, root_resource, "/models", consumer, matched=stem, impact="model-not-consumed")
            model_report["consumers"].append(consumer)
            # These renderer paths do not read this JEM at all. Inspecting its
            # animation entries as effective native assignments would mislead.
            continue
        earlier = {}
        closure = {root_resource["path"]}
        work = 0

        def charge(amount):
            nonlocal work
            limit = min(MAX_WORK, MAX_TOTAL_WORK - report["counts"]["analysis_work_units"])
            if amount > limit - work:
                work = max(work, limit)
                return False
            work += amount
            return True

        for index, entry in enumerate(entries):
            if index >= MAX_ENTRIES or work >= MAX_WORK or model_report["effective_assignment_occurrences"] >= MAX_ANIMATIONS:
                gap("analysis-model-work-limit", "Model/animation work limit reached; remaining entries were not analyzed.", root_resource, f"/models/{index}")
                break
            pointer = f"/models/{index}"
            if not isinstance(entry, dict):
                gap("model-entry-unverified", "Model entry is not an object.", root_resource, pointer)
                continue
            layers = [(entry, root_resource, pointer)]
            if "model" in entry:
                ref = entry["model"]
                if (not isinstance(ref, str) or not ref.endswith(".jpm") or ":" in ref or "\\" in ref or
                        any(part in ("", ".", "..") for part in ref.split("/")) or ref.startswith("/")):
                    gap("model-reference-unverified", "Only safe ordinary relative JPM references are resolved.", root_resource, pointer + "/model", reference=ref)
                    continue
                path = str(PurePosixPath(root_resource["path"]).parent / ref)
                imported = resources.get(path)
                if imported is None:
                    dependency = {"source": provenance(root_resource), "pointer": pointer + "/model", "reference": ref,
                                  "resolved_candidate": path, "status": "unresolved-in-provided-scope"}
                    report["unresolved_dependencies"].append(dependency)
                    gap("unresolved-model-dependency", "JPM reference is unresolved in the provided resource scope; this entry is not assumed consumed.", root_resource, pointer + "/model", reference=ref)
                    continue
                if path not in closure:
                    closure.add(path)
                    model_report["native_distinct_path_bytes"] += imported["size"]
                if model_report["native_distinct_path_bytes"] > MAX_MODEL_BYTES:
                    gap("analysis-model-byte-limit", "Distinct resolved paths exceed the per-model byte budget, even if their contents share a hash.", root_resource, pointer)
                    break
                data = parse(imported)
                if data is None:
                    continue
                if "model" in data:
                    gap("nested-import-unverified", "Native imports do not recursively resolve another model field in the JPM object.", imported, "/model")
                layers.append((data, imported, ""))
            base_id = entry.get("baseId")
            if base_id is not None:
                if isinstance(base_id, str) and base_id in earlier:
                    own_import = layers[1][1]["path"] if len(layers) > 1 else None
                    layers.extend(layer for layer in earlier[base_id]
                                  if not (own_import is not None and layer[1]["path"] == own_import and layer[2] == ""))
                else:
                    gap("base-id-unresolved", "baseId does not identify an earlier entry; no inherited keys are guessed.", root_resource, pointer + "/baseId")
            work += len(layers) + 1
            if work > MAX_WORK:
                gap("analysis-model-work-limit", "Inheritance layer work exceeded the analysis budget.", root_resource, pointer)
                break

            def key(name):
                return next(((obj[name], resource, here + "/" + _pointer(name))
                             for obj, resource, here in layers if name in obj), None)

            own_id = key("id")
            if own_id and isinstance(own_id[0], str):
                earlier.setdefault(own_id[0], list(layers))
            # Native skips entries with no effective string part, after recording their id.
            part = key("part")
            if not part or not isinstance(part[0], str):
                continue
            for obj, resource, here in layers:
                if "submodels" in obj:
                    work += unsupported_nested(obj["submodels"], resource, here + "/submodels")
                if work > MAX_WORK:
                    break
            if work > MAX_WORK:
                gap("analysis-model-work-limit", "Repeated inherited model work exceeded the analysis budget.", root_resource, pointer)
                break
            selected = key("animations")
            if selected is None:
                continue
            value, resource, where = selected
            pairs, raw_count, complete = animation_pairs(
                value, resource, where, charge,
                MAX_ANIMATIONS - model_report["raw_expression_occurrences"])
            model_report["raw_expression_occurrences"] += raw_count
            model_report["effective_assignment_occurrences"] += len(pairs)
            chain = [provenance(layer_resource) | {"pointer": here} for _, layer_resource, here in layers]
            consumer = {"model": stem, "root": root_resource["path"], "model_index": index,
                        "part": part[0], "chain": chain, "binding_verified": False}
            model_report["consumers"].append(consumer)
            if pairs and stem in BLOCK_ENTITIES:
                # Resolve each native consumer separately: book remains the lectern
                # fallback even when enchanting_book supplies the enchanting table.
                alias_targets = {
                    "book": (("book", "enchanting_book"), ("lectern_book", "lectern_book")),
                    "banner": (("standing_banner", "banner_base"), ("wall_banner", "banner_base"),
                               ("standing_banner_flag", "banner_flag"), ("wall_banner_flag", "banner_flag")),
                }
                targets = [target for target, preferred in alias_targets.get(stem, ((stem, None),))
                           if preferred not in roots]
                if stem == "banner":
                    targets = [target for target in targets if part[0] == "root" or
                               (part[0] == "slate") == target.endswith("_flag")]
                if part[0] not in BLOCK_PARTS[stem]:
                    gap("block-entity-part-unverified", "This part is not a mapped native part for the named block-entity target.", root_resource, pointer + "/part")
                elif not targets:
                    gap("block-entity-alias-binding-unverified", "Preferred roots cover each native consumer; this fallback is not assumed consumed if native parsing falls through.", root_resource, pointer)
                else:
                    consumer["native_block_entity_targets"] = targets
                    emit("cem.block-entity-animation-not-applied", resource, where, consumer, impact="known-engine-omission")
            for target, expr, location in pairs:
                namespace, _, prop = target.rpartition(".")
                if namespace == "render" and prop:
                    emit("cem.render-property-write-unused", resource, location, consumer, matched=target)
                if not isinstance(expr, str):
                    continue
                if any(mark in expr for mark in ('"', "'", "/*", "//", "#")):
                    gap("expression-lexical-scope", "Quoted/comment-like expression syntax is not interpreted by this scanner.", resource, location)
                    continue
                for token in NAME.finditer(expr):
                    if token.group() in STUBS and not expr[token.end():].lstrip().startswith("("):
                        emit("cem.stubbed-parameter-read", resource, location, consumer, matched=token.group())
            if not complete:
                break

        report["counts"]["analysis_work_units"] += work
        prop_path = str(PurePosixPath(root_resource["path"]).with_suffix(".properties"))
        properties = resources.get(prop_path)
        if properties is None:
            continue
        try:
            lines = properties["data"].decode("utf-8").splitlines()
        except UnicodeError:
            gap("properties-encoding-unverified", "CEM properties are not strict UTF-8.", properties)
            continue
        selectors = {}
        continued = False
        for line_number, line in enumerate(lines, 1):
            text = line.strip()
            was_continued = continued
            continued = (len(line) - len(line.rstrip("\\"))) % 2 == 1
            if not text or text.startswith(("#", "!")):
                continue
            if was_continued or "\\" in text:
                if text.startswith("models") or was_continued:
                    gap("properties-syntax-unverified", "Escapes/continuations are not interpreted as model selectors.", properties, f"line:{line_number}")
                continue
            if not text.startswith("models"):
                continue
            match = re.fullmatch(r"models\.([0-9]+)\s*=\s*(.*)", text)
            if not match:
                gap("properties-selector-unverified", "Model selector syntax is outside the supported subset.", properties, f"line:{line_number}")
                continue
            rule, value = match.groups()
            if len(rule) > 10 or int(rule) <= 0:
                gap("properties-selector-unverified", "Rule number is not a bounded positive integer.", properties, f"line:{line_number}")
                continue
            selectors.setdefault(int(rule), []).append((line_number, value))
        for rule_number, occurrences in selectors.items():
            if len(occurrences) != 1:
                gap("properties-duplicate-selector", "Repeated model selector is ambiguous to this scanner.", properties, rule=rule_number)
                continue
            line_number, value = occurrences[0]
            tokens = value.split(maxsplit=MAX_SELECTOR_TOKENS)
            values = []
            valid = bool(tokens) and len(tokens) <= MAX_SELECTOR_TOKENS
            for token in tokens:
                match = re.fullmatch(r"([0-9]{1,10})(?:-([0-9]{1,10}))?", token)
                if not match:
                    valid = False
                    break
                first = int(match[1])
                last = int(match[2]) if match[2] else first
                if not 1 <= first <= last <= 2 ** 31 - 1:
                    valid = False
                    break
                values.append([first, last])
            if not valid:
                gap("properties-selector-unverified", "Model indices/ranges are malformed, zero, or over the selector analysis budget.", properties, f"line:{line_number}")
                continue
            if any(last > 1 for _, last in values):
                consumer = {"model": stem, "root": root_resource["path"], "rule": rule_number,
                            "conditions": "opaque; conditional, not assumed triggered", "binding_verified": False}
                emit("cem.alternate-model-selection", properties, f"line:{line_number}", consumer,
                     matched=values, impact="conditional")
    report["findings"] = list(findings.values())
    return report
