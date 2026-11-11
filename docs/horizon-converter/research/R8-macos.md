# R8: macOS-specific performance for Horizon on M1 Air 8 GB (2026-11-06)

## Findings
1. Game Mode
 - Needs: LSApplicationCategoryType games and/or LSSupportsGameMode (macOS 26+) / GCSupportsGameMode (macOS 14+) in Info.plist, AND a fullscreen, focused window. Eligibility only; OS decides. Apple docs: https://developer.apple.com/documentation/bundleresources/information-property-list/lssupportsgamemode ; Apple Support https://support.apple.com/105118 ; forums 782343, 787702 (child Java process did not trigger).
 - Effect (Apple): higher CPU/GPU priority for the game, lower priority for background tasks, lower Bluetooth latency. Not measured by our harness.
 - Launcher: horizon-launcher (launcher-app/Horizon.app) has category games, no Game Mode keys, and is a Mach-O arm64 launcher, not the game. Real game is spawned by launcher/src/backend.rs client_command -> client_program -> crate::game_app::ensure(): a per-version Horizon.app whose plist (launcher/src/game_app.rs INFO_PLIST) has category games + NSHighResolutionCapable + mic string, but NO GCSupportsGameMode/LSSupportsGameMode; executable is a hard link of the bare binary. Falls back to bare binary on error.
 - Prior measured work (docs/horizon-converter/gamemode-2026-11-05.md): bare binary never labeled; bundle with both keys logged "Found game ... labelReason=LSSupportsGameMode", "Game mode enabled" (4/4 fullscreen runs). Windowed: labeled but off. A/B FPS: no significant change (38.3 vs 38.5 avg). Unverified whether category-only (current game_app plist) is enough on macOS 27; test with probe.sh.
2. Fullscreen/present
 - Horizon: --fullscreen = winit Fullscreen::Borderless(None) by default; Exclusive only with exclusiveFullscreen option (crates/horizon-client-input/src/window.rs:586-611). On macOS winit borderless = native fullscreen Space, which lets the compositor skip/composite cheaply; Apple gives no hard "direct-to-display" guarantee (unverified).
 - wgpu present: compositor.rs:86 Fifo, desired_maximum_frame_latency 2; vsync off picks Mailbox else Immediate (:105). Metal backend (third_party/wgpu-hal/src/metal/surface.rs:264,333,340) only supports Fifo/Immediate: displaySyncEnabled = (Fifo); maximumDrawableCount = latency+1 = 3. Mailbox is never in macOS caps, so vsync-off = Immediate (tearing, uncapped, GPU runs flat out = more heat).
 - Frame pacing default Efficient (sleep, no spin) - good for thermals.
 - Apple forum 773229: nextDrawable can stall ~1 s after drawableSize change (resize); DTS suggests CAMetalDisplayLink. Avoid live-resizing windows.
3. Thermals / App Nap / LPM
 - M1 Air fanless: reviews/forums report clocks starting to drop after ~8-10 min sustained load, typically up to ~15% (anecdotal, no controlled source): https://forums.macrumors.com/threads/how-does-the-air-manage-throttling-and-performance-loss-in-games.2269457 ; https://forums.macrumors.com/threads/m1-air-throttles-to-a-maximum-of-4w-during-a-game.2305984/
 - Low Power Mode caps clocks/GPU; keep OFF on AC and for benches. App Nap only hits occluded/hidden windows; fullscreen focused game is exempt (not checked in source: no beginActivity found by grep; threads use QoS USER_INTERACTIVE in crates/horizon-threads/src/lib.rs:59).
4. Memory: 8 GB, unified with GPU. Prior benches had 2.7-3.1 GB swap. Swap/compression stalls show in 1% lows, not avg. Close Safari/Roblox (~3.5 GB), check `sysctl vm.swapusage`, `memory_pressure`, Activity Monitor pressure graph green.
5. Retina: NSHighResolutionCapable true -> native 2x drawable. Horizon has Resolution Scale (50-200% in 5% steps, graphics_ui.rs:836) and Upscaling (TAA-based ratios). Native 2x on a 13" Air = 2560x1600 (or scaled-mode backing larger) and is the main GPU/heat cost.

## Things the user can do
- Play --fullscreen (Game Mode needs it); close Safari/Roblox first.
- Plug in AC, Low Power Mode off, hard flat surface / stand / cooling pad; limit FPS cap to ~60 (vsync Fifo) to cut heat.
- Lower Resolution Scale to 70-80% or use Upscaling ratio; biggest lever for sustained 10+ min.
- System Settings > Displays: choose a "More Space"-off / default scaled mode; lower display mode cuts backing size.
- Leave Frame Pacing = Efficient.

## Code changes
1. game_app.rs INFO_PLIST: add GCSupportsGameMode=true and LSSupportsGameMode=true (proven in prototype to trigger Game Mode fullscreen). Verify with gamemode-wrapper/probe.sh against the real per-version Horizon.app. Hard link vs APFS clone: prototype used clone + ad-hoc codesign; changing plist must keep bundle signature/validity (check codesign).
2. Optionally on first fullscreen focus: nothing else needed; consider auto-defaulting to fullscreen on 8 GB macs (user choice).
3. Consider capping fps to display refresh when vsync off on battery/thermal state (NSProcessInfo thermalState / isLowPowerModeEnabled) and lowering Resolution Scale automatically at Serious/Critical thermal state. Not present in source.
4. Consider default Resolution Scale <100% on 8 GB M1 presets; check bench.
