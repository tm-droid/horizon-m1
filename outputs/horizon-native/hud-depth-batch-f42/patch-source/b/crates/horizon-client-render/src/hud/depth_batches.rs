//! Keep independent GUI item depth buffers in one tile pass where their scissors do not overlap.
use super::Blend;
use std::ops::Range;

/// Match the renderer's existing conversion from GUI pixels to framebuffer scissors.
pub(super) fn scissor(clip: [u32; 4], zoom: f32, size: [u32; 2]) -> [u32; 4] {
    let [x, y, w, h] = clip.map(|v| (v as f32 * zoom) as u32);
    let (x, y) = (x.min(size[0]), y.min(size[1]));
    [x, y, w.min(size[0] - x), h.min(size[1] - y)]
}

fn overlaps(a: [u32; 4], b: [u32; 4]) -> bool {
    a[2] != 0 && a[3] != 0 && b[2] != 0 && b[3] != 0
        && a[0] < b[0] + b[2] && b[0] < a[0] + a[2]
        && a[1] < b[1] + b[3] && b[1] < a[1] + a[3]
}

/// Every depth write is confined to its scissor, so disjoint scissors can share
/// one initial clear. Any overlap needs a fresh clear; ordinary blend runs keep
/// their original ordering and pass boundaries. No extra allocation per frame.
pub(super) fn group_end(runs: &[(Range<u32>, Blend)], at: usize, zoom: f32,
                        size: [u32; 2], batch_depth: bool) -> usize {
    if !matches!(runs[at].1, Blend::Depth(_)) {
        return runs[at..].iter().position(|(_, b)| matches!(b, Blend::Depth(_)))
            .map_or(runs.len(), |n| at + n);
    }
    if !batch_depth { return at + 1; }
    let mut end = at + 1;
    while let Some((_, Blend::Depth(clip))) = runs.get(end) {
        let next = scissor(*clip, zoom, size);
        if runs[at..end].iter().any(|(_, blend)| match blend {
            Blend::Depth(previous) => overlaps(scissor(*previous, zoom, size), next),
            _ => false,
        }) { break; }
        end += 1;
    }
    end
}

#[cfg(test)]
mod tests {
    use super::*;
    fn depth(rect: [u32;4]) -> (Range<u32>, Blend) { (0..6, Blend::Depth(rect)) }
    fn end(runs: &[(Range<u32>, Blend)]) -> usize { group_end(runs, 0, 1.0, [100,100], true) }
    #[test] fn touching_items_share_a_clear() {
        assert_eq!(end(&[depth([0,0,10,10]),depth([10,0,10,10]),depth([20,0,10,10])]),3);
    }
    #[test] fn overlap_with_any_earlier_item_starts_a_new_pass() {
        assert_eq!(end(&[depth([0,0,10,10]),depth([20,0,10,10]),depth([5,5,10,10])]),2);
    }
    #[test] fn two_dimensional_separation_is_enough() {
        assert_eq!(end(&[depth([0,0,20,10]),depth([0,10,20,10])]),2);
    }
    #[test] fn intervening_alpha_preserves_the_boundary() {
        assert_eq!(end(&[depth([0,0,10,10]),(6..12,Blend::Alpha),depth([20,0,10,10])]),1);
        assert_eq!(end(&[(0..6,Blend::Alpha),(6..12,Blend::Alpha),depth([0,0,10,10])]),2);
    }
    #[test] fn uses_physical_clipped_scissors() {
        assert_eq!(scissor([8,9,10,10],1.5,[20,20]),[12,13,8,7]);
        assert_eq!(scissor([120,120,10,10],1.0,[100,100]),[100,100,0,0]);
        assert_eq!(end(&[depth([120,120,10,10]),depth([0,0,10,10])]),2);
    }
    #[test] fn control_keeps_one_depth_run_per_pass() {
        let runs=[depth([0,0,10,10]),depth([20,0,10,10])];
        assert_eq!(group_end(&runs,0,1.0,[100,100],false),1);
    }
    #[test] fn later_groups_use_their_own_start() {
        let runs=[depth([0,0,10,10]),depth([5,0,10,10]),depth([20,0,10,10])];
        assert_eq!(group_end(&runs,1,1.0,[100,100],true),3);
    }
}
