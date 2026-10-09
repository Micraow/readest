# Complete native-resource paper reading prototype

This isolated follow-on to e2dc640a moves beyond a local glyph replay to complete paragraphs and the already-established column/float flow of one previously seen paper page. It is not unseen-document validation or a production Readest integration. No frozen earlier directory is changed.

## What is actually improved

The final private prototype has 7 prose/caption paragraphs, 3 protected display objects and a source-page-number block. Its 660 reading tokens consist of 638 native vector tokens and 22 bounded native images. All 707 earlier source units appear once. Text drawing uses 2,690 native glyph paint references with 197 shared contours, 404 affine programs and one shared solid paint state. Native font character identity is used for drawing; candidate Unicode is never substituted for a glyph.

A conservative cross-renderer bridge only accepts mutually unique source origins/baselines within the declared 0.002 PDF-point bound. Ambiguous/unsupported/clipped correspondences retain the previous native representation. These are PDFium and PDF.js IDs, not a shared ID namespace. The bridge and source-unit count do not prove pixel completeness.

Old composite proposals are revised rather than allowed to lock long text runs. Whole existing native-word members are repartitioned by bounded script edges, including a same-script-row edge after a nested smaller prime. Scripted bases can then keep adjacent parenthesized arguments. All original source affine geometry and native paint references are retained inside each resulting group. Twenty-two old composites were repartitioned; no width limit was increased and no glyph was sliced. There are no document-ID, scientific-word or font-family exceptions.

Nine source-line hyphen separator decisions retain the printed hyphen but remove the extra word gap. When the first extractor reports an unknown terminal, an independent native Unicode candidate plus short-horizontal-bar geometry is used only as a traceable boundary hypothesis. It does not certify copy semantics or delete the glyph. Full dehyphenation is still open.

## Actual visual review and limitations

The same final payload was rendered and visually reviewed in full at 390 CSS px, font 20/DPR1 (5 strips) and font 28/DPR2 (8 strips). The review includes all paragraphs, the cross-column continuation, the observed base/script and function/argument failure sites, display equation/number, 16 table rows, both graphic panels, the full caption and final text. Earlier faulty versions remain private alongside the final evidence.

The complete page is not stored as a reading image. The HTML uses 11 paragraph/object canvases with reusable glyph paths and 22 local image resources, all embedded for the private prototype. It includes font-size and bounded local-image-focus code, but no browser was executed. The native Node renderer uses the same layout module. Text selection/copy are not implemented. Dark-background transformation, arbitrary local magnification, cross-page joining, mobile deployment, mixed-engine pixel equivalence and unseen-paper acceptance remain open.

A suspected remaining image/script problem was corrected during diagnosis: the true function-argument break was inside over-broad vector composites. A separate mixed candidate was an ordinary plus sign before an intact native fraction, where an operator-adjacent line break is permissible. The fraction was not missing a numerator or denominator. This rejected grouping is retained in the trace rather than forced into an unrelated script relation.

Old pixel-crop frames failed continuous-outline containment: 218 final vector tokens extend by at most approximately half a source pixel. The renderer does not clip to these frames. They are layout anchors; native contours retain separate paint bounds. At both inspected sizes, no contour/local-image box exits its canvas or intersects another token's box. This is geometric evidence, not mixed-engine pixel completeness. The earlier strict postposed-glyph replay failure is not silently converted to a pass.

## Resource/cost receipts

Final payload: 1,816,511 B JSON; 792,547 B gzip. Standalone private HTML: 1,824,037 B. Local PNGs: 673,633 B, decoded RGBA 15,028,916 B; their 6× sampling was regenerated using the existing native target-grid ownership checks. No per-word PNG is needed for the vector tokens. These resource statistics exclude preprocessing runtimes/model weights described in prior checkpoints.

The complete 27-source-unit local-image stage costs 23.749 s wall / 23.586 s CPU / 391.04 MiB. It reuses an existing ownership/flow plan. The final native reader process, including import/resource loading/layout/drawing and evidence encoding, costs 3.467/3.167 s and 109.91 MiB at 20/DPR1; 4.707/3.890 s and 145.82 MiB at 28/DPR2. One CPU is pinned; load varies and is recorded. These are cached-stage costs, not full cold-page times. There is no 60 s cold-page budget pass.

Twenty-two original Python controls and four pure-layout controls pass. Syntax checks pass. No new CI was run. Holdouts remain unopened.

## Reproduction and licensing

Reuse the source/ownership/order plan and exact PDF.js/native-canvas runtime recorded in prior private checkpoints. `bridge.py` and `prepare_reader.py` establish the conservative candidate mapping and packed representation. `request_local_images.py` regenerates needed local assets; `update_local_images.py` preserves their fixed source layout anchors. `refine_vector_components.py` and `flow_refinements.py` revise source-geometric relations. `render_reader.mjs` produces non-browser evidence, `audit_geometry.mjs` reports separate geometry checks, and `make_preview.py` packages the private prototype. `measure_stage.py` caps explicit stages to 1 CPU, 1 GiB and 60 s and labels reused preprocessing.

Original code follows the repository AGPL-3.0 license. Third-party pinned runtimes and license receipts are unchanged from the glyph-resource and target-grid checkpoints. Public files contain only original code/configuration and aggregate evidence. No paper resources, native glyph arrays, source text, images, private URLs or secrets are included.
