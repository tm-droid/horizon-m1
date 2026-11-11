# Fresh Animations binding gaps — f42 / 2026-11-03 trial

The133 warnings in `outputs/horizon-runtime/tests/f42-cow-fa-sourceopts-r1/console.log` are concentrated in missing **standard model-part aliases**, rather than evidence that133 independent animation features need ports.102 are guardian/elder-guardian cascades. Source evidence supports a small versioned native binding-table extension that could address132 warnings; that count is a **prediction requiring validation**, not an observed repaired result. The remaining baby-piglin jacket read has no proven alias and may intentionally rely on unknown-name zero behavior.

Root agent observed the cow's distinctive Fresh Animations geometry/idle motion and60FPS in this isolated trial. That observation establishes neither whole-pack parity nor support for these failing entities. This audit launched nothing and changed no source, packs, original settings or runtime.

Target source commit: `f42ef42ef6ceccb3c6a20bea2481d87949a51c81`. Inputs: that build's prepared `entity-models.json`; only named FA JEM/JPM members needed below; installed EMF3.3.12 model-mapping class; the single actual trial log. No full JAR/mod/pack scan was repeated.

## Actual warning groups

| File/model label | Count | Observed symptoms | Highest confidence explanation |
|---|---:|---|---|
| guardian |51| body missing;50 unknown animation targets | body→head alias absent; skipped body owns custom target descendants |
| elder_guardian |51| same | same canonical skeleton and alias |
| salmon |9| fin_back_1/fin_back_2/tail missing, repeated3 times | one salmon JEM is used for3 size layers; three missing aliases |
| horse_armor |4| neck/mouth missing; neck.ty/rx unknown | horse alias family omits armor suffixes |
| skeleton_horse_armor |4| same | same; maps onto undead_horse_armor main layer |
| puffer_fish_small |3| tail/eye_right/eye_left missing | three exact aliases absent |
| happy_ghast_harness |3| body missing; body2.rx/rz read0 | body→harness alias absent; body2 is within skipped custom body |
| wolf |2| mane missing; mane.rz read0 | mane→upper_body absent |
| wolf_armor |2| same | same alias required for armor |
| tropical_fish_pattern_a |1| fin_top missing | native alias covers main a/b, excludes pattern a/b |
| tropical_fish_pattern_b |1| same | same |
| villager_baby |1| bodywear missing | baby uses bb_main, not adult jacket; current normalization erases baby distinction |
| piglin_baby |1| jacket.ry read0 | shared animation references adult-only custom jacket; not a verified missing vanilla alias |

Totals:24 `no part`,100 `unknown target`,9 `unknown name` warnings. Repeated warnings are retained evidence, not independent missing assets. The log says salmon for all3 applications; prepared salmon/small/large skeletons establish the3 potential consumers, but the warning alone does not identify each layer.

## Verified alias candidates

Installed `traben.entity_model_features.models.EMFModelMappings` bytecode was read with `javap -p -c`; its model-specific mappings match each target below. This establishes the actual installed Java compatibility convention, without guessing from a similar English name. Native exported nodes exist at the listed paths. Coordinates below are their exported local pose `[x,y,z,rx,ry,rz]`, rotations in radians. They are evidence of the destination frame; copying a translation alone is not a complete transform proof.

| Exact model context | Standard name → native target | Exported destination/frame | Installed EMF mapping bytecode offset |
|---|---|---|---|
| guardian, elder_guardian | body→head | `/head`, `[0,0,0,0,0,0]` |5800–5804 |
| wolf, wolf_armor (also mapped wolf_collar upstream) | mane→upper_body | `/upper_body`, `[-1,14,-3,1.5707964,0,0]` |2524–2529 |
| happy_ghast_harness | body→harness | `/harness`, `[0,24,0,0,0,0]` |2444–2449 |
| puffer_fish_small | tail→back_fin | `/back_fin`, `[0,22,1.5,0,0,0]` |7368–7373 |
| puffer_fish_small | eye_right→right_eye; eye_left→left_eye | `/right_eye`,`/left_eye`, each `[0,20,0,0,0,0]` |7344–7350;7356–7362 |
| tropical_fish_pattern_a/b | fin_top→top_fin | small pattern `/top_fin` `[0,20.5,-3,0,0,0]`; large `[0,16,-3,0,0,0]` |8563–8569;8645–8651 |
| salmon, and salmon applied to small/large layers | fin_back_1→top_front_fin; fin_back_2→top_back_fin; tail→back_fin | `/body_front/top_front_fin` `[0,-4.5,5,0,0,0]`; `/body_back/top_back_fin` `[0,-4.5,-1,0,0,0]`; `/body_back/back_fin` `[0,0,8,0,0,0]` |7858–7864;7870–7876;7882–7887 |
| horse_armor, skeleton_horse_armor (upstream also zombie_horse_armor) | neck→head_parts; mouth→upper_mouth | `/head_parts` `[0,4,-12,0.5235988,0,0]`; child `/upper_mouth` `[0,0,0,0,0,0]` |horse-family3690–3728; shared neck71–75 and mouth43–47 |
| **villager_baby only** | bodywear→bb_main | `/bb_main`, `[0.5,24,0,0,0,0]` |844–848 |

The main, small and large salmon layers have the same named fin hierarchy; the table's concrete poses are from main only. Likewise do not assume adult/baby frames are equal. Apply exact model/layer rules, never global substring replacements.

For guardian, FA's `body` entry has custom `body2`, `tail1_1` and `spine_1` descendants (plus others). The body's source translate is `[0,-8,0]`, invertAxis `xy`; it must remain unchanged. Current f42 builds its custom bone, then cannot find native body and skips attachment. The later animation binder cannot discover the now-detached custom descendants. A verified body→head native alias attaches the authored subtree to the standard EMF target at the zero-pose head and preserves source geometry/transforms. It plausibly removes all51 warnings per guardian species through one mapping, rather than50 per-expression patches.

Harness is analogous: skipped body contains `body2`, so adding a standalone body2 alias would mask the underlying omitted subtree and be wrong. The native harness pivot24 must remain intact; its source body subtree has its own authored transforms. Wolf mane and salmon fin entries are empty placeholders in this FA version: they still matter because replacement clears vanilla geometry and animations can read their canonical pose. Do not omit them merely because they contain no boxes.

## Small native pattern; unsafe pack rewrite

Preferred implementation task is a **model-scoped alias table extension** in `mobs/cem.rs::vanilla_part`, shared by entry binding and animation lookup. Preserve exact model identity where necessary: `CemLayer::build` currently strips `_baby` before resolving aliases, which makes villager_baby bodywear erroneously use adult jacket. Consult an exact-model override before generic baby normalization, or pass both identities; avoid a broad rewrite of unrelated naming rules.

The existing binding pipeline already applies `vanilla_part` when finding entry destinations, collecting named replacement nodes and resolving expression references. Extending this common resolver keeps those operations consistent. Do not rename exported skeleton nodes: vanilla animations still expect head, upper_body, head_parts, etc. Do not move vertices, zero pivots, flatten parents, add guessed synthetic body nodes, or remove warning-producing expressions.

**Changing only JSON `part` is not semantically equivalent.** `Names::find` prefers a resolved vanilla node before an authored custom ID. If guardian part body becomes head but ID stays body, later body.rx can start binding the custom body bone instead of the canonical head. The two have different local frames. Global string replacement additionally corrupts custom IDs, path-qualified references, variable names, strings and other model contexts. A converter should emit a versioned `cem.missing-standard-part-alias` task with evidence and required native alias, not silently transform pack bytes. A future adapter needs a parsed model/expression binding proof and a preserved-source output; the current evidence favors an engine binding fix.

Other guards: alias targets must exist **uniquely in the intended layer**; preserve first-depth lookup semantics, authored ID precedence and `this`/`part` scope; compare original parent chains and all9 pose components; keep attach flag and replacement visibility rules unchanged. Adult aliases must not leak into baby/armor/pattern contexts. An alias successful on the main layer does not prove a fallback layer has the same skeleton.

## Remaining baby-piglin read

`piglin_animations.jpm` reads `jacket.ry==0` in two melee-state expressions. Adult `piglin.jem` defines custom ID jacket at `/models/10`; `piglin_baby.jem` does not. Native exported baby skeleton also has no jacket node, and installed EMF's baby mapping does not supply one. Unknown-name reads become0 in f42, intentionally matching its documented EMF policy; both comparisons then evaluate true for that term. Keep the warning and classify it as **unresolved/shared-expression zero fallback**, not a proven visual failure or invitation to alias jacket→body. Establish Java baby behavior before making a structural change.

No inspected failed part requires a demonstrated new skeleton hierarchy: all24 omitted standard parts have evidence-backed aliases. That statement is bounded to this log and these assets; invisible hierarchy/pose problems can remain after warnings disappear.

## Evidence and acceptance

Pinned source: [alias table](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/mobs/cem.rs#L408), [context/binding/replacement](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/mobs/cem.rs#L562), [canonical-first animation names](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/mobs/cem_anim.rs#L244), [zero fallback](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/mobs/cem_anim.rs#L377), [unmodified custom poses/IDs](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/mobs/cem.rs#L670), [native guardian head/tail/spike animation](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/mobs/guardian.rs#L448). Installed Java source project identified by its own metadata: [EMF repository](https://github.com/Traben-0/Entity_Model_Features); online HEAD is not used as proof of installed3.3.12 behavior.

Local SHA256 evidence: prepared `entity-models.json` `a09df39fba73d2f63d189b3c96c689692b1024838eab9f84662fb3759d652497`; installed EMF JAR `4a8b04d26c94909a3ba9f08972fb475e7d39f715f666f99a294017baaa37cb69`. Reproducible read command: `java/java-runtime-epsilon/bin/javap -p -c -classpath instances/Tanush-26.3/minecraft/mods/entity_model_features-3.3.12-26.3-fabric.jar traben.entity_model_features.models.EMFModelMappings`; exit0. This disassembles class metadata and executes no EMF/game code. Scratch output: `/private/tmp/emf-3.3.12-model-mappings.javap`.

Acceptance for a later isolated native fix: exact resolver assertions for each table row and negative neighboring contexts; binding targets/consumers resolve to expected canonical nodes; original pack hashes and all authored geometry/UV/transforms unchanged; guardian descendants become reachable and all100 unknown-target cascades disappear; no duplicate vanilla eye/spine/fin/clothing surfaces; pose matrix checks preserve pivot/parent composition at zero and nonzero rotations; shader-independent scene checks cover guardian/elder tail/eye/spines, harness riding, wolf shake, three salmon sizes, puffer inflation, tropical patterns, horse armor with head motion, villager baby clothing. Distinguish fewer warnings from parity and keep baby-piglin fallback visible. Native source/build/runtime acceptance remains pending with the root's serial device queue.

Audit check: focused Python warning grouping/document assertions completed with exit0:24 no-part,100 unknown-target,9 unknown-name; required alias/context markers present. This is a log/document check, not native behavior testing.
