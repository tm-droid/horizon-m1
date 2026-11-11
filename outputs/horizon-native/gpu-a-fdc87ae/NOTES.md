# gpu-a: merge gbuffers render passes

What: sky, solid terrain and cutout terrain draw in one render pass. Lines and clouds also share one. A pass is kept open (`Carry`) only when every program drawn in it `merges()`, the next program writes exactly the same attachments, and neither samples a buffer the other writes. These are the same rules `run_lengths` uses for entity runs.

Why safe: draw order and Load/Store ops do not change. A carried pass is dropped before `bind` whenever the next program cannot take it, so no copy is recorded while the encoder is locked by a `forget_lifetime` pass. Nothing touches the encoder between the draws and the hand-off.

Gain: one tile store and reload of colortex1 plus depth per merged boundary, about 1-1.5 ms each at 2560x1600 on M1. Expect sky to terrain always, lines to clouds when the outline shows, and solid to cutout on split packs.

Risk: medium-low. Merged programs lose their own GPU timestamp labels. If the code compiles but wgpu rejects it, the error will read "encoder is locked" or be a usage conflict.

Visual checks:
- Sky still shows behind and between terrain, with no seams at the horizon.
- The block outline draws, and the clouds draw over it.
- On split packs, cutout leaves and grass render correctly.
- The log has no wgpu validation errors.
