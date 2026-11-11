# Horizon daily compatibility — 2026-11-07

The test target is the actual daily Horizon profile on the 8 GB M1, with all 52 selected ZIPs in their original order and MakeUp Ultra Fast 9.6 with the daily trim. The earlier disposable v4 migration is a different pack snapshot. The tests use a clone of the disposable Horizon-Test world. The Java instance and personal worlds were outside the write scope.

## Per-item audit

`outputs/horizon-compatibility/daily-20261107/inventory.json` records each pack's archive result, contents by category, winning root paths and overlay metadata. It also records each Java JAR's archive result, enable state, metadata and matches to the project's porter. All 52 ZIPs and all 259 Java JARs passed archive reads. Of those JARs, 240 were enabled in Java and 19 were disabled. The project's porter matched 239 current source JARs. Five Fabric descriptors needed lenient control-character parsing. Only CEM and Zoom are compiled as native add-ons in the daily binary. A Java inventory match shows where to start a port. Runtime parity requires a native implementation and a test for the behavior.

The root-path inventory approximates layer priority and does not resolve every dynamic selector, filter, or conditional asset. The paired test's pack selection confirms the mounted stack and targeted screenshots exercise effective assets. Many pack assets are conditional or shadowed by a later layer. Passing archive checks and loading the combined stack do not establish feature parity for every mod or asset.

## Findings and changes

- **Fullbright.** The previous native build carried CEM and Zoom and lacked the Java fullbright gameplay shortcut. The new native J toggle starts off each launch. It changes the native lightmap and MakeUp's night-vision input without granting a gameplay effect. It is manual. Turn it on when entering a cave and off when leaving. It can brighten exposed terrain while on. Chat, menus and repeats are guarded.
- **Player animation.** Horizon's local third-person render entity was missing the grounded and sprinting state used by the animation pack. The native change passes those flags through and supplies `is_gliding` from the render entity's existing fall-flying state. This is scoped to the relevant animation inputs.
- **Adult mooshroom.** The earlier play log shows a missing animation import in the active extension's JEM. The overlay connects the compatible shared cow carrier with the mooshroom's expected variable setup. Its three native mushroom props replace the duplicate CEM boxes. Red and brown variants need visual checks for alignment.
- **Smithing.** The earlier play log shows that Horizon rejected the pack's custom text shader. The dark container pack uses it for an animated title glyph and blanks six help strings. The overlay restores those strings and gives the title white text. It replaces four double-frame armour placeholders with one-frame vanilla sprites while preserving the dark container background. Other container titles can still depend on the unsupported shader.

## Reproduction

Run with framework Python 3.13 and from the launcher data root.

- `python3 tools/horizon-compat-inventory.py outputs/horizon-compatibility/daily-20261107` exited 0 and produced the inventory and a hashed pack snapshot.
- `python3 tools/horizon-build-compat-overlay.py` exited 0 and verified all eight output ZIP members. `overlay-provenance.json` records source and member hashes.
- `git apply --check` passed for `outputs/horizon-native/daily-compat-f42/daily-compat.patch` against the verified daily r3 source.
- `python3 -m py_compile tools/horizon-compat-inventory.py tools/horizon-build-compat-overlay.py tools/horizon-offline-test.py tools/horizon_daily_compat.py outputs/horizon-runtime/run-daily-compat.py` checks the audit, overlay builder and fixture.
- Use the shared device queue with `HORIZON_TEST_QUEUE=1` and `python3 outputs/horizon-runtime/run-daily-compat.py baseline 1107` or `fixed 1107`. The runner checks input hashes, the ordered pack selection, the native executable and positive MakeUp program activation.

## Remaining compatibility scope

The remaining missing model imports are tracked in [the full-stack JPM audit](full-stack-jpm-gaps.md). Each needs a bone and expression compatibility check. The rejected resource text shader affects more than smithing. Further Java feature coverage should be tracked by the porter task IDs, using reproducible behavior checks and an explicit disposition for features that require native work. Continue the render optimization measurements independently of the compatibility fixtures.

## Verified runtime results and rollout

The r8 build completed in 821.95 seconds through shared queue ticket 171 with Rust 1.99.1. The native executable SHA-256 is `50e9896067e385fa1a9c8399871360e679e9d59a0c750e8452e219c2d904aca0`. CEM and Zoom were carried over with their original mod hashes.

Ticket 172 reproduced the mooshroom and smithing UI defects and the missing J behavior in r3. Its synthetic local-only smithing menu could not verify the recipe. The fixture now places the table on the integrated server and opens it through the standard interaction path. Ticket 175 passed that corrected baseline with the same broken smithing appearance. Ticket 173 passed all four corrected fixture cases with r8 and the overlay. These were Apple M1 Metal captures at 2880×1676. Both arms loaded six MakeUp programs. In `tests/daily-compat-fixed-1107`:

- The red and brown adult mooshrooms have coherent bodies and visible mushrooms in front and oblique views. The missing adult carrier warning is gone.
- Third-person idle, walking and jump screenshots show changing poses. The `is_gliding` unknown-variable warning is gone for both player model variants. Sprinting, swimming, elytra flight and other skins were outside this visual fixture.
- The dark strip across the smithing screen disappeared. The empty, template-only and result screens display a readable Upgrade Gear title. A diamond sword upgraded to netherite, transferred into the hotbar and cleared the inputs. The baseline passed that recipe with the original visual defect present.
- In a fixed crop of the sealed stone cave, mean 8-bit grayscale luminance was 10.57 before J, 44.33 with fullbright on and 10.53 after turning it off. The game logged exactly one on/off pair despite a J press while smithing was open. Gameplay effects were unchanged. Baseline J produced only normal variation at 10.57, 10.79 and 10.84.
- C zoom magnified the scene, captured the wheel, released and re-engaged. The wheel did not change the selected hotbar slot while zoom was held.

Ticket 174 selected `native-f42-m1-r8-903e75d76f09` and appended `Horizon-Daily-Compatibility.zip` at highest priority after verifying every original active pack hash and both MakeUp files against the test inputs. The rollout changed only the selected version and pack list and added the local overlay. Backups and the verification receipt are in `outputs/horizon-runtime/checkpoints/daily-compat-20261107`. If a rollback is required, close Horizon, restore the two backed-up configuration files or revert the two selected values, and remove the added overlay. Preserve newer user options when reverting individual values.

The media pass `python3 tools/horizon-check-pack-media.py outputs/horizon-compatibility/daily-20261107/snapshot outputs/horizon-compatibility/daily-20261107/media-checks.json` exited 0 with 5,426 PNG and 59 Ogg decodes across the 52 original packs and zero failures. The original pack inventory read 30,840 members and found no invalid JSON in the metadata it parsed. These checks cover source assets, with in-game verification scoped to the features above.

## Follow-up animation checks

A read-only source comparison found that the elder guardian and wandering trader extension models can use their original Fresh Animations shared carriers without missing bone references or collisions with addon animation writes. The separate compatibility ZIP preserves each addon model and places its original carrier flags ahead of the import. The elder keeps the addon fin expressions. The trader still has Horizon's existing per-part texture limitation on its pouches.

`python3 tools/horizon-build-compat-overlay.py --animation-followup` verified all three ZIP members. The SHA-256 is `005451cd7c8a9cbe98c40fd514e1c4418ec6fb1058c52ecd541bbed0906ab750`. Ticket 176 ran `run-daily-compat.py mobs-base 1107` and `run-daily-compat.py mobs-fix 1107` sequentially, both exit 0. These were the same r8 build with the same MakeUp and original layer hashes. The candidate added only the second overlay. It removed both missing-import warnings and added no CEM warnings. Screenshots show the trader standing on the platform with visible legs and the elder positioned correctly on land and in water with changing dry poses. The stationary fixtures do not cover the complete AI movement cycle or trader pouch textures.

Eight original missing imports remain. Parched and stray share a compatible skeleton carrier and retain separate physics writes, which makes them the next grounded candidates for movement checks. Mule's donkey carrier fits the model's literal bone references and needs mounted, bare and chest-equipped checks. Cave spider has overlapping leg writes and needs an ordered carrier/extension check. Bogged's mushroom carrier has mismatched geometry. Skeleton horse, charged creeper and happy ghast harness have missing literal targets in their winning models. A global filename alias would lose those distinctions.

Ticket 177 activated the second overlay after verifying the r8 binary, both MakeUp files, both overlay hashes and all 52 original ZIP hashes against the successful test. The daily list now contains vanilla, the original 52 packs and the two compatibility overlays. `outputs/horizon-runtime/checkpoints/daily-compat-mobs-20261107/options.txt` backs up the state with only the first overlay. Restore that file or remove just the second selection when rolling back the follow-up.
