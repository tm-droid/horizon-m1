// Independent implementation based on Dynamic FPS's public feature description.
use serde::{Deserialize, Serialize};
use std::{sync::OnceLock, time::Duration};

#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
#[serde(default, deny_unknown_fields)]
pub struct Config {
    pub enabled: bool,
    pub apply_in_menus: bool,
    pub focused_fps: u32,
    pub hovered_fps: u32,
    pub unfocused_fps: u32,
    pub minimized_fps: u32,
    pub idle_fps: u32,
    pub idle_timeout_seconds: u64,
    pub unfocused_delay_ms: u64,
    pub battery_mode_fps: u32,
    pub reduce_volume: bool,
    pub hovered_volume: f32,
    pub unfocused_volume: f32,
    pub minimized_volume: f32,
    pub idle_volume: f32,
}
impl Default for Config {
    fn default() -> Self {
        Self {
            enabled: true,
            apply_in_menus: true,
            focused_fps: 0,
            hovered_fps: 30,
            unfocused_fps: 10,
            minimized_fps: 1,
            idle_fps: 20,
            idle_timeout_seconds: 60,
            unfocused_delay_ms: 500,
            battery_mode_fps: 30,
            reduce_volume: false,
            hovered_volume: 1.0,
            unfocused_volume: 0.25,
            minimized_volume: 0.0,
            idle_volume: 0.5,
        }
    }
}
impl Config {
    pub fn validate(&self) -> Result<(), &'static str> {
        if [
            self.focused_fps,
            self.hovered_fps,
            self.unfocused_fps,
            self.minimized_fps,
            self.idle_fps,
            self.battery_mode_fps,
        ]
        .iter()
        .any(|&v| v > 1000)
        {
            return Err("FPS caps must be between 0 (inherit) and 1000");
        }
        if self.idle_timeout_seconds > 86400 || self.unfocused_delay_ms > 60000 {
            return Err("idle timeout must be <= 86400s and focus delay <= 60000ms");
        }
        if [
            self.hovered_volume,
            self.unfocused_volume,
            self.minimized_volume,
            self.idle_volume,
        ]
        .iter()
        .any(|v| !v.is_finite() || !(0.0..=1.0).contains(v))
        {
            return Err("volume multipliers must be finite and between 0 and 1");
        }
        Ok(())
    }
    pub fn decide(&self, input: Input) -> Decision {
        if !self.enabled || (!self.apply_in_menus && !input.in_world) {
            return Decision {
                phase: Phase::Focused,
                fps: 0,
                volume: 1.0,
            };
        }
        let phase = if input.invisible {
            Phase::Invisible
        } else if !input.focused
            && input.unfocused_for >= Duration::from_millis(self.unfocused_delay_ms)
        {
            if input.hovered {
                Phase::Hovered
            } else {
                Phase::Unfocused
            }
        } else if input.focused
            && self.idle_timeout_seconds != 0
            && input.idle_for >= Duration::from_secs(self.idle_timeout_seconds)
        {
            Phase::Idle
        } else {
            Phase::Focused
        };
        let (mut fps, mut volume) = match phase {
            Phase::Focused => (self.focused_fps, 1.0),
            Phase::Hovered => (self.hovered_fps, self.hovered_volume),
            Phase::Unfocused => (self.unfocused_fps, self.unfocused_volume),
            Phase::Invisible => (self.minimized_fps, self.minimized_volume),
            Phase::Idle => (self.idle_fps, self.idle_volume),
        };
        if input.battery_mode && self.battery_mode_fps != 0 {
            fps = if fps == 0 {
                self.battery_mode_fps
            } else {
                fps.min(self.battery_mode_fps)
            };
        }
        if !self.reduce_volume {
            volume = 1.0;
        }
        Decision { phase, fps, volume }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Phase {
    Focused,
    Hovered,
    Unfocused,
    Invisible,
    Idle,
}
#[derive(Clone, Copy, Debug)]
pub struct Input {
    pub focused: bool,
    pub hovered: bool,
    pub invisible: bool,
    pub in_world: bool,
    pub battery_mode: bool,
    pub idle_for: Duration,
    pub unfocused_for: Duration,
}
#[derive(Clone, Copy, Debug)]
pub struct Decision {
    pub phase: Phase,
    pub fps: u32,
    pub volume: f32,
}
impl Decision {
    pub fn loop_limit(self, original: i32) -> i32 {
        if self.fps == 0 {
            return original;
        }
        // Let the client continue processing input/networking/ticks at up to 20 Hz
        // when rendering at 1 FPS. Never raise a user's or another mod's lower cap.
        original.min(self.fps.max(20) as i32)
    }
}

#[derive(Default)]
pub struct RenderGate {
    last: Option<Duration>,
    phase: Option<Phase>,
}
impl RenderGate {
    pub fn allow(&mut self, now: Duration, decision: Decision) -> bool {
        if decision.fps == 0 {
            self.last = None;
            self.phase = Some(decision.phase);
            return true;
        }
        let interval = Duration::from_nanos(1_000_000_000u64.div_ceil(u64::from(decision.fps)));
        let changed = self.phase != Some(decision.phase);
        let due = self
            .last
            .is_none_or(|last| now.saturating_sub(last) >= interval);
        self.phase = Some(decision.phase);
        if changed || due {
            self.last = Some(now);
            true
        } else {
            false
        }
    }
}

pub fn config() -> &'static Config {
    static CONFIG: OnceLock<Config> = OnceLock::new();
    CONFIG.get_or_init(|| {
        let path = std::path::Path::new("config/dynamic-fps-for-rust.json");
        let loaded = std::fs::read_to_string(path);
        match loaded {
            Ok(text) => match serde_json::from_str::<Config>(&text) {
                Ok(c) => match c.validate() {
                    Ok(()) => c,
                    Err(e) => {
                        eprintln!("[dynamic_fps_for_rust] {e}; using defaults");
                        Config::default()
                    }
                },
                Err(e) => {
                    eprintln!("[dynamic_fps_for_rust] Invalid config: {e}; using defaults");
                    Config::default()
                }
            },
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                let c = Config::default();
                if let Some(parent) = path.parent() {
                    let _ = std::fs::create_dir_all(parent);
                }
                if let Ok(mut file) = std::fs::OpenOptions::new()
                    .write(true)
                    .create_new(true)
                    .open(path)
                {
                    use std::io::Write;
                    let _ = writeln!(file, "{}", serde_json::to_string_pretty(&c).unwrap());
                }
                c
            }
            Err(e) => {
                eprintln!("[dynamic_fps_for_rust] Cannot read config: {e}; using defaults");
                Config::default()
            }
        }
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    fn active() -> Input {
        Input {
            focused: true,
            hovered: true,
            invisible: false,
            in_world: true,
            battery_mode: false,
            idle_for: Duration::ZERO,
            unfocused_for: Duration::ZERO,
        }
    }
    #[test]
    fn states_have_distinct_caps_and_invisibility_wins() {
        let c = Config::default();
        let mut i = active();
        assert_eq!(c.decide(i).fps, 0);
        i.focused = false;
        i.unfocused_for = Duration::from_secs(1);
        assert_eq!(c.decide(i).phase, Phase::Hovered);
        assert_eq!(c.decide(i).fps, 30);
        i.hovered = false;
        assert_eq!(c.decide(i).fps, 10);
        i.invisible = true;
        assert_eq!(c.decide(i).phase, Phase::Invisible);
        assert_eq!(c.decide(i).fps, 1);
        i.focused = true;
        assert_eq!(c.decide(i).fps, 1);
    }
    #[test]
    fn focus_grace_idle_boundary_and_disabled_timeout() {
        let mut c = Config::default();
        let mut i = active();
        i.focused = false;
        i.hovered = false;
        i.unfocused_for = Duration::from_millis(499);
        assert_eq!(c.decide(i).fps, 0);
        i.unfocused_for = Duration::from_millis(500);
        assert_eq!(c.decide(i).fps, 10);
        i = active();
        i.idle_for = Duration::from_secs(59);
        assert_eq!(c.decide(i).fps, 0);
        i.idle_for = Duration::from_secs(60);
        assert_eq!(c.decide(i).phase, Phase::Idle);
        c.idle_timeout_seconds = 0;
        assert_eq!(c.decide(i).fps, 0);
    }
    #[test]
    fn existing_caps_and_battery_mode_are_respected() {
        let c = Config::default();
        let mut i = active();
        i.invisible = true;
        let d = c.decide(i);
        assert_eq!(d.loop_limit(260), 20);
        assert_eq!(d.loop_limit(5), 5);
        i = active();
        i.battery_mode = true;
        assert_eq!(c.decide(i).fps, 30);
        assert_eq!(c.decide(i).loop_limit(15), 15);
    }
    #[test]
    fn disabled_mod_and_excluded_menus_leave_outputs_alone() {
        let mut c = Config {
            enabled: false,
            ..Default::default()
        };
        let mut i = active();
        i.invisible = true;
        let d = c.decide(i);
        assert_eq!(d.loop_limit(144), 144);
        assert_eq!(d.volume, 1.0);
        c.enabled = true;
        c.apply_in_menus = false;
        i.in_world = false;
        assert_eq!(c.decide(i).fps, 0);
    }
    #[test]
    fn one_render_per_second_keeps_twenty_update_opportunities() {
        let d = Decision {
            phase: Phase::Invisible,
            fps: 1,
            volume: 1.0,
        };
        let mut g = RenderGate::default();
        let rendered: Vec<_> = (0..40)
            .filter(|&tick| g.allow(Duration::from_millis(tick * 50), d))
            .collect();
        assert_eq!(rendered, vec![0, 20]);
        assert_eq!(d.loop_limit(120), 20);
    }
    #[test]
    fn refocusing_and_hovering_render_immediately() {
        let mut g = RenderGate::default();
        let mut d = Decision {
            phase: Phase::Invisible,
            fps: 1,
            volume: 1.0,
        };
        assert!(g.allow(Duration::ZERO, d));
        assert!(!g.allow(Duration::from_millis(50), d));
        d.phase = Phase::Hovered;
        d.fps = 30;
        assert!(g.allow(Duration::from_millis(60), d));
        d.phase = Phase::Focused;
        d.fps = 0;
        assert!(g.allow(Duration::from_millis(61), d));
        assert!(g.allow(Duration::from_millis(62), d));
    }
    #[test]
    fn volume_is_optional_and_returns_to_full_on_focus() {
        let mut c = Config::default();
        let mut i = active();
        i.invisible = true;
        assert_eq!(c.decide(i).volume, 1.0);
        c.reduce_volume = true;
        assert_eq!(c.decide(i).volume, 0.0);
        i = active();
        assert_eq!(c.decide(i).volume, 1.0);
    }
    #[test]
    fn unsafe_configuration_values_are_rejected() {
        let mut c = Config::default();
        assert!(c.validate().is_ok());
        c.minimized_fps = 1001;
        assert!(c.validate().is_err());
        c.minimized_fps = 1;
        c.idle_volume = f32::NAN;
        assert!(c.validate().is_err());
        assert!(serde_json::from_str::<Config>(r#"{"typo":1}"#).is_err());
    }
}
