# Horizon M1 work area

Tuning, patches and bench tooling for Horizon (native Rust/wgpu/Metal Minecraft 26.3 client,
https://github.com/horizon-rust/horizon) on a MacBook Air M1, 8 GB RAM, 2880x1800, 60 Hz. Layout: see README.md.
Task ledger: `.claude/task-ledger.md`. History: `docs/Codex-history.md` (never in this file).

## Hard rules
- This repo is PUBLIC. Never commit `accounts.json`, `servers.dat`, game logs or chat logs (server chat), tokens,
  emails or account names. Commit only; push only when asked.
- Before changing live game/launcher settings: `tools/config-sync.sh snapshot`, then commit `config/`.
- Edit `options.txt` / `horizon-graphics.txt` only with the game closed: the game rewrites them on exit.
- 8 GB RAM: builds, benches and game sessions strictly one at a time. Builds need >= 8 GiB free disk.

## Live install
- Game data: `~/Library/Application Support/horizon`. Launcher data + builds: `~/Library/Application Support/horizon-launcher/versions/<tag>`.
- Launcher CLI: `/Applications/Horizon.app/Contents/MacOS/horizon-launcher` (`settings`, `versions`, ...).
- Selected build: `native-fdc87ae-m1-daily7-73decc0fdc30` (stack `outputs/horizon-native/daily7-stack.txt` + `mods.lock.tsv`).
  daily8 was built and not selected (no gain; rebuilt stack renders the ender dragon blue).

## Commands
- Play offline (launcher Play needs a Microsoft account): `tools/play-offline.sh` (also `~/Applications/Horizon Offline.app`).
  Starts with Agent Control on socket `${TMPDIR}/horizon-control.sock`; MCP `game_*` tools attach to it.
- Perf presets (game closed): `tools/horizon-perf.sh pretty|fast|max|status`.
- Real-profile bench (player's own settings, packs, shader, fullscreen):
  `cd outputs/bench-2026-11-10 && python3 -u real.py --uncapped --tag t1 --order 'F7,F7@x,F7' --variant 'x:gfx.uploadBudgetKiB=4096'`
  Also `--drop 'x:packsubstr|other'`, `--sub 'x:old=>/path/new.zip'`. Results: `runs-real/<label>.json`.
  Synthetic bench: `bench.py`; visual regression: `gallery.py`.
- Build: `python3 outputs/horizon-runtime/build-fast-fdc87ae.py --stack <stack.txt> --tag <tag> [--dry-run] [--only mods] [--profile m1]`.
  Builds never select a version. Check that every patch applied: a past run skipped patches silently (`outputs/horizon-native/u7c-rebuild-diff.md`).
- Source for reading: `outputs/horizon-src-nightly/nightly-2026-11-08-fdc87ae/crates`.

## Measuring (gotchas)
- Memory: use `footprint -p <pid>` (phys_footprint). RSS hides compressed and GPU memory; the game is ~3.3 GB, ~3.1 GB of it graphics.
- daily7 ships `dynamic-fps-for-rust`: a focused window with no input for 60 s drops to 20 fps. Hands-free benches
  must write `config/dynamic-fps-for-rust.json` = `{"enabled": false}` in the profile (bench.py/real.py do this).
  Flight numbers recorded before 2026-11-12 are unreliable for this reason.
- Adoption rule: median of >= 3 runs, >= 2% gain in avg or 1% low, no other metric > 2% worse, no visual change.
- Bench gates: on AC, screen unlocked, nothing else heavy running. A locked screen presents no frames (invalid runs).
- Dead ends (checked in source or benched): `HORIZON_MEMORY_LIMIT_MB` does not exist at fdc87ae; `HORIZON_SUBMIT_THREAD`
  is off on macOS because it stalls Metal; `uploadBudgetKiB 4096`, `textureBudgetMiB`, mipmaps, shadowCache: no gain;
  TAA upscaling is slower (no MetalFX); `leafCulling` is ignored while a leaf-model pack is enabled; `MIMALLOC_PURGE_DELAY` is forced to 0.
- Big costs on this machine: Optimized Bushy Leaves (-12 fps, 320 MB), Dramatic Skys textures (use the slim `Dramatic Skys M1.zip`),
  MakeUp shader (~2x vs shader off), and macOS swap when other apps are open.

## Shell
- `ls` is aliased to eza: use `command ls`. Quote zsh args containing `[`, `*` or `=`.
- In background pipelines use `python3 -u` and `grep --line-buffered`, or output appears only at exit.
