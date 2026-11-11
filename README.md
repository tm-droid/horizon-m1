# Horizon M1 work area

Tuning and mod work for Horizon (native Rust/Metal Minecraft 26.3 client) on a MacBook Air M1, 8 GB.

- `outputs/horizon-native/<fix>/` patches against Horizon commit `fdc87ae`, each with `NOTES.md`. Build stacks: `outputs/horizon-native/daily*-stack.txt` (current: `daily7-stack.txt`).
- `outputs/horizon-runtime/build-fast-fdc87ae.py` builds a client from a stack plus the mods in `mods.lock.tsv` (repo + pinned commit per mod).
- `outputs/bench-2026-11-10/` bench harness (`bench.py`), gallery test (`gallery.py`), run results (`runs/*.json`).
- `tools/`, `tests/`: converter and test tools. `docs/`: research and reports.
- `config/`: snapshot of the live game and launcher settings. `tools/config-sync.sh snapshot` copies live settings in (then commit); `tools/config-sync.sh restore` puts them back (game and launcher closed). Account files are not tracked.

Builds, source clones, screenshots and pack zips stay local (see `.gitignore`).

Files copied from or patching Horizon (https://github.com/horizon-rust/horizon) are under its MIT license, see `third_party/horizon-LICENSE`. Mods listed in `mods.lock.tsv` belong to their authors and are not included here.
