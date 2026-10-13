# Optional AVX2 CPU backend upgrade

These source-only tools create a complete, separate copy of the supported offline
Ovis distribution and replace its generic CPU backend. They do not download
models, enable a GPU, modify the original directory, or update Readest itself.

The updater pins the exact original distribution manifest and optimized backend
SHA-256 in `upgrade.py`. It is deliberately not a general-purpose updater.
Distributors must authenticate those artifacts and review any changes to the
pinned hashes. A checksum is not a signature.

## Build the backend

Use the unmodified llama.cpp source at commit
`5266f24da75dc449bd56cbed7addb9c8e4a6a73e` from
<https://github.com/ggml-org/llama.cpp/tree/5266f24da75dc449bd56cbed7addb9c8e4a6a73e>.
Start with the original distribution's build configuration in a new build
directory, preserving its compiler, ABI, shared-library and offline options.
Keep `GGML_NATIVE=OFF`, `GGML_BACKEND_DL=OFF`, and GPU backends disabled. Set:

```text
GGML_SSE42=ON
GGML_AVX=ON
GGML_AVX2=ON
GGML_FMA=ON
GGML_F16C=ON
GGML_BMI2=ON
```

Keep AVX-512, AVX-VNNI, AMX and `GGML_CPU_ALL_VARIANTS` disabled. Do not use
`-march=native` on a different build machine. Use Release with shared libraries,
`CMAKE_INSTALL_RPATH=$ORIGIN`, `CMAKE_BUILD_WITH_INSTALL_RPATH=ON` and
`CMAKE_BUILD_RPATH_USE_ORIGIN=ON`. Build only the required target:

```sh
cmake --build build-avx2 --target ggml-cpu -j1
```

The prepared payload is the actual regular file behind `libggml-cpu.so.0`, not
its build-tree symlink. Preserve the original generic runtime unchanged.
Compiler versions, source changes and build settings can change the output
checksum: a fresh build is not automatically accepted by the pinned updater.

## Validate and prepare a distribution

Before distributing, compare exported symbols, SONAME, required symbol versions,
dynamic dependencies and runtime search paths against the original backend.
Test the existing CLI with the new backend and original companion libraries;
verify through the loader trace that it actually uses the new file. Check CPU
feature reporting and small f32, f16 and Q3_K/Q8_K kernels. These checks do not
replace end-to-end model quality and timing validation.

Ship the updater beside `libggml-cpu.so.0`, an accurate
`BACKEND-VALIDATION.json`, all required licenses/notices and corresponding-source
references. The upstream native backend retains its upstream licensing; these
original Python tools are AGPL-3.0-or-later. Preserve the original distribution's
component-specific obligations. No binary libraries, weights, private documents,
results, personal measurements or credentials belong in this source directory.

## Apply a prepared upgrade

Requires Linux x86-64, Python 3.11 or newer and CPU flags SSE4.2, AVX, AVX2, FMA,
F16C and BMI2 on every reported processor. From the prepared upgrade directory:

```sh
python3 upgrade.py /absolute/path/original-package /absolute/path/new-avx2-copy
cd /absolute/path/new-avx2-copy
./run.sh --check
```

The destination must not exist, its parent must exist, and it must be outside
the original package. Budget the complete original package size plus the new
backend and 32 MiB of free space. Files are copied, including model files; model
inodes are not shared. All original manifest entries are validated first.
Unlisted runtime files, symlinks, changed source files and wrong backend bytes
are rejected. An incomplete destination is retained on failure for inspection;
do not run it or retry into the same directory.

The new `run.sh` checks CPU flags before invoking the original launcher. Bypassing
that entry and directly invoking native libraries bypasses the CPU guard. A new
manifest binds the copied runtime, backend, guard and upgrade receipt. Inherited
build records describe the original package; `UPGRADE.json` and
`BACKEND-VALIDATION.json` describe this backend replacement. The original package
remains the fallback.

## Tests and performance limits

```sh
python3 -B test_upgrade.py
```

The synthetic tests require no model or network. They cover copy preservation,
manifest integrity, changed payload/source, existing or nested destinations,
extra runtime files, symlinks and path traversal. They are focused Python tests,
not the application's complete CI suite.

Do not infer document speed from microkernel measurements. Measure a fixed page
with the same model, prompt, visual budget, thread count and power conditions on
the target machine; compare output completeness and important text/table/formula
accuracy as well as wall time. The upgrade does not claim a measured speedup on
any particular user machine.

SPDX-License-Identifier: AGPL-3.0-or-later
