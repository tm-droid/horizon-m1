# MakeUp 9.6 deferred AO experiment

The current R11 trace recorded a 5.14 ms median for MakeUp's deferred pass. The candidate reuses the center depth and its linearization. It skips all eight neighbor taps where AO distance attenuation is exactly one, since that makes the AO multiplier one. The same samples and attenuation apply everywhere else. The input ZIP, sidecar and shader settings are pinned. The generator compares every archive member and preserves the original license.

`python3 build-candidate.py` writes the candidate ZIP and its byte-identical sidecar beside the generator. The active shader archive and game profile are outside the write path.

Use an explicit shader archive override in the disposable runner. Compare matching R11 and resource packs, with a terrain scene and a cave scene. Keep the camera, weather, shader options and Retina dimensions fixed. Confirm the pack translated and the deferred pass actually ran. Compare whole-frame GPU time and 1% lows alongside deferred pass medians. Compare near terrain, distant skyline, held hand and water captures against repeated controls for normal cloud and temporal-AA variation. Test the Nether separately if selecting the candidate because it changes its AO fog depth after reading the center depth. The current checks cover archive integrity and member contents. Translation, appearance and speed need the device run.
