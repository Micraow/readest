# Real candidate-role pilot: learnable signal, failed acceptance gate

One 144-parameter softmax classifier was trained on 646 role-labeled native lines from 12 documents, with six different calibration documents and 12 source/style-held-out test documents. Features use native geometry/fonts, local context and the existing PP-S candidate scores. Source documents are distinct across partitions; held-out collection groups are absent from fit/calibration. Upstream PP-S training overlap remains unknown.

On 1145 test native lines, the fixed geometric/PP-label comparator has 750 correct role assignments, 205 wrong or unverifiable accepted assignments and 190 refusals. Unrestricted learned prediction has 1031 correct and 114 wrong/unverifiable, with no refusal. Its accepted-error fraction is 9.96%; a descriptive independent-line Wilson95% interval is 8.35–11.83%. Lines cluster by document, so that interval is not a certified document-level risk bound. The two comparators have different acceptance counts; accepted-only accuracy is not a fair coverage comparison by itself.

The model proposes 21648 of21922 annotated body glyphs as body, but also proposes185 glyphs inside Formula annotations,92 auxiliary glyphs and1685 other-role glyphs as body. The geometry comparator proposes20005 body glyphs, with1241 Formula-region and92 auxiliary glyphs falsely body. Formula annotations can contain verbal prefixes, so these counts are role discrepancies, not proof that every such glyph causes a mathematical semantic error. Visual audit does confirm a fraction denominator being treated as body, which would be unsafe to use directly for unrestricted word wrapping.

## Refusal result

The pre-frozen calibration sweep is thresholds0.50 through0.99, requiring zero observed incorrect/unverifiable acceptances and at least20 accepted lines. No threshold in that declared set qualifies; the learned accepted coverage is therefore zero. This is a failed usefulness gate, not a zero-error success. Higher thresholds or class-specific policies were not tested and must not be inferred to succeed.

The two highest-confidence calibration mistakes, self-audited against the original source, confuse an appendix heading and a section heading with page-edge auxiliary content (confidence0.99150 and0.99076). This is a real hierarchy/role error, not a raster alignment failure. Training has only16 auxiliary lines, and the feature set does not describe full heading scope. No threshold or feature was changed after test inspection.

## Scope and resources

All mixed/unlabeled native lines remain in denominators. All annotated text/formula/auxiliary objects are counted, including those without native glyph support. This pilot does not evaluate source ink preservation, paragraph order, equation-number ownership or actual readable reflow. The role targets are human layout annotations, not complete mathematical structure.

All30 PDFs and matching PNGs were obtained from official immutable-ETag ZIP ranges, with entry CRC and SHA256 verification. Cumulative download153.5MB; no full30GB archive. A Chinese-source test page contains706 Han characters. The Japanese-law source page is an English translation and supplies no Japanese-language evidence.

The classifier fit takes0.024s; all feature extraction, fitting and evaluation take2.83s with102200KiB peak process-group RSS. The same frozen PP-S detector takes20.44s for30 pages,585628KiB peak; individual pages stay under60s. One CPU affinity is enforced, which does not prove an exclusive physical CPU quota. No VLM, new model download, paid service or additional runtime package was used.

## Product conclusion and next experiment

This provides a cheap, reproducible role-learning comparator, not a production decision-maker. The user explicitly rejects whole-page image fallback as a reading experience. The next end-to-end test must make ordinary prose flow at phone width and keep only necessary formula/figure/uncertain local atoms in source form. The original page is an optional comparison view, never counted as successful reading output.

The favored next hypothesis is local constraints on each proposed split or line break: preserve glyph/visible-ink provenance, script/fraction dependencies and supported source order, and lock only the smallest uncertain neighboring atoms. A blank seam alone does not prove that mathematical or reference relations may be split. Avoid the current recursive rectangle union that turns one uncertain inline object into an entire protected paragraph. These are proposed operations; no new engine result is claimed here.

Original source/crops, raw annotations and trained coefficients stay local. Public files contain original code, frozen configuration and aggregate measurements. Official data source and license: [DocLayNet](https://github.com/DS4SD/DocLayNet), [CDLA-Permissive-1.0](https://github.com/DS4SD/DocLayNet/blob/main/LICENSE).
