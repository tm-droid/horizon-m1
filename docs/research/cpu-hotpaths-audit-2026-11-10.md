# CPU per-frame hot paths (2026-11-10)

Code-read only, no profile. Source: m1-performance-r12/20261110-195836/source. hud.rs contains a NUL byte, so search it with `rg -a`.

**Verdict:** CPU prepare overlaps the previous frame's GPU work (submit thread, frame latency 2, compositor.rs:87). The ~50% semaphore_timedwait is acquire/submit wait. CPU work does not limit FPS under MakeUp (GPU ~34 ms), so fixes below buy thermals and headroom, not FPS.

## Ranked findings
1. **HUD pass boundaries** (GPU): hud.rs:2835 draw_range opens one pass per Blend::Depth run (depth_since :1758); gfx.rs:11599-11635. On TBDR each run is a full-res store/load. The 4.8 ms HUD timestamp is probably a pass boundary plus attribution of the wait for pack post. Fix: merge the HUD into the last pack pass and batch Depth items. Potentially 1-4 ms, unmeasured.
2. **Pool sizing from 8 logical cores**: lan/chunks.rs:493 (7 encode threads), lan/io_pool.rs:267 (4 net threads), vanillagen/lod.rs:75, client-render/src/lod.rs:1339, graphics.rs:1479, save.rs:2148, hud.rs:480/:1272, pack_post.rs:1507. horizon-threads default_workers() is already P-cores-1 = 3, with QoS lowered (lib.rs:194-204). Fix: cap encode threads at min(worker_count()-1, P-1) in single-player; put net threads at UTILITY QoS. Helps hitches and thermals while chunks load.
3. **Hotbar item prep**: item_draw.rs:386/:329/:271; game.rs:8036/:8132. Allocates per slot even on a gui_drawn cache hit. Fix: cache per slot by (stack hash, atlas epoch, clock). ~0.1-0.2 ms.
4. **Jade HUD**: game.rs:29543, jade_config::frame :31591. Raycasts every frame and clones NAME_PROVIDERS under a mutex. Fix: cache by target, recompute at 5-10 Hz. ~0.1 ms.
5. **HUD text**: hud.rs:2046 styled_text, font.rs:770 glyph_of. Allocates per string and takes a RefCell borrow per char. Fix: scratch buffers and an ASCII fast path. 0.1-0.3 ms.
6. **Minimap**: extras.rs update_minimap, minimap.rs:280/:329. 128x128 f64 compose plus full-image clone on each rotation. ~0.3 ms while rotating.
7. Minor items:
   - shader_pack_inputs (shader_packs.rs:201): current_dir() syscall per frame.
   - mark_entity_part (:619): SipHash on Strings.
   - update_world (game.rs:16356): sorts uploads per frame.
   - entity_geometry (game.rs:10529): Vec collects.
   - native_hooks.rs:2738/:2882: format! per frame.
   - native_mod_image (:12791): RGBA clone.

Already optimized, leave alone: native_emissive, ViewArrival, particle culling, dynamic_lights, pack_pixels, gui_drawn cache.
