# Shared native glyph resources: bounded mechanism evidence

Existing Readest lockfile pins PDF.js 6.2.108. Its actual paint path retains native `fontChar`/original character code separately from candidate Unicode. In the already-seen paper, 3,380 observed glyph paints reuse 269 contours across 26 font IDs; the raw contour JSON is 406,427 B, gzip 64,072 B. This is a resource mechanism, not yet a complete reader or a certified selection layer.

## Verified and failed separately

- Untouched-engine vs instrumented observer: zero pixel difference on the authored control and seen paper.
- Replacing original glyph drawing with shared contours *in the original native drawing context*: zero pixel difference on the seen paper. Native clipping/order/state are retained in this control.
- Moving all glyphs after the complete non-text layer initially failed by 71,393 pixels. A native Node canvas `fillStyle` getter was stale after save/restore: a 1×1 original control reads black while actually drawing gray. Explicit state tracking fixes this and preserves two clip resources, but the postposed reconstruction still differs at one pixel/max1. It remains a strict failure and is not the production drawing architecture.
- Actual relocation of a complete native text-show interval, selected by maximum eligible glyph count, uses 51 glyphs/18 contours on the seen page (45/19 on the original control). At 1× and 3×, native source-path replay matches a separately transformed native reference exactly. Only text is included; this does not claim ownership of formula bars/figure paths.
- The earlier final-matrix version differed at five anti-aliased pixels. Keeping the source affine command sequence instead of a quantized final matrix fixes it. Failed code/evidence are retained privately.
- A failed opaque-reference comparison and an incorrect test assumption that native alpha stores exactly .25 are also retained. PDF.js's default canvas path asks for an opaque context; the transparent local reference now explicitly supplies `canvas:null`. This is not a browser result.

Paint inventory is checked separately: seen page has 879 text-show calls, 3,384 native glyph records, 3,380 eligible paint calls and 3,380 observed calls, no Type3/invalid-font calls on that page. Unsupported paths/fonts/patterns/soft masks/clipping must abstain; zero such calls in this page is not general support. SVG clip serialization matched the native clip objects here, not a global serialization guarantee.

## Cost and deployment limits

The latest complete seen-paper probe is 16.883 s wall / 16.471 s CPU / 308.10 MiB peak family RSS, one CPU. It includes multiple quality/reference renders, serialization and selected relocation; it excludes dependency installation, logical reflow, an actual browser and interaction. Different runs had different load; do not infer algorithm speedups from them. The original control final probe is 3.594/3.539 s and 163 MiB. These are not cold complete-page reflow times.

Package provenance/integrities/license hashes and uncompressed installed bytes are in `PROVENANCE.json`. PDF.js is Apache-2.0; the test-only native canvas package is MIT with its platform binary. Existing repository code remains under the repository AGPL-3.0 terms. No vendored binaries, private PDF/Unicode/glyph paths or screenshots are public. Node legacy build was needed after the modern-build Node probe failed on `Uint8Array.toHex`; this is not evidence about Readest's actual browser runtime.

The probe depends on pinned internal renderer anchors and carries maintenance cost. Compiled path caching, an actual browser bundle, dark backgrounds, mobile deployment and validated copy/selection remain open. PDF.js IDs are not PDFium IDs. The next isolated paragraph experiment must prove or abstain on their correspondence, preserve local mathematical/figure paint, and inspect complete paragraphs rather than only local pixel controls. All holdouts remain unopened.

## Reproduction

Create a private runtime with the provided package manifest/lock, then `npm ci --ignore-scripts --no-audit --no-fund`. Use the existing original authored control first, followed only by authorized seen-page PDFs. Run `node code/test_state_tracker.mjs PRIVATE_RUNTIME` and `python3 code/measure_probe.py PRIVATE_RUNTIME PRIVATE_PDF NEW_PRIVATE_OUTPUT --script probe_stateful.mjs`. Old probe variants intentionally retain failed approaches; see private evidence for exact source snapshots. Native Node canvas is explicitly non-browser evidence.
