# Target-font/DPR native local assets

Written before the new raster-grid tests; follows frozen `1e853235`. This is an on-demand native asset mechanism, not validated browser zoom or a production app feature. No holdout opened.

## Request and computation

A request names existing native unit IDs (or an existing small bundle's member IDs), target CSS body-font size, device-pixel ratio, and optional bounded local enlargement. Choose the smallest typed raster-grid rung at or above the required samples/PDF-point. Do not reuse/rescale a 2x mask. Reopen the original source PDF and regenerate each participating text object's native alpha at the target grid, using the existing logical ownership map and all external glyph owners from that object. Keep original glyph semantics unknown when unknown.

All target alpha must have an unambiguous owner and stable padded viewport. A newly ambiguous ownership or unsupported scale refuses the asset; do not grow the logical unit, erase pixels or interpolate the old mask. Nontext paint remains native paint in original order. Shared text-object support excludes foreign words. Selected-support RGB must match a full native reference at the same grid. Source ink and coordinate coverage are audited separately from atom IDs. No whole-page image becomes reader output.

## Bounds and cache

Typed bounds cap scale, full native reference pixels, one-object crop pixels and requested unit count. A decoded/encoded byte-bounded LRU cache keys source PDF hash, ownership-plan hash, requested source IDs, raster grid, renderer version and native backdrop policy. Higher-DPR requests cannot hit lower-grid assets. No unbounded per-word pre-render matrix of sizes. Account cache hit, miss, eviction and preprocessing separately. The source PDF/font resources are required for a miss; the runtime must release native pages/bitmaps/documents.

## Verification

First reuse the existing original control, then D4 old-page native word/math/figure units selected by generic kind/geometry, without paper keywords. Compare native asset pixels and relative PDF-coordinate geometry at 2x and a grid sufficient for 28px/DPR2. Inspect actual high-resolution local output, not a screenshot stretched from old PNGs. Record CPU/wall/RSS, bytes, pixel dimensions, grid-selection reason, source-support differences, ambiguity/quarantine and cache eviction. Whole-page generation cost from a different run cannot stand in for this miss, and a warm cache hit cannot stand in for first-use cost.

This does not remove raster content inherent in the source PDF, certify Unicode copy, dark theme or browser interactions. A native-grid failure remains explicit and original low-resolution assets are not silently called sharp. Readest UI integration and true zoom/font interaction remain separate acceptance gates.

## Diagnostic-driven reference amendment

The 6x floating crop API failed pixel alignment. Integer device-coordinate viewports fixed alignment, but local/full alpha RGBA differences required an independent complete-object reference. That strict baseline was too expensive for a quick font/zoom miss. The candidate now batches only text-object sets proven fully owned by an existing unit, checks the complete native set's alpha (including outside-unit ink) and keeps shared objects on strict complete-object partitioning. This unit-domain mask is explicitly distinguished from each individual object's alpha. All actual native paint operations remain enabled once and in original order during final local rendering. Exact output bytes/coordinates are compared with the retained slow reference, not just an atom count. No whole-page target-grid performance is inferred.
