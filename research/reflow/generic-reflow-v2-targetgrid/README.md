# Target-font/DPR native local requests and bounded cache

Development mechanism only, following immutable `1e853235`. No paper holdout opened, browser/Android result or complete-page font-switch acceptance. It reuses a previously computed native page plan; it does not rerun the layout model or OCR.

## What changed

A request selects existing unit IDs and target CSS size, DPR and optional local enlargement. Typed grid rungs are 2/3/4/6/8 pixels per PDF point. For the old D4 body, 28px/DPR2 requires 5.621; the chosen 6x grid supplies 1.067 native samples per device pixel rather than enlarging a 2x image. Native source glyphs/fonts, geometry and unknown mappings are retained.

The initial floating-point crop API failed with a global-pixel alignment error at 6x. The failed source and outputs are preserved. Integer native device-coordinate viewports avoid that rounding path. A stricter independent full-object alpha baseline revealed 1,949 local/full RGBA pixel differences among 88 participating text objects even though none escaped the padded viewport. Stable local clipping alone was therefore insufficient.

The strict baseline re-rendered every complete text object; its three-unit 6x miss took 34.930s wall/32.347s CPU, and the fresh service probe including startup, 6x miss/hit and 2x miss/eviction took 39.919s/37.155s CPU. That cost is retained, not replaced by a warm-cache time.

The optimized reference uses **complete native text sets whose every potentially painted character record belongs to one existing unit**. Each set is painted once with the original engine/order onto a transparent native canvas. Its complete alpha and outside-unit support are checked. This is not compositing independent rounded RGBA layers. Shared objects retain strict complete-object alpha partitioning. Unmapped potential native records reject the shortcut.

D4's three requested native units have closed sets of 11, 13 and 63 text objects plus one externally shared text object. Output PNG bytes and source coordinates exactly match the strict reference. Their complete glyph/raster geometry was visually inspected at actual native size. The first unit classified by the earlier extractor as a `native_word` actually contains inline mathematical text; it is not evidence of a new semantic prose classifier.

## Stable geometry and cache

Scale-dependent ink extents do not become layout advances. The asset reports a fixed native PDF box plus the image-origin offset and sampling grid. The fixed box is identical between 2x and 6x while the raster's fringe can round differently. A future client must apply that offset rather than stretch a prior image or substitute its pixel-crop width as logical advance.

The in-memory LRU has independent limits: 8MiB encoded, 32MiB decoded, 64 entries by default. Oversize content is returned without caching. Keys cover source PDF, plan plus ownership policy, unit set, actual grid, PDFium version, adapter-code fingerprint and native backdrop policy. A policy/renderer change cannot reuse a stale asset. Unit IDs address the response; logical reading order remains in the existing flow graph, not the archive order.

The runtime probe forced a one-entry capacity to verify hit identity and eviction: high-grid miss, same high-grid hit, distinct low-grid miss with high-grid eviction. Nine control tests cover density, enlargement/refusal, keys, byte limits, eviction, shared-object exclusion and unowned native-record rejection. Existing original authored PDF controls also ran at both grids.

## Measured scope and remaining gaps

Three old-page assets only: a native text run, an inline fraction group and a complete two-panel figure. Their 6x PNGs total 331,049 bytes and decode to 7,925,204 bytes. The packaged response is about 336KB. Full page remains 707 units/642 image resources at its earlier baseline grid; this experiment does not claim all those assets have been regenerated or optimized into an atlas.

The first optimized fresh service probe took 5.383s wall/5.318s CPU/324.094MiB; its high-grid miss was 3.192s and hit 0.015s. A later guarded-code probe under higher shared load took 9.911s/9.076s CPU/324.152MiB, with high-grid miss 6.142s and hit 0.039s. Do not present the best observation as a guaranteed latency or a cache hit as first-use cost. The final current-code result is in `PUBLIC-RESULT.json`; all earlier results remain private.

These request costs exclude the earlier page extraction/model/order cost and all browser integration. They cannot simply replace the measured page latency. PDFium source/font resources are required on a miss. Default source-light theme remains; unknown native glyph semantics remain unknown. Real font controls, whole-page target-grid cost, selectable-text semantics, dark theme, local-zoom interaction, mobile deployment and untouched-paper validation remain open gates.

Private evidence retains full alpha references/diagnostics, both slow and optimized variants, native 6x images, cache traces and failure source. Public files contain original code, contracts and aggregate numbers only. Earlier frozen code is not modified.
