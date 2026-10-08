# Frozen real-candidate column baseline: useful negative result

The two selected paper pages were unused in the checked local experiment registries. Source URLs, versions and SHA-256 values are in `INPUT-FREEZE.json`. The algorithm was frozen before either source page was downloaded or inspected; a recorded code-review amendment for detected page furniture preceded materialization. Source-only QA preregistered eight complete prose units on RoFormer and four on ConvNeXt, plus two separately counted ConvNeXt page-boundary fragments. No manual reference boxes drove the algorithm. Both papers are now seen diagnostics.

## Results, separated by meaning

| Measure | RoFormer v5 page 4 | ConvNeXt v2 page 3 |
| --- | ---: | ---: |
| Source nonwhite pixels | 506,343 | 1,034,375 |
| Unassigned / duplicated source ink | 0 / 0 | 0 / 0 |
| Native body nonspace glyph denominator, including fragments | 2,491 | 3,208 |
| Glyphs entering candidate word reflow | 2,366 | 932 |
| Complete prose units visibly reflowed | 7/8 | 0/4 |
| Baseline k2 complete prose units locally reflowed | 8/8 | 4/4 |
| Inferred columns | 1, matching source | 2, matching source |
| Composition time | 1.75 s | 1.89 s |

The total complete-prose result is 7/12 versus baseline 12/12. Branch membership across all body glyphs, including partial paragraphs, is 3,298/5,699; that is not a semantic-fidelity or complete-paragraph reflow rate. Original-image fallback stays in the denominator. Native glyph extraction is itself not character-exact truth. All 15 output tiles and both reference pages were visually self-audited; no independent full-page acceptance is claimed.

On RoFormer, four detected formulas acquired the correct native number lines, and all four headings stayed in the appropriate source sequence. The three-line equation and matrix product retained their original atomic shape, whereas baseline k2 split the matrix rows/columns into a linear sequence and placed the three-line equation's number before its final line. Ordinary operator-based formula wrapping was not treated as semantic damage merely for changing the number of lines. The protected formulas became very small at 390-pixel width, with main characters around 10 pixels and smaller indices. One complete prose unit was conservatively kept as an approximately 8-pixel original crop. Thus this is a relationship/shape improvement accompanied by an important readability failure, not an accepted scientific reading experience.

On ConvNeXt, the new pipeline made a wide protected region containing the left chart and the upper right-column prose. The right-column continuation appeared before the left-column beginning of its paragraph; section 2.2 likewise appeared before section 2.1. Only the two partial paragraphs and a short beginning of the cross-column paragraph were reflowed. They do not count as four successful complete units. The chart retained its color but was squeezed into the left half of a 390-pixel-wide compound image; its tiny labels are not readable reflow. The original k2 baseline kept the cross-column sentence adjacent and reflowed all four complete prose units locally. We did not verify every numerical chart label at character level.

## Diagnosed mechanism

The wide region was triggered by `unknown_paint_parent`. Inspection showed that its paint operation was a broad **white background rectangle**. Its bounding rectangle extended behind material from both columns. The implementation treated a remaining dark pixel's inclusion in that bounding rectangle as if it established ownership by that paint operation, then merged intersecting semantic candidates. That implication is false: a paint envelope establishes possible spatial support, not which operation produced a final visible pixel and not which semantic object owns it.

Column inference itself found the two correct columns. The failure is therefore more specific than 'geometry cannot work' or 'the detector needs a bigger model'. It exposes the compositor's substitution of bounding-box overlap for pixel/semantic ownership. The pipeline did not trigger whole-page refusal because the resulting compound parent looked spatially nonconflicting after the merge. This is a missed rejection as well as a reading-order failure. No rule was changed after these outputs.

The next falsifiable mechanism is to keep paint bounds as coverage evidence, preserve separate semantic candidates, and represent their visible source pixels with masks. A connected ink component supported by one source candidate may extend that candidate's physical mask; multi-owner or unseeded components must remain explicitly uncertain. A broad white paint envelope must not merge candidates just because their ink falls inside its rectangle. Blindly deleting all white operations is also unsound because white paint can occlude earlier content. This mask hypothesis needs an independent invariant test and then real-candidate validation; it has not been demonstrated by the present result.

## Resources and evidence

The unchanged PP-DocLayout-S process used a recorded maximum RSS of 546,088 KiB; the external process-group sampler peaked at 537,512 KiB, with the difference expected from sampling. Startup plus both pages took 5.66 seconds, with 0.53/0.25-second model inference. The externally monitored compositor plus child k2 processes peaked at 332,176 KiB. Single CPU, 1-GiB memory bounds and the per-page time budget were respected. No training, model download or paid API was used.

RGB source crops and source-map rectangles were retained. Source ownership counts precede resizing; they do not imply identical output pixels, correct scientific colors/relations, or readable scale. Cached paper originals, detector output, glyph data, actual source/output images and QA references stay local. Public files contain original source, fixed settings and aggregate audit/results. The old frozen rounds were not modified. This checkpoint is research only, with no application or Android acceptance claim.

The scripts expect `paint-envelope-v1`, `k2-reuse-v2-default/build/k2-reflow-harness`, the existing Paddle environment and model directory as sibling dependencies. Older engine glue is archived under `research/reflow/2026-10-08`; reconstruct those working directories and dependencies using its README before attempting reproduction. The public checkpoint deliberately does not package paper PDFs, rendered evidence, model weights or a complete execution environment.
