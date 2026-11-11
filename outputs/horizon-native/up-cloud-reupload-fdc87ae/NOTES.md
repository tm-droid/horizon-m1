# up-cloud-reupload (upstream 203b3ac8)
Base: nightly fdc87ae + daily7 stack (33 patches). Applies alone and after all earlier candidates (`git apply --check`). NOT compiled or run (benchmark in progress; no cargo allowed): build before benching.
Files: client-render/src/clouds.rs (clean cherry-pick).

## What
Cloud mesh origin snaps to a 4-cell grid (`SNAP_CELLS`) instead of every 12-block cell, +4 ring of cells, and `Uniform::offset` carries the sub-snap shift; `sub_x/sub_z` added to MeshKey for the 3x3 inward faces only when the camera is inside the layer. Rebuild + 6.5 MB re-upload (~11 ms at 128 chunks) happens 4x less often.

## Expected effect (M1 8 GB)
Removes the periodic ~11 ms cloud frame spike in flight; slightly more cloud vertices (extra ring, past fog). Visually identical (extra cells beyond fully faded alpha).

## Conflicts
None (applies unchanged).
