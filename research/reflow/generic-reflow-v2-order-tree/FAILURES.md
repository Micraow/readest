# Retained failures and narrow fixes

All diagnostics below concern previously seen pages or original synthetic controls, never unopened holdouts.

- Original global y-order passed native inventory checks but interleaved two-column paper text, table cells and math. Native accounting alone was inadequate; this is the reason for a separate region tree.
- Splitting all empty horizontal gaps before retrying columns let large paragraph gaps outrank the gap below a spanning title. The original spanning-title control failed. Recursing after only the first barrier now passes that control and plain/middle-span/embedded-figure controls. Crossing floats still abstain.
- Full source/output inspection shows a remaining cross-column sentence interrupted by the right-column figure and caption. Native-index intervals and column order pass, but logical prose continuity does not. This is an open reading failure, requiring a separate main-flow/float relation rather than a page-specific sentence patch.
- A no-prior D4 tree still abstains at table overlaps. Optional layout priors supply bounded proposals, not a hidden always-successful fallback.
- A table predicate restricted to stroked paths rejected a true thin image rule. Type-independent aspect/height evidence was added, along with repeated native row/column evidence; a single underlined text column remains rejected.
- Formula prose filtering initially concatenated smaller subscripts as ordinary letters. It now examines dominant-size alphabet runs only. This is seen-page-driven development, not validation.
- Closing every nearby fraction row accidentally absorbed a next-line numerator. A nearest-row contract/test prevents it; the failed fraction output is retained.
- A support-neighbour heuristic pulled a short ordinary word into a superscript group. The loose result is retained; new cross-object closure disables that optional short-word attachment. Actual touching ink remains bounded/local.
- A native graphic candidate missed pale fills and contained labels, even while its selected support pixels matched. Iterative contained printed paint/text plus bounded logical closure recovers those pieces on the seen page. A later full-reader visual review exposed another missed axis-label row and corrected an earlier overoptimistic partial-figure assessment.
- Independent native RGBA layers were not perfectly equivalent after quantization: prior checkpoint has an original control with 3 differing pixels/max1 and D4 with 536/max1. Original-order native action replay, not sums of alpha counts, is used for source equivalence.
- New integer-copy bundles initially stored black RGB under alpha-zero pixels. All owned opaque pixels remained exact, yet the static PDF path displayed hollow/outlined glyph artifacts. Keeping the native flat-backdrop RGB under zero alpha fixed the observed preview. Failed screenshots and assets are retained; this observation is not a proof for every browser compositor.
- A true cold live-model page timed out at 60.077s. Isolated-model-process plus passive-thread settings completed at 52.669s. Both are retained; single-run improvement is not production latency evidence.

## Metadata correction after measured run

The adapter initially hardcoded `cached_predictions_only=true` and a cached model label even when handed the fresh local model result. This was a reporting bug: the enclosing pipeline and child output correctly recorded fresh inference, its costs, model hashes and raster. The measured files remain unaltered with a private erratum. Current code accepts typed historical/live provenance; two new tests reject unknown provenance and verify live-versus-adapter inference counts. No layout threshold or visual output changed in this metadata correction. The exact fresh prediction hash is recorded in the aggregate result.
