// Original implementation for Horizon; uses the documented Fast Items behavior.
use serde::{Deserialize, Serialize};
use std::sync::OnceLock;

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(default, deny_unknown_fields)]
pub struct Config {
    pub enabled: bool,
    pub entity_shadows: bool,
    pub render_sides: bool,
    pub affect_3d_models: bool,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            enabled: true,
            entity_shadows: true,
            render_sides: false,
            affect_3d_models: true,
        }
    }
}

impl Config {
    pub fn shadow(self, original: (f32, f32)) -> (f32, f32) {
        if self.enabled && !self.entity_shadows {
            (0.0, 0.0)
        } else {
            original
        }
    }
}

pub fn config() -> &'static Config {
    static CONFIG: OnceLock<Config> = OnceLock::new();
    CONFIG.get_or_init(|| {
        // Horizon runs with the selected instance as its working directory.
        // Read once, so there is no disk I/O in the per-item rendering path.
        let path = std::path::Path::new("config/fast-items.json");
        match std::fs::read_to_string(path) {
            Ok(text) => match serde_json::from_str(&text) {
                Ok(config) => config,
                Err(error) => {
                    eprintln!(
                        "[fast_items] Invalid {}: {error}; using defaults",
                        path.display()
                    );
                    Config::default()
                }
            },
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
                let defaults = Config::default();
                // Never overwrite an existing configuration, even if another window creates it.
                if let Some(parent) = path.parent() {
                    let _ = std::fs::create_dir_all(parent);
                }
                if let Ok(mut file) = std::fs::OpenOptions::new()
                    .write(true)
                    .create_new(true)
                    .open(path)
                {
                    use std::io::Write;
                    let _ = writeln!(file, "{}", serde_json::to_string_pretty(&defaults).unwrap());
                }
                defaults
            }
            Err(error) => {
                eprintln!(
                    "[fast_items] Cannot read {}: {error}; using defaults",
                    path.display()
                );
                Config::default()
            }
        }
    })
}

// Replace only a dropped item's world orientation; all positional animation stays.
pub fn face_camera(original: glam::Mat4, camera: glam::Quat) -> glam::Mat4 {
    glam::Mat4::from_translation(original.w_axis.truncate()) * glam::Mat4::from_quat(camera)
}

pub type Positions = [[f32; 3]; 4];

// Recognize the canonical generated sprite slab geometrically, conservatively.
// Cubes, arbitrary thin/rotated models and special renderers keep their geometry.
// BakedItemModel does not retain the source model's builtin/generated marker.
pub fn sprite_fronts(quads: &[(Positions, bool)], uses_block_light: bool) -> Option<Vec<usize>> {
    if uses_block_light || quads.is_empty() {
        return None;
    }
    const EPS: f32 = 1.0e-5;
    let mut fronts = Vec::new();
    for (index, (corners, south)) in quads.iter().enumerate() {
        if !corners.iter().all(|p| {
            p.iter().all(|v| v.is_finite())
                && p[0] >= -EPS
                && p[0] <= 1.0 + EPS
                && p[1] >= -EPS
                && p[1] <= 1.0 + EPS
                && p[2] >= 7.5 / 16.0 - EPS
                && p[2] <= 8.5 / 16.0 + EPS
        }) {
            return None;
        }
        if *south {
            let z = corners[0][2];
            if !corners.iter().all(|p| {
                (p[2] - z).abs() <= EPS
                    && (p[0].abs() <= EPS || (p[0] - 1.0).abs() <= EPS)
                    && (p[1].abs() <= EPS || (p[1] - 1.0).abs() <= EPS)
            }) {
                return None;
            }
            let lo_x = corners.iter().map(|p| p[0]).fold(f32::INFINITY, f32::min);
            let hi_x = corners
                .iter()
                .map(|p| p[0])
                .fold(f32::NEG_INFINITY, f32::max);
            let lo_y = corners.iter().map(|p| p[1]).fold(f32::INFINITY, f32::min);
            let hi_y = corners
                .iter()
                .map(|p| p[1])
                .fold(f32::NEG_INFINITY, f32::max);
            if lo_x.abs() > EPS
                || lo_y.abs() > EPS
                || (hi_x - 1.0).abs() > EPS
                || (hi_y - 1.0).abs() > EPS
            {
                return None;
            }
            fronts.push(index);
        }
    }
    (!fronts.is_empty()).then_some(fronts)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn front(z: f32) -> Positions {
        [[0.0, 0.0, z], [1.0, 0.0, z], [1.0, 1.0, z], [0.0, 1.0, z]]
    }
    #[test]
    fn layered_sprites_keep_each_front_and_drop_extrusion() {
        let side = [
            [0.0, 0.0, 7.5 / 16.0],
            [0.0, 1.0, 7.5 / 16.0],
            [0.0, 1.0, 8.5 / 16.0],
            [0.0, 0.0, 8.5 / 16.0],
        ];
        let quads = [
            (front(8.5 / 16.0), true),
            (front(7.5 / 16.0), false),
            (side, false),
            (front(8.5 / 16.0), true),
        ];
        assert_eq!(sprite_fronts(&quads, false), Some(vec![0, 3]));
    }
    #[test]
    fn cubes_custom_geometry_and_bad_data_are_preserved() {
        assert_eq!(sprite_fronts(&[(front(1.0), true)], false), None);
        assert_eq!(sprite_fronts(&[(front(8.5 / 16.0), true)], true), None);
        let mut custom = front(0.5);
        custom[1][0] = 0.8;
        assert_eq!(sprite_fronts(&[(custom, true)], false), None);
        let mut bad = front(0.5);
        bad[0][2] = f32::NAN;
        assert_eq!(sprite_fronts(&[(bad, true)], false), None);
        assert_eq!(sprite_fronts(&[], false), None);
    }
    #[test]
    fn flattened_sprites_remain_identifiable() {
        assert_eq!(sprite_fronts(&[(front(0.5), true)], false), Some(vec![0]));
    }
    #[test]
    fn camera_facing_preserves_bobbing_and_handles_vertical_views() {
        use glam::{Mat4, Quat, Vec3};
        let original =
            Mat4::from_translation(Vec3::new(4.0, 0.375, -8.0)) * Mat4::from_rotation_y(0.73);
        for (camera, toward_camera) in [
            (Quat::IDENTITY, Vec3::Z),
            (Quat::from_rotation_y(std::f32::consts::FRAC_PI_2), Vec3::X),
            (Quat::from_rotation_x(std::f32::consts::FRAC_PI_2), -Vec3::Y),
            (Quat::from_rotation_x(-std::f32::consts::FRAC_PI_2), Vec3::Y),
        ] {
            let posed = face_camera(original, camera);
            assert!((posed.transform_vector3(Vec3::Z) - toward_camera).length() < 1e-5);
            assert_eq!(
                posed.transform_point3(Vec3::ZERO),
                Vec3::new(4.0, 0.375, -8.0)
            );
            assert!((posed.transform_vector3(Vec3::X).length() - 1.0).abs() < 1e-5);
        }
    }

    #[test]
    fn config_is_partial_and_malformed_values_are_rejected() {
        let config: Config =
            serde_json::from_str(r#"{"render_sides":true,"affect_3d_models":false}"#).unwrap();
        assert!(config.enabled && config.entity_shadows && config.render_sides);
        assert!(!config.affect_3d_models);
        assert!(serde_json::from_str::<Config>(r#"{"enabled":"false"}"#).is_err());
        assert!(serde_json::from_str::<Config>(r#"{"typo":true}"#).is_err());
    }
    #[test]
    fn disabling_mod_restores_original_shadow_settings() {
        let mut c = Config {
            entity_shadows: false,
            ..Default::default()
        };
        assert_eq!(c.shadow((0.15, 1.0)), (0.0, 0.0));
        c.enabled = false;
        assert_eq!(c.shadow((0.15, 1.0)), (0.15, 1.0));
        assert_eq!(Config::default().shadow((0.15, 1.0)), (0.15, 1.0));
    }
}
