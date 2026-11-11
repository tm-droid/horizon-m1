# Zoom f42 source candidate — UNBUILT / UNTESTED

`bundle/` is an unpacked `.hnmod` source input. It contains `horizon-native.json`, the copied mixin TOML, all seven Rust files and the original MIT license. It is not a compiled mod or installed game. Pass **bundle/** to the launcher, not `bundle/mixins/zoom/`.

The JSON and TOML preserve upstream's historical tested engine `6f8c7a0e5d531d3834c4d0be4659a1db8e7e5c2a`. The recognized JSON `hooks: 1` allows the launcher to select the explicitly requested f42 base and repin its staged copy. f42 is the desired source target, not a claim of completed testing. No source outside this candidate was changed.

The copied local runtime defaults to C, starts at 4x, multiplies scroll by 1.5, clamps 1–10x and resets on release. Existing user bindings override the default. All copied helper/runtime bytes are preserved in `provenance.json`; prior local defaults patch, upstream hashes and licenses remain traceable in `provenance/`. Upstream README's Z default is historical.

`hook-contract.json` records six injection signatures and five helper signatures inspected against fresh official f42 source (API359). `build-plan.json` contains exact **unexecuted** build argv, environment, prerequisites and required engine identity. See `docs/horizon-converter/zoom-f42-candidate.md` for acceptance. Source contracts are retained with pinned URLs and SHA256 hashes.

Remaining gaps include native compilation and behavior tests, Zoomify high range and exact scroll-step count, precise easing/sensitivity/hand FOV, secondary F6/HUD behavior and spyglass composition. Menu/focus transitions and disabling while held still require runtime checks.
