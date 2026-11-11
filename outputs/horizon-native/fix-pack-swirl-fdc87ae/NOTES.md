# fix-pack-swirl
Cause: crates/horizon-client-render/src/gfx/pack_entities.rs `plain()` (~675) rejects overlay 34, so the whole mob run (body + swirl quads) failed the `program_of(..).filter(plain)` check in `prepare` (~516) and went to Horizon's fallback draw (`rest`, fs_energy_swirl) instead of the pack's entity program.
Fix: the run split in `prepare` now also triggers when `has_swirl(run)`; swirl quads -> new `Part::Swirl` (program None -> `rest`), body quads -> `Part::Plain` -> pack program.
Risk: split runs skip `copied.push` (motion-vector history, `at_velocity`) so body of charged mob has no previous-frame link (TAA/motion blur ghost-free but zero velocity). Swirl still not pack-lit (uses Horizon additive draw). Not compiled/tested (no cargo per instructions).
