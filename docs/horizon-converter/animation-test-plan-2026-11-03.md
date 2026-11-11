# Fresh Animations fixture plan — exact f42 controls

Source-only lookup for `f42ef42ef6ceccb3c6a20bea2481d87949a51c81`. No game/process/tool binary, device operation, world edit, build or test was run here. Execute later only in root's owned disposable world/profile and device-queue turn. Start shader-off: this checks entity models/animation, independently of Mellow's renderer issue.

## Verified commands and replies

Use the installed f42 `horizon-ctl` with its explicit owned `--socket PATH`. Coordinates below are placeholders for root's fixed fixture site, not a discovered safe location. Check ground/lighting and record actual camera/position; never apply these commands to an original world.

| Command after socket arguments | Actual f42 reply/use |
| --- | --- |
|`summon cow X Y Z`|`{"ok":true,"id":N}`; only optional `baby` is understood. This convenience command does **not** accept arbitrary NBT. Do not append a compound and assume it was honored|
|`command 'summon minecraft:cow X Y Z {UUID:[I;28211,0,0,1],NoAI:1b,PersistenceRequired:1b,NoGravity:1b,Silent:1b,Invulnerable:1b,Rotation:[180.0f,0.0f]}'`|In local single player, dispatches on the integrated server and replies `{"ok":true,"chat":[...]}`. Inspect chat for success/error; `ok` alone means control dispatch succeeded|
|`entities 16 cow`|`{"entities":[...]}`, nearest first within radius. Mob entries have `id`, `kind:"mob"`, `type:"minecraft:cow"`, `pos:[x,y,z]`, `distance`, `health`, `baby`, `hurt_time`. Select the fixture by its known position/identity, not first entry if another cow is present|
|`mobs 16`|`{"count":N,"near":[...],"projectiles":N}`. In integrated single player this queries the server's owner-level mobs. Entries include `id`, `kind`, `pos`, `health`, `baby`, `goals`, `targets`, `on_ground`, `variant`, `ints`, etc.; `count` is all server mobs, not only the near list|
|`command 'data get entity 00006e33-0000-0000-0000-000000000001 NoAI'`|Text result in the command reply's `chat`; check the actual reported flag rather than expecting structured NBT. Likewise read `PersistenceRequired`, `NoGravity`, `Rotation` and `Pos`|
|`tp PX PY PZ`, then `look YAW PITCH`|Fixed player/camera control; look pitch is clamped−90..90. Retain identical values and physical framebuffer dimensions across profiles|
|`look-at entity N`|Supported agent control when a numeric entity ID has been observed. Useful to frame the cow; save the resulting camera values, then reuse them exactly for the comparison|
|`options-get resourcePacks`, `status`, `screenshot ABS_PATH`|Retain raw JSON and actual image. A selected pack list proves selection, not successful CEM parsing or draw selection|

Source evidence: [control summon/mobs](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/game/control.rs#L777), [entities reply construction](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/game/agent.rs#L676), [integrated console-command reply](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/game/agent.rs#L1645), [server mob observation fields](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/game/creatures.rs#L725), [summon/data access implementation](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/game/commands/data.rs).

The deterministic UUID prevents unrelated random-identity changes between independent profiles; use the same fixture world copy rather than summoning duplicate UUIDs into an existing copy. The text UUID shown corresponds to `[I;28211,0,0,1]`. Numeric runtime entity IDs can differ between launches and must be observed anew. Do not use global `/kill @e` cleanup: discard the owned profile or address only the known fixture.

## Fixed pose is a geometry check, not frozen animation

f42 loads and saves `NoAI`, `PersistenceRequired`, `NoGravity`, `Silent`, `Invulnerable` and rotation; its own save-roundtrip fixture uses NoAI/Silent/NoGravity/Invulnerable SNBT. NoAI prevents AI decisions, not all animation, aging, collision response or render-time variables. NoGravity is useful for a floating static model inspection but changes on-ground context, so it cannot validate grazing/walking behavior. Read back the flags and verify position remains fixed; do not infer them from a successful summon message. [NBT loading](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/entity_nbt.rs#L1566), [upstream fixed fixture](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/tools/save_roundtrip_scene.py#L104).

CEM `age`, world time/day time, `frame_time` and `frame_counter` are real animation inputs; frame time/counter advance from rendered calls and wall-clock Instant. No verified control was found that sets all CEM inputs to a fixed frame. Consequently compare model geometry and short matched time sequences, allowing expected phase differences; a one-pixel screenshot diff is not a valid animation parity test. Follow the static fixture with a separate ordinary-AI cow sequence to inspect walking/head/body/idle behavior. Changes in camera, biome/variant, standing block, baby state, health or on-ground state can legitimately select different rules and must be held or recorded. [f42 animation context/clock](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/mobs/cem_anim.rs#L77).

## CEM selection and observability

At pack load the f42 CEM loader builds model layers from the resolved asset root. For one name it tries **EMF `assets/minecraft/emf/cem/` before OptiFine `assets/minecraft/optifine/cem/`**, and flat `cow.jem` before nested `cow/cow.jem`; the first parseable candidate/fallback for the layer wins. A cow's biome variant may draw a layer such as `cold_cow#main`, which can fall back to the shared cow model. Presence of cow.jem somewhere in a ZIP does not prove that it wins after pack overlays. [Candidate selection/layer fallback](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/mobs/cem.rs#L68), [file precedence](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-optifine/src/cem/files.rs#L9).

Capture these exact warning families from the full load log, not just lines containing `shader`:

- `Horizon: custom entity model <path>: unreadable or over <MAX_BYTES> bytes`;
- `Horizon: custom entity model <parse error>` and every parsed model warning;
- `Horizon: custom entity model <name>: no part <part>`;
- `Horizon: custom entity model <file>: unknown target <target>`;
- `Horizon: custom entity model <file>: unknown name <name> reads 0`;
- `Horizon: custom entity model <file>: <target>: <compile error>`;
- `more than <MAX_EXPRESSIONS> animation expressions, the rest are left out`.

These are material compatibility findings: unknown expressions can become zero, targets can be skipped, or a fallback model can be selected while the rest of the pack renders. A successful frame plus no fatal error does not establish complete animation. [Read/parse warnings](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-optifine/src/cem/files.rs#L40), [partial animation behavior](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/mobs/cem_anim.rs#L367).

No positive per-entity `selected_jem`, model-part tree or expression-execution counter was found in the checked f42 control state/entities/mobs APIs, and no documented runtime env switch proving a cow's selected CEM path was verified. The test-only `HORIZON_TEST_RESOURCES` in CEM tests is not a gameplay diagnostic. Do not invent a `cem-info`/`model-info` command or treat absence of warnings as a positive load certificate.

The strongest available unmodified-runtime evidence chain is: unchanged source pack SHA256 and selected order; resolved overlay winning model/includes/texture byte provenance; no relevant partial-parse/animation warnings; matching cow context; and visible distinctive Fresh Animations geometry/motion versus the base-only control. If the images remain vanilla/ambiguous, report selection **unproven**. Any later runtime instrumentation exposing the actual chosen model would require a separate reviewed source change/build; this plan does not authorize or claim it.

## Minimal comparison sequence

1. Clone one owned fixture world into separate fresh base and FA profiles; keep shader off, native resolution, camera/lighting/settings identical, and fix AFK throttling/full-scene readiness as in the existing runner. Use full source pack ZIP bytes unchanged. Base selection is vanilla; FA selection is vanilla plus the unchanged Fresh Animations pack in its actual intended precedence.
2. Create/read back the fixed UUID cow once in the fixture before cloning, or issue exactly the same verified summon in each empty clone. Save identity, context, entity JSON, camera and frame size. Confirm the cow is actually in frame.
3. Collect a static geometry capture and a bounded sequence of idle captures, then a separately labeled moving/normal-AI sequence. Review images and CEM warnings before considering any performance figures. A static NoAI cow cannot cover all Fresh Animations behavior.
4. Only after the plain FA case is attributable, add FA extensions, then harness/model overlays one at a time in the selected source order. Recompute winning asset provenance at each step. Do not use an arbitrary subset as proof of the full52-pack stack.

This is a test specification with verified source interfaces. It makes no device pass, selected-model, animation-fidelity or FPS claim.
