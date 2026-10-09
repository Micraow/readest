# Existing model, direct backend result

All twelve fresh-process A-B-B-A runs (authored PDF, seen H5, seen H6) completed.
Native page PNGs and the ordered final class/score/coordinate records are exact
within each group. Four authored tensor preprocessing cases are array-exact;
postprocessing matches on 410 authored candidate boxes, empty input and two
unsupported-mode refusals. No model or dependency was downloaded or updated.

Model stage wall seconds, old/direct/direct/old:
- Authored PDF: 23.285 / 8.453 / 6.266 / 18.189
- H5: 23.950 / 10.952 / 10.658 / 19.516
- H6: 21.145 / 4.825 / 5.082 / 16.526

H5 total accounted CPU: 23.254 / 10.626 / 10.111 / 19.479 seconds.
H6: 20.750 / 4.587 / 4.810 / 15.710. Supervisor runs on the same CPU and its cost
is included. H5 direct peak family+supervisor RSS 454.7/472.3 MiB versus old
636.8/623.1; H6 direct 453.5/471.8 versus old 608.6/642.6 MiB. Every load reading
and run is in RESULT.json. OS page cache was not flushed. Variation is substantial;
the evidence is consistent reduction, not a guaranteed speedup factor.

This removes broad PaddleX application startup from this path. The same existing
Paddle 3.3.1 runtime, model, CPU kernels and graph options remain. Paddle still
occupies roughly 716 MiB installed; this is not a lightweight mobile deployment.
The optional model remains a weak region prior. Native paint/interval gates still
validate its proposals. A model-stage improvement is not whole-page acceptance.

Initial failures retained privately: a supervisor CLI option was placed after a
REMAINDER positional argument, so no model was started; the first direct run
produced equivalent H5 predictions but failed serializing a NumPy int64 trace
count. That count was converted to Python int. An invalid-box skip discovered
in reference source review was added before the authored and paired comparisons.
No scores/boxes were tuned to a page, and no old result was overwritten.

Original adapter code is config-driven and explicit about supported operations.
Compatibility with the Apache-2.0 PaddleX reference is documented in CONTRACT.md
and exact installed reference/model hashes are recorded in PROVENANCE.json.
Both original and direct output remain private. No new holdout and no CI run.
