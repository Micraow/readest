# Cached layout-region weak prior, before integration

Reuse the **already-local PP-DocLayout-S** detector output from the frozen experiment. This is not a new model score or a repeated reading-order experiment. Candidate use is confined to table/chart/display-formula regions. Ignore native text/heading predictions for now because old D4 contains overlapping text boxes. No private content is sent to a model service.

- Record input PDF and cached-prediction hashes, native image dimensions, model files/hashes and frozen runtime costs. A cached-only experiment cannot claim measured cold model+page end-to-end cost.
- The adapter can be disabled. A candidate below the typed confidence threshold is ignored with a reason; absence of a model produces no candidates. Labels are hypotheses, never GT.
- Conflicting overlapping region candidates are rejected rather than resolved by a page-specific rule. A region must own a bounded continuous native visible interval after whole-unit closure, keep paint membership exact, and include all its enclosed native text. Any out-of-bound closure rejects.
- A proposed table needs independent native structure evidence (repeated row/column alignment or table rules); a proposed graphic needs native nontext paint evidence. Local preservation may not absorb a page/whole body.
- Full source-support rendering, complete reading screenshot and regional order checks remain mandatory. Inference confidence cannot waive them.
- Negative tests include disabled/missing prior, low confidence, contradictory overlap and a text-only rectangle mislabeled as a table. Thresholds are fixed before this use on D4 and are not selected from a holdout.

Mechanism amendment after the seen-page diagnostic: a physical table rule may be a thin native image, not only a stroked path. The original predicate rejected the real table's raster rule despite strong row/column alignment. A typed aspect/height test now recognizes any native thin paint primitive. Formula prose checks use only dominant-size alphabet runs so smaller script letters cannot create a fake long ordinary word. These changes are diagnostic-driven development, not frozen holdout evaluation.

## Later live probe

After the cached diagnostic, the same existing model files were invoked locally with a fresh PDFium raster. This is separately costed in `COSTS.md`; the cached diagnostic and historical MuPDF raster remain separate evidence. The predictor process exits before native work. No OCR recognizer or reading-order head runs.
