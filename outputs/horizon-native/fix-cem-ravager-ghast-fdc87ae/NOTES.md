# fix-cem-ravager-ghast (fdc87ae daily6)

Patch: fix-cem-ravager-ghast.patch (only crates/horizon-client/src/mobs/cem.rs). Not compiled or tested: no cargo run.

## Bug 1: Ravager upside down / legs up / floating 24 px
- Cause: crates/horizon-client/src/mobs/cem.rs `vanilla_part` (arm `(_, "back_left_leg") => left_hind_leg`, and the three siblings, ~l.476-479), used as `Names.vanilla` in `CemLayer::build` (~l.636) and resolved first in `Names::find` (cem_anim.rs:255-259, vanilla node before bone id).
- FA ravager.jem keeps its legs as submodels with ids back_left_leg / back_right_leg / front_left_leg / front_right_leg under `body > legs`, boxes [-4,0,-4,8,37,8] with pivot at file y 0. ravager_animations.jpm writes `back_left_leg.tx=9, .ty=24, .tz=21.8, .rx/.ry/.rz` (ty=24 = ground, relative to body at ty=0).
- Horizon resolved `back_left_leg` to the vanilla `left_hind_leg` node (an emptied sibling under root), so the FA leg bones never got ty=24 and stayed at their rest pivot y=0 (24 px above the ground, y-down). Their inverted-y boxes (37 tall) then point up from there: legs up above the body, head lower than the leg tops, whole rig floating 24 px (1.5 blocks).
- Fix: `animation_target` (new, cem.rs) keeps a submodel id as is when it is also a vanilla alias, unless a top-level jem entry (part name or id) carries that name. Top-level parts, ids that are no alias, and `this`/`part` are unchanged.
- Unit test: `a_submodel_id_beats_a_vanilla_alias_unless_a_top_level_entry_has_the_name` (cem.rs tests).
- Confidence: high on cause (every other FA ravager target resolves fine; no warnings in latest.log), medium-high that it is the whole visual symptom. Not checked in game.
- Risk: a pack with a submodel id equal to an alias name but meaning the vanilla part, with no top-level entry of that name, now animates the bone. That is what OptiFine/EMF do (ids resolve to jem bones).

## Bug 2: Ghast without tentacles (squid)
- No CEM bug found in code. ghast.jem has empty top-level `tentacle1..9` parts (they map to vanilla tentacle0..8 and just clear the vanilla boxes) and the real tentacles are 9 submodels `tentacle_1..9` (box [-1,-8,-1,2,8,2]) under `body`. Targets `tentacle_N.*` resolve to those bones (no alias hit: `n("tentacle")` fails on "_1"), no warnings for ghast in latest.log.
- Geometry: root pose is y=-84.056, scale 4.5, ground at model y=24. FA body ty=20.5 (+4 bone pivot) puts the body bottom at model y~24.5 = the entity's feet; the tentacles pivot ~1 px above the body bottom and hang 7-8 px (x4.5 x0.9) = about 1.8 blocks BELOW the feet. The gallery spawns the ghast on the floor, so the tentacles are inside the floor. Vanilla ghast hangs 3.8 blocks below its feet, so this is expected for a floor spawn.
- If the ghast is grounded (is_on_ground true), FA tucks the tentacles (rx -85 deg) mostly inside/under the body, so only small stubs show.
- Suggested check (no code change): summon the ghast 6 blocks up (or via a glass floor) and look from the side. If tentacles are still missing there, rerun with `RUST_LOG` model dump; I would then look at Poses/skip_draw of the `cem#` bones, which I found no reason for.
- Squid / glow_squid: same pattern (empty top-level tentacle1..8, real `anim_tentacleN` submodels under `body > tentacles`); targets are not aliases, so the same non-finding. The gallery squid sits in a water tank; not checked visually in detail.
- Confidence that ghast is not a Horizon bug: medium (~65%), because I cannot render it.

## render.rs
No change needed.
