# Blind batch failed: 0 of 2 accepted

The frozen 0444ceee candidate was run once on H5 then H6, without inspection-driven changes or replacement. The public preregistration/freeze was committed before sample parsing. All 3,452 raw first-run files were hashed before source-image diagnosis. The original selection registry and candidate implementations remain unchanged. Future work on these pages is seen-page diagnosis.

Both pages reached native region analysis/rendering but were refused by the paragraph builder with `unresolved native inline units`. H5 had 10 unresolved units; H6 had 5. Neither reached the native glyph bridge or the 28 px / DPR 2 reader, so there is no 20/28 px visual reading improvement, formula-completeness pass, or completed-page time from this batch.

Separately, original-position masked native replay failed by 49 pixels (maximum channel delta 56) on H5 and 3 pixels (maximum delta 8) on H6. No duplicate masks were reported. The local unit-render tests themselves reported zero support-color failures: that does not establish complete support. The page-level check correctly exposed content-support missing from those local masks. These differences were not waived as anti-aliasing.

## Actual first attempts

H5: 29.085 s wall to refusal; 26.017 s request-family CPU; 695.8 MiB sampled family-plus-supervisor RSS. H6: 34.433 s wall to refusal; 34.002 s request-family CPU; 706.7 MiB sampled RSS. Cold detector inference, extraction and preprocessing were included. Input transfers were separate: 13.214 s / 103,295 range bytes and 5.560 s / 118,386 range bytes. Dependency acquisition was already complete; filesystem cache was not flushed.

Measurement defect retained: the request family was pinned to one CPU, but the high-frequency external supervisor was not pinned to that same CPU. It used an additional 4.489 / 5.208 s CPU. Therefore these are not certified strict one-CPU whole-system benchmarks. Both requests exited normally, so `wait4` includes their waited descendants; the same frozen supervisor would under-report unreaped descendant CPU after some timeout kills. A future instrumentation-only version must fix that and disclose it. No budget-success claim is made from early refusal.

## Post-blind source diagnosis

The actual full source images were inspected after both first attempts were preserved. Source content is private; the descriptions below avoid paper-specific tokens and contain no source text.

1. H5 contains a multi-line display equation. Its region proposal was geometrically bounded and logically closed, but the prior verifier rejected it solely because one native unit looked like a word with more than two letters. Some of those character mappings are not certified Unicode. This makes a semantic/word-shape heuristic block the geometric native-preservation route. Several resulting unknown/small mathematical glyphs had no admissible anchor.
2. H6 includes a normal small-type horizontal metadata line. All five words are below the global body-font anchor threshold, so the entire line was treated as possible scripts and could find no larger nearby anchor. A complete small-type line needs local line evidence, not a globally large font. The same page also contains 46 rotated sidebar glyphs. Native orientation is available from PDFium but was discarded by the frozen inventory; the horizontal ordering layer produced 38 native-index boundary conflicts. Those conflicts alone are not a semantic order oracle, but the rotated text needs an explicit direction-aware representation rather than single-glyph horizontal lines.
3. The missing support was traced to two text objects in H5 and one in H6. Their local transparent renders were stable across the tested crop paddings. A separate full-device-canvas transparent native render nevertheless contained real nonzero alpha at every one of the 49 / 3 missing live pixels. Thus local crop stability does not imply equivalence to the global native raster grid. The next source-support mechanism must use or verify that global reference, not fill arbitrary bbox pixels or relax the exact source check.
4. A second H6 equation proposal was rejected after logical interval closure pulled a distant equation number beyond the allowed prior margin. This is a legitimate model-box/interval conflict to handle structurally; the model box is not GT. It must not be repaired with a paper-specific identifier.

## Next candidate contract, not a result

Use a new isolated version: global-canvas native alpha or exact verification against it; local scale/baseline and direction-aware line anchors; bounded formula-structure evidence which never treats unknown character candidates as prose. A separate adjacent equation-number child may be admitted only with source-interval closure, unique row association, empty intervening content and fixed size/extent bounds. Preserve source-order draw actions and every native glyph. Include authored small-body vs script, mixed-baseline formula, distant number, rotation and wrong-prior negative controls before seen-page diagnostics. These proposals have not yet been implemented or passed.

No new CI, browser test, text selection/copy test or zoom-interaction test was performed. Paper-first scope still excludes handwritten annotation work. No complete-paper/generalization acceptance is claimed.
