# R12 Java mod compat in Horizon (2026-11-06)

Answer: NO today. PLANNED-but-unstarted (ROADMAP "Running Java mods that aren't rewritten": "Hard and not started"). Only data/assets carry over.

- docs/mods.md: "Fabric and NeoForge jars do not run as they are ... Horizon has none [Java classes]. What carries over is the data and assets inside a jar."
- Native mod (.hnmod) = horizon-mixins bundle: Rust source patched into the game, compiled per instance. Not sandboxed.
- "native hooks" (native-hooks.json, 41 hooks, API 24) = Rust hook points in horizon-client; docs/native-hooks-neoforge.md is a naming proposal (NeoForge event names). Not a JVM bridge, not loading NeoForge mod code. horizon-port-pack may *suggest* listener->hook mappings for a human; no auto translation.
- horizon-port-pack (crates/horizon-port-pack, docs/modpacks.md): carries data, assets, worldgen, block/item defs, tags, biome modifiers from jars/.mrpack/CurseForge zip/Prism instance (mmc-pack.json). Mods with code need a hand-written/agent-written Rust native mod. Sodium, GeckoLib, Fabric API "don't run".
- Open, unmerged: issue #6679 bounded Fabric/NeoForge jar runtime (AI-agent filed; interpreter + JVM fallback runner), PR #10409 (open, draft) Native Java mod compat, PR #10216 (open) Java bridge design note. Closed: #527, #5088 Fabric compat layer WIP.
- Local f42 candidate-source has same docs/files (mods/horizon, 40 crates incl. horizon-port-pack, horizon-mods, horizon-mod-registry); no JVM bridge in tree.

Community native mods (QoL):
- minimap: DenoxyYT/ayynoxs-map-pack, AzaelMew/horizon-seedmap; built-in minimap in horizon-mods/native
- freecam: hakergeniusz/freecam (port of Freecam)
- AppleSkin: CayMac97/appleskin
- dynamic lights: built-in optional extra (v2026.10.22, #1162); no third-party found (search errored)
- also: enderliker/horizon-jei, steimerbyte/horizon-accurate-block-placement, sirrayi/greenhouse, BenjiSyS/visuality-horizon
Unverified: quality/review status of these repos; registry listing not checked.

Survival of Fabric QoL set: pure-code mods (Sodium, Iris, Xaero, Lithium, etc.) die; only bundled datapacks/resource packs/lang/recipes/tags survive. Resource packs + shaders have Horizon-native equivalents (docs/shaders.md, resource-packs.md); configs not carried unless native mod reads them.

URLs: https://github.com/horizon-rust/horizon/issues/6679 /pull/10409 /pull/10216 /issues/527 ; ROADMAP.md L347-353
