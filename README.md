# Lean Radeon nightlies

Public binary releases of the experimental Lean AMD Radeon (RDNA) backend.
The compiler is built separately; this repository holds distribution tooling,
release metadata, and installation instructions. Compiler sources and history
are not published here.

**No binary release has been published yet.** An empty release index means that
no candidate has completed the release gates. Preparing this repository does not
start a nightly build schedule.

The initial platform is **Linux x86_64**. Kernel compilation requires a ROCm
LLVM toolchain; GPU execution additionally requires a supported AMD GPU and HIP
runtime. Each release records its tested GPU target, ROCm version, and host OS.
Support for a target is not a claim that every Radeon GPU has been tested.

For workloads that launch cooperative kernels on gfx1151, see the
[stock-driver workaround and tested configuration](docs/gfx1151-cooperative-launch.md).

## Installation

Choose an exact tag from [Releases](https://github.com/ranvier-labs/lean4-radeon-nightly/releases).
Once a release exists, put its identifier in your project's `lean-toolchain`:

```text
ranvier-labs/lean4-radeon-nightly:nightly-YYYY-MM-DD
```

Or install it explicitly:

```sh
elan toolchain install ranvier-labs/lean4-radeon-nightly:nightly-YYYY-MM-DD
```

The dates above are placeholders, not available releases. For a manual install,
download the `.tar.zst` archive and its `.sha256` sidecar from the same release,
verify with `sha256sum -c`, then extract it and use `elan toolchain link`.
Elan installation does not itself verify our checksum sidecar.

## Release policy

* Standard Lean `lean-<version>-linux.tar.zst` archives support elan installation.
* Every release includes SHA-256 checksums, an archive file manifest, and a JSON record.
* Tags use `nightly-YYYY-MM-DD`; same-day corrections use `-rev1`, `-rev2`, etc.
* Published tags, records, and binary assets are never replaced.
* A clean build, relevant tests, an extracted-package smoke test, and GPU execution
  must all pass before publication. Skips do not count as passes.
* Only small metadata and tooling are committed. Binaries live in GitHub Releases.

See [publishing](docs/PUBLISHING.md) for the build handoff and
[the release contract](docs/RELEASE_CONTRACT.md) for machine-readable metadata.

## Development

Python 3.11 or newer and Make are sufficient for repository checks. Archive audit
also requires `zstd`; publication requires an authenticated GitHub CLI and Git.

```sh
make check
make build
```

`make build` generates `_build/index.json` from validated release records.
Validation CI runs on pushes and pull requests. The compiler build and its
credentials belong in the separate source repository.

Apache 2.0. Binary distributions must retain their own licenses and notices.
