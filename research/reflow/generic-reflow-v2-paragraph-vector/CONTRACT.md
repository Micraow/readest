# Complete-paragraph native vector integration contract

This experiment follows the glyph-resource probe without further tuning on its five anti-aliasing pixels. Existing source/order/flow checkpoints remain immutable. Only already-seen paper diagnostics are used; holdouts remain unopened.

## Reader outcome

Render a continuous existing paper reading-flow range containing complete prose paragraphs, inline mathematical groups, a display equation and a figure/caption. Keep the established region/column/paragraph order; source line endings must not automatically force output lines. Reuse native glyph contours across words and font sizes. Bounded non-text mathematical/figure groups retain the prior native renderer rather than losing bars or labels. A generated PNG is QA evidence only; it is not the reading representation.

A first prototype may retain declared native-image assets for local groups. It must report vector/fallback units, requests/bytes, cold preprocessing, native target-size generation and warm layout/redraw separately. It must not call low-resolution fallback or semantic selection a pass. No browser execution is authorized locally; native Node canvas and static layout are labeled accordingly.

## Cross-renderer bridge, explicit abstention

The previous logical-unit IDs belong to PDFium. PDF.js paint IDs are separate. Geometric source origin/baseline correspondence is a proposed bridge, not an identity assertion. The initial diagnostic precision bound is 0.002 PDF points per axis (typed configuration, no font family/string/document exceptions). Only mutually unique one-to-one glyph correspondences inside one existing native-word unit are eligible. Missing, duplicate, ambiguous, clipped, unsupported or extra paint operations prevent conversion of that unit. Candidate Unicode is recorded only for diagnosis and never used to select the drawn contour. All other units retain their previous representation and explicit reason trace.

This bridge cannot itself prove complete pixel ownership. Original-coordinate native replay, paint inventory, cross-unit support/contact checks, source interval closure and the previous ownership evidence are separate checks. No mixed-engine whole-page visual-equivalence claim is permitted without a dedicated comparison.

## Predeclared distinct acceptance reports

1. Strict pixels: record exact differing pixels/channel maxima against the same native renderer. Any nonzero difference is a strict failure, retained rather than thresholded away.
2. Structural geometry: no missing/duplicated owned paint references, no changed contour commands, no unexpected clipping, and within each text/local group only a common affine placement transform. Unknown/multiple ownership is an abstention. A glyph inventory is not by itself ink completeness.
3. Actual reading: inspect every output line in the complete selected paragraphs at 390 CSS px and 20/28 CSS px font, with target DPR stated. Check paragraph order/continuation, inline-script/fraction attachment, equation/number association, figure/caption association, accidental source-line breaks, spaces, collisions and omissions. Preserve visible failure examples. Real interactive selection/font control/local zoom remain separately unverified until tested.
4. Cost: 1 CPU / 1 GiB / 60 s page remains the product target. A fragment, cache hit or redraw cannot be substituted for a full cold-page cost. Record load, CPU, wall, peak family RSS and included stages.

The bridge and native resource layout are provisional. If the bridge fails broadly, rebuild the logical layer on one renderer's own atoms instead of relaxing ownership conditions or encoding paper-specific patches.

## Existing composite proposals are revisable

A newly observed parameter break comes from an old over-broad vector composite, not from a missing image. Before increasing any width limit, repartition all-vector composites using their existing whole native-word members. Adjacent baseline-sized members can become separate breakable components; smaller glyph runs attach only through bounded preceding native geometric script edges or same-script-row edges. Preserve each native paint exactly once and keep source transforms; do not split a glyph or a non-text/local-image group. Then apply the same bounded function-argument relation. A plus sign next to an already closed fraction is a possible ordinary operator break, not evidence that the fraction lost a base. Existing local image groups remain closed until a genuine cross-group paint dependency is established.
