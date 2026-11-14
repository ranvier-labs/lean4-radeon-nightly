# Publishing

Build in the separate compiler repository. The public repository does not hold
source credentials or execute untrusted compiler builds on a GPU runner.

## Build and test gates

Use a clean, committed source revision and a Linux x86_64 release environment
with ROCm and access to `/dev/kfd` and the AMD render node. Record the actual host
OS, ROCm version, and target architecture. Never label a skipped test as passed.

Configure a unique version, then use the source repository's documented commands:

```sh
cmake --preset release \
  -DCHECK_OLEAN_VERSION=ON \
  -DLEAN_SPECIAL_VERSION_DESC=radeon-nightly.YYYYMMDD.gSHORTSHA
CCACHE_READONLY=1 CCACHE_TEMPDIR=/tmp make -j"$(nproc)" -C build/release
CTEST_PARALLEL_LEVEL="$(nproc)" CTEST_OUTPUT_ON_FAILURE=1 \
  make -C build/release -j"$(nproc)" test
```

Replace the date and commit placeholders before configuring. Run the relevant
RDNA and HIP test directories on real hardware, including `native_rdna`,
`native_hip_host`, and `native_rdna_ad_runtime`; inspect the output for skips.
The full suite is the intended nightly gate. Set `validation.tests` only when
all required tests pass.

Use Lean's stage1 install target to install into a fresh staging prefix. Keep
that staging tree private: the source repository currently installs Lean source
files under `src/lean`. Build the public archive from only `bin`, `lib`, `include`,
`share`, `LICENSE`, and `LICENSES`, then run the archive audit. Do not archive the
whole staging tree or the compiler checkout. Do not put private logs in the
staging tree. Dereference necessary runtime library links only after confirming
they point to distribution files.

Use a single `lean-<version>-linux` archive root and name the result
`lean-<version>-linux.tar.zst`. Compress with zstd. Run:

```sh
python3 scripts/release.py audit /path/to/lean-VERSION-linux.tar.zst > /tmp/radeon-manifest.json
```

Extract into a fresh location outside the compiler checkout. With `LEAN_PATH`
and `LEAN_SYSROOT` unset, verify `bin/lean --version`, `bin/lake --version`, and a
fresh Lake project importing `Lean.Rdna`. Emit AMDGPU IR for the recorded target,
compile it with the matching ROCm LLVM toolchain, then execute a kernel using
the installed HIP runtime bindings and verify its result. This is the
`installed_smoke` gate; source-tree tests alone do not establish relocatability.
The package must work without the source checkout on its module or library path.

## Evidence and publication

Create a private evidence JSON file using measured values, not placeholders:

```json
{
  "release_id": "nightly-YYYY-MM-DD",
  "source_commit": "FULL_40_CHARACTER_COMMIT_SHA",
  "version": "VERSION_WITH_radeon-nightly_DESCRIPTION",
  "platform": "linux/x86_64",
  "gpu_target": "TESTED_GFX_TARGET",
  "rocm_version": "ACTUAL_ROCM_VERSION",
  "host_os": "ACTUAL_HOST_OS_AND_VERSION",
  "validation": {
    "build": "passed",
    "tests": "passed",
    "installed_smoke": "passed",
    "gpu_execution": "passed"
  }
}
```

Run publication from a clean `main` checkout of this public repository with an
authenticated `gh` and Git credentials authorized to write this repository:

```sh
bash scripts/publish.sh /path/to/lean-VERSION-linux.tar.zst /path/to/evidence.json
```

The script audits the actual archive, computes checksums and a file manifest,
creates a draft prerelease, downloads every uploaded asset and compares it to
the original, then publishes the release. It commits metadata only after the
assets are public. It never uses upload `--clobber` or force-push.

If verification fails, the draft stays unpublished. Diagnose it before retrying.
If the final metadata push fails after publication, retain the generated local
commit, reconcile it with `origin/main`, and push it; do not recreate the release
or overwrite assets. Temporary evidence and downloads are retained under the
printed system temporary directory for diagnosis.

## Nightly automation

The repository includes public validation CI. A scheduled compiler build is not
yet configured. To enable it, install a narrowly scoped publishing GitHub App on
this repository with Contents write access and keep its credentials only in the
source repository. Schedule the canonical build and GPU tests on the private
AMD runner; invoke `publish.sh` only after every gate passes. Never expose a
self-hosted GPU runner or publishing secrets to public pull requests.
