# Seen compact-fraction and paragraph repair

The frozen H7 holdout remains **failed 0/1**. The registered failed recovery and
previous 60-second continuation timeout are retained. This report is a new,
explicitly seen-data diagnostic, not a cold-request or independent-holdout pass.

## General rules

A compact native fraction now supplies an alternative positive structure witness:
a bounded horizontal paint with projected native support above and below it,
a local script, and a bounded candidate height. The existing 8% global script
fraction threshold is unchanged. No paper name, words, font family or page-specific
coordinates participate. Negative controls reject missing numerator/denominator,
long separators, nonhorizontal/unowned paint, baseline-only text, distant scripts
and multirow extent. Input-order and character/font mutations preserve decisions.

For paragraphs, repeated same-column native rows estimate normal ink clearance.
A taller inline object may justify extra baseline distance only while the normal
ink clearance, font, column, indentation and absolute gap bounds still hold.
Extra paragraph whitespace, ordinary-height gaps and insufficient evidence refuse.

The existing independent formula-label association is now reachable because its
core passes the compact-fraction proof. Its original unique row, column, empty
corridor and continuous native-source interval gates remain. Numeric-label syntax
also rejects unmatched parentheses; a label is not guessed from unknown Unicode.

## Reproduction and evidence

Both public helpers were executed from current source, separately with an external
60-second process cap. `prepare_seen_plan.py --overhead-support` reacquired native
geometry from the existing verified fixture and reused cached model boxes. Its
recorded stages total 36.57 seconds. `continue_verified_reader.py` consumed that
verified plan and completed all stages, including whole-reader rendering, in
24.76 seconds of recorded stages. These exclude process overhead and are **not**
one end-to-end benchmark. No new model inference occurred. The rebuilt payload
is byte-identical to a separate continuation from the earlier equivalent plan.

Exact source replay, resolved order, independent source support and native glyph/
paint conservation pass. The result has 16 blocks and 372 grouped native units;
the smaller unit count reflects grouping, not deleted content. Text mapping has
341 eligible and 26 refused tokens. Copy across uncertain content stays blocked.

All four visual bands of the 28 px/DPR 2, 390 px native Canvas render were reviewed:
the radical/radicand stay attached, the two unwanted body splits are removed, and
the equation label belongs to the formula block. At 320/390 px it follows at the
right edge within that block; at 800 px it shares the core's row. All nine 20/24/28
px × 320/390/800 px placement cases stay within the canvas. The 28 px render has
no undersampled local images.

The actual shipped entry imports the new private bundle, copies eligible text,
refuses uncertain text and clears selection on font changes using jsdom plus
native Node Canvas, with zero network attempts. The old H5/H6 candidate still
matches all 30 native reference blocks exactly. Neither check is browser evidence.

## Limits retained

Reading acceptance remains false. Source line-end hyphenation is preserved, not
semantically repaired. A footnote contour-box contact persists at 20 and 28 px;
38 vector contour boxes extend outside their source token boxes, though none
extends beyond the output canvases. These geometric facts do not prove mixed
native-image/vector pixel ownership. Real browser selection, clipping/compositing,
clipboard behavior, arbitrary PDFs and the full Readest app remain unverified.
All H7 source, glyphs, images and populated bundles stay outside public Git and
the distributable private allowlist. Only non-content diagnostic records are added.
