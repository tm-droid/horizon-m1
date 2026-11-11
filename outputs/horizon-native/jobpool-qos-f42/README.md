# jobpool-qos-f42

Verdict: **ready**. Status: UNBUILT / UNTESTED at authoring (anchors, render chain and `git apply --check` only).

- Origin: m1-code-audit-2026-11-05 candidate #2 (not in upstream).
- What: new `horizon_threads::pool_helper_current()`. The general job-pool workers (`horizon-threads/src/jobs.rs`, meshing/lighting/etc.) and the LAN `horizon-chunk-encode-*` threads (`lan/chunks.rs`, which never called `behind_server`) call it as they start. Like `behind_server` it only acts after `put_helpers_behind()`. macOS: `pthread_set_qos_class_self_np(QOS_CLASS_USER_INITIATED, -15)`. Linux/Android: `behind()` as before. Windows: no-op as before.
- QoS choice: USER_INITIATED at relative priority -15, not UTILITY. Render/main/server threads are USER_INTERACTIVE and stay untouched, so helpers sit below them but remain eligible for P-cores; UTILITY would steer meshers to the 4 E-cores and risks slower chunk loading (qos-backport already puts the Far terrain threads at UTILITY). If r2 shows no 1% low gain, the follow-up is to try UTILITY here; if settle time regresses >10%, drop this mod.
- Render/main thread: not touched. Other `behind_server()` callers (world loading, chat, lod_net, lan conn): not touched.
- Visual change: none. Risk: scheduling only (chunk fill-in latency). Whether the inherited-QoS theory holds is unverified.
- Files: crates/horizon-threads/src/lib.rs (shared with qos-backport, disjoint anchor; run after it), crates/horizon-threads/src/jobs.rs, crates/horizon-client/src/lan/chunks.rs

## Use
Same API as qos-backport-f42: `mod.render(relative, bytes)`, `FILES`, `NEW_FILES`; CLI `prepare.py --workspace DIR --record NEW.json`. `jobpool-qos.patch` is the unified diff against the launcher stage tree (`git apply -p1`).
