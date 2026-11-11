// Rendering adapters for Horizon 998b1d830. No gameplay or shared model mutation.
use super::fast_items_runtime::{config, face_camera, sprite_fronts};
use horizon_assets::{item_bake::BakedItemModel, model::Direction};
use horizon_client::item_render::{ItemRenderState, LayerGeometry};
use std::{
    collections::BTreeMap,
    sync::{Arc, Mutex, OnceLock, Weak},
};

struct Cached {
    original: Weak<BakedItemModel>,
    flat: Option<Arc<BakedItemModel>>,
}

fn descriptor(model: &BakedItemModel) -> Vec<(super::fast_items_runtime::Positions, bool)> {
    model
        .quads
        .iter()
        .map(|q| (q.positions, q.facing == Direction::South))
        .collect()
}

fn flattened(model: &Arc<BakedItemModel>) -> Option<Arc<BakedItemModel>> {
    static CACHE: OnceLock<Mutex<BTreeMap<usize, Cached>>> = OnceLock::new();
    let mut cache = CACHE
        .get_or_init(Mutex::default)
        .lock()
        .unwrap_or_else(|e| e.into_inner());
    let key = Arc::as_ptr(model) as usize;
    if let Some(cached) = cache.get(&key) {
        return cached.flat.clone();
    }
    // Weak source keys cannot alias new allocations. Bound retained output models,
    // and release stale resource-pack/animated sprite models before adding more.
    cache.retain(|_, entry| entry.original.strong_count() != 0);
    if cache.len() >= 4096 {
        // Preserve unknown models beyond the budget instead of churning GPU model identities.
        return None;
    }
    let flat = sprite_fronts(&descriptor(model), model.uses_block_light).map(|fronts| {
        let mut flat = (**model).clone();
        flat.quads = fronts
            .into_iter()
            .map(|i| {
                let mut q = model.quads[i].clone();
                for p in &mut q.positions {
                    p[2] = 0.5;
                }
                q
            })
            .collect();
        Arc::new(flat)
    });
    cache.insert(
        key,
        Cached {
            original: Arc::downgrade(model),
            flat: flat.clone(),
        },
    );
    flat
}

pub(super) fn prepare(mut state: ItemRenderState) -> ItemRenderState {
    let cfg = config();
    if !cfg.enabled || cfg.render_sides {
        return state;
    }
    for layer in &mut state.layers {
        if let LayerGeometry::Quads(model) = &mut layer.geometry
            && let Some(flat) = flattened(model)
        {
            *model = flat;
        }
    }
    state
}

fn sprite_state(state: &ItemRenderState) -> bool {
    !state.layers.is_empty()
        && state.layers.iter().all(|layer| match &layer.geometry {
            LayerGeometry::Quads(model) => {
                sprite_fronts(&descriptor(model), model.uses_block_light).is_some()
            }
            LayerGeometry::Special { .. } => false,
        })
}

pub(super) fn pose(
    original: glam::Mat4,
    game: &super::Game<'_>,
    state: &ItemRenderState,
) -> glam::Mat4 {
    let cfg = config();
    if !cfg.enabled || (!cfg.affect_3d_models && !sprite_state(state)) {
        return original;
    }
    // Original pose is translation * Y spin. Replace its orientation only;
    // preserve interpolation, bobbing, ground lift, stack copies and model transforms.
    face_camera(original, game.camera_orientation())
}
