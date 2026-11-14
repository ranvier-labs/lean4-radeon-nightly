# Release contract v1

`releases/<release_id>.json` is the canonical immutable record. The semantic
validator is `scripts/release.py validate releases`. `_build/index.json` is a
local generated discovery index, not a published service.

A record contains:

| Field | Meaning |
| --- | --- |
| `schema_version` | Integer `1` |
| `release_id` | UTC `nightly-YYYY-MM-DD`, optionally suffixed `-revN` |
| `source_commit` | Full 40-character source commit SHA |
| `version` | Lean version containing `radeon-nightly` |
| `platform` | `linux/x86_64` |
| `gpu_target` | Tested AMD architecture, for example `gfx1151` |
| `rocm_version` | ROCm toolchain version actually used |
| `host_os` | Distribution and version used for the build and package smoke |
| `validation` | `build`, `tests`, `installed_smoke`, `gpu_execution`, all `passed` |
| `archive` | Asset `name`, immutable `url`, byte `size`, and lowercase `sha256` |

The archive name is `lean-<version>-linux.tar.zst`. Its URL belongs to the matching
tag in `ranvier-labs/lean4-radeon-nightly`. The corresponding `.sha256` and
`.manifest.json` sidecars are attached to the same release. The JSON record is
both attached and committed after publication.

The archive contains one `lean-*` root with `bin`, `lib`, `include`, `share`, and
license files. Required files include Lean, Lake, leanc, compiled `Lean.Rdna`,
the shared runtime, public runtime headers, and license notices. The validator
rejects compiler sources, build logs, hidden paths, unsafe paths, duplicate
entries, links, and special files. Package with dereferenced links only after
checking their targets. Header files are part of the supported FFI interface.
The automated policy is a gate, not a substitute for reviewing public contents.

Validation values are publisher attestations: the metadata tool cannot prove
that a test was run. Keep full logs in the source repository and set each value
only after its corresponding command succeeds. Do not publish private logs.
