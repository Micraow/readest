# Indexed bridge: identical decisions, measured stage benefit

All six authored test methods pass, including 3,006 exact-cell/adjacent-float cases plus seeded perturbations, duplicates, zero tolerance, nonfinite and extreme-coordinate behavior. The full JSON decision outputs were byte-identical across old/indexed/indexed/old fresh-process runs on all three already-seen inputs. Native correspondence, refusals and unsupported-glyph handling were not relaxed.

Measured wall seconds for A-B-B-A, including process startup, input parse, bridge and JSON output:

- D4: 3.810, 1.549, 1.205, 3.717
- H5: 0.850, 0.380, 0.409, 0.770
- H6: 15.097, 3.201, 0.927, 4.561

CPU seconds were also lower in each indexed run; exact pairs and host load are in RESULT.json. H6's large between-run variation is retained rather than hidden behind a single average. The corresponding H6 CPU sequence was 11.452, 2.689, 0.882, 4.343 s. Same-core supervision was used; file caches were not flushed. This is evidence of a useful bridge-stage reduction under the observed runs, not a guaranteed speedup factor on every device.

The optimization is isolated and has not yet been integrated into/retested as a completed cold page. Inference startup, native processing and target-grid assets still matter. The earlier full-page 60 s failures are unchanged. No new model, network dependency, OCR, browser test, CI or holdout was introduced.
