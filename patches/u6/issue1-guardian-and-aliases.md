# Issue 1 (client part): guardian and elder_guardian spine targets

Warning: `unknown target spine_N.tx/ty/tz` on guardian and elder_guardian.

Root cause: FA's guardian jem binds its bones to the part name `body`, but the native model exports the guardian head as the parent of the spines and the body is not a separate node. `vanilla_part` in `crates/horizon-client/src/mobs/cem.rs` (line 409 in fdc87ae) has no guardian entry, so the entry is dropped (`CemLayer::build`, "no part") and every animation target under it has no bone.

Fix: `cem-binding.patch` (in this directory, copied from `outputs/horizon-native/cem-binding-f42/`). It adds `("guardian" | "elder_guardian", "body") => Some("head".into())` plus the wolf mane, happy-ghast harness, puffer, tropical fin and salmon fin/tail aliases. `git apply --check -p1` passes on `nightly-2026-11-08-fdc87ae` (checked 2026-11-10, not built).

Salmon and cow are handled pack-side by `Horizon-Tanush-Compat-2026-11-10.zip`, so this patch is only needed for guardian/elder_guardian.
