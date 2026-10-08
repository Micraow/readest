# Results and failure boundaries

These are small diagnostic experiments, not corpus accuracy or production acceptance. Source rectangle/ink coverage, correct reading relationships, and genuine word reflow are separate measurements. Original-image fallback stays in every denominator and never counts as successful reflow. Resampling changes source pixels even when a source rectangle is retained.

## k2 reuse

The first round used word spacing -1, inherited from the bare FFI context. It is configuration-confounded exploration. Four previously seen pages exposed math/matrix/order failures despite complete measured source-ink mapping.

The second round froze -0.2 after checking KOReader reader defaults. Three new pages were tested once, and the original four were rerun once as a paired configuration regression. No page-informed tuning followed. Of 24 complete prose audit units on the new pages, 21 visibly reflowed with locally correct order, two failed order, and one short sentence supplied insufficient reflow evidence. Six inspected math objects retained their visible structure. One of three pages passed its visual block checklist; two had reading-order failures, including a footer entering a cross-column sentence. This is not character-exact fidelity. Paired pages improved typography while their prior structural failures persisted.

New-page engine time was approximately 0.165–0.266 seconds with about 76 MiB RSS. RGB input and RGB source crops preserved color rather than silently converting scientific diagrams to grayscale. Source-map coverage still cannot certify color, text, or relation correctness.

## Atomic protection

PP-DocLayout-S detections plus protected image regions were compared with the unchanged k2 baseline on BERT page 3 and LayerNorm page 4. There were 13 preregistered complete prose units; separate partial paragraphs were not promoted to complete units.

Baseline k2 visibly reflowed all 13 complete prose units locally. Protection reflowed 11/13. The denominator contained 4,478 native nonspace body characters: 4,322 entered candidate word reflow, 82 protected regions, and 74 the unassigned panel. These branch counts do not establish character correctness.

The detector missed a table and formula numbers. Our compositor also placed unidentified material at the tail and failed to anchor a heading. That made the result worse despite preserving source ink: a table moved after the body, numbers separated from formulas, and a heading followed its paragraphs. Mixed prose/footnote regions fell back to original images. Equation wrapping at a valid operator in the baseline was not classified as semantic damage merely because the line count differed from the source.

Selected failures received external visual spot checks, not full independent audit of all 13 units. The model process group peaked near 653 MiB; startup plus two pages took 6.65 seconds. Composition took 1.40–1.58 seconds per page, near 239 MiB peak. This round does not show that all lightweight detector combinations fail; it locates both detector and compositor gaps.

## Source glyph / interval anchoring

The next frozen round changed only association/composition. The same detector outputs, k2 bitmaps, rendering settings and old two pages were reused for mechanism regression. Native glyph IDs and actual source-ink/map intersections replaced center-point association. Unassigned text retained its native parent, and uncertain overlap/order caused conservative coarsening or original-page fallback. Native PDF blocks were treated as evidence, not semantic truth.

The old-page heading and formula-number positions improved. Complete prose reflow decreased from 11/13 to 10/13 because a native parent merged otherwise separate prose. Of 4,478 body characters, 3,793 entered candidate word reflow and 685 protected regions. Protected equations/tables remained small; correct placement did not solve readable object size. Old-page composition took 0.48–0.67 seconds, near 244 MiB peak.

A previously unused GroupNorm page 3 was acquired from the preregistered official URL and run once with unchanged code. Two source-ink pixels lacked a permitted native parent, triggering whole-page fallback. Actual complete-body reflow was 0/11; all 2,633 body characters stayed in the fallback denominator. At 390 pixels wide, estimated body em was only 6.35 pixels. The baseline locally reflowed 11/11 units but inserted the footer into the column transition. Returning the original page preserved its relationships; it did not demonstrate automatic relationship recovery.

Post-run diagnosis located the two pixels at a radical's lower tip. The native logical glyph/block extent was smaller than the actual `fill-text` paint extent. Outward floor/ceil conversion was internally consistent for that logical box, so this was not proven to be a simple off-by-one bug. No semantic omission was established, and the final whole-page fallback omitted nothing. No threshold relaxation, residual deletion, or same-page rerun occurred. The page is now a seen diagnostic.

Holdout model startup/inference took 5.47 seconds with about 650 MiB process-group peak. Prior composition took 1.61 seconds; anchoring took 0.56 seconds with about 198 MiB peak. The new round occupied about 111 MiB locally. All current-round output inspection was self-audit; no independent full-page acceptance is claimed.

## Next falsifiable questions

First separate logical glyph bounds from actual paint provenance and define a uniform pixel-cell coverage transform. This is a geometry foundation issue, not evidence that a larger recognition model is needed. Then test a small relation predictor for paragraph continuity, headings, number/formula and caption/object ownership, with calibrated rejection. Keep original glyphs/pixels authoritative for content. Evaluate relationships and useful reflow coverage at readable size, in addition to detection and source coverage. No new round is represented by this checkpoint.
