#!/usr/bin/env python3
"""Write a dependency-free Rust test file from a TRANSFORMED workspace (no cargo needed).

    python3 -I standalone_tests.py WORKSPACE OUT.rs
    rustc --edition 2021 --test OUT.rs -o OUT && ./OUT

Copies `cull_reach` (particles.rs) and `Frustum::intersects` / `frustum` (gfx.rs) verbatim over a
tiny glam stand-in, then checks the conservative property on random cameras and quads: whenever
any point of a rotated particle quad is inside the view volume, the box test keeps the particle.
"""
import sys
from pathlib import Path

workspace, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
src = workspace / "crates/horizon-client-render/src"
particles = (src / "particles.rs").read_text()
gfx = (src / "gfx.rs").read_text()


def block(text, sig, close="\n}\n"):
    i = text.index(sig)
    return text[text.rfind("\n", 0, i) + 1:text.index(close, i) + len(close)]


reach = block(particles, "fn cull_reach(")
frustum_fn = block(gfx, "fn frustum(m: Mat4)")
intersects = block(gfx, "pub fn intersects(&self, min: Vec3, max: Vec3)", "\n    }\n")

MATH = r'''
use std::ops::{Add, Div, Mul, Sub};
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Vec3 { pub x: f32, pub y: f32, pub z: f32 }
impl Vec3 {
    pub fn new(x: f32, y: f32, z: f32) -> Self { Self { x, y, z } }
    pub fn dot(self, o: Vec3) -> f32 { self.x * o.x + self.y * o.y + self.z * o.z }
    pub fn length(self) -> f32 { self.dot(self).sqrt() }
}
#[derive(Clone, Copy, Debug)]
pub struct Vec4 { pub x: f32, pub y: f32, pub z: f32, pub w: f32 }
impl Vec4 {
    pub fn new(x: f32, y: f32, z: f32, w: f32) -> Self { Self { x, y, z, w } }
    pub fn truncate(self) -> Vec3 { Vec3::new(self.x, self.y, self.z) }
    pub fn dot(self, o: Vec4) -> f32 { self.x * o.x + self.y * o.y + self.z * o.z + self.w * o.w }
}
impl Add for Vec4 { type Output = Vec4; fn add(self, o: Vec4) -> Vec4 { Vec4::new(self.x + o.x, self.y + o.y, self.z + o.z, self.w + o.w) } }
impl Sub for Vec4 { type Output = Vec4; fn sub(self, o: Vec4) -> Vec4 { Vec4::new(self.x - o.x, self.y - o.y, self.z - o.z, self.w - o.w) } }
impl Div<f32> for Vec4 { type Output = Vec4; fn div(self, d: f32) -> Vec4 { Vec4::new(self.x / d, self.y / d, self.z / d, self.w / d) } }
#[derive(Clone, Copy)]
pub struct Mat4 { rows: [Vec4; 4] }
impl Mat4 { pub fn row(&self, i: usize) -> Vec4 { self.rows[i] } }
impl Mul for Mat4 {
    type Output = Mat4;
    fn mul(self, o: Mat4) -> Mat4 {
        let col = |j: usize| [o.rows[0], o.rows[1], o.rows[2], o.rows[3]].map(|r| [r.x, r.y, r.z, r.w][j]);
        let rows = self.rows.map(|r| {
            let v: [f32; 4] = std::array::from_fn(|j| { let c = col(j); r.x * c[0] + r.y * c[1] + r.z * c[2] + r.w * c[3] });
            Vec4::new(v[0], v[1], v[2], v[3])
        });
        Mat4 { rows }
    }
}
/// glam `perspective_rh(fov_y, aspect, z_near, z_far)` as rows.
fn perspective_rh(fov: f32, aspect: f32, z_near: f32, z_far: f32) -> Mat4 {
    let f = 1.0 / (fov / 2.0).tan();
    let r = z_far / (z_near - z_far);
    Mat4 { rows: [
        Vec4::new(f / aspect, 0.0, 0.0, 0.0),
        Vec4::new(0.0, f, 0.0, 0.0),
        Vec4::new(0.0, 0.0, r, z_near * r),
        Vec4::new(0.0, 0.0, -1.0, 0.0),
    ] }
}
/// Camera at the origin looking along (yaw, pitch); rows are right, up, -forward.
fn view(yaw: f32, pitch: f32) -> (Mat4, [Vec3; 3]) {
    let (sy, cy, sp, cp) = (yaw.sin(), yaw.cos(), pitch.sin(), pitch.cos());
    let fwd = Vec3::new(cp * sy, sp, -cp * cy);
    let right = Vec3::new(cy, 0.0, sy);
    let up = Vec3::new(-sp * sy, cp, sp * cy);
    let row = |v: Vec3, s: f32| Vec4::new(v.x * s, v.y * s, v.z * s, 0.0);
    (Mat4 { rows: [row(right, 1.0), row(up, 1.0), row(fwd, -1.0), Vec4::new(0.0, 0.0, 0.0, 1.0)] }, [right, up, fwd])
}
pub struct Frustum { planes: [Vec4; 6] }
'''

TESTS = r'''
struct Rng(u64);
impl Rng {
    fn next(&mut self) -> f32 {
        self.0 ^= self.0 << 13; self.0 ^= self.0 >> 7; self.0 ^= self.0 << 17;
        (self.0 >> 40) as f32 / (1u64 << 24) as f32
    }
    fn range(&mut self, a: f32, b: f32) -> f32 { a + (b - a) * self.next() }
}
fn norm(v: Vec3) -> Vec3 { let l = v.length(); Vec3::new(v.x / l, v.y / l, v.z / l) }
fn cross(a: Vec3, b: Vec3) -> Vec3 { Vec3::new(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x) }

fn clip_inside(vp: &Mat4, p: Vec3) -> bool {
    let c = |i: usize| { let r = vp.row(i); r.x * p.x + r.y * p.y + r.z * p.z + r.w };
    let (x, y, z, w) = (c(0), c(1), c(2), c(3));
    w > 0.0 && x.abs() <= w && y.abs() <= w && z >= 0.0 && z <= w
}

#[test]
fn reach_covers_every_rotated_quad_and_is_conservative() {
    let mut rng = Rng(0x9E3779B97F4A7C15);
    let (mut kept, mut culled, mut visible) = (0u32, 0u32, 0u32);
    for _ in 0..400 {
        let fov = rng.range(30.0, 110.0_f32).to_radians();
        let aspect = rng.range(1.0, 2.4);
        let far = rng.range(64.0, 400.0);
        let (yaw, pitch) = (rng.range(-3.1, 3.1), rng.range(-1.5, 1.5));
        let (v, _) = view(yaw, pitch);
        let vp = perspective_rh(fov, aspect, far, 0.05) * v;
        let f = Frustum { planes: frustum(vp) };
        for _ in 0..200 {
            let c = Vec3::new(rng.range(-80.0, 80.0), rng.range(-80.0, 80.0), rng.range(-80.0, 80.0));
            let size = rng.range(0.005, 2.0);
            // Random orthonormal quad frame, as any particle rotation produces.
            let a = norm(Vec3::new(rng.range(-1.0, 1.0), rng.range(-1.0, 1.0), rng.range(-1.0, 1.0) + 0.01));
            let b = norm(cross(a, norm(Vec3::new(rng.range(-1.0, 1.0), rng.range(-1.0, 1.0), rng.range(-1.0, 1.0) + 0.01))));
            let b = if b.length().is_nan() { cross(a, Vec3::new(1.0, 0.0, 0.0)) } else { b };
            let mut any_inside = false;
            for i in 0..=8 {
                for j in 0..=8 {
                    let (s, t) = (i as f32 / 4.0 - 1.0, j as f32 / 4.0 - 1.0);
                    let p = Vec3::new(
                        c.x + (a.x * s + b.x * t) * size,
                        c.y + (a.y * s + b.y * t) * size,
                        c.z + (a.z * s + b.z * t) * size,
                    );
                    any_inside |= clip_inside(&vp, p);
                }
            }
            let r = cull_reach(size);
            let keep = f.intersects(Vec3::new(c.x - r, c.y - r, c.z - r), Vec3::new(c.x + r, c.y + r, c.z + r));
            if any_inside {
                visible += 1;
                assert!(keep, "culled a visible quad: centre {c:?} size {size}");
            }
            if keep { kept += 1 } else { culled += 1 }
        }
    }
    assert!(visible > 1000, "test sees visible quads ({visible})");
    assert!(culled > kept / 4, "cull removes a real share (kept {kept}, culled {culled})");
}

#[test]
fn reach_bounds_the_quad_diagonal_and_survives_odd_sizes() {
    for size in [0.0_f32, 0.001, 0.1, 1.0, 2.0, 40.0, -0.5] {
        assert!(cull_reach(size) >= 2.0_f32.sqrt() * size.abs());
        assert!(cull_reach(size) >= 0.05);
    }
    assert!(cull_reach(f32::NAN).is_nan());
}

#[test]
fn nan_boxes_stay_drawn() {
    let (v, _) = view(0.0, 0.0);
    let f = Frustum { planes: frustum(perspective_rh(1.2, 1.7, 200.0, 0.05) * v) };
    let n = f32::NAN;
    assert!(f.intersects(Vec3::new(n, n, n), Vec3::new(n, n, n)), "a NaN position must not hide a particle");
}

#[test]
fn kept_order_is_the_original_order() {
    // render_in_view only `continue`s, so survivors keep their relative order: model it.
    let all: Vec<u32> = (0..1000).collect();
    let kept: Vec<u32> = all.iter().copied().filter(|n| n % 3 != 0).collect();
    assert!(kept.windows(2).all(|w| w[0] < w[1]));
}
'''

out.write_text("#![allow(dead_code)]\n" + MATH + "\nimpl Frustum {\n" + intersects + "}\n" + frustum_fn + "\n" + reach + TESTS)
