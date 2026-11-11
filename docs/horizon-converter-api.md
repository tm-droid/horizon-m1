# Horizon migration integration: pinned source findings

Research date: 2026-11-02. Revision: [`e6e12d40c522b8f5ee8740dd861c96689023737a`](https://github.com/horizon-rust/horizon/commit/e6e12d40c522b8f5ee8740dd861c96689023737a), `main` when queried. Source inspection only; no build, install, game launch or instance changes. Claims below describe this revision, not a tested migration.

## Recommended integration

Use Horizon's existing **`horizon-port-pack`**, with an analyzer that adds evidence and manual-port tasks. It already imports `.mrpack`, CurseForge ZIP and installed-instance directories, inventories mods, carries supported data and writes coverage. Its automatic `port` selects only `class == "content" && tier == "data"`; arbitrary Java logic is not translated. [CLI implementation](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-port-pack/src/main.rs#L1-L34), [selection and pipeline](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-port-pack/src/pipeline.rs#L323-L355).

Exact commands for an **already-built** pinned binary (examples, not executed):

```text
horizon-port-pack import <pack-or-instance> <fresh-work-directory>
horizon-port-pack inventory <work> --offline
horizon-port-pack carry <work> [--resources <prepared-root>] [<mod-id>...]
horizon-port-pack report <work>
horizon-port-pack check <single-jar> <output-directory>
```

Online integration also supports `fetch <work> [--from <local-folder>] [<mod-id>...]` and `port <pack> <work> [--from <folder>] [--resources <root>]`. **`port --offline` is not download-free**: only inventory consumes that flag; `port` still calls resource-pack and jar fetching. Use the separate local stages above when downloads are unwanted. `--resources` constrains templates to prepared Horizon tables. [Argument handling](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-port-pack/src/main.rs#L43-L94).

Do not point outputs at the Java instance. Import reads the source and writes staging plus `pack.json` under work; bad resource-pack staging is logged and may still leave a successful mod import, so inspect its report. [Import writes](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-port-pack/src/pipeline.rs#L24-L42).

## Supported-copy versus manual-port matrix

| Input | Automated result | Required qualification / remaining work |
|---|---|---|
| Java resource-pack folder/ZIP | Copy intact to staging, then Horizon `resourcepacks/` | Enable through game screen; copying is not rendering verification. |
| Jar `assets/` and `data/` | Upstream carry into API 0.2 folder content mod; supported recipe/loot/model upgrades | Verify references and namespace ownership; inspect `outside/`, unreadable files and unknown registrations. |
| Simple blocks/items | Vanilla-template content declarations | Templates inferred from blockstates are **guesses** without oracle facts; preserve provenance and mark partial. |
| Fabric/NeoForge Java classes, Mixins, event callbacks | Inventory classes, dependencies, source entrypoints and affected features | Manual Rust source port and behavior tests; no JVM/Fabric execution in Horizon. |
| HUD, input, freecam, minimap, recipes UI | Candidate native hook mapping and task brief | Author/test real native mixin bundle; availability of a hook does not prove a port. |
| Iris/OptiFine shaderpack or pack GLSL | Preserve source, classify features | Shaderpack conversion pending upstream; pack post chains unsupported and only GUI text core shader path partially works. |
| Java mod configs, scripts, keybindings | Keep separately as source evidence | No generic settings/behavior translation; upstream import does not copy scripts or `options.txt`. |

Evidence: [carry contract and report](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-port-pack/src/carry.rs#L1-L58), [Java code boundary](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/docs/mods.md#L3-L28), [resource staging/profile behavior](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/docs/modpacks.md#L335-L356).

## Exact usable schemas and hooks

Content package: `.hmod` or folder containing `horizon-mod.toml`, `assets/`, `data/`; install under `horizon-mods/`, enabled separately in `horizon-mods.txt`. Manifest fields: `id`, `name`, `version`, `description`, `authors`, `api = "0.2"`, `side = "both"`, `capabilities = ["registries"]`, optional `namespaces`. Unknown fields are refused. [Manifest example](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/docs/mods.md#L55-L78).

Registrations belong in `data/<id>/horizon/{block,item,mob_effect,creative_tab,entity_type,menu}/*.json`. Block JSON requires `template`; optional fields include `properties`, `shapes`, `state_properties`, `default_state`, `connects_to`, `thickness`, `wood_type`, `wall_block`, `item`, `components`. Item JSON requires `template`; optional fields are `max_stack_size`, `rarity`, `components`, `crafting_remainder`. The filename determines the registry ID; do not invent an `id` JSON field. [Authoritative block codec](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-mods/src/content.rs#L160-L189), [item codec](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-mods/src/content.rs#L255-L279).

Native code is Rust source transformed by `horizon-mixins` before game compilation, not dynamically loaded Java or WASM. Bundle uses `horizon-mixin.toml` plus Rust helpers; native package `.hnmod` has `horizon-native.json`: `schema=1`, `id`, `version`, `game`, exact 40-character `horizon` and `mixins` revisions, optional integer `hooks`. `mod.wasm` is explicitly rejected. [Native package schema](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-mods/src/index/native.rs#L1-L65), [build/compatibility contract](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/docs/native-mods.md#L3-L50).

Current `NATIVE_HOOKS_API = 153`. Verified hook signatures include `native_tick(&mut self)`, `native_hud(&mut self, batch: &mut HudBatch, corners: &mut Corners)`, `native_key(&mut self, key: &str, pressed: bool)`. They are `pub(super)` game source hooks, not a standalone external Rust library API. [API constant](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-client/src/game/native_hooks.rs#L528), [tick](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-client/src/game/native_hooks.rs#L1538), [HUD](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-client/src/game/native_hooks.rs#L1698), [key](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-client/src/game/native_hooks.rs#L1792).

A useful analyzer emits a per-mod manual task with source class/Mixin targets, dependencies, config semantics, observed assets, candidate hook names/signatures, behavior acceptance cases and explicit unknowns. This is an integration recommendation, not an upstream schema. Generate no “converted Rust” from class names alone. For actual bundles, use the upstream-linked [native template](https://github.com/horizon-rust/horizon-native-mod-template) and separately pin/inspect its current mixin schema before generating files.

## Resource-pack compatibility limits

Target formats are resource **97.1**, data **121.0**, Minecraft **26.3**. Preserve `pack.mcmeta`; do not rewrite its range merely to suppress compatibility warnings. Packs layer in selection order, later winning; languages, sounds, fonts and atlases merge as resource stacks. [Version constants](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-core/src/version.rs#L5-L15), [load/overlay behavior](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/docs/resource-packs.md#L3-L28).

Upstream documents support for textures, blockstates/models, item definitions, sounds, languages, bitmap/space/unihex/reference fonts, atlases, particles, equipment, custom entity models, connected/random/emissive/blinking textures and CIT. Flag these documented gaps: animation interpolation; pack blur/clamp overrides; some HD GUI scaling; TrueType/custom component-selected fonts; credits/end poem; villager hats; worn armour trims; locator styles; GLSL post effects; core shaders beyond GUI text. These are source/documented claims, not local visual validation. [Detailed feature matrix](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/docs/resource-packs.md#L30-L85).

## Reports and bounded handling

Consume upstream JSON rather than parsing terminal prose:

- `coverage.json`: array of `{key,name,class,tier,license,license_kind,status,reason}`; serialized `status` is `ported`, `partial`, `not-yet`, `not-needed`. [Schema](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-port-pack/src/report.rs#L14-L51).
- `check.json`: `{mod_id,name,version,loader,license,verdict,summary,ports,skipped,depends,namespaces,code}`; verdict serializes `works`, `partly`, `no`, distinct from display strings. [Schema](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-port-pack/src/check.rs#L16-L55).
- `resourcepacks.json`: `{files: {<path>: {state,detail}}}`, state `available|missing|failed|conflict|unsupported`; copied packs remain partial in coverage. [Schema/path checks](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-port-pack/src/resourcepacks.rs#L11-L75).

Resource staging limits: 65,536 files, 512 MiB combined resource bytes; links refused, paths restricted. Downloaded resources/jars are bounded to 512 MiB each; SHA-1 is checked when supplied, so do not report every downloaded jar as cryptographically matched when its index omitted a hash. Native builds execute mod code and require a separate reviewed action; import/carry are data stages. [Resource staging limits](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/docs/modpacks.md#L337-L356), [conditional hash verification](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-port-pack/src/fetch.rs#L217-L249).

Verification: GitHub API resolved the revision; pinned raw source files were inspected without full checkout. Tool binaries, compilation, generated content acceptance and in-game rendering remain unverified.

## Obtaining a real converter on Apple Silicon

No standalone `horizon-port-pack` asset was found in the latest 100 official releases inspected on 2026-11-02. The game release workflow builds/packages client, control, preparation and server binaries, excluding this CLI. [Build list](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/.github/workflows/game-build.yml#L152-L156).

An official prebuilt **launcher** does embed the porting library. [`launcher@0.2.37`](https://github.com/horizon-rust/horizon/releases/tag/launcher%400.2.37) publishes `horizon-launcher-macos-arm64.zip` (14,547,266 bytes). Commands are `horizon-launcher modpack import <PATH>` then `horizon-launcher modpack port <slug> --from <local-folder>`. This is not a standalone offline/check interface: import queries Modrinth metadata and writes the launcher's `ports/<slug>` staging/profile; port may download. [CLI](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/launcher/src/cli.rs#L197-L220), [side effects](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/launcher/src/modpacks.rs#L206-L237).

For a separately controlled CLI, obtain the pinned source archive and run `cargo build --locked -p horizon-port-pack --profile fast`; the executable is `target/fast/horizon-port-pack`. Rust **at least 1.95** is required by `horizon-mods`, despite the tool declaring 1.86; other dependencies may impose higher requirements. It inherits MIT licensing. Dependencies are serialization, ZIP, hashes, HTTP/TLS and content rules; this selection does not build the game renderer. Workspace inheritance, lint definitions, lockfile and local patch paths must remain available, so copying only the crate is insufficient. [Tool manifest](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-port-pack/Cargo.toml#L1-L22), [dependency MSRV](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-mods/Cargo.toml#L1-L16), [workspace/profile](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/Cargo.toml#L43-L85). Build duration, expanded source, dependency downloads and disk/RAM use remain unmeasured; no bounded estimate is established.

Use the separate local import/inventory/carry/report commands above. `check <jar> <fresh-output>` reads class bytes, writes `check.json`, and calls carry, creating `carry/` and `outside/`; it does not execute Java. [Check implementation](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-port-pack/src/check.rs#L94-L157), [output directories](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-port-pack/src/carry.rs#L712-L735).

Built-in replacements: upstream explicitly classifies Sodium, FerriteCore, ModernFix and ImmediatelyFast as unnecessary performance ports; this does not prove benchmark equivalence or preserve Sodium Extra's UI features. EMF/ETF-style entity models and random/emissive/blinking textures are documented native pack features. No specific Lithium equivalence was established here. [Performance boundary](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/docs/modpacks.md#L54-L64), [entity features](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/docs/resource-packs.md#L41-L45).

## Verified Rust-free conversion subset

**Practical first output: a generated resource-only folder pack**, with copied jar `assets/` and this exact root `pack.mcmeta`:

```json
{"pack":{"description":"Assets carried from source_mod; no Java behavior","min_format":[97,1],"max_format":[97,1]}}
```

This is the target's real format codec: two-number arrays mean major/minor, both range endpoints are mandatory, and 97.1 is the pinned resource format. Do not write `"pack_format":97.1`: that field requires an integer. [Codec](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-client-render/src/packs.rs#L170-L182), [range validation](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-client-render/src/packs.rs#L233-L257). Generated metadata declares the intended target; it does not establish that old asset contents have been upgraded or rendered successfully.

Copy supported textures, sounds, languages and model resources without changing namespace paths; retain all other `assets/` files as potential unsupported resources, with feature warnings. Their presence does not create missing mod blocks/items/entities or execute Java. `data/` is not resource-pack gameplay content: retain it separately for manual review. Preserve licenses, notices and source metadata in a provenance directory beside the generated pack; retain original filenames and hashes. Do not treat `fabric.mod.json` as Horizon's manifest. Existing complete resource packs should retain their original metadata instead of receiving this generated metadata.

**A second valid output is a data-only content folder**, not a Rust native mod. Minimal `horizon-mod.toml`, assuming the source owns only `source_mod`:

```toml
id = "source_mod"
name = "Source Mod assets carry"
version = "0.0.0+carry"
api = "0.2"
side = "both"
capabilities = ["registries"]
```

Place `assets/source_mod/` and selected `data/source_mod/` beside this manifest. No `data/source_mod/horizon/*` registration files are required: the loader iterates whatever declarations actually exist, so an assets-only package is structurally valid. [Manifest fields/defaults](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-mods/src/manifest.rs#L33-L60), [content roots](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-mods/src/content.rs#L412-L441), [zero-registration path](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-mods/src/content.rs#L627-L659).

List additional nonreserved source namespaces in `namespaces = ["other_namespace"]`; preserve resource identifiers rather than renaming them. Content mods reject `assets/minecraft/` and unowned namespaces; shared `data/minecraft/` and `data/c/` are allowed **only under `tags/`**. Consequently, do not blindly wrap every jar's `assets/`+`data/` in a content mod. [Ownership rules](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-mods/src/content.rs#L590-L625), [namespace validation](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-mods/src/manifest.rs#L270-L299).

Recipes use `data/<owned-namespace>/recipe/<path>.json` in current formats. The namespace stays unchanged; plural-to-singular directory normalization, if needed for an older input, does not validate its JSON. Carry's implementation separately upgrades recipes and identifiers, records custom/untransformed recipes, and removes recipes for unregistered items. A no-registration converter must defer recipes requiring missing mod items, tags, serializers or behavior; it may retain an already-current vanilla-only recipe only after checking those references. [Recipe handling](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-port-pack/src/carry.rs#L785-L813), [unregistered recipe policy](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-port-pack/src/carry.rs#L38-L43). Content-loader acceptance alone does not establish gameplay validity. Any translated upstream formatting rules should retain MIT attribution and the pinned source reference; author content licenses remain separate.

## Offline replacement catalog: exact policy and limits

The actual offline catalog is [`docs/modpacks/atm10-mods.csv`](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/docs/modpacks/atm10-mods.csv): 495 rows, 54,985 bytes. No separate small replacement JSON was found in the porting crate/docs catalog paths. Columns are `mod_id,name,version,class,tier,confidence,source,license,client,server`. `license` describes the classified mod, not a license grant for that mod's assets/code.

Verified rows suitable for a small pinned derived catalog:

| Mod ID | Upstream class / tier | Evidence |
|---|---|---|
| `sodium` | `performance` / `none` | [row 429](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/docs/modpacks/atm10-mods.csv#L429) |
| `sodium_extra` | `performance` / `none` | [row 430](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/docs/modpacks/atm10-mods.csv#L430) |
| `iris` | `other` / `none` | [row 242](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/docs/modpacks/atm10-mods.csv#L242) |
| `ferritecore` | `performance` / `none` | [row 184](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/docs/modpacks/atm10-mods.csv#L184) |

These rows have `confidence=categories`. The classifier nevertheless indexes all rows except `confidence=guess`, normalizes IDs/names to lowercase ASCII alphanumeric, and tries ID, Modrinth slug, then name. It does **not compare versions**. A match wins over heuristics and the inventory labels it `known`, losing that original confidence detail. [Catalog matching](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-port-pack/src/classify.rs#L5-L60), [precedence](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-port-pack/src/inventory.rs#L104-L110).

`not-needed` is a reporting policy for `tier=none` or class `library`/`performance`, not a compatibility test. Iris's row therefore does not prove shaderpack equivalence, and Sodium Extra's row does not prove its individual options exist. No catalog rows match Lithium, EMF (`entity_model_features`), ETF (`entity_texture_features`), Continuity or Fresh Animations; leave these without a known-catalog verdict. EMF/ETF/Continuity-style pack features have separate documented engine support; classify Fresh Animations as a resource pack with those dependencies/features to check, not a Rust logic port or a verified compatible release. [Reporting policy](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-port-pack/src/report.rs#L228-L246), [engine feature evidence](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/docs/resource-packs.md#L41-L45).

A derived catalog may preserve `source_revision`, source path/line, exact ID, original row confidence, class/tier and a separate `feature_evidence` list; this is a recommended local schema, not an upstream API. Retain Horizon's MIT copyright/license notice when vendoring its mapping/rules: **Copyright (c) 2026 Ludovic Marie and the Horizon contributors**. [License](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/LICENSE#L1-L21). No local jar scanning or build was performed for this lookup.
