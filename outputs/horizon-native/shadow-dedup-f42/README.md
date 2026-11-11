# shadow-dedup-f42 (audit #6, hasher-only variant)

Status: **ready, UNBUILT / UNTESTED**. Requires shadow-scratch applied first (it edits the `shadow_seen` lines that patch adds).

## What
`Renderer::shadow_seen` becomes `crate::fast_hash::FxHashSet<SectionKey>` (initialised with `Default::default()`), the
hasher the renderer already uses for `lod_retiring`. Only `clear`, `extend` and `contains` are used, so behaviour and
the order of `shadow_visible` are unchanged.

## What was NOT taken from the audit
Dropping the `boxed` pre-sort, or replacing the set with an `in_view_distance` predicate, changes the input order of the
final unstable height sort, so equal-height ties could reorder (bit-identical output not guaranteed), and the predicate
equivalence needs a full read of `Resident::visible`. Gain of those over the hasher swap: well under 0.1 ms. Skipped.

## Expected gain / risk
0.02-0.1 ms render-thread CPU with shadows on (SipHash of every near section key per frame). Visual risk zero; compile risk
very low (same type API as the std set used here).

## Tests
No new test: the set is membership-only. After the build: existing shadow tests + MakeUp static "shadow visibility" span.
