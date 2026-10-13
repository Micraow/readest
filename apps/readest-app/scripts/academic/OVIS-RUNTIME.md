# Local Ovis resource inspection

The app currently imports pre-generated Ovis bundles. It does not register a
native inference command. Reading mode explicitly reports that local inference
is unavailable in this build; existing PDF text and result import remain usable.

`verify-ovis-runtime.py --root /absolute/package/path` is an **inspection-only
developer tool**. It reads fixed resources; it never imports their Python code,
loads shared libraries, invokes a process, downloads files, or grants access.
The exit code is 2 because this stage cannot establish launch readiness, even
when `integrity` is `verified`. Read `blockers` and each artifact's `status`.
There is no option to replace the expected hashes or override the platform.

## Fixed candidate

The code-owned table pins fourteen files by relative path, byte length, and
SHA-256: four current producer scripts under `scripts/`, the CLI and six versioned
shared libraries under `bin/`, Q3_K_M model and Q8_0 projector under `models/`,
and `prompt.txt`. Hashes identify the reviewed development bytes. They are not a
reproducible-build attestation or permission to redistribute third-party assets.
No weights, executables, library binaries, or prompts are shipped by this patch.

Declared source identities are llama.cpp v0.4.0 at
`5266f24da75dc449bd56cbed7addb9c8e4a6a73e`, and
`MDfox/OvisOCR2-GGUF-SOTA-20260823` at
`dbd462d4e3fbbb85da78443e7e34e87d688dd8a0`. The runner is
`ovis-pdf-runner-1`; its exact current hash is independently pinned rather than
relying on that version string alone. Future producer edits must deliberately
review and update the corresponding pin.

The candidate profile is `ovis-linux-x86_64-cpu-v1`: sequential pages, 2 threads,
144 DPI, context 8192, output limit 4096, image-token limit 2048, CPU only,
flash attention off, 900 seconds per page, 3600 seconds per document,
12288 MiB sampled process-group RSS guard, and 2 seconds termination grace.
These match the runner defaults; its remaining fixed settings include seed 0,
temperature 0, batch 512 and micro-batch 128. Sampled limits are not hard kernel
resource limits, and complete page coverage does not prove correct/complete OCR.

## Failure behavior

- Anything other than Linux x86_64 is rejected before opening the package.
- Missing roots/files, wrong sizes or hashes, absent executable bits, links,
  directories and other non-regular leaves have distinct stable reason codes.
- All root/path components are opened without following links. A held Linux
  `O_PATH` descriptor identifies the regular leaf before opening it for reading;
  FIFO/device leaves are never opened for data I/O. Hashing is streamed and
  bounded by the pinned size. Detected in-place changes fail verification.
- Reports contain logical relative paths, not local absolute paths or file data.
- Verification is a snapshot, not authorization for later execution. It does
  not prevent later replacement, hard-link mutation or establish full isolation.

## Remaining installation gates

Even all fourteen matching resources leave these concrete blockers:

1. A controlled Python interpreter and PyMuPDF dependency closure have not been
   packaged/pinned. The development environment used Python 3.12.14 and PyMuPDF
   1.26.6, but inheriting an arbitrary host interpreter is not the package contract.
2. The development CLI has an absolute build-directory RUNPATH. Its build also
   used `GGML_NATIVE=ON`. A portable loader/library closure and CPU baseline must
   be rebuilt, pinned and tested in a clean destination. Merely copying the seven
   ELF files is insufficient; their SONAME aliases and system ABI also matter.
3. The app's fixed native job entry, real per-run confirmation, caller/PDF/profile
   binding, cancellation and cleanup have not been integrated and tested together.
   Existing confirmation-backend and supervision proofs do not establish that.

These blockers are unconditional in this tool. A future implementation must
replace them only with evidence from the corresponding product path. There is
no enabled button, new IPC command, capability grant or native resource mapping.

## Native app build route

Use the existing Linux CEF route, not a substitute Wry build:
`apps/readest-app/scripts/tauri.mjs` applies `src-tauri/.cargo/cef.toml`, swaps
`Cargo.cef.lock` for the duration, and disables default features in favor of CEF.
`.github/workflows/academic-linux.yml` documents prerequisites and invokes
`scripts/academic-linux-ci.py prepare-cef`, which verifies the fixed CEF archive
before extraction. Do not change the two lockfiles or pin an arbitrary current
CEF release to get a local build through.

The workflow's build command, from `apps/readest-app`, is:

```sh
pnpm tauri build --debug --no-bundle \
  --config '{"build":{"beforeBuildCommand":""}}' -- --locked
```

It requires the production frontend already built, the pinned CEF SDK, the
resolved locked Rust graph and native development libraries. A passing Python
resource inspection or browser UI test is not a full Tauri compilation or native
dialog integration test.

Synthetic tests: `python3 -m unittest discover -s scripts/academic -p
'test_verify_ovis_runtime.py'` from the app directory.
