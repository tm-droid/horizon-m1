# MakeUp dropped light experiment

The Rust patch targets the exact r11 source at `outputs/horizon-runtime/m1-performance-r11/20261108-091244/source`. Horizon already sorts the native light sources once per frame. The patch retains the four nearest nonlocal sources from that sort, then adds their camera-relative positions and levels to the legacy shader uniform provider. The MakeUp variant reads the uniforms in terrain and water vertices and raises the existing block-light coordinate where a nonlocal light is brighter. MakeUp still calculates held light from its own held-item uniforms. Disabling Horizon Extras dynamic lights produces an empty source list.

From the launcher data directory, check and generate the inputs:

```sh
candidate_dir=$(mktemp -d /private/tmp/horizon-makeup-light.XXXXXX)
patch="$PWD/outputs/horizon-native/makeup-dropped-light-r11/makeup-dropped-light.patch"
git -C outputs/horizon-runtime/m1-performance-r11/20261108-091244/source apply --check --whitespace=error "$patch"
python3 outputs/horizon-native/makeup-dropped-light-r11/build-makeup-dropped-light.py \
  outputs/horizon-runtime/game/shaderpacks/MakeUp-UltraFast-9.6.zip "$candidate_dir"
```

The apply check passed. Two generator runs yielded identical ZIP bytes with SHA-256 `172412da8acae03f65c78f6ca90864f6a872425762832350dd4e7e10c294e910`. All 359 names matched the source and exactly three shader members changed. The Rust build, shader translation and visuals still need device verification.

The existing disposable runner accepts the generated archive via `--makeup-source` and the daily options via `--shader-options-file`. Use `--scene daily-compat-light` to compare the unlit, held and dropped states. For activation, first confirm that the light follows a moved dropped torch, vanishes on pickup, keeps held-only lighting consistent and adds no visible change when Extras are disabled. Profile matched terrain and water with Extras off, then with four active nonlocal lights to measure the M1 cost.
