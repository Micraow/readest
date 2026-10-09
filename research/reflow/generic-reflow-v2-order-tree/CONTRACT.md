# Reading hierarchy contract (registered before the next old-page diagnostic)

The previous native-ink checks are not reading-order acceptance. This layer owns **region → column → paragraph → inline interval** order and is independent of native paint/resource ownership. Old D4/D5 are mechanism diagnostics only; no holdout is opened.

## Input/output

- Input leaves have a stable ID, page-coordinate bounds, visible character-index membership, paint-owner references and a provenance/role confidence. A native tag or model region is optional, versioned, removable evidence. A predicted region never overrides missing/duplicated ink or continuous-interval guards.
- A page tree has vertical bands for cross-column blocks, columns inside each band, paragraph/figure/table/display-math blocks inside each column, and inline units inside a paragraph. Unsupported overlapping layouts return an explicit ambiguity, not a whole-page image.
- The tree's leaf flattening is a bijection of the input leaves. Each node's emitted descendants form one continuous output interval. This is a structural certificate only; native text-index contiguity and semantic order are separate checks.
- An approved column must finish before the next column begins. A spanning title/figure's band must occur between its above/below bands. A graphic owns enclosed text only after geometric containment and bounded logical closure; arbitrary nearby body text cannot be swallowed.
- Normal paragraph continuation must survive source line breaks. Inline sub/superscripts and fractions must keep relative geometry inside bounded groups. Ordinary following words must remain outside such groups; the observed short-word overmerge is a required negative regression.
- Source index order, geometry, native tags and model priors may disagree. Record conflicting pairs and provenance; do not rename a self-consistent generated order as ground truth.

## Measured gates

1. Hand-authored rectangular mechanism cases, not a synthetic PDF corpus: ordinary two columns; full-width title then two columns; full-width middle figure separating column bands; one embedded figure in a column; overlapping/floating cross-column region that must abstain; duplicate/missing leaves must reject. Exact expected sequences are registered in the unit tests before old-page diagnosis.
2. Build trees on the old pages. Independently inspect source and full reading output, not only a local successful crop. Report region containment, column transitions, paragraph continuation, source-index conflicts and unresolved table/math blocks separately.
3. Native ownership, compositing, source-support checks continue to apply after a region is moved. Pixel equality does not satisfy gates 1–2, and order invariants do not satisfy visual completeness.
4. Any unresolved column/table/math role, interleaved region, unowned figure label, long-body lock, selected text with uncertified Unicode, or unreadable complete output fails reading acceptance. No hidden whole-page fallback.
5. A layout model is optional. Compare with/without it on identical already-seen pages, including model download/runtime/package size, cold 1-CPU CPU/RSS/page cost, false regions and readable-output gain. Add no default dependency unless there is measured net benefit. Native tagged structure may be used with the same provenance/conflict contract.

## Initial deterministic strategy and limits

Use protected local blocks plus reconstructed source-line envelopes as leaves. Try a genuine empty vertical gutter first (columns); otherwise an empty horizontal band (spanning structure); recurse. A simple single-column remainder can sort vertically only when its leaves do not overlap in a contradictory order. A floating/crossing arrangement without a safe cut abstains. This avoids the previous universal y-sort that interleaved left/right columns. It does not classify a borderless table or repair unprotected math by itself. Those unresolved roles are explicit, not an excuse to count a tree as a good reading result.

All distances/bounds belong in typed config, and each split or refusal has a reason trace. No page ID, document title, exact token or font-family lookup is allowed.

## Scope amendment 2026-10-09 (user-directed, not an algorithmic gain)

Current priority is academic papers: printed body text, mathematical glyphs/strokes, figures, tables, ordinary/mixed column layouts, local enlargement and font-size changes. Ink annotations are outside this current evaluation scope. The prior annotation experiments remain historical evidence and annotation support is no longer a current reading gate. This does not remove printed glyphs, equations or table rules. Nonacademic/Chinese registered holdouts stay unopened for future work; paper holdouts must still be from unseen source documents. No scope reduction is counted as a model/algorithm improvement.
