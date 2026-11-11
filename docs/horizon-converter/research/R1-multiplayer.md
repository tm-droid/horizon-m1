# R1 multiplayer research (2026-11-06)
Source root S = outputs/horizon-runtime/m1-performance/candidate-source. f42ef42 committed 2026-11-03T08:12Z (gh api). Upstream repo horizon-rust/horizon.

## 1. Host vs guest
- Host's integrated server ticks INSIDE the client frame loop: S/crates/horizon-client/src/game.rs:7390 `spans::time("tick_lan", || self.tick_lan(false))`; then `tick_friends()` at :7391. Impl S/crates/horizon-client/src/game/lan.rs:2202. docs/server.md:147-148 says "integrated server on its own thread" is still planned (after perf-ticks-2). So host pays server CPU on the render thread; guest pays none.
- Singleplayer already runs the same server over a memory connection (no compression, conn.rs:868 "memory connections are not compressed"). Marginal host cost of a friend = per-guest chunk send, entity tracking, zlib (threshold 256, lan/mod.rs:222) + ChaCha20-Poly1305 tunnel (play-with-friends.md "Encryption"), plus the friend's own chunks/entities loaded around them (view/simulation union).
- Memory: server idle ~300 MB, 100 bots 2.1 GB (docs/performance/server-vs-pumpkin.md:61,64; dedicated, Linux, not integrated). `low_memory` only affects Linux THP (hosting.md:577-590); irrelevant on macOS.
- Recommendation: the machine with more CPU/RAM hosts. If the friend has a desktop, friend hosts; M1 8GB joins as pure guest. If M1 must host: keep sim distance low, 1 guest only.
- UNVERIFIED: no upstream number for integrated-server MSPT with 1 guest on M1.

## 2. Knobs (integrated server)
- Host follows the client's own options live: S/.../game/integrated.rs:1021-1041 `follow_distances` (render_distance -> hub view_distance, simulation_distance -> hub simulation). Guest view is clamped `clamp(2, host view)` hub.rs:737, 3287-3288. So HOST's render/sim distance caps what the guest gets and what the server loads.
- Entity tracking range: `sees()` entity.rs:806-818 `range = min(type range, view_distance*16)`; `entity_range_percent` is dedicated-only (hub.rs:338). Integrated reads the client "entity distance" option (integrated.rs:1023-1024).
- Compression threshold fixed 256 for LAN (lan/mod.rs:222); dedicated: `props.network_compression_threshold` (game/dedicated.rs:950). No integrated knob.
- Chunk send rate: guest-driven, `chunks_per_tick` from client ChunkBatchReceived clamp 0.01..64 (hub.rs:3213-3219), quota hub.rs:2141, max_unacknowledged gate :2136. Not host-configurable.
- Tick rate: no integrated knob found (vanilla /tick command only).
- Dedicated-only (hosting.md:140-195 server.toml): view_distance, simulation_distance, max_view_distance (far ring, off=0), max_players, [engine] low_memory, [properties] any server.properties key (incl. entity-broadcast-range-percentage, network-compression-threshold). Applies on restart.
- Not applicable to friends play unless user runs `horizon-server` separately on the M1 or a friend's box. Dedicated is a separate process (not on the render thread), but needs its own ~300 MB+.

## 3. Relay vs direct
- Order: guest dials all code endpoints at once, first Horizon answer wins (play-with-friends.md "Joining"). Direct = UPnP/PCP/NAT-PMP mapping on TCP 25580, STUN for public IP. TCP_NODELAY on all (host.rs:392,410; guest.rs:205; lib.rs:124).
- Relay: only if configured (no default relay). Relayed session first races direct (TCP simultaneous open from direct port), `direct::RACE` = 3000 ms (crates/horizon-friends/src/direct.rs:18); stays on relay only if none connects. Relay cap 1024 KiB/s per stream (RELAY_SESSION_KBPS); play 10-50 KB/s, flying up to few hundred KB/s.
- Direct = one hop, lowest latency; relay adds a hop through the relay host. No measured RTT numbers upstream (UNVERIFIED). With no relay set, CGNAT both sides = cannot connect; use Tailscale (code embeds 100.x).
- Host macOS: must click "Allow" on incoming-connection prompt (doc Troubleshooting).

## 4. PRs after f42 (all MERGED 2026-11-06; all post-date f42 by ~3 days). Measures are dedicated-server CPU ms/tick on desktop with 36 bots/4000 mobs unless noted; benefit scales with loaded mob count, so small on a lightly loaded friends world.
- #10331 idle entities: ChunkMap rule + bare states (lan/entity.rs, game/lan_idle.rs). tick_lan 6.84->5.00, 6.57->5.07, 6.98->5.36 (~-1.5 ms); lan_entity_states 3.5->2.4, lan_track_entities 2.0->1.35. Biggest LAN-host win; also less network (no MoveEntityPos every 60 ticks for idle entities outside entity-ticking range, vanilla behaviour). Fixes #10253.
- #10361 mob loop: villagers/looting walk only nearby items, no PlayerView clones for out-of-sim mobs (closes #10252). creature_villagers was 12.8 of 23 ms on the official SMP load test. Tail of measured table truncated in my fetch, unverified exact after-figure.
- #10429 mob snapshot in place + reused buffer: creature_prepare 1.2->0.8, tick_creature_entities 7.9->7.4 (MSPT 16.7->16.2).
- #10366 sculk events: tick_sculk_entities 1.0->0.6, sculk_entity_events 0.9->0.5 (flat world; SMP gains more). Closes #10254.
- #10423 sculk: only ticking mobs/items step, land, flap: MSPT round2 20.4->16.7 vs #10406 (noisy; round1 17.2->16.7).
- #10406 mobs outside sim distance pick up nothing (vanilla parity bug fix): tick_creature_entities ~8.5->8.0 / 7.9->8.2 (noise; mainly a correctness fix). Closes #10378.
- Net: all server-side; only matter with thousands of mobs. #10331 is the one that matters for a friends-play host. Needs a rebuild newer than f42; I did not check whether they apply cleanly to f42 (no builds allowed).

## 5. Known multiplayer bugs (open, gh issue list)
- #10255 (OPEN): official SMP, 16 slow ticks in 36 s, `tick_lan_packets -> lan_events -> use_block` 0.27->1.23 s, no culprit note; cost grows per use (suspect chest/structure search). SMP-scale, engine 52882c1; may or may not affect integrated.
- #4664 (OPEN): 600 FPS singleplayer vs 60-70 FPS on a multiplayer server (Ryzen 5 1600, RX 480); one thread ~11 CPU s per 10 s; sim/render dist 8. Cause not stated in issue.
- #9615 (OPEN): relay gets unlimited short-code guesses (only if running a relay). #8645 server simulation ownership (design). #10317 incompatible-server narration. #3823 fullbright/multiplayer compliance.

## Recommended settings (M1 8GB, 1 friend, no look change)
1. Best: friend hosts if their PC is stronger; M1 is guest (no server tick on its render thread). Both on same game version (26.3 / same Horizon build).
2. If M1 hosts: keep render distance 12 is the cap for the friend; simulation distance low (user already 8; try 6) since sim distance drives mob ticking/tracking; entity distance option modest. Sim distance does not change visuals of terrain.
3. Don't run Roblox/Safari while hosting; close other apps (swap).
4. Connect directly: UPnP on, or Tailscale on both. Skip relay unless CGNAT both sides.
5. Don't host a heavy-mob farm world; mob count drives integrated tick cost (#10331 etc.).
6. Consider a Horizon build newer than f42 for #10331 only if hosting is the pain point; verify first via A/B.

Sources: S/docs/play-with-friends.md, S/docs/hosting.md, S/docs/server.md, S/docs/performance/server-vs-pumpkin.md, gh PR/issues 10331 10429 10361 10366 10423 10406 10255 4664 (github.com/horizon-rust/horizon).
