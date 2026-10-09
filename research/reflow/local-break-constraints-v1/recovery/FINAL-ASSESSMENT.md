# Frozen local-break candidate: negative final assessment

2026-10-09. Frozen implementation: `9f6b88cfa9b15169f7d739b10c350efa261e19dd`.

## Decision

Do not promote this candidate. The required 85% complete-body readability and 15 percentage-point gain over B are not established. A has directly observed prose-order, paragraph-continuation and foreground/background grouping failures. B additionally suppresses three entire displayed formulas, contaminating the comparison. Fewer locked words or perfect declared source-pixel ownership cannot establish readability.

The frozen batch is closed with this negative result. No algorithm, threshold, font rule or input was changed during the final assessment. No engine replay was run for this assessment. These twelve pages are now seen data and cannot support a fresh generalization claim after a repair.

## What was actually inspected

All twelve native source-page images and all twelve A outputs were visually inspected at 390 CSS px / 20 CSS px. D1-D2 use the retained WeasyPrint CSS raster; D3-D6 use source-atlas blits at WeasyPrint box coordinates, omitting UI labels/borders. Neither is Chromium/Android evidence. Local object viewport clipping is not automatically content loss, and horizontal interaction was not verified on these PDFs.

The five other width/font combinations have generated HTML, but have not received equivalent visual review. B has a selected D1-P1 visual comparison and all-page atom/HTML accounting. E, C and D do not have a completed twelve-page visual comparison. Source math was not exhaustively glyph-checked. Unknowns are retained rather than certified as successes.

Original-fixture Chromium run [37882285419](https://github.com/Micraow/readest/actions/runs/37882285419) passed five synthetic-control groups on validation commit `892e08ba765767d97d1409c39c30d0b9dd3e2bd5`. That verifies renderer controls, not real-PDF semantics or this experiment's acceptance target.

## Corrected body-unit accounting

The earlier 95-region / 76-mechanical-candidate result is invalid. The QA loader joined annotations on `image_id` alone, mixing train annotations into validation D3-P2, whose ID is 2553. The corrected key is `(split, image_id)`. Per-page class counts now match the pre-frozen selection. Old observations and the old reference remain preserved for audit; they must not be cited as a valid score.

The corrected official reference contains 87 Text/List regions, not 87 complete paragraphs. Two are running titles. The other 85 regions map exactly once into 69 paragraph/list units after joining continuations across displayed equations, columns and the registered adjacent pages. Clipped or unverified units remain in the denominator. This grouping was completed after observing outputs and is a descriptive self-audit, not a preregistered measurement.

At the inspected setting, 34 units visibly rewrap without an identified internal sequence/boundary defect, 31 have a definite defect, and 4 remain unknown. The 34 are not certified full-matrix/math/browser successes, so no overall acceptance percentage is reported. The full mapping, reasons and validation assertions are in `FINAL-ASSESSMENT.json` and `final_assessment.py`.

- D1: 2 visibly readable, 1 failed, 1 unknown. The long equation-connected derivation is one unit, not four independently countable prose successes. Multi-line islands reorder its words; the last paragraph exits the supplied pages.
- D2: 5 visibly readable, 1 failed, 1 unknown. The equation chain spanning the page boundary stays one unit. A footnote/rule island interrupts the conclusion; paired-reader continuation remains untested. The first figure's default viewport shows only a restricted slice.
- D3: 1 visibly readable, 8 failed, 1 unknown. The first formula-heavy fragment breaks apart. Source paragraph boundaries are merged; a page number interrupts the cross-column summary. Formula-connected prose on page 2 remains unknown pending complete math/horizontal-access verification.
- D4: 8 failed. All audited units have inline-math/prose-island ordering or continuation defects. Figures/captions and page numbers also intrude into cross-column body continuation.
- D5: 8 visibly readable, 9 failed, 1 unknown. The grey Tips background connects the list into a wide unwrapped island. Figure legend fragments escape their object, and red margin revision strokes are inserted into body sentences and an expression. An introduced calculation lies beyond the pair.
- D6: 18 visibly readable, 4 failed. Chinese glyphs genuinely wrap, but four source paragraphs retain false gaps at original line divisions. Page numbers are also joined to running titles, which are explicitly excluded from the body denominator and retained as non-body relationship failures.

## Contaminated B baseline

All three missing components contain a formula and its own associated identifier. The renderer treats the component as consumed by its own association, then skips it. Rechecking the frozen atom inventory against emitted HTML confirms:

- D1-P1, equation (3.19): 12,912 declared source-ink pixels omitted
- D3-P2, equation (17): 4,188 omitted
- D4-P1, equation (4): 3,363 omitted

These are complete-object omissions, not initial viewport clipping. A's twelve pages account for all declared atoms in HTML with no duplicate IDs, but this still does not prove correct semantic order or final browser paint. No causal quality gain over B is claimed. Font-hint ablation E's weak mechanical counts cannot establish output equivalence or generalization.

## Execution, integrity and durable evidence

All 36 restored execution groups (AB, E and CD for twelve pages) exited successfully. The largest group took 46.84 seconds. This is not per-arm latency: AB/E each prepare two alternatives and six settings. Summing AB+E+CD exceeds 60 seconds on four pages, with a maximum 109.86 seconds before the hot per-page detector cost. Thus a full-comparison 60-second-per-page budget is not met. Restored cold detector initialization took 15.02 seconds; per-page raster/encode/inference took 0.90-1.44 seconds. Cold costs are separate, and restored timings are not conflated with the pre-reset measurements.

All 13 frozen engine/glue files and 24 distinct source PDF/official PNG files were rehashed and match their recorded receipts. All six private document-pair archives were checked against every internal manifest hash (810 archived files in total). No source PDF, source image/crop, model weight, native paper text or private storage URL is included in the public checkpoint. Corrected references and annotated visual evidence are kept privately. Historical evidence storage exceeded the planned 200 MiB allowance; durable backup copies do not retroactively satisfy that cap.

## Next generic mechanism, not a paper-specific patch

1. Separate painted backgrounds, foreground glyph ink and decorative/revision marks before dependency closure. Connected paint is not necessarily one logical object.
2. Enforce exactly-once emission of every geometry atom, even when semantic association endpoints resolve to the same component.
3. Make source logical intervals agree with actual renderer event ordering. Preserve complete paragraphs and column/page continuations; keep headers, footnotes and captions out of body sentences.
4. Preserve figure-label and caption relationships and provide a useful initial object view.
5. Test these invariants on original controls first, then freeze a new unseen corpus. Do not tune by paper identity, font keyword or the twelve reviewed samples.
