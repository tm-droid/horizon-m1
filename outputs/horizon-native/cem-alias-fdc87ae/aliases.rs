// Evidence: docs/horizon-converter/cem-binding-gaps-2026-11-03.md.
// Exact f42 and fdc87ae caller already removed `_baby`; never infer a baby's identity here.
fn audited_part_aliases(model: &str, part: &str) -> core::ops::ControlFlow<String> {
    let target = match (model, part) {
        ("guardian" | "elder_guardian", "body") => "head",
        ("wolf" | "wolf_armor", "mane") => "upper_body",
        ("happy_ghast_harness", "body") => "harness",
        ("puffer_fish_small", "tail") => "back_fin",
        ("puffer_fish_small", "eye_right") => "right_eye",
        ("puffer_fish_small", "eye_left") => "left_eye",
        ("tropical_fish_pattern_a" | "tropical_fish_pattern_b", "fin_top") => "top_fin",
        ("salmon" | "salmon_small" | "salmon_large", "fin_back_1") => "top_front_fin",
        ("salmon" | "salmon_small" | "salmon_large", "fin_back_2") => "top_back_fin",
        ("salmon" | "salmon_small" | "salmon_large", "tail") => "back_fin",
        ("horse_armor" | "skeleton_horse_armor", "neck") => "head_parts",
        ("horse_armor" | "skeleton_horse_armor", "mouth") => "upper_mouth",
        _ => return core::ops::ControlFlow::Continue(()),
    };
    core::ops::ControlFlow::Break(target.to_owned())
}
