# Local geometry candidate: useful repairs, not an accepted reader

This isolated candidate follows the failed first blind batch. H5/H6 are now seen diagnostic pages; their original blind failures remain unchanged. No further holdout was opened. No old implementation/report was edited, no model downloaded, and no CI or browser run was started.

## What actually improved

- Actual source-paint replay is now exact on both pages: changed pixels 49→0 and 3→0. Full integer-device native alpha is generated before array cropping. It is not inferred from agreement between two small crop paddings. Original native geometry, paint order, observed alpha and ambiguity rejection remain required.
- Unresolved native units went 10→0 and 5→0. Unknown Unicode is separated from visual shape evidence. Small, coherent native baseline runs can anchor a line without being as large as the body median. Adjacent small scripts and ambiguous isolated glyphs still have negative controls.
- Rotated text is grouped by native direction and closed source interval before alpha ownership partition. The second page's 46 rotated glyphs remain one local auxiliary group, with original geometry. Upright conversion is not implemented. Native-index boundary conflicts went 38→0; this statistic is not itself semantic-order proof.
- Both pages retain a one-to-one native-unit ledger (316 / 749). Native word-resource paints are separately conserved (1,384 / 4,091). Display-math proposals now use positive geometry, script density and native rules rather than unreliable alphabetic strings. Model boxes remain weak priors; conflict/extent/interval checks can refuse them.
- Repeated source baseline spacing per column is used for paragraph leading, with explicit font/indent constraints. On the first page this reduced the former source-line-per-paragraph behavior from 23 paragraph blocks to 11. It did not fix every paragraph boundary.

21 original geometry controls pass, including wrong-prior/citation, mixed direction, foreign source interval, small standalone prose versus adjacent script, equation-label interference/ambiguity and repeated wide leading. An authored native PDF replay is also exact. Its first control attempt had 92 ambiguous rotated pixels; that failure and the failed initial integration attempts remain private evidence. Grouping direction before partition, rather than trying to merge already-quarantined files later, resolved that control. These small controls do not establish paper generalization.

## Complete visual review, and remaining failures

The full source pages and all 18 output bands at 390 CSS px, 20 px / DPR 1 and 28 px / DPR 2 were actually inspected. The second page's main reading flow goes through the full-width front matter, left column, then right column with equations; there was no observed column interleaving. Its small metadata line is present. Native formulas and the rotated sidebar are present as bounded local assets.

Reading acceptance remains false. Some source first-line indents exceed the old backward-return allowance and still cause breaks inside paragraphs. Other local line/paragraph splits also remain. The first page has one detached equation label. Its wide multiline equation becomes too small and visually weak at the default fit-to-width scale, especially 20 px / DPR 1. The second page's preserved rotated sidebar creates a long, impractical tail. Source-line hyphens remain inside rewrapped words. These are actual visible defects, not merely missing score annotations. The tiny first-page equation cannot be certified symbol-by-symbol from its fit-to-width appearance alone.

Both output sizes have no measured contour/asset bbox escaping its canvas and no inter-token bbox intersection, but subpixel contours can exceed historical raster-crop frames. Those strict old-frame failures remain reported. A unique glyph/event ledger and source replay do not prove exact mixed-engine pixel completeness after reflow. Selection/copy and local-zoom interaction are still unverified/unimplemented, and no arbitrary dark-backdrop support is claimed.

## Real whole cold request: both fail 60 s

The newly versioned supervisor pins itself and all request processes to the same single CPU. Linux process-local subreaping captures CPU for orphan descendants after timeout. Normal-child and killed-grandchild controls verified both paths. This fixes the old monitoring defect without editing the old records.

New-process cold requests included live offline PP-S import/load/raster/inference, all source processing, native glyph capture (including its existing QA), bridge, paragraph data, requested target-grid assets and initial reading output. No source/model-prediction plan was supplied; filesystem caches were not flushed.

- H5: stopped at 60.103 s wall; request CPU 52.386 s plus supervisor 5.495 s = 57.882 s total; sampled RSS 696.1 MiB. The native/model phase took 49.409 s and the request was interrupted while building target-grid images.
- H6: stopped at 60.091 s wall; request CPU 52.200 s plus supervisor 5.084 s = 57.284 s total; sampled RSS 685.0 MiB. The native/model phase took 41.046 s and the request was interrupted during paragraph-payload preparation.

Neither completed a cold page under budget. Monitoring overhead is material and is not hidden. Shared host load and I/O conditions are recorded; timing differences between samples or prior runs are not attributed solely to algorithm changes.

The reviewed previews came from explicitly separate cached diagnostic stages. H6's earlier cached reader attempt also hit 60 s; the final incomplete local-image request was then regenerated in a 5.000 s diagnostic continuation using only verified prior requests. Both final visual QA renders reused native plans/capture/assets. Their 9.040 / 11.881 s costs are not complete-page time. No group-average or sum of conveniently selected phases is presented as a successful page latency.

## Next bounded work

Correct paragraph continuation using native column/first-line structure rather than increasing one source-specific threshold. Separate formula core and numeric-label layout while preserving each local geometry; test actual fit-scale raster clarity, not only a nominal 28 px target. Profile global alpha, model startup, bridge correspondence and target assets before optimizing; any reduced capture/renderer path must remain paired with the current complete evidence path. Keep the strict source drawing gate and all blind failures.
