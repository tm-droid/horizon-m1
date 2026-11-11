# Dimension-switch shader pack freeze: warm-up patch

## Where the time goes (read from code + log, not profiled)
Per switch, `Game::shader_pack_inputs` (game/shader_packs.rs) on the MAIN thread: Pack::open + options,
read_properties, load_post (GLSL parse/translate), block/entity/item.properties parse, mc_Entity table
(105 ms logged), then `Renderer::load_shader_pack` spawns a thread running `PackPost::new` (pack_post.rs):
`build` (naga/WGSL shader modules, colortex/shadow targets) then `compile` = `create_render_pipeline`
for all jobs on up to 8 threads. Metal compiles MSL cold there.
Log: first nether 3037 ms, first overworld 2508 ms, but overworld return 372 ms. Same code path, so
re-parse/translate/table/target creation is at most ~370 ms; the other ~2.1-2.7 s is cold Metal
compilation, which macOS caches per shader (not per process). wgpu 30.0.1 PipelineCache is Vulkan-only
(`cache: None` already), so no persisted-cache option on Metal.
So option (b) (parse/translation caches) saves <=0.2-0.3 s and (a) (keep PackPost per dimension) would
duplicate colortex/shadow targets; both rejected. The fix is to make the first visit warm.

## Design (gfx/pack_warm.rs + hooks)
After the running dimension's pack has been installed for >=5 s and nothing is loading, the game builds
each OTHER dimension's folder (only if `dimension_folder_named` differs from the current and from folders
already warmed) through the normal load path, with `warm=true`: compiled on 2 threads, result dropped
(only Metal's shader cache keeps the work), next warm 5 s later. Real dimension change cancels a warm
(CancelOnDrop). Key = final folder name (dimension.properties aware); nothing from the warm is reused
in-process, so no staleness/correctness risk (warm build runs the identical load_post/macros path with
that dimension's folder; running pack_ids/separate_ao state untouched, warm failures never turn the pack off).
Pack switch/drop resets warm state. Opt out: `HORIZON_PACK_WARM=0`.
Files: gfx/pack_warm.rs (new, Warm state + pure `pick` + 3 unit tests), gfx.rs (fields, load_shader_pack
`warm` arg, poll reaps warm, accessors), gfx/pack_post.rs (`new_with`/`compile_with` thread cap, `new`/`compile` unchanged),
game/shader_packs.rs (`next_pack_warm`, closure takes dimension from `warm`).

## Expected saving
Unvisited dimension first switch ~3.0 s -> ~0.4 s (the observed warm path), provided Metal's cache serves
the warm-built pipelines to the real build (shown by the 372 ms return). Not measured.
Remaining ~0.4 s: main-thread prep (could be trimmed later by caching Pack/properties/table).

## Cost / risks
- Memory: transient per warm (~5-15 s, 2 times per session): a second PackPost's colortex (up to 8 buffers
  x ping-pong) + shadow targets, roughly 150-450 MB at 1080p-1440p, freed on drop. Pipelines are small.
  Not persistent. On a swapping 8 GB machine this is the main risk; opt out via env var.
- CPU: 2 compile threads + ~0.35 s main-thread prep hitch (load_post, tables) when a warm starts, 5 s after load.
  Previously that hitch was the user's 3 s; now ~0.35 s twice, unprompted, mid-play.
- Warm log lines reuse "mc_Entity ... building its pipelines" text; the reap logs "warmed dimension N".
- If the dimension's folder is identical to the current one (MakeUp world0 fallback), it is skipped.
- Uncertain: whether the in-game freeze is compile-thread starvation vs main-thread prep; warm removes both
  from the switch either way.

## Tests
Not built/run: game was running (pgrep found horizon-client). No cargo/rustfmt (rustfmt not on PATH).
Unit tests added in pack_warm.rs: `cargo test -p horizon-client-render --lib pack_warm` when game is closed.
Patch dry-run: applies clean on original tree and after terrain-single-draw + fullbright patches (stack clone).
