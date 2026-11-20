# Horizon M1: a tuned Minecraft client for Apple Silicon Macs

[Horizon](https://github.com/horizon-rust/horizon) ([site](https://playhorizon.dev)) is an unofficial rewrite of Minecraft: Java Edition 26.3 in Rust. It runs natively on Apple Silicon, with no Java needed to play. **Horizon M1** is a build of it tuned for a MacBook Air M1 with 8 GB of RAM, plus a one-click installer and a set of handy mods (minimap, zoom, FPS counter and more).

> Horizon M1 is not affiliated with, endorsed by, or connected to Mojang or Microsoft. It contains no Minecraft game files. You need your own copy of Minecraft: Java Edition.

## Download

**[Download Horizon-M1-daily7.zip](https://github.com/tm-droid/horizon-m1/releases/latest/download/Horizon-M1-daily7.zip)**

Release page: <https://github.com/tm-droid/horizon-m1/releases/latest>. The page lists the SHA-256 checksum of the zip. To check your download, run `shasum -a 256 ~/Downloads/Horizon-M1-daily7.zip` in Terminal and compare the result with the release page.

## Requirements

- A Mac with Apple Silicon (M1, M2, M3 or M4). Intel Macs and Windows are not supported by this build.
- macOS 12 or newer.
- About 2 GB of free disk space.
- Minecraft: Java Edition (for a Microsoft account, or for the offline option below).

## Install

1. **Download** the zip from the link above.
2. **Unzip** it by double-clicking it in Downloads. You get a folder called `Horizon M1`.
3. **Open the installer.** Right-click `Install Horizon M1.command`, choose **Open**, then click **Open** again in the warning.
   - On macOS 15 Sequoia or newer, if it says the file can't be opened: go to **System Settings > Privacy & Security**, scroll down, and click **Open Anyway**.
   - Still blocked? Open Terminal, run this, then double-click the installer again:
     ```sh
     xattr -dr com.apple.quarantine ~/Downloads/"Horizon M1"
     ```

The installer copies `Horizon.app` (the official launcher) to `/Applications`, installs the tuned build, selects it, and turns off the launcher's auto-install of new versions so the M1 build stays selected. It also adds starter graphics settings if you have none. Then it asks how you want to play.

### A. Microsoft account

Pick this if you own Minecraft: Java Edition. You get multiplayer servers and your skin.

1. Type `1` in the installer. The Horizon launcher opens.
2. Sign in with the Microsoft account that owns Minecraft: Java Edition.
3. Press **Play**. The first start prepares the game files and takes a few minutes. Later starts are fast.

### B. Offline (no sign-in)

Pick this if you want to play without signing in. Offline mode works for singleplayer, LAN, and servers that run in offline mode. It does not work on online-mode servers and has no Microsoft skin.

You need Minecraft: Java Edition 26.3 installed and launched at least once, using the official launcher, Prism, Modrinth App, MultiMC, ATLauncher or GDLauncher. Horizon builds its textures and sounds from your own install.

1. Type `2` in the installer.
2. Enter a player name (3 to 16 letters, numbers or `_`).
3. The installer prepares the game from your Minecraft install. If it can't find it, drag your Minecraft launcher's game folder into the Terminal window when it asks (or see Troubleshooting).
4. It creates `~/Applications/Horizon Offline.app`. Open it from Launchpad or that folder to play.

## Playing

Basic controls (the usual Minecraft ones):

| Action | Key |
|---|---|
| Look around | Mouse |
| Move | W A S D |
| Jump | Space |
| Sneak | Left Shift |
| Sprint | Left Ctrl |
| Break block / attack | Left click |
| Place block / use item | Right click |
| Select hotbar slot | 1 to 9 or scroll wheel |
| Inventory | E |
| Drop item | Q |
| Hide HUD | F1 |
| Screenshot | F2 |
| Debug screen | F3 |
| Pause menu | Esc |
| Light level overlay | F7 |

Keys added by mods (zoom, minimap and so on) can be changed in **Options > Controls**.

## Included mods

| Mod | What it does | Author |
|---|---|---|
| AppleSkin | Shows food and saturation on the HUD | [soufied/AppleSkin-Horizon](https://github.com/soufied/AppleSkin-Horizon) |
| Zoom, Minimap, FPS overlay | Zoom key, a small map, an FPS counter | [horizon-rust/horizon-mods](https://github.com/horizon-rust/horizon-mods) |
| Minimap Worldmap & Waypoints Reworked | Full world map and waypoints | [daniliammo](https://github.com/daniliammo) |
| Fullbright, Armor status, Status effect HUD, Toggle sprint, Light overlay (F7), Crosshair indicator | Quality-of-life HUD and view tweaks | [CayMac97](https://github.com/CayMac97) |
| Chat heads | Shows player heads next to chat messages | [Domanffe](https://github.com/Domanffe) |
| Held item info | Shows details of the item in your hand | [AltMugen](https://github.com/AltMugen) |
| Jade | Look-at tooltip for blocks and mobs | [Joeypc6](https://github.com/Joeypc6) |
| Dynamic FPS | Drops to 20 fps when the window is idle for 60 s, saving battery | [Lyvt-Dev](https://github.com/Lyvt-Dev) |
| Dynamic lights | Held light sources light up their surroundings | [DeportedToHell/MCRE-Mods](https://github.com/DeportedToHell/MCRE-Mods) |

Full credits and licenses: `LICENSES/CREDITS.md` inside the zip, or [dist/LICENSES/CREDITS.md](dist/LICENSES/CREDITS.md) in this repo.

## Tips for smooth FPS on 8 GB

- Close Chrome and other heavy apps. When macOS starts swapping memory to disk, FPS collapses.
- Set render distance to 10 to 12.
- In Video Settings, set resolution scale to 70 to 85.
- Plug in the charger.
- Heavy shader packs roughly halve FPS.
- Large resource packs use extra memory.

## Updating

- The launcher may offer newer Horizon releases. The installer turned off auto-install so the M1 build stays selected. Only install a newer release if you want to leave the M1 build.
- To go back after trying another version, pick the M1 build in the launcher under Settings > selected version, or run:
  ```sh
  /Applications/Horizon.app/Contents/MacOS/horizon-launcher settings selected-version native-fdc87ae-m1-daily7-73decc0fdc30
  ```
- For a new M1 build, download the new zip and run its installer. Your worlds are kept.

## Where things live

| What | Location |
|---|---|
| Worlds and game settings | `~/Library/Application Support/horizon` |
| Launcher and installed builds | `~/Library/Application Support/horizon-launcher` |

## Troubleshooting

**macOS says the installer is "damaged" or "can't be opened".**
Follow the quarantine steps in Install, step 3: right-click > Open, **Open Anyway** in System Settings, or the `xattr` command.

**The installer says it "could not find Minecraft 26.3".**
Launch Minecraft: Java Edition 26.3 once in your Minecraft launcher, then run the installer again. Or drag the launcher's game folder (the one holding `versions` and `assets`) into the installer window when it asks.

**The game crashes or won't start.**
Print the logs with:
```sh
/Applications/Horizon.app/Contents/MacOS/horizon-launcher logs
```
To get a link you can send to someone for help, run:
```sh
/Applications/Horizon.app/Contents/MacOS/horizon-launcher share-log
```

**Horizon Offline does nothing when I open it.**
Check `~/Library/Application Support/horizon/logs/play-offline.out`.

**Low FPS.**
See the tips above.

## Uninstall

Delete these:

- `/Applications/Horizon.app`
- `~/Applications/Horizon Offline.app`
- `~/Library/Application Support/horizon-launcher`
- `~/Library/Application Support/horizon`

Warning: the `horizon` folder holds your worlds. Back it up first if you want to keep them.

## Credits and licenses

- Horizon is made by [horizon-rust](https://github.com/horizon-rust/horizon) and is licensed under LGPL-3.0.
- Each mod belongs to its author (see the mods table).
- The modified source in this build is the set of patches in this repo (see below).
- Minecraft is a trademark of Mojang Studios / Microsoft. No Minecraft files are included.

## For developers

Tuning and mod work for Horizon (native Rust/Metal Minecraft 26.3 client) on a MacBook Air M1, 8 GB.

- `outputs/horizon-native/<fix>/` patches against Horizon commit `fdc87ae`, each with `NOTES.md`. Build stacks: `outputs/horizon-native/daily*-stack.txt` (current: `daily7-stack.txt`).
- `outputs/horizon-runtime/build-fast-fdc87ae.py` builds a client from a stack plus the mods in `mods.lock.tsv` (repo + pinned commit per mod).
- `outputs/bench-2026-11-10/` bench harness (`bench.py`), gallery test (`gallery.py`), run results (`runs/*.json`).
- `tools/`, `tests/`: converter and test tools. `docs/`: research and reports.
- `config/`: snapshot of the live game and launcher settings. `tools/config-sync.sh snapshot` copies live settings in (then commit); `tools/config-sync.sh restore` puts them back (game and launcher closed). Account files are not tracked.
- `dist/` holds the release installer. `dist/package.sh` builds the zip from the live build.

Builds, source clones, screenshots and pack zips stay local (see `.gitignore`).

License: upstream Horizon is LGPL-3.0, see `dist/LICENSES/`. Mods listed in `mods.lock.tsv` belong to their authors and are not included here.
