# fix-pack-entity-id

## Lead check (entityId 10101)
Disproved. No code path hands a pack id 10101: ids come only from `entity.properties` by entity name
(`game/shader_packs.rs:621 mark_entity_part`), nothing marks `minecraft:lightning_bolt` (bolts draw
separately via `frame.lightning`), unmapped names get `missing_entity` (65535 with item.properties).

## Dragon (confirmed from code, not run)
`game.rs` (~15673) appends `dragon_geometry` / `dragon_fireball_geometry` to `entities` with no
`mark_entity`. `entity_geometry` ends on `mark_stage(..., "DESTROY")` (game.rs:11242), so the dragon
inherits that span. `pack_entities.rs:program_of` maps it to DESTROY and `plain(run)` is true for the
dragon (overlay 0/1), so the pack's `gbuffers_damagedblock` draws the whole body: flat pale look.
Fix: mark `minecraft:ender_dragon` / `minecraft:dragon_fireball` spans, then re-mark `DESTROY` so later
unmarked geometry (end crystals, outline fill) keeps its old behaviour.

## Charged creeper / wither swirl (NOT confirmed)
Swirl quads (overlay 34) are in the mob's own span (creatures.rs:7508 marks before the mob draws), so
they carry the creeper/wither id. `plain()` (pack_entities.rs:675) rejects overlay 34, so the whole
mob run goes to Horizon's own draw (`rest`), not the pack, with `fs_energy_swirl` additive. Not found
by reading: why that looks flat under MakeUp. Needs a frame capture. Suspects: additive (one,one)
swirl into pack targets, or whole-run fallback drawing the body outside the pack's lighting.

## Risk
Low: 6 lines, only when a pack/native spans are active (mark_* no-op otherwise). After the dragon,
a DESTROY stage mark is re-added so following geometry behaves as before. No test added (frame
assembly in game.rs has no unit harness).
