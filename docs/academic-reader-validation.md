# Academic reader validation

Implementation scope: Phases 0–3, based on upstream
`4c3ccfe85d4afd81e674b67d6a0627d83ba0744d`. No OCR, remote parser, AI, translation,
Zotero writes or cloud upload were added.

The published final source checkpoint is
[`288f421885745ad9e9d08879d0febf183ad92add`](https://github.com/Micraow/readest/commit/288f421885745ad9e9d08879d0febf183ad92add),
Git tree `a67bb2aa207516af494f43c5a9ce0a38430ef4db`.
Checks below distinguish code/build evidence from real-account/device acceptance.

## Final source and frontend gates

- `pnpm lint`: passed, including TypeScript and Biome
- Offline-compatible unit suite: **13,016 passed, 16 skipped**; **1,114 test files
  passed, 4 skipped**
- One existing file was explicitly excluded:
  `src/__tests__/services/novel/novel-import.test.ts`. Its synthetic image fixtures
  make an unmocked external network request. No unrelated test modification was
  included; this result must not be represented as an unqualified full-suite pass
- Web production build: passed, including TypeScript and all 54 static pages
- Tauri frontend export: passed, including TypeScript; verified all 25 HTML files,
  especially index, Library and Zotero entry points, plus the complete 44 MiB output
- Source remained unchanged through the final gates
- Publication scan: text-only source/tests/docs; no PDFs, screenshots, original
  paper text, private keys, real API keys, private library metadata or workflow edits

Reproducible commands from the repository root:

```sh
pnpm lint
pnpm --filter @readest/readest-app test --run --maxWorkers=2 \
  --exclude src/__tests__/services/novel/novel-import.test.ts
export READEST_BUILD_SOURCEMAPS=0 RAYON_NUM_THREADS=1 CIRCLE_NODE_TOTAL=2
export NODE_OPTIONS=--max-old-space-size=4096
pnpm --filter @readest/readest-app build-web
pnpm --filter @readest/readest-app build
```

Both constrained production builds used `READEST_BUILD_SOURCEMAPS=0`. Default
builds retain upstream sourcemaps. Build-time Turbopack filesystem caching is explicitly disabled,
as the upstream configuration comment intended: interrupted caches caused repeated
memory exhaustion when the newer Next.js default enabled it. A split compile/generate
attempt produced incomplete output and was rejected; the verified output comes from
the ordinary full build.

The CEF lockfile also needed one baseline metadata correction: the Readest package's
already-present `windows 0.61.3` dependency is included in its dependency list. No
crate version was changed.

## Native platform evidence

Provisioned toolchains: Rust/cargo 1.99, Node 24, JDK 21, Android SDK 36, build-tools
36.0.0, NDK 28.2.13676358, Gradle 8.14.3, and Linux Clang/GTK/WebKit/libsoup/Ayatana/
PipeWire/librsvg with the pinned CEF runtime.

- Linux default CEF debug build: passed against the Phase 1 export
- Linux Phase 1 runtime smoke: passed on the cloud desktop. Verified launch,
  Library, both Zotero navigation paths, Settings connection form, session-only
  disclosure, overlay dismissal and Back navigation. No credentials were entered
- Android x86_64 debug APK: built and signature/ABI/manifest verified against the
  Phase 1 export. Package `com.bilingify.readest`, version 0.12.12, min SDK 26,
  target/compile SDK 36, APK v2 signature. This is a build checkpoint, not the
  phone-ready or final-feature artifact
- Phase 3 arm64 Android debug APK (before the heading correction): built and verified. APK v2 signature,
  arm64-v8a only, min SDK 26/target SDK 36, and 16 KiB ELF segment alignment verified.
  The entire final frontend hash manifest remained unchanged through packaging
- Phase 3 Linux CEF build and runtime smoke passed before the heading correction.
  Native HPCC opening through the supported Open With workflow defaults to Original
  PDF. Manual Reading, continuous text, Figure 3 fullscreen zoom/pan, Escape closing
  only the viewer with scroll preserved, intact Algorithm 1 with all 27 numbered
  lines, the complete eight-panel Figure 9 with its shared caption and fullscreen
  zoom, PDF/Reading switching, saved-position/cache reuse, Library return and normal
  native file-picker import were observed
- Corrected final Linux CEF rebuild: passed in 5m28s against the verified
  `academic-2` export. Native repeat verified both formerly false headings as
  continuous body paragraphs and genuine headings unchanged. The old cache was
  retained but not reused; a new versioned cache was generated without PDF reimport.
  Fullscreen zoom/pan, Escape, PDF switching and reopening preserved position; both
  cache files remained byte/hash/mtime-identical on the completed cached reopen
- Corrected final arm64 optimized APK: built and verified against the same export.
  Its development certificate, package/version/API levels, ABI, native payload and
  alignment checks passed; exact artifact details follow
- Android runtime/device smoke: not executed; a successful APK build is not device
  acceptance

The supported cloud browser is available, but navigation to the running localhost
web preview is blocked (`ERR_BLOCKED_BY_CLIENT`). No alternate address or tunnel
bypass was attempted. Linux native smoke uses the existing cloud desktop instead.

The initial Phase 3 arm64 debug artifact is
`Readest-academic-reader-arm64-debug.apk` (190,805,317 bytes), SHA-256
`b75529e3efe14de37781833a065cf319e8e78544b83efe30138386c10e862c18`.
It exceeded the private chat attachment limit and is not the delivery artifact.
The final corrected standalone artifact is
`Readest-academic-reader-arm64-optimized-dev.apk` (36,484,832 bytes / 34.8 MiB),
SHA-256 `d15e462480c9404488001da7c0ffc10eaa10074e084d4a0fbdac7e5c04bce2ec`.
It embeds the final `academic-2` source/export and uses the same development
certificate. Native artifacts are not committed to the source repository.

The compact APK uses the normal release profile (optimization 3, one codegen unit,
no debug symbols, symbol stripping), R8 and Gradle native-library compression
(`jniLibs.useLegacyPackaging=true`, consistent `extractNativeLibs=true`). No
application features or source assets were removed. A task-local build override
reuses the outer Tauri command's fresh Rust result instead of repeating it inside
Gradle: the repeated compiler had been killed under combined JVM/compiler memory
pressure. The reuse guard verifies the exact frontend manifest, fresh arm64 ELF,
JNI symbol/symlink and generated Kotlin glue. Normal resource, R8, strip, package,
alignment and signing steps remain enabled. All allocated ELF sections and LOAD
mappings match the pre-strip binary, and the signed APK's native payload matches
Gradle staging exactly. ZIP and all native-library 16 KiB alignment checks pass.
This packaging evidence does not replace Android runtime acceptance.

The existing GitHub workflows trigger on main; this feature branch has no Actions
runs, check runs or commit-status contexts. Local checks above are the verification
evidence; no GitHub CI pass is claimed.

Both APK variants use a development signing key. An existing official Readest installation
may reject an update signed with that key. Back up your library before making any
manual installation decision; this task does not uninstall or replace an existing
installation.

## Real PDF.js corpus evidence

The [manifest](./academic-pdf-corpus.json) lists 10 public author/publisher PDFs,
139 pages in total. All were downloaded outside the repository, checked for PDF
signature and full SHA-256, and parsed with the installed PDF.js 6.2.108.

- Live extraction and analysis: 139/139 pages processed
- All 39,787 PDF.js text items accounted for exactly once as reflowed, visual or
  deliberately suppressed source items
- 275 visual regions: 142 carry an explicit preservation/fallback reason and 10
  have unknown role; no whole-page unsupported-layout fallback in this corpus.
  These counts are unchanged by the final heading correction
- HPCC author-copy SHA-256:
  `8199b81f7325b8797623b6c44fad90eb2664b4bc6a8e0f9bdbad7e043b02fe8a`
- HPCC page 6: Algorithm 1 preserved as one complete region, including all 27 numbered
  rows and its caption/bounding rules
- HPCC page 10: all eight vector panels of Figure 9, their labels and the shared
  caption grouped into one wide visual region before the two-column prose
- Real region rendering compared against original 2× HPCC renders; only negligible
  edge/rounding differences were measured
- Engine/runtime/cache/geometry tests: 48 passed at the Phase 2 checkpoint; all
  79 academic service/UI tests pass after the final native-smoke correction
- 120-page yielding analysis probe: 703 ms, 240 yields, maximum timer gap 12.5 ms on
  the cloud Node host. These figures are not Android performance measurements

Geometry/source coverage proves neither perfect semantic order nor publication-
quality text recovery. Heading, paragraph, caption, footnote and equation detection
remain geometric heuristics. In particular, the large-font heading heuristic can
be affected by a page dominated by smaller references or notes. Ambiguous regions
retain original visuals. Exhaustive human reading-quality review of all 139 pages has not been claimed.

The local corpus harness performs no network transfers:

```sh
cd apps/readest-app
node --experimental-strip-types scripts/academic-regression.mjs /path/to/pdfs \
  --output /path/to/report.json
```

The committed HPCC fixture contains measured geometry with synthetic text labels,
not the PDF, original text or vector drawing paths.

## Review regressions covered

- Account-switch cache failure cannot display the previous account with the new provider
- Cancelled credential persistence rolls back previous account/key state
- Native HTTP explicitly suppresses ambient cookies on each manually followed hop;
  API authorization is never forwarded to storage redirects
- The service worker bypasses its caches for authenticated/no-store/Zotero requests
- Browser Back closes zoom, Reading and provider Original PDF in order; reopening,
  Forward into stale entries and native/Escape dismissal are covered
- Source changes cannot retain a previous paper's zoomed image
- Inspector opening cancels pending zoom; initial lazy loading is cancellable
- Numbered lists retain their starting number
- Body-sized numeric prose requires corroborating font evidence before becoming a
  heading. Distinctly styled run-in subsection labels keep their source order.
  Parser version `academic-2` invalidates previous saved classifications; the live
  corpus removes six false headings while preserving all seven DRILL run-in labels
- Near-viewport rendering, canvas/URL cleanup, parser cancellation, retries, repeated
  toggles and local scroll restoration have deterministic React tests

## Remaining acceptance

Real Zotero Personal Library/Storage authentication and the user's own HPCC
attachment have not been exercised. No real key or private metadata was supplied.
Mocked downloads/offline reopening do not substitute for that check.

On Android first, then Linux, confirm the user's collection hierarchy, lazy HPCC
Storage download, offline reopening, Original PDF, manual Reading, figure/algorithm
zoom, return to the shelf, cache reuse and local-only removal. Confirm no ordinary
Book duplication, no Readest Cloud upload and no Zotero writes. Physical touch and
memory behavior still need target-device evidence.
