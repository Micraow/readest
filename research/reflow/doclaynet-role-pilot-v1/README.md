# Real native-line role pilot: frozen design

This pilot uses a bounded subset of official human-annotated DocLayNet to compare one small geometry/font/context role classifier against a fixed geometry/PP-label baseline. It does not yet establish reflow, source conservation or formula-number ownership quality.

The selected 30 documents are frozen before inference: 12 training, six calibration, 12 test. Test collection groups are absent from fit/calibration; all document names are distinct and known earlier diagnostic paper IDs are excluded. Collection groups are source/style strata, not proof that upstream pretrained PP-S never saw a page or that near-duplicates are absent. One Chinese-law test document was available, so the pre-inference sampling plan uses one Chinese and one Japanese law source instead of two Chinese documents. Actual page language still needs inspection.

Source and rights: [official DocLayNet](https://github.com/DS4SD/DocLayNet), [CDLA-Permissive-1.0](https://github.com/DS4SD/DocLayNet/blob/main/LICENSE). The official ZIP objects are read only through bounded HTTP ranges with stable ETag and per-entry CRC/SHA checks. Whole 28GiB/7.5GiB archives are never downloaded. All source pages and annotation data stay local; this repository contains original glue, source identifiers, configuration and aggregate results only.

The 565MB uncompressed training annotation file is streamed from its 82MB compressed entry. Download budget is256MiB total; local data budget512MiB. No model or runtime package was added. Line targets aggregate human layout boxes, requiring90% glyph-role agreement. Mixed/unlabeled lines remain in evaluation and abstention counts. Learned logits do not override missing source evidence.

Execution status is recorded separately. Design/code publication is not a successful experiment or quality result.
