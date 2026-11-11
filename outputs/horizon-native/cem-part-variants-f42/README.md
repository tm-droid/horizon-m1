# Random sprites on explicit CEM body parts

`cem-part-variants.patch` applies to `outputs/horizon-runtime/m1-performance-r10/20261108-084936/source`.

The r10 CPU part renderer used the base atlas sprite directly. The patch appends explicit body part texture names after the existing draw names in the tick-driven picker, preserving which texture supplies the primary variant. Part rendering now consults the existing random and blink sprite lookup. An unavailable selected sprite falls back to the part's base sprite, then to the existing inherited texture when the base is also missing. Body overlays still skip successfully painted explicit parts. Ordinary mob and layer sprite selection is unchanged.

In the active FA extension, six explicit sheep wool bones use `entity/sheep/sheep_wool`. The pack's `colors.7=red` rule selects variant 6. Iron golem headwear uses `entity/iron_golem/iron_golem_hat`. The base texture is fully transparent and variant 2 is visible. The pack selects variant 2 for a golem named Cletus and weights base versus variant 2 at 50 to 1 for the ordinary rule. The patch leaves those pack decisions in the existing selector. The pack's `jeb_` rule asks for the base sprite. Dynamic rainbow tint on explicit body parts is a separate case.

`git apply --check --whitespace=error` passed from exact r10. The added Rust test covers a part-only rule, red and named variants, the ordinary default and missing-variant atlas fallback. Rust tests and in-game verification are still pending. For a live comparison, use red and white adult sheep, a named Cletus golem, and an ordinary golem with a fixed seed that chooses the transparent base.
