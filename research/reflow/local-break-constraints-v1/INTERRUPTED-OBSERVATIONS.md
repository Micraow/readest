# Readest frozen local-break experiment: observed results before execution-environment reset

Recorded 2026-10-09 03:35 UTC from visible tool outputs and direct image inspection. This is an interrupted audit, not a complete quality report. Raw files became unavailable at 03:34:37 when the executor reported a key change; the workspace then showed a nearly empty 32GB filesystem. No reset cause is established.

## Durable baseline

Research branch: research/reflow-20261008, Micraow/readest. Source freeze 9f6b88cfa9b15169f7d739b10c350efa261e19dd was pushed successfully at approximately 03:24 UTC and independently read back with git ls-remote. This SHA preserves the actual A/B implementation and the preselected twelve inputs/URLs/hashes. Historical source was not changed after observing held-out outputs.

The font-name-disabled E ablation was registered before any of the twelve pages was processed: replace only atoms.MATH with a never-match regular expression, then call the same run_page.py. All other detector, thresholds and renderer settings stayed fixed. E removes font-name hints, not fontsize/geometry rules or learned detector bias.

Known pre-test defect was retained: a small token with no proposed script parent is logged as ambiguous but remains unlinked in A; it may wrap freely. No repair was applied on held-out pages.

## Executions completed, quality audit incomplete

All twelve pages completed all 36 execution groups AB, E, CD with return code 0. Largest measured group wall time was 22.71141527299187 seconds. AB and E each prepare two alternatives and all six width/font settings; this is not per-arm latency. Detector timing must be added. A/B/E UI screenshots were being audited; only the first six A pages had been visually inspected at reset, with limited B comparisons. No complete twelve-page paragraph score, six-setting visual score or Android result exists.

Detector: cold initialization 2.8578915469988715 seconds; per-page raster/encode/inference 0.435–0.713 seconds. Whole detector batch 9.999226061991067 seconds, sampled sum-of-process RSS peak 650816 KiB, single CPU affinity. Initial attempt never entered inference because /usr/bin/time was absent. Next attempt failed loading a Paddle library under a 1GiB virtual-address cap before processing pages. Successful attempt used a 1GiB resident-memory supervisor, because virtual library mappings are not resident memory. These startup failures were retained locally, not erased.

A declared every source ink pixel assigned and shown for all twelve pages; this is an ownership/display-accounting observation, NOT semantic correctness. B source ink was assigned but three entire formula atoms were absent from its rendered HTML: D1-P1 formula (3.19), 12912 pixels; D3-P2 formula (17), 4188 pixels; D4-P1 formula (4), 3363 pixels. Each atom included both a formula dummy and its identifier. The renderer consumed the atom as its own associated identifier and then skipped it. This contaminates the intended same-relations A/B comparison, so no causal A-over-B quality gain can be claimed.

## Directly observed A failures and successes

- D1-P1: 425344 source ink pixels assigned, 340 A atoms versus 310 B atoms. A locked 56 words in islands versus B84; this is not a reflow percentage. First and third prose paragraphs contain islands spanning source lines and retaining ordinary prose; surrounding flow appears in wrong or interrupted sequence. Last long ordinary paragraph visually flows. Three displayed equations are local horizontal objects; screenshot clipping at the viewport right edge does not by itself mean source content is missing. B visibly omits the entire first equation as described above.
- D1-P2: four source prose paragraphs visually flow at390px/20px with a correctly positioned section heading. This is a limited single-setting self-review, not full-size/semantic acceptance.
- D2-P1: three prose paragraphs visually flow, displayed formula(13) and identifier remain together. Figure is enlarged such that the initial viewport mainly shows the left axis rather than the whole scientific trend; local horizontal access does not make this a good default object view.
- D2-P2: first prose and three numbered formulas appear in correct sequence, but the final paragraph is interrupted by an island containing the footnote/rule and part of its last prose line. Mechanical region screening incorrectly treated this as a candidate, demonstrating why screening cannot stand in for visual acceptance.
- D3-P1: first formula-heavy paragraph is fragmented into islands. A page-header number8 occurs between the bottom-left prose and its right-column continuation. Body text otherwise visibly flows, but this cross-column paragraph interruption fails the reading relationship requirement.
- D3-P2: source-column order is broadly followed in the A overview, and identifiers(15–17) remain present. No full glyph-by-glyph/math review was completed, so no pass is assigned. The B formula(17) omission was verified from output metadata.

## Mechanical screen, explicitly NOT reflow success

Official DocLayNet Text/List annotations produced95 source regions. Some are fragments of one paragraph; these must not be called95 complete paragraphs. All missed/rejected regions remained in the denominator. Positive screening meant only native IDs are present once, shown as body, with no detected multi-baseline alphabetic island within that reference region. It misses sequence errors and source-parent merging across reference regions.

A/B/E candidate counts were identical by this weak screen: D1-P1 1/4; D1-P2 4/4; D2-P1 3/3; D2-P2 6/6; D3-P1 7/8; D3-P2 14/16; D4-P1 0/5; D4-P2 1/6; D5-P1 8/11; D5-P2 8/8; D6-P1 11/11; D6-P2 13/13. These76/95 candidates are NOT a paragraph reflow score or a quality pass, and the font ablation having the same weak counts does not show output equivalence.

## Resource/storage and browser limitations

Repeated embedded atlas data in static HTML caused a transient evidence-disk overshoot above the planned200MiB. A content-addressed, byte-roundtrip-verified representation of generated HTML and identical atlas PNG hardlinks reduced the total experiment directory from over500MiB to248MiB before reset; that total also included prior development controls. Every compacted HTML recorded its originalSHA and was reconstructed byte-identically before CSS rendering. This was storage-only; the algorithm was unchanged. No large model/data download was added.

New Chromium validation branch commits did not produce an Actions run in the last verified listing; only the old5448fd5070d7332dc8dae40de0ce2669b7ac0abd run37870213958 was successful. That old success is not evidence for the new engine. Local WeasyPrint screenshots were explicitly not browser QA. On a dense page local layout/raster QA took about38 seconds; no claim of mobile renderer speed was made.

## Next falsifiable mechanism, not yet executed

Preserve this failed frozen batch. A repair stage should first enforce that every displayed atom appears exactly once even when association endpoints resolve to the same geometry component, and that source-order interval closure is respected by the renderer's actual event ordering. Semantic association must not hide geometry atoms. This is a general invariant, not a paper-specific patch. Source-line/paragraph continuation and header/footnote placement still need independent constraints. A subsequent batch needs new documents for generalization; these twelve are now seen.
