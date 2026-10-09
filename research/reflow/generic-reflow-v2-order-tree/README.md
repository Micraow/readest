# Bounded regions and hierarchical paper flow

Status: **seen-page reading improvement; not accepted generic paper reflow** (2026-10-09). This is an isolated follow-on to `generic-reflow-v2-inkownership`, not an alteration of that checkpoint or the closed `local-break-constraints-v1` experiment.

The current user scope prioritizes papers and excludes handwritten/ink annotations from acceptance. Printed glyphs, formula strokes, tables, figures, and captions remain mandatory. Historical annotation failures remain documented. The change in scope is not an algorithmic gain.

## Concrete mechanism

1. Native ink ownership and bounded local paint closure retain original printed content. Enclosed native text belongs to a graphic only after containment and logical-interval checks. No whole-page fallback is a successful reading result.
2. An optional PP-DocLayout-S region prior proposes table/chart/display-equation regions. Its labels are not ground truth. Confidence, contradictory overlap, native table structure, whole-unit/continuous native interval closure, and area/height/character caps can reject a proposal. Missing/disabled priors add no regions.
3. A typed, traced region tree prefers genuinely empty column cuts. Where a span blocks them, take the first empty horizontal barrier and retry columns recursively. Crossing/ambiguous regions abstain rather than interleave by global y-order. Parent descendants occupy continuous output intervals.
4. Native source-line envelopes associate smaller scripts and unknown-mapping glyphs geometrically. The bounded fraction rule takes the nearest numerator and denominator rows, not every nearby row. It cannot assume extracted Unicode equals a native painted symbol.
5. The reader groups small continuous native intervals using integer pixel copies with no raster resize. Paragraph candidates join consecutive source lines in the same tree column by baseline/indent conditions. Independent native units appear once; this is an accounting gate, not semantic completeness proof.

Every threshold is in typed configuration and output traces. No paper IDs, literal scientific terms, named fonts, or particular formula strings select behavior. Generic rules and their diagnostic-driven changes still need source-disjoint validation.

## Current old-page diagnostic

D4 is a development page seen repeatedly, **not a holdout**. Both historical cached regions and a fresh local PP-S invocation lead to 67 tree leaves, 8 paragraph blocks, 3 protected blocks, 707 native units, and 45 inline/display bundles. The fresh region scores were 0.833 formula, 0.785 table, and 0.726 chart. Full source-position replay and every final local unit's tested native support matched their source reference. Original source and output were visually inspected through the entire page: left table/caption and body/equation/section finish before right figure/caption/body. The previous catastrophic column interleaving is visibly improved.

That finding is narrower than a full acceptance claim:

- Cross-column prose continuation is not yet resolved around floats: on D4 a sentence ending at the left-column bottom continues below the right-column figure/caption, but those floats interrupt it in current output. A correct column order alone does not make this paragraph continuous.
- Source-line discretionary hyphens and awkward justified gaps remain in reflow; some math can wrap awkwardly.
- Unknown native glyphs retain their visual paint; this does not certify their Unicode. Math bundles deliberately have no guessed selection string. Known-word selection lacks a complete tested semantic-space/copy contract.
- The new tree preview has no validated font-size control or local-zoom UI. Static 20px and 28px layouts are different generated tests, not successful interaction tests.
- Assets remain 2 source pixels per PDF point. The approximately 9.96pt body gives only 0.71 source samples per CSS pixel at 28px/DPR1, 0.36 at DPR2. CSS enlargement is not native rerasterization.
- The fitted table remains small. Dark-theme adaptation and arbitrary-backdrop compositing are unsupported; the supported preview retains the native light backdrop.
- 642 actual DOM image units/requestable PNG resources remain. They total 872,809 encoded bytes and 3,280,036 decoded RGBA bytes; HTML is 186,497 bytes. Loading costs are not measured by static layout.
- Visible pixel correctness at one grid cannot prove all-scale completeness. Source-index coverage cannot prove reading completeness.
- No registered holdout was opened. No new remote CI, Android, or real browser result is claimed.

See `COSTS.md`, `FAILURES.md`, `PROVENANCE.md` and the pre-implementation contracts. Private evidence contains full traces, source comparison, 390px screenshots, and a region-by-region review; public files contain original code and aggregate findings only.

## Reproduction

Run the 19 original mechanism tests in `code/test_*.py` and the 10 prior ownership tests. Use `code/measure_page.py INPUT.pdf PRIVATE_OUTPUT --model-dir LOCAL_PP_S_DIRECTORY` with one-core thread settings for a cold offline pipeline. The wrapper enforces a 60s wall deadline and 1GiB sampled process-family RSS, includes model child startup/exit and all native phases, and explicitly excludes browser rendering. Existing local model/runtime installation is required; this code does not download weights.

The optional cached mode requires prediction file and original raster width/height; it cannot count as cold model performance. Omit a model for explicit abstention when geometry alone cannot safely resolve regions.

Acceptance remains false until complete real-paper readability, printed content, interaction, target-size sampling, platform costs, and untouched source-document holdouts are tested with a frozen candidate.
