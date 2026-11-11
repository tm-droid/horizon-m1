"""Group static evidence into review tasks without claiming runtime equivalence."""
from collections import Counter

# These implementations optimize Java-specific engine structures. Features and
# settings still require review; this is not a claim of Horizon parity.
JAVA_OPTIMIZERS = {"sodium", "lithium", "ferritecore", "c2me", "modernfix", "immediatelyfast", "krypton", "noisium"}
APPEARANCE_MODS = {"iris", "entity_model_features", "entity_texture_features", "continuity", "citresewn",
                   "bettergrassify", "skyboxify", "fabricskyboxes", "animatica", "polytone", "moremcmeta"}


def walk_reports(report):
    yield report
    for entry in report.get("nested_jars", []):
        child = entry.get("report")
        if isinstance(child, dict):
            yield from walk_reports(child)


def classify_mod(report):
    mod_id = report.get("id")
    if mod_id in APPEARANCE_MODS:
        role, priority = "appearance-feature", 1
        action = "Verify native support and every visible feature/configuration; port missing behavior explicitly."
    elif mod_id == "zoomify":
        role, priority = "utility-pilot", 2
        action = "Compare C-key zoom behavior/settings with native zoom; implement and verify any missing semantics."
    elif mod_id in JAVA_OPTIMIZERS:
        role, priority = "java-engine-optimizer", 4
        action = "Keep installed in Java. Review settings and user-facing features; do not mechanically port Java engine optimizations."
    else:
        role, priority = "feature-or-dependency-review", 3
        action = "Inspect actual features and dependencies before choosing native replacement, asset carry, or Rust implementation."
    return {"role": role, "priority": priority, "next_action": action,
            "java_installation_unchanged": True, "feature_review_required": True,
            "native_equivalence_verified": False}


def feature_for(item):
    code = str(item.get("code", "")).lower()
    evidence = item.get("evidence")
    if item.get("severity") == "error":
        return "input-or-export-blocker"
    if isinstance(evidence, dict):
        cats = set(evidence.get("categories", []))
        for category, feature in [("shader-integration-reference", "shader-integration"),
                                  ("hud-reference", "hud"), ("input-reference", "input"),
                                  ("tick-callback-reference", "tick"), ("networking-reference", "networking"),
                                  ("registry-reference", "registrations"), ("graphics-native-reference", "rendering"),
                                  ("fabric-event", "events")]:
            if category in cats:
                return feature
    for tokens, feature in [(("shader",), "shaders"), (("cem", "entity_model"), "entity-models-animation"),
                            (("ctm", "connected"), "connected-textures"), (("cit",), "custom-items"),
                            (("font",), "fonts"), (("sound",), "sounds"),
                            (("interpol", "texture"), "texture-features"),
                            (("overlay", "filter", "pack_metadata"), "pack-layer-semantics"),
                            (("alias", "duplicate", "unsafe"), "archive-paths"),
                            (("depend", "nested"), "dependencies"), (("metadata", "json"), "metadata")]:
        if any(token in code for token in tokens):
            return feature
    if code == "native-port-required":
        return "mixins-and-native-code"
    if code == "java_port_review":
        return "feature-inventory"
    return code or "unclassified-review"


def group_findings(items, classifications):
    """Every raw line is referenced once; samples are bounded, evidence is retained."""
    severity_rank = {"error": 0, "warning": 1, "review": 2, "info": 3}
    groups = {}
    for line, item in enumerate(items, 1):
        subject = str(item.get("subject", "instance"))
        feature = feature_for(item)
        scope = item.get("scope", "source")
        key = subject, feature, scope
        if key not in groups:
            classification = classifications.get(subject, {})
            priority = 0 if feature == "input-or-export-blocker" else classification.get("priority", 1 if subject.startswith("file/") else 3)
            groups[key] = {"subject": subject, "feature": feature, "scope": scope, "priority": priority,
                           "severity": item.get("severity", "review"), "finding_count": 0,
                           "raw_evidence_file": "raw-review-queue.jsonl", "raw_evidence_lines": [],
                           "codes": Counter(), "evidence_samples": [],
                           "next_action": (item.get("next_action", "Resolve this blocker first.") if priority == 0 else
                                           classification.get("next_action", item.get("next_action", "Review the source evidence and target feature support."))),
                           "status": "blocked" if priority == 0 else "needs-review"}
        group = groups[key]
        if severity_rank.get(item.get("severity"), 2) < severity_rank.get(group["severity"], 2):
            group["severity"] = item["severity"]
        group["finding_count"] += 1
        group["raw_evidence_lines"].append(line)
        group["codes"][str(item.get("code", "unknown"))] += 1
        if len(group["evidence_samples"]) < 5:
            group["evidence_samples"].append(item)
    result = []
    for i, group in enumerate(sorted(groups.values(), key=lambda g: (g["priority"], g["subject"], g["feature"], g["scope"])), 1):
        group["task_id"] = f"review-{i:04d}"
        group["codes"] = dict(sorted(group["codes"].items()))
        result.append(group)
    return result


def appearance_contract(selected, packs, shader, settings):
    features = []
    for layer in packs:
        if layer.get("selection") == "vanilla":
            continue
        features.append({"selection": layer.get("selection"), "order": layer.get("order"),
                         "sha256": layer.get("sha256"), "content_sha256": layer.get("content_sha256"),
                         "status": layer.get("status"), "category_counts": layer.get("category_counts", {}),
                         "detected_features": dict(Counter(feature_for(f) for f in layer.get("findings", [])))})
    return {"status": "preserved-inputs-runtime-unverified", "resourcepack_selection": selected,
            "layers": features, "shader": shader, "source_settings": settings,
            "priority_checks": ["Fresh Animations and EMF/ETF model, expression and texture behavior",
                                "Connected textures/custom items, fonts and sounds",
                                "Exact layer order, Mellow programs/overrides, distances and resolution"],
            "future_quality_candidate": "Complementary Reimagined; not selected or tested",
            "runtime_visual_parity_verified": False}
