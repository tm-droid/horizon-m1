// Window-local adapter. No shared game settings or server clocks are modified.
use super::{
    Game,
    dynamic_fps_runtime::{self as runtime, Decision, Input, RenderGate},
};
use std::{
    collections::HashMap,
    sync::{Arc, Mutex, OnceLock, Weak},
    time::Instant,
};
use winit::{
    event::WindowEvent,
    window::{Window, WindowId},
};
struct State {
    window: Weak<Window>,
    hovered: bool,
    occluded: bool,
    activity: Instant,
    unfocused_since: Option<Instant>,
    clock: Instant,
    gate: RenderGate,
}
fn states() -> &'static Mutex<HashMap<WindowId, State>> {
    static STATES: OnceLock<Mutex<HashMap<WindowId, State>>> = OnceLock::new();
    STATES.get_or_init(Mutex::default)
}
fn supported(game: &Game<'_>) -> bool {
    game.window.is_some()
        && !game.options.headless
        && !game.options.offscreen
        && game.options.frames.is_none()
        && game.options.world_frames.is_none()
}
fn with_state<T>(game: &Game<'_>, f: impl FnOnce(&mut State, Instant) -> T) -> Option<T> {
    if !supported(game) {
        return None;
    }
    let window = game.window.as_ref()?;
    let now = Instant::now();
    let mut states = states().lock().unwrap_or_else(|e| e.into_inner());
    states.retain(|_, s| s.window.strong_count() != 0);
    let s = states.entry(window.id()).or_insert_with(|| State {
        window: Arc::downgrade(window),
        hovered: false,
        occluded: false,
        activity: now,
        unfocused_since: (!game.focused).then_some(now),
        clock: now,
        gate: RenderGate::default(),
    });
    Some(f(s, now))
}
fn decision(game: &Game<'_>, s: &State, now: Instant) -> Decision {
    let window = game.window.as_ref().unwrap();
    let invisible =
        s.occluded || window.is_minimized().unwrap_or(false) || window.is_visible() == Some(false);
    runtime::config().decide(Input {
        focused: game.focused,
        hovered: s.hovered,
        invisible,
        in_world: game.title.is_none(),
        battery_mode: game.settings.horizon.battery,
        idle_for: now
            .saturating_duration_since(game.last_input)
            .min(now.saturating_duration_since(s.activity)),
        unfocused_for: s.unfocused_since.map_or(std::time::Duration::ZERO, |t| {
            now.saturating_duration_since(t)
        }),
    })
}
pub(super) fn event(game: &Game<'_>, id: WindowId, event: &WindowEvent) {
    if game.window.as_ref().is_none_or(|w| w.id() != id) {
        return;
    }
    with_state(game, |s, now| match event {
        WindowEvent::Focused(focused) => {
            s.unfocused_since = (!focused).then_some(now);
            if *focused {
                s.activity = now;
                s.occluded = false;
            }
        }
        WindowEvent::Occluded(hidden) => s.occluded = *hidden,
        WindowEvent::CursorEntered { .. } => s.hovered = true,
        WindowEvent::CursorLeft { .. } => s.hovered = false,
        WindowEvent::CursorMoved { .. } => {
            s.hovered = true;
            s.activity = now;
        }
        WindowEvent::KeyboardInput { .. }
        | WindowEvent::MouseInput { .. }
        | WindowEvent::MouseWheel { .. }
        | WindowEvent::Touch(_) => s.activity = now,
        _ => {}
    });
    if matches!(event, WindowEvent::Destroyed) {
        states()
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .remove(&id);
    }
}
pub(super) fn limit(game: &Game<'_>, original: i32) -> i32 {
    with_state(game, |s, now| decision(game, s, now).loop_limit(original)).unwrap_or(original)
}
pub(super) fn skip_render(game: &Game<'_>) -> bool {
    with_state(game, |s, now| {
        let d = decision(game, s, now);
        !s.gate.allow(now.saturating_duration_since(s.clock), d)
    })
    .unwrap_or(false)
}
pub(super) fn audio(game: &mut Game<'_>) {
    if !supported(game) || !runtime::config().reduce_volume {
        return;
    }
    let volume = with_state(game, |s, now| decision(game, s, now).volume).unwrap_or(1.0);
    // Always derive from the saved user option, so repeated ticks never compound attenuation.
    game.audio.master = game.settings.master_volume * volume;
}
