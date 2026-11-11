# Versioned CEM preflight: minimum useful implementation

Target: **`f42ef42ef6ceccb3c6a20bea2481d87949a51c81`**, researched2026-11-03. This is a shader-independent **analysis/report stage**, not a complete CEM validator, Rust code generator or EMF/ETF port. It must neither rewrite pack bytes nor classify a copied file as working behavior.

Only this document was changed by this unit. Verification consisted of bounded reads of cached pinned source and the named staged ZIP members below; no builds, tests, installs or device workloads were run.

## 1. Versioned capability facts

Store facts under the exact target revision, with their source URLs/line anchors. A different target yields `target_capabilities_unverified`; do not silently carry these gaps forward as facts about all Horizon versions. The f42 hook constant is359, but these asset findings depend on the source revision, not just a minimum hook number.

| Fact | Exact tokens / condition | Source |
| --- | --- | --- |
| Registered parameters returning zero | Bare expression identifiers `height_above_ground`, `fluid_depth_up` | [parameter registration43–71](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/mobs/cem_anim.rs#L43), [zero branch649](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/mobs/cem_anim.rs#L649) |
| Render properties do not affect rendering | Effective animation assignment targets with namespace **exactly** `render`, e.g. `render.shadow_size`; these receive VM slots but have no renderer consumer | [slot routing303–314](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/mobs/cem_anim.rs#L303), [module contract1–10](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/mobs/cem_anim.rs#L1) |
| Block-entity CEM animations are not evaluated | Consumed block-entity model plus a nonempty effective animation list, including inherited JPM animations | [block-entity implementation1–12](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/block_entity_cem.rs#L1), [actual target names102–141](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/block_entity_cem.rs#L102) |
| Alternate JEM meshes are not selected | Effective CEM `.properties` selector `models.N` requests an index greater than1; **N is the rule number, not the requested model index** | [rule parser222–255](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/mobs/cem.rs#L222) |

Useful vocabulary, without implying semantic completeness:

- Part properties are `tx ty tz rx ry rz sx sy sz visible visible_boxes` ([source16–28](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/mobs/cem_anim.rs#L16)).
- `var`, `varb`, `global_var`, `global_varb` are variable namespaces. A token such as `var.height_above_ground` is **not** the bare stubbed parameter. `render` is a separate namespace; `var.render` is not a render-property assignment.
- Current block-entity CEM input stems are `chest`, `chest_left`, `chest_right`, `trapped_chest`, `trapped_chest_left`, `trapped_chest_right`, `ender_chest`, `shulker_box`, `banner_base`, `banner`, `banner_flag`, `head_skeleton`, `head_wither_skeleton`, `head_zombie`, `head_creeper`, `head_dragon`, `head_piglin`, `head_player`, `bell`, `enchanting_book`, `book`, `lectern_book`, `conduit`, `decorated_pot`. These are literal names from the target table, not prefix patterns. **`chest_boat` is not a chest block entity; `chest_large` is not itself a direct target in that table.** Auxiliary files need a verified consuming chain before receiving this finding.

The77 registered parameter tokens, extracted only from the pinned `params!` block, are below. Registration is **not** an implementation-status allowlist; the first pass audits only the two specified stubbed reads.

```text
limb_swing limb_speed age head_yaw head_pitch swing_progress health max_health hurt_time death_time
pos_x pos_y pos_z rot_x rot_y id time day_time day_count frame_time frame_counter dimension
player_pos_x player_pos_y player_pos_z player_rot_x player_rot_y rule_index anger_time anger_time_start
distance move_forward move_strafing height_above_ground fluid_depth fluid_depth_down fluid_depth_up
is_aggressive is_alive is_burning is_child is_glowing is_hurt is_in_hand is_in_item_frame is_in_ground
is_in_gui is_in_lava is_in_water is_invisible is_on_ground is_on_head is_on_shoulder is_ridden is_riding
is_sitting is_sneaking is_sprinting is_tamed is_wet is_climbing is_blocking is_crawling is_jumping
is_swimming is_right_handed is_swinging_right_arm is_swinging_left_arm is_first_person_hand is_using_item
is_holding_item_right is_holding_item_left is_paused is_hovered is_player_first_person
is_player_third_person is_player_third_person_reversed
```

## 2. Analyze the effective resource view

Input must identify the ordered selected packs and their hashes, target revision, whether the provided scope includes every selected layer, and whether implicit mod-resource layers are known. Reuse validated ZIP-entry catalogues; do not extract archives or introduce new case-folded matching.

Resolve exact resource paths across **all provided layers**, later selected packs winning for the same path. Honor known applicable format overlays and filters. If those semantics are not implemented for a pack, emit a coverage gap and label affected winners uncertain. Do not scan every ZIP independently and call a lower-pack resource missing.

CEM root selection also has its own rules: EMF versus OptiFine paths, nested `name/name.jem` forms, and parse-fallback candidates. Follow the pinned loader's candidate order or report it as unverified. Do not emit active findings for a proven shadowed root; retain its occurrence as shadowed evidence if useful. A failed strict-JSON parse is an analyzer limitation, **not** proof Horizon rejects that file: its CEM parser uses its own JSON representation. [root selection](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/mobs/cem.rs#L55).

### Dependency and inheritance minimum

For a parsed JEM, handle `models[]` entries in order. Native property precedence is **entry's own key, then its referenced JPM's key, then an earlier `baseId` entry**; presence wins even when the value is empty or null. An explicit `animations:[]` therefore masks imported animations. The first earlier definition of an ID is the native `baseId` lookup; do not substitute a last-ID-wins dictionary. [layer lookup116–126](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-optifine/src/cem/model.rs#L116), [import/base handling203–238](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-optifine/src/cem/model.rs#L203).

`model` references resolve relative to the referring JEM according to the target's resource-path rules. The first implementation may support safe ordinary relative JPM names and explicitly defer other forms. Missing, ambiguous, unsafe, unsupported-form or out-of-scope dependencies must remain visible. Call a reference **unresolved in the provided scope** unless completeness and path resolution are both established; do not assert it is globally absent from the user's setup.

Do not invent recursive native imports. In f42, the root entry imports a JPM object; another `model` field inside that object is not recursively resolved by this path. Likewise, recursively finding `animations` anywhere in JSON does not establish that the native loader evaluates it. A nested `submodels[].animations`, root-JEM `animations` outside consumed model entries, or nested import declaration should receive an analysis-scope note, not be silently treated as an effective animation or silently ignored as clean. [JPM read284–313](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-optifine/src/cem/model.rs#L284), [animation extraction252](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-optifine/src/cem/model.rs#L252), [bone construction404–486](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-optifine/src/cem/model.rs#L404).

## 3. Detection rules

Native compilation resolves an assignment target **before** its expression. Ignore values of obviously non-target metadata keys such as `#comment` or bare `credit`; named variable namespaces and registered bare parameters are recognizable, while bone targets still require runtime binding. Syntactically valid but unverified bone bindings must remain qualified rather than called compiled/active. [target-first handling377–380](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/mobs/cem_anim.rs#L377).

1. **`cem.stubbed-parameter-read`**: tokenize only effective animation expression values. Match a complete bare name equal to either stubbed parameter, in a variable-read position. The native name grammar starts with ASCII letter/underscore and continues with ASCII alphanumeric, underscore, dot or colon; substring searches are wrong. Exclude a matched name used as a function-call name. Credits, descriptions, filenames, target keys and arbitrary JSON strings are not expressions. Native animation values may also be numeric or boolean constants; these contain no parameter reads. This is a **potential dependence**, not proof of visible failure: a constant-dead branch may contain a token. No control-flow solver is required. [lexer304–340](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-optifine/src/cem/expr.rs#L304).
2. **`cem.render-property-write-unused`**: inspect assignment **targets** in effective animation objects. Require a nonempty property with the portion before the **last dot exactly `render`**, mirroring native slot routing. Reads of `render.x` may participate in the VM and should not be mislabeled as an unsupported write. A text value merely mentioning `render.shadow_size`, target `var.render`, or malformed multi-dot target `render.foo.bar` does not match this rule.
3. **`cem.block-entity-animation-not-applied`**: classify the consuming model using the verified block-entity stem table, then check effective animation pairs, including a JPM inherited by a consumed entry. Record that the engine does not run those animations; do not claim every assignment would necessarily change pixels. Unknown/auxiliary bindings remain unverified. In particular, never classify models by a `chest*` prefix.
4. **`cem.alternate-model-selection`**: inspect CEM properties beside a selected JEM, not unrelated random-texture properties. Parse a positive rule number and a bounded whitespace list of integer indices/ranges in its value. `models.104=1` is base mesh1; `models.1=104` requests an alternate. Lists/ranges containing only1 do not match. Any requested index>1 is a conditional capability requirement even if an alternate file is absent. Preserve opaque rule conditions; do not infer that a named/nighttime rule always triggers. Zero, malformed selectors, unsupported property syntax, escapes/continuations or ambiguous duplicates should produce an explicit unresolved/parse-scope status rather than guessed indices or a clean result. Avoid expanding enormous ranges. Common `stem<N>.jem` paths can be offered as candidates, not asserted for every naming convention.

5. **`cem.bed-model-not-applied` and `cem.minecart-model-not-applied`**: check the exact `bed` and seven minecart model stems. The pinned f42 terrain bed renderer and minecart renderer bypass those JEM inputs altogether. Report the preferred supplied file without treating its animation entries as executed native assignments. A separate terrain overlay can compensate for the bed model; the rule still describes the JEM path itself.

Do not expand this minimum into an allowlist that rejects every unfamiliar expression identifier. Bone references, authored variables, functions and native state require more context. The stage reports known source patterns plus coverage gaps; it does not prove expressions compile or bind.

## 4. Real bounded fixtures from the staged setup

These observations cover only the named members in the three priority ZIPs. Hashes below identify member bytes, not the whole pack.

| Fixture | Verified observation | Required outcome |
| --- | --- | --- |
| FA `optifine/cem/villager.properties` (SHA256 `5684410196f3a4fcc3ba32701794e10092ae2e521e6733cfdf6cf7d5bab2c540`) | `models.1=1` plus sleeping-position condition | **No alternate-mesh finding.** This is the state-rule pattern f42 already supports. |
| Harness `optifine/cem/happy_ghast.properties` (`0a0c1f841a6495a6bf1504763fa3baf5effc95a5f3e9b49ca3e1f0be2d6535a3`) | Selectors104/100/101/102/103, with names and daytime conditions; numbered meshes exist in that ZIP | Alternate-selection findings with conditional impact and those selectors, not a claimed unconditional rendering error. |
| Harness `happy_ghast_harness.properties` (`dc662f93b911ff21097e487249c71e4f4624d0d76c29391205b836560133378c`) | Rules request index2 | Flag alternate selection; key numbers must not be confused with model indices. |
| Harness `happy_ghast.jem` → `happy_ghast_animations.jpm` | The higher Harness ZIP has the reference but not that JPM; the lower FA ZIP supplies it | Cross-pack resolution succeeds. No per-ZIP missing-file finding. |
| Harness `happy_ghast_harness.jem` and `happy_ghast_harness2.jem` → `happy_ghast_harness_animations.jpm` | That filename is absent from the **three inspected priority ZIPs**, including overlay-prefix filename checks | Report unresolved within this subset. Other selected packs or implicit resources were not exhaustively catalogued; do not call it globally missing. |
| Extension `emf/cem/chest.jem` (`cbe59c4489b2e355a9a67013bf5786952b3878ac7589431a1db0dce5e55d8f79`) → `chest_animations.jpm` (`c5e7448016b5bd3b87c6dbada0d62c8e939f03937ea16f01b3317af3e073cffb`) | Root entry imports JPM animations without an own-key override. JPM has18 assignments, including `base.rx`, `base.tx`, `base.tz`; lid entry has another local variable assignment | Block-entity animation finding must include the external-JPM evidence chain; do not inspect only inline JEM animation text. |
| FA `bat_animations.jpm`, `allay_animations.jpm`, sampled zombie JEM; extension chest JPM; sampled Harness harness2 JEM | The inspected animation values have **no** exact stubbed-parameter reads or render-property writes | Do not invent these findings because the native capability catalogue lists them. This does not establish the rest of the packs are clean. |

Original relative layer order is FA42, extensions43, Harness46 in `appearance-contract.json`. The effective resource view, not those numbers hardcoded into the implementation, is authoritative.

## 5. Small synthetic regression fixture set

No tests were run for this specification. An implementation should cover:

| Input variation | Expected classification |
| --- | --- |
| Effective `root.ty = height_above_ground`; `root.tx = fluid_depth_up` | Two exact stub-read occurrences, linked to one capability task per name. |
| `var.height_above_ground`, `fluid_depth_up_extra`, `custom:height_above_ground` | No exact stub-read match. |
| Credits string contains all four pattern names; unrelated JSON has an `animations` key | No active known-gap findings; unrelated placement is not native consumption. |
| An animation object's `#comment` value mentions a stub; an expression contains unsupported quoted text | No confirmed active stub read from the comment; lexical/target uncertainty stays explicit rather than scanning arbitrary text. |
| Effective `render.shadow_size = 0.5`; numeric/bool animation values | Render-write finding for that target; constants are valid input shapes. |
| `var.render = 1`, or expression reads `render.shadow_size` without assigning it | No render-write finding. |
| `models.104=1`, `models.1=1 1`, `models.1=1-1` | No alternate selection. |
| `models.1=104`, `models.2=1-3` | Alternate requested; range checked without unbounded expansion. |
| `models.1=0`, malformed range, relevant escaped/continued key | Explicit unresolved selector/parser scope; no fabricated mesh index or clean certificate. |
| Root entry has `animations:[]` or null over a JPM containing a gap | The own key masks the JPM list; no effective imported-gap finding for that consumer. |
| Two roots share a JPM, which has one gap; a higher pack replaces it | Analyze the winning JPM once, retain both consumer chains; no active finding from the shadowed bytes. |
| Missing/forward/ambiguous `baseId`, nested import or nested submodel animation | Preserve a coverage/inheritance note; do not invent native recursive resolution. |
| Known chest imports animated JPM; `chest_boat` has the same inline list | Chest gets the known block-entity gap; boat is not classified by prefix. |
| Traversal reference, conflicting ZIP member, cycle-like declaration, input/graph budget reached | Explicit coverage gap with source location; no extraction, rewrite, silent truncation or successful-port claim. |

## 6. Output, bounds and acceptance

Minimum report fields: target revision; rule-set version; ordered input-pack hashes and scope-completeness facts; resource-winner provenance; findings with pack/member hash, JSON pointer or property line, consumer/reference chain, matched token/selector, capability source link and impact (`potential`, `conditional`, or known engine omission); unresolved dependencies; analysis-limit records; examined/skipped counts. Deduplicate a shared source finding by target/rule/member-hash/pointer while retaining every consumer. Do not create one task per repeated consumer or drop their evidence.

Native bounds are **4MiB total JEM/JPM bytes per model**,1024 model entries,65536 model-work units; the animation compiler stops after4096 expressions, and its expression parser bounds nesting64/nodes1024. These are evidence about the engine, not proof an independent scanner implements the same parser. [model bounds85–91](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-optifine/src/cem/model.rs#L85), [expression-count bound344](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/mobs/cem_anim.rs#L344), [expression parser bounds14–20](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-optifine/src/cem/expr.rs#L14).

Suggested independent scanner defaults:4MiB/member,4MiB/active-model dependency closure,64MiB shared decoded CEM bytes,512 candidate roots and64 JSON nesting levels. These are proposed analysis budgets, not upstream defaults. Reuse cached parse results by content hash, but keep resource identity/pack provenance and every reference context distinct. Native JPM byte accounting is per distinct resolved path, not per content hash; applying shared animations in several model entries also costs native model/animation work repeatedly. Keep analysis-read budgets separate from runtime-bound estimates. Every refusal or budget hit leaves a visible coverage gap. Duplicate JSON keys or unsupported lenient syntax must not be silently normalized into a guessed native interpretation.

Acceptance for this stage is **accurate bounded findings and unchanged source/export bytes**. An empty finding list means only that no configured pattern was detected in examined inputs. Runtime model binding, complete CEM semantics, Java visual parity and performance remain separate checks. Never remove expressions, rename alternate meshes into the base model or rewrite assets as an automatic "fix" for these findings.
