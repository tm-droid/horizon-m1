# Changelog

Each section is one Horizon M1 build. `dist/release.sh` copies the section of the build it publishes into the
release notes, so add the section before releasing.

## daily7-fix5

Same game build as daily7-fix4; the installer, the uninstaller and the bundled launcher change.

- Play always starts the Horizon M1 build. The installer now pins the Horizon instance to it, so a launcher
  that was already set to another Horizon version can no longer start that one instead (no mods, broken shader).
  It also refuses to run while the launcher window is open, and checks the result before it finishes.
- The uninstaller removes only what Horizon M1 added. If you had Horizon before, your launcher, its other
  versions, your instance and settings, packs and shader stay or are put back as they were.
- Bundles the Horizon launcher 0.2.97 (was 0.2.86).

## daily7-fix4

Same game build as daily7-fix3; only the look and the installer change.

- Faster full look: Optimized Bushy Leaves is removed (about +12 fps and 320 MB less memory on an M1 Air).
  The full look is now 63 packs at about 58 fps.
- The installer asks two looks instead of three: 1 full or 2 plain. The Fast look is gone because it is now
  the same as the full look. Updating keeps your choice and turns Optimized Bushy Leaves off.

## daily7-fix3

- Updates itself: the new **Horizon M1** app (in Launchpad) checks for a new build once a day and asks before
  updating. It replaces "Horizon Offline" and works for Microsoft and offline players.
- Updating keeps your answers (look, Microsoft or offline, player name) and asks nothing.
  Old M1 builds are removed after an update; the previous one stays as a fallback.
- Shorter install line: `zsh -c "$(curl -fsSL https://tm-droid.github.io/horizon-m1/i)"`.
- Mob fixes: mooshroom mushrooms sit on the back, slimes have a see-through outer layer,
  charged creepers show their aura.
- Horizon-Texture-Fixes pack: sheep wool, chickens, bees and other Fresh Animations mobs render correctly.
- Offline: the installer finds Minecraft 26.3 in any launcher folder, or downloads it from Mojang without sign-in.

## daily7

- First public build: M1-tuned Horizon (native Rust) client for Minecraft Java 26.3 with 16 mods.
- The full look: 63 resource packs and the MakeUp Ultra Fast shader, with fast and plain options.
- One-click installer for Microsoft or offline play, and an uninstaller.
