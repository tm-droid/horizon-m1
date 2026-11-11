# Horizon container GUI sweep — 2026-11-07

The test target is daily r8, the 52 original selected packs, both prior compatibility overlays, and the daily MakeUp Ultra Fast 9.6 settings. Fixtures use a clone of Horizon-Test. The Java profile and personal worlds are outside the write scope.

## Root cause and scope

The active Recolourful Containers DARK pack uses Java's resource core shaders to select a tile from encoded sprites, move or hide those sprites based on screen position, and animate private-use font glyphs. Horizon draws GUI atlas sprites through its native HUD and rejects the pack's text shader at its sampler declaration. The selected pack remains readable and contributes its artwork. Shader-dependent artwork requires a compatible representation.

- The duplicated book is one control rendering a 42×21 sheet with two book states. The native click target is 20×18. The overlay supplies one 20×18 book image per hover state from the original art. The same image serves open and closed states, and the panel still toggles normally.
- The four original armor sprites are 32×16 two-tile sheets. The earlier smithing overlay already overrides the shared armor sprite paths globally. The current baseline confirmed one icon in each empty slot. Equipping four iron pieces replaced the four placeholders.
- Seven more screen titles use animated font glyphs. Dispenser, dropper, enchanting, anvil, ender chest, cartography and stonecutter now use readable native titles. The new locale inherits the first overlay's smithing corrections and intentionally blank labels.
- Beacon has four 84×84 button sheets, six 36×18 effect icon sheets in the active version overlay, and transparent confirm and cancel sprites. Native-size buttons, one effect icon per cell and visible controls address those dependencies while retaining the beacon background.
- Powered crafter and villager trade arrows use geometry encoded for the Java shader. The GUI overlay supplies native-size versions for those three paths.

The pack has other deliberate animations. Furnace and HUD progress sheets are sampled as their first frame in the paths inspected. This pass does not implement general Java core-shader support or guarantee that every non-container screen, item model, language or pack animation has parity.

## Checks and results

- `python3 -m py_compile tools/horizon_gui_compat.py tools/horizon-build-compat-overlay.py tools/horizon-offline-test.py outputs/horizon-runtime/run-daily-compat.py` exited 0.
- `python3 tools/horizon-build-compat-overlay.py --gui-followup` verified all 20 archive members. Final candidate SHA-256 is `07e743e35a66091cf4d702e190f5d5c19a33e8e3f1a5c31152d5f38d1f99c7f3`.
- `run-daily-compat.py gui-base 1107` in shared queue ticket 178 reproduced the recipe-button duplicate, shader-glyph corruption and beacon overlap. Twenty of 21 fixture cases passed. The ender-chest screen used the client's virtual container key, which the initial fixture mistook for a mismatched position. The client itself exited 0.
- `run-daily-compat.py gui-fix 1107` in ticket 179 passed all 24 controls and captured the new titles and one recipe image. Visual review caught a second beacon issue that the interaction-only assertions missed. The final candidate corrects the effect art and confirm/cancel separately.

- `run-daily-compat.py gui-fix beacon-r2` in ticket 180 exited 0. All 24 screen cases completed and captured 33 screenshots at 2880×1676 on Apple M1 Metal with six MakeUp programs active. The screenshots show a single recipe button in inventory, crafting and the furnace family, single armor placeholders, readable titles, single beacon effects and visible confirmation icons, and separate normal/out-of-stock trade arrows. Crafting produced and transferred four sticks. A paid beacon applied Haste after confirmation. The crafter power flag was read back before its screenshot. The remaining cases check opening and appearance, with further recipe, equipment, stock and animation permutations outside this fixture.
- Ticket 181 activated `Horizon-GUI-Compatibility.zip` after matching the daily binary, MakeUp archive and options, all 52 original ZIPs and both earlier overlays to the tested inputs. It changed only the Horizon pack selection and added the local archive. The rollback copy of `options.txt` and the receipt are in `outputs/horizon-runtime/checkpoints/gui-compat-20261107`.
- Follow-up logs still report eight unresolved CEM imports, 11 model assets with unsupported per-part texture/sprite rendering, and five unresolved animation names across happy ghast, its ropes and baby piglin. Those are independent of container artwork. The Better Lanterns empty placeholder warning was already reproduced and found visually harmless in the existing [lantern fixture](lantern-compat-overlay.md). Archive integrity does not establish those feature behaviors.

## Performance evidence

The ordinary daily log records shader loading, unsupported assets and whether GPU timing is available. It contains no sampled FPS or per-pass cost from the user's play session. The earlier controlled [fresh-flight diagnostic](research/Codex-fresh-flight.md) averaged 7.33 ms CPU and 22.46 ms GPU on its first pass, with similar FPS on the revisit.

Ticket 182 ran `run-daily-compat.py render-profile 1107` with the full 56-layer daily pack stack, r8 and MakeUp. The on-screen M1 Metal sample measured 955 frames in 19.99 seconds at 2880×1676 with a 260 FPS cap and Immediate presentation. Average FPS was 47.78. Mean CPU and GPU frame times were 6.39 ms and 20.07 ms. Medians across 14 logged timing windows after the cow fixture were 5.44 ms for world rendering, 5.33 ms for MakeUp deferred shading and 3.11 ms for terrain G-buffer rendering. These timings describe the sampled scene and include instrumentation. They are not a paired estimate of the GUI overlay's FPS impact.

The game and harness exited 0. The first wrapper exit was 1 after reading raw-series keys from a summary-only measurement. The validator now uses the actual CPU and GPU summary fields. Revalidating the saved result passed with foreground, Metal, active pack and MakeUp program checks. The measurement and rolling timings are in `outputs/horizon-runtime/tests/daily-compat-render-profile-1107`.
