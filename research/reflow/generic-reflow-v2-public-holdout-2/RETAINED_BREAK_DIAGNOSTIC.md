# H8 seen reading repair: keep uncertain source marks at line ends

Eight already-supported source line boundaries now remain line boundaries in the
experimental reader. Their printed marks stay visible at the ends of lines,
instead of appearing inside a newly reflowed word. No glyph is deleted, no word
is reconstructed, and no uncertain Unicode is certified. The complete local
reader and the affected paragraphs were inspected against the source.

A naive forced-break variant produced one to four isolated prefix rows on five
of the six tested grids, and was rejected. The bounded line-balancing variant
has none on all six grids. The extra page height is 0.59%–5.08%. The title and
panel-label repairs remain visible; all 42 renders of unmarked blocks are
byte-identical to the preceding reader.

## Scope and evidence

The annotation reuses the existing `hyphen_relation` evidence and its unchanged
native geometry, lexical-candidate, source-order and source-interval gates. It
adds only eight `retained_source_break_after` flags and an explicit
`native-retained-line-v1` policy. Existing fields, resources, token order, gaps
and mapping data remain identical. A nonzero existing separator or incompatible
source box keeps the old layout. Cross-paragraph reconstruction is not attempted.

The layout minimizes squared unused row width between the retained boundaries,
without changing native token dimensions or paint. It does not split a
negative-gap native pair. Work is capped at 100,000 candidate intervals per
marked block and fails closed on an impossible layout. The existing bounded
singleton behavior is preserved: a long word may use existing right padding but
cannot leave the canvas. Unmarked readers use the exact old greedy path.

The bundle validator requires the explicit policy, boolean marker, paragraph
scope, zero separator and a following token on a later source row. Malformed
markers fail before import. The empty offline entry is regenerated from the
shared module and still embeds no paper content.

## Completed gates

- Six actual native Canvas grids: 20/24/28 px × 320/390 px at DPR 2.
  All eight boundaries stay at row ends; no one-token prefix rows, out-of-canvas
  native contours/assets, or undersampled images were found.
- All 529 source units and 3,072 glyphs are retained. 2,806 vector paints and 16
  native image composites pass the unchanged exact conservation/support audit.
- The text map is byte-identical: 454 eligible / 27 refused tokens. Actual shipped
  module tests select across all eight marked boundaries and confirm copying
  remains refused without writing a clipboard payload.
- The actual entry still opens the full native figure, returns to its source
  region/whole page, and cleans/restores focus on closing.
- All 30 H5/H6 native reference blocks remain pixel-identical. Their import,
  copy, cache-return, error-preservation and source-fallback checks still pass.
- Eight annotation, 12 layout and eight bundle-marker controls pass. The selected
  Python suites total 230 passing tests; existing selection/mapping/interaction,
  formula layout and 27 hostile-bundle controls were rerun.

These are local native Canvas/jsdom results, not real browser acceptance. No
model or extraction rerun is counted as a new cold request. The original H8
blind result remains **0/1** and all previous failures remain unchanged.

## Remaining reading boundary

Whole-page reading acceptance is still **false**. One reference boundary with
an uppercase continuation does not satisfy the unchanged evidence gate and is
left alone. The eight unknown terminal mappings remain refused for copy. Wide
figures need local focus. Browser compositing, selection/clipboard behavior,
full application integration and mixed-engine pixel ownership are still not
verified. The separate native-clip replay comparison retains its 20-pixel
mismatch; observer and serialized replay differences are zero. Source-PDF
fallback remains the authoritative recovery path.

## Reproduction

Start with the hash-verified, privately acquired seen spatial/title reader.
Run `retain_source_breaks.py READER PLAN EVENTS BRIDGE OUTPUT_READER`, then the
existing source-conservation audit and six-grid renderer. Regenerate the empty
entry with `build_entry.py`. `audit_retained_layout.mjs` checks row-end and orphan
conditions; `test_retained_break_runtime.mjs` checks actual entry copy refusal.
The source-break bundle and pure-layout controls cover the explicit marker.

Only code, source-acquisition metadata and non-content measurements are public
or included in the standalone handoff. Original H8 paper, text, glyph resources,
rendered images and populated bundles remain excluded.
