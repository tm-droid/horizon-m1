# Horizon migration assistant

This tool prepares a partial conversion of a Minecraft Java/Fabric instance for
Horizon. It creates actual resource-only candidate packs from mod assets, preserves
selected resource packs and their order, and produces evidence and tasks for the
remaining manual Rust ports. It does not execute Java, install Horizon, change the
source instance, or claim that generated files have been visually verified.

Horizon is pinned to `e6e12d40c522b8f5ee8740dd861c96689023737a`, native hooks API
153, resource format 97.1. These contracts can change. Source findings and exact
links are in [the API investigation](../horizon-converter-api.md).

## Run

Python 3.10+ and its standard library are sufficient. From the launcher directory:

```sh
python3 tools/horizon-convert.py \
  --game-dir instances/Tanush-26.3/minecraft \
  --output outputs/horizon-converter/my-new-migration \
  --stage-packs --stage-mod-assets
```

Use a **fresh** output directory. Omit the two staging flags for reports only.
Close the Java game while taking a snapshot. Substantial device work should also
use this project's shared testing queue, as used for the recorded validation.
No saves, accounts or server worlds are copied. This tool does not select a live
Horizon home or enable any candidate pack.

## What it automates

- Reads the exact `options.txt` pack selection, including its order and built-in
  layers. Copies selected ZIPs byte for byte and directory packs file for file.
  Missing or unsafe layers stay visible as blockers rather than disappearing.
- Preserves the selected Iris shader and its override sidecar as source evidence.
  Shader conversion and Metal visual parity remain unverified.
- Creates a resource-only ZIP from each Java mod's `assets/`, with target-format
  metadata, source licenses and hashes/provenance. It excludes Java classes,
  nested jars and `data/` behavior. Each result requires explicit activation and
  ordering review; assets can reference registrations that have not been ported.
- Inspects Fabric entrypoints/dependencies, mixin declarations, Java class
  constant-pool references and Mixin annotations. Recognized input, HUD and tick
  patterns suggest verified Horizon source hooks for a manual implementation.
  A reference is evidence, not proof that a method executes or has an equivalent.
- Inspects declared nested jars in memory, with a shared read budget, depth limit,
  SHA256 deduplication and complete archive-chain evidence. Literal control
  characters accepted in Fabric descriptions use a recorded parsing fallback;
  malformed syntax remains a visible gap.
- Flags extension formats, interpolation, fonts, shader sources, unsafe archives,
  malformed metadata and analysis limits. CEM/CIT/CTM and related features are
  **not** automatically treated as unsupported: Horizon documents support, and
  their exact rendering still needs testing.

## Outputs and next work

`manifest.json` records source fingerprints, pack order and preparation status.
`mod-asset-packs/` contains the converted asset candidates. `mods/` holds detailed
evidence; `porting-index.json` and `dependency-graph.json` help prioritize work.
`tasks/` and `AGENT_WORKFLOW.md` provide a concrete queue that a person or agent
can work through. Manifest schema 2 identifies `review-queue.jsonl` as grouped
tasks and `raw-review-queue.jsonl` as the complete evidence stream. Every raw line
is referenced by a grouped task. Repeated references stay available without
becoming separate implementation tasks. The tool does not send messages or mark
ports complete autonomously.

`appearance-contract.json` prioritizes the actual pack layers, Fresh Animations,
EMF/ETF, connected textures, fonts, sounds and Mellow. Selected source settings
are copied as evidence; their semantics are not automatically translated.
Java-specific optimizers stay installed in Java and receive a separate review
classification. This never establishes that their visible features can be omitted.

The generated `upstream-plan.json` integrates with Horizon's existing
`horizon-port-pack` tool: import, offline inventory, carry and report, plus per-jar
checks. The commands are argv arrays and are **not executed**. Horizon's carry
can translate more content, but inferred item/block templates need review.
`port --offline` still fetches in the pinned implementation, so it is excluded.
No standalone port-pack binary was found in the checked official releases, and
this Mac had no Rust toolchain; that upstream conversion was not built or run.

Exit 0 means a migration preparation was generated, still requiring review.
Exit 2 means blocked/incomplete preparation or invalid inputs. Neither means
Java behavior or visual parity was verified. A source hash mismatch invalidates
the snapshot. Nested jars and class-analysis limits are explicitly recorded and
must be resolved before declaring a full port.

## Validation

```sh
python3 -m unittest discover -s tests -p 'test_horizon*.py' -v
```

Fixtures cover real class-file evidence, metadata and dependencies, pack ordering,
asset hashes, deterministic ZIP output, licenses/omissions, corrupt inputs, path
traversal, duplicate entries, symlinks, FIFOs, bounded reads, source mutation and
refusal to overwrite existing output. No game benchmark is needed for these
checks; actual Horizon behavior and appearance require a separate runtime test.
