# Academic reader validation

Implementation scope: Phases 0–3, based on upstream
`4c3ccfe85d4afd81e674b67d6a0627d83ba0744d`. No OCR, remote parser, AI, translation,
Zotero writes or cloud upload were added.

Before the quality correction, the implementation source checkpoint was
[`288f421885745ad9e9d08879d0febf183ad92add`](https://github.com/Micraow/readest/commit/288f421885745ad9e9d08879d0febf183ad92add),
Git tree `a67bb2aa207516af494f43c5a9ce0a38430ef4db`.
Checks below distinguish code/build evidence from real-account/device acceptance.

## Confirmed monospaced text: academic-12 (in validation)

Same-document comparison identified typewriter-style parameter names that were
still rendered in the body font. Confirmed CM-Super fixed-width text faces now
carry an explicit flag through extraction, cached analysis and selectable inline
text. Only those runs receive a monospace family; proportional body text retains
the user's reading font. Variable-width typewriter shapes and PDF.js's inferred
monospace fallback for single-glyph mathematical subsets are deliberately excluded.

Synthetic regressions, cache round-trip and four-file (61-page) source comparison
pass. The supplied single-column document changes only in confirmed font metadata
and inline family; both HPCC variants and MP-RDMA remain structurally and textually
unchanged. Parser `academic-12` requires fresh analysis while keeping older caches.
Final native comparison and the aggregate suite are pending for this checkpoint.
The academic-11 package and acceptance below remain immutable.

## Structured inline content and source-order figures: academic-11 (2026-10-07)

Same-file native comparison exposed issues remaining in academic-8: inline math
became scrambled text, citation-based float movement reversed adjacent figures,
and small charts with raster captions were enlarged too far. The academic-9 and
academic-10 native candidates were withheld when real reading exposed further
fraction placement and undecodable summation-glyph defects.

The local pipeline now preserves source-near float order after completing an
interrupted paragraph, extracts safe bottom captions as selectable text, scales
small visuals relative to source text, and keeps adjacent source-row plots together.
Inline runs retain explicit bold, italic and script styles, including CM-Super's
documented short font names. Actual fraction bars bound local source crops;
undecodable glyphs retain their original PDF appearance instead of guessing a
Unicode replacement. Ordinary text beside the notation determines its grouping
baseline while original source geometry stays intact.

Body-size comparisons use prose runs rather than counting small mathematical
glyphs. Display expressions stay adjacent to their colon-ending introductions
before deferred figures or notes. Numbered emphasized leads remain in the same
paragraph as their body text, bold run-in labels preserve paragraph boundaries,
and footnotes have superscript markers and a distinct note presentation.

Where a following source row touches an inline crop, rendering removes edge ink
only after finding a full-width blank raster band below the lowest selected
baseline. This preserves continuous descenders and leaves an inseparable source
unchanged. Preview and zoom use the same rule. Inline-source completeness is
validated independently of block ownership. Parser `academic-11` invalidates
older analysis without deleting it.

### Actual Linux acceptance

The independently staged portable candidate was opened in the native CEF app
with the supplied HPCC PDF, MP-RDMA and the supplied single-column manuscript.
Normal reading and zoomed pixels were compared with the original PDFs; local
styles were also compared with Scholaread on the same supplied document.

- HPCC summation symbols and adjacent fractions retain their order and baseline;
  rate and reduction-factor fractions appear after their correct prose prefixes.
- MP-RDMA's continued mathematical paragraph remains complete before its figure;
  the available-window expression follows its introduction. Numbered italic
  paragraph leads stay with their continuation, and the fifth footnote is visibly
  distinct without suggesting an unimplemented link.
- The single-column document preserves separate bold paragraph labels, compact
  adjacent figures, shared legends, both captions and the three-line display
  expression. Algorithms 1 and 2 retain all 11 and 17 numbered lines respectively,
  indentation, vertical guides, formulas and borders. Normal-size and enlarged
  views were inspected; hiding viewer controls exposes the complete final line.
- At 527px window width, prose wraps and adjacent figures stack without horizontal
  overflow. Scrolling away and back reloads visuals; zoom dismissal and reopening
  Reading preserve position. Nineteen older cache files kept their hashes and
  modification times; the three new academic-11 caches were reused unchanged.

This is representative same-page acceptance, not an exhaustive semantic audit of
all pages. All private PDFs, extracted prose, paper-specific assertions, geometry
and screenshots remain outside the public source repository.

### Build and checks

Application source `8e3d70113eb1e080fb070e990129366f9e0fbcfd` has the same complete
Git tree as public source
[`eeb324bfe8d9675a7a5c78abd5fdfe08ae2d33eb`](https://github.com/Micraow/readest/commit/eeb324bfe8d9675a7a5c78abd5fdfe08ae2d33eb).
The Linux candidate uses a production frontend and the existing debug/unoptimized
CEF native profile. Its unstripped ELF is 226,740,032 bytes, SHA-256
`601e84b8a20e6da498c2e88c4707843e10b570953692cccfaeb4824dcd335f2a`.
The complete frontend export passed with a 2048 MiB Node heap, source maps disabled
and one Rayon thread; the locked offline native build passed. These resource limits
avoid the earlier exit-137 frontend attempt without changing application behavior.

TypeScript, Biome and 238 focused academic/UI tests passed. The final aggregate
completed in eight bounded shards: **13,176 passed, 16 skipped**, **1,126 test files
passed, 4 skipped**. Its only additional exclusion is the previously documented
`src/__tests__/services/novel/novel-import.test.ts`, which performs unmocked external
network contact. Four local PDF copies (61 pages) also passed source mapping,
figure order, paragraph continuity, style and cache round-trip assertions.
The source head had no GitHub Actions/check runs when checked; local results are
not described as a remote CI pass.

### Remaining limitations

The reader does not reconstruct arbitrary mathematical semantics. Unrecognized
complex notation can still need the Original PDF view; an inline operator and its
operand may wrap across lines, and high magnification can reveal tiny neighboring
ink at a crop's upper edge. Preserved notation and algorithms remain local source
images rather than selectable mathematical expressions.

Scholaread's same-file view still has more spacious typography and retains some
monospaced parameter fonts that this reader currently normalizes to the reading
font. Original PDF links and inferred citation/footnote navigation are not yet
represented by the academic inline model. The supplied MP-RDMA citation example
has no original PDF link annotation. These are recorded gaps, not claimed fixes.
The academic-8 and UI-1 delivered artifacts remain separate historical versions.

## Continuous reading and local caption repair: academic-8 (2026-10-07)

This checkpoint supersedes the academic-4 delivery and reading-quality conclusions
below. Native reading exposed further failures that item-coverage totals had not
caught: page-top floats interrupted sentences, single-column captions could share
incorrect crops, and running heads or notes could enter continued body paragraphs.

The PDF parsing and reflow pipeline is entirely local. See
[the local pipeline contract](./academic-reader-local-pipeline.md). No remote
layout service, PDF upload for parsing, OCR, or AI was added.

The repair now:

- Joins supported cross-page and cross-column continuations before placing nearby
  figures after complete referring paragraphs; grouped references retain source order.
- Separates adjacent captions independently of body column count. Shared legends
  stay with a combined visual and both explicit caption identities. Crop bounds
  exclude following body prose.
- Removes repeated inset running heads using stable position and spacing, while
  protecting shared legends and ordinary body lines. Wrapped numeric assignments
  remain prose rather than becoming numbered lists.
- Keeps recognized publication notes and superscript-marked footnotes separate
  from a continued paragraph. Page-top algorithms no longer split supported
  continuations; same-column algorithm boundaries remain conservative.
- Uses parser version `academic-8`, preserving older cache files without reusing
  their layout results. Caption ownership survives cache validation and reopening.

Validation uses four local PDF copies (61 pages): public HPCC and MP-RDMA author
copies, the supplied HPCC copy, and a supplied single-column manuscript. Private
PDFs, extracted prose, screenshots, geometry and paper-specific assertions remain
outside the public repository. Committed tests use synthetic or public-source cases.

The Linux candidate uses a production frontend with the existing debug/unoptimized
CEF native profile. Its unstripped ELF is 226,752,224 bytes, SHA-256
`08439924accc508eaba5ef3ee597fd0e8ddc0a7e5961cc60702df8a1a14d32b4`.
The frozen application build source is `dd10a8bde889783c3a63c335805310d22f561eca`;
subsequent validation-document changes do not alter the application blobs.

Known limitations remain: complex inline fractions can flatten into imperfect
text order; a footnote after a completed paragraph can still precede a display
formula introduced by that paragraph. The Original PDF view preserves the source
presentation. The checks below cover the reported cases and representative native
reading flows, not exhaustive semantic reconstruction of every page.

Completed checks for this source: TypeScript/Biome, 152 focused academic tests,
and the offline-compatible aggregate: **13,118 passed, 16 skipped**, **1,119 test
files passed, 4 skipped**. Only the existing external-network
`src/__tests__/services/novel/novel-import.test.ts` exclusion remains. A platform
interruption stopped an incomplete shard; only that and subsequent shards were
resumed, with the same frozen source. No interrupted shard is counted as passed.
The production frontend exported all 25 HTML pages and five academic-8 chunks;
the native build and portable ELF/dependency checks passed.

Final Linux native acceptance used the independent portable candidate and the
same preserved profile:

- HPCC's two reported interrupted paragraphs are continuous; Figures 1, 2 and 3
  follow their complete referring paragraphs, and the full Figure 3 caption remains.
- MP-RDMA's introduction and a later cross-column paragraph remain continuous
  around publication details and a superscript-marked note; note text is retained.
- The single-column manuscript keeps independent adjacent diagrams, combined
  figures with shared legends and both captions, complete display equations and
  algorithms, and continuous body text across page-top floats.
- A 526-pixel window wraps the body fully. Figure zoom from 44% to 53%, panning,
  closing and PDF/Reading reopening return to the same position. Scrolling away
  and returning reloads visual regions.
- New academic-8 caches were generated. Their completed cached reopen preserved
  hashes and modification times; ten older academic-4/5/6/7 caches were unchanged.

These are actual native reading and interaction results, supplemented by parsing
and ownership assertions. They are not inferred from unit-test totals. GitHub
Actions had not created runs/check-runs for the preceding main checkpoints; no
remote CI pass is claimed. This follow-up delivers Linux only. The earlier Android
development signing key was unavailable after the workspace reset, so no
same-certificate Android update is claimed.

## Reflow quality correction: academic-4 (2026-10-06)

The academic-2 source-coverage and build gates below did not establish reading
quality. A published, Distiller-optimized HPCC copy exposed a complete-page fallback
on PDF page 3 and a clipped Figure 3 caption on page 4; MP-RDMA exposed interleaved
columns, detached diagram pieces, and inline prose promoted to oversized formulas.
These failures were reproduced in the original Linux CEF application before repair.

The correction uses three local inputs (46 pages): the original author HPCC golden,
an additional 15-page optimized HPCC copy tested privately, and the 16-page
MP-RDMA ToN author copy with SHA-256
`1622088345c08283aa4b920f5f43c461c044043012c3587ea9599c00ff26d3c1`.
PDFs, extracted prose, and screenshots remain outside the repository. The committed
public fixtures contain only geometry from the public author copies and generated
replacement labels. The supplied-copy geometry and document-specific assertions
remain local and are excluded from publication.

Changes in `academic-4`:

- Infer recurring column whitespace before joining baselines; short bibliography
  markers participate in the final gutter position. Genuine three-column layouts
  keep their explicit conservative fallback.
- Use real captions and local source bands to collect complete figures, small
  vector/image pieces, captions, and rotated axis labels. Distinct captions remain
  separate even when padding overlaps. Figure/table references in prose are not
  captions, and standalone Roman-numeral table labels are recognized.
- Preserve complete column-local display mathematics, including raised fractions
  and multi-branch braces, while keeping inline settings and reference URLs in prose.
  Equation previews use the surrounding text scale rather than stretching every
  short expression to the article width.
- Join wrapped article titles, preserve run-in abstracts, and do not assign prose
  outside a crop via geometric ownership slack. Attach a multi-row dropped capital
  only to its first body baseline, preserving the subsequent line order.
- Increment the parser version so old academic-2 and intermediate academic-3
  layout caches are not reused.

Acceptance adds semantic and rendered checks, not just source counts: no unexpected
cross-column prose in the 46-page corpus, separate ownership for all 54 figure/table
captions, complete target labels/branches/numerators, and before/after crop pixels.
Both the primary repair and subsequent boundary regressions were tested red before
their fixes. Final frontend/native build and installed-application results are
recorded below when completed; a dependency-warming binary with the old frontend
is not a corrected deliverable.

Frozen local build source: `0d3567ca478fceef2da5aebd2cc4955b8bffddc4`.
Published corrective source: [`f7af41401cc9289b2e0e9bf7d7bedb5d0ce46f76`](https://github.com/Micraow/readest/commit/f7af41401cc9289b2e0e9bf7d7bedb5d0ce46f76),
with identical application-source blobs and only public-source/synthetic fixtures.
Local source gates passed: TypeScript/Biome; 158 focused academic tests; and the
offline-compatible aggregate with **13,095 passed, 16 skipped**, **1,117 test files
passed, 4 skipped**, retaining the existing `novel-import.test.ts` exclusion. Those counts include the
local-only supplied-copy cases; they are not the public-checkout test count. The reduced
public fixture/test set independently passes TypeScript/Biome and all 144 focused
academic checks. Its offline-compatible aggregate independently passes with
**13,081 passed, 16 skipped**, **1,117 test files passed, 4 skipped**, with the same
explicit external-network test exclusion.
The final Tauri frontend export passed with all 25 HTML pages and five verified
academic-4 parser chunks. An initial concurrent frontend attempt was terminated
with exit 137; the same constrained build completed after tests and old native
test processes finished. This was a resource retry, not a skipped compiler gate.

The corrected Linux native build passed offline with the pinned CEF toolchain.
It remains a debug/unoptimized native profile with a production frontend, not an
optimized release build. The 226,739,936-byte ELF has SHA-256
`73d5e2ea54b2ff748537c90444285afce6a638c81d39bb07bf27ac3be2694e52`.
All five frontend parser chunks were matched byte-for-byte to embedded Brotli
assets; only academic-4 was present. `RUNPATH=$ORIGIN`, runtime dependencies
resolve without build-toolchain paths, and the minimum GLIBC version is 2.39.
Native reader acceptance passed using the portable candidate and preserved profiles:

- The exact optimized HPCC file regenerated academic-4 automatically. Old
  academic-2/3 cache files were neither deleted nor modified.
- HPCC pages 3 and 10 show complete, local figure crops and live body text rather
  than page images; page 4 retains both Figure 3 caption rows and normal timer prose.
- MP-RDMA's abstract and dropped-cap introduction have correct text order. Its
  packet-header diagram includes both panels, callouts, and the complete caption.
- Figure zoom/pan/close returns to the same reading position; scrolling away and
  back reloads crops; a 663-pixel window keeps content within the viewport.
- The final drop-cap change affects only MP-RDMA page 1. Reanalysis of the preserved
  HPCC runtime geometry produces identical blocks across all 15 pages.

The portable candidate's symbol stripping was verified to preserve all loadable
ELF sections/segments. The final portable archive was verified after packaging: all 238 payload files
match the included `SHA256SUMS`, launcher/binary executable modes are retained,
and no absolute or parent-traversing paths, PDFs, screenshots, profiles, or caches
are included. The 206,025,785-byte archive has SHA-256
`4fa844a9595460f1a6dc286348080ddd23133a82809f8fdd8edd8fd9aaa8a146`.
Library publication is a separate delivery action subject to its current file scope.

Known remaining limitation from native inspection: complex inline fractions in
the optimized HPCC parameter discussion around PDF pages 9–10 can still flatten
into an imperfect numerator/denominator text order. Display-equation crop fixes do
not claim complete inline mathematical reconstruction. The original PDF view
remains the authoritative presentation for that expression. This is recorded
separately from the repaired cross-column body order and figure/caption failures.

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

Real Zotero Personal Library/Storage authentication and authenticated attachment
downloads have not been exercised. The separately supplied local PDF was tested
in the reader as described above. No real API key or library metadata was supplied.
Mocked downloads/offline reopening do not substitute for that check.

On Android first, then Linux, confirm the user's collection hierarchy, lazy HPCC
Storage download, offline reopening, Original PDF, manual Reading, figure/algorithm
zoom, return to the shelf, cache reuse and local-only removal. Confirm no ordinary
Book duplication, no Readest Cloud upload and no Zotero writes. Physical touch and
memory behavior still need target-device evidence.
