# pass-merge-f42 (audit #3, partial; #4 not done)

Status: **partial, UNBUILT / UNTESTED**. Touches only `crates/horizon-client-render/src/gfx/pack_post.rs`.

## What
`draw_entities` opened one render pass per entity program (each Load+Store of every written colortex and the depth).
Now consecutive entity programs that write exactly the same (location, buffer) outputs share one pass. `draw_sky`
already did this for its two programs; this applies the same pattern (bind first, open one pass, draw in order).
Pure helper `run_lengths` decides the runs and is unit tested; `Pass::merges()` is the eligibility predicate.

## Safety rule (what keeps the image identical)
A program may share the pass of the program before it only if ALL hold:
1. Both `merges()`: no `copies` (read-and-write copies), no `image_copies`, no `snapshots`, no `images` at all
   (so no stand-in clears and no storage-image writes that would need a barrier between draws), no SSBO `buffers`,
   no `flip`, `mipmaps`, `compute`, `sink`, partial `viewport`, and not shadow-space. Binding such a program records
   nothing on the encoder, so binding a whole run before its pass opens leaves every encoder command in place.
2. Identical `writes` => identical colour attachments, same depth, same Load/Store ops as separate passes
   (`begin()` uses `Load/Store` for all of them).
3. No program in the run samples a buffer another program in the run writes (`reads & written == 0` both ways, across
   the run). A buffer that is both written and sampled needs a pass boundary (wgpu would reject it as a usage conflict
   inside one pass; on the GPU the sampled data would also be stale). Such a program starts a new pass.
4. Order is preserved: programs in index order, draws in `geometry.draws` order inside each program, `late` filter
   unchanged. A non-mergeable program is always its own pass, and splits the run around it.
Per-program UBOs are written by `queue.write_buffer` before submit, so binding early does not change what any draw reads
(each program owns its UBO; the bind-twice-per-frame case is already last-write-wins today).
`mips_valid &= !written` is applied after the run; it cannot change a member's bind-group key because of rule 3.
GPU timing (`pack_timing`) now attributes a merged run to its first program's name; the other names disappear from the
list, so pass counts differ from the control by design.

## Not done (and why)
- Cross-function merging (sky -> terrain -> entities -> lines -> clouds -> hand): each `draw_*` binds, draws and
  closes its own pass and the draw closures borrow `PackPost`; threading one open pass through 6-8 functions with
  Rust lifetimes is not something to write blind without a compiler. Likely the bigger gain; do it with cargo available.
- #4 (fold clear-only passes into the first writer's `LoadOp::Clear`): needs flush-before-sample tracking in `bind()`
  and every `begin()` caller, plus proof the first writer covers the whole attachment. Same reason.

## Expected gain / risk
Only shader packs with 2+ mergeable entity programs on screen (MakeUp/Complementary entity, block-entity, translucent
parts): a fraction of the audit's 1-4 ms, unmeasured. Risk: wgpu validation error if a predicate misses a hazard
(loud, not silent); Rust compile errors are possible (borrow/closure shapes; not compiled). Visual risk zero when the rule holds.

## Tests
- Passed here without cargo (`standalone_tests.py` + isolated rustc, 5 tests): same writes merge, different writes split,
  read/write conflicts split (both directions), non-mergeable splits and is alone, random sequences partition exactly.
- After the build: `cargo test -p horizon-client-render pass_merge_tests`, then the existing pack_post tests
  (`cargo test -p horizon-client-render pack_post`), then MakeUp/Complementary static + flight exact image diff and
  `pack_timing` pass counts (expect fewer entity passes).
