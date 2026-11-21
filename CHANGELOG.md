# Changelog

Each section is one Horizon M1 build. `dist/release.sh` copies the section of the build it publishes into the
release notes, so add the section before releasing.

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
