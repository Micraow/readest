# Tiny relation scorer: one frozen synthetic probe

This experiment isolates a learned relationship scorer. It is not a PDF parser, reflow renderer or detector. All formula candidates and numeric-token boxes come from an original source-authored geometry generator. Nothing from the ten prior paper diagnostics enters training. No pretrained model or paper content was downloaded.

The source and configuration were published before the sole run in commit `6b80c1be9b7e8f349dd00b9408943b99456547b2`. `CODE-FREEZE.json` and `RUN-STARTED.json` record unchanged hashes. Run `python run.py` in a fresh directory containing the source and `FREEZE.json`, with NumPy installed. The recorded runtime was Python 3.12.14 with NumPy 2.3.5. The guard prevents an accidental second run in the same directory. Deterministic seeds and `RESULT.json`'s data hash identify the generated data. Wall times can differ across hosts; floating-point libraries can affect last-bit values.

The task: for each numeric-token candidate, choose its formula parent or refuse attachment. Four training-layout families and two held-out families vary columns, margins, side of numbering, multiline height and vertical alignment. Header/footer/diagram numeric tokens have no formula parent. Parent IDs, family names, text and input order are excluded from the 24 features. IDs and input order are randomized. The 25-parameter logistic model uses one fixed fit; both methods choose rejection settings on the calibration partition only.

## Observed results

| Partition | Correct accepted / true links | Wrong / accepted | Rejected / all candidates | Entire page correct |
| --- | ---: | ---: | ---: | ---: |
| Calibration | 536/600 | 0/536 | 266/802 | 46/80 |
| New pages, known layout families | 531/600 | 0/531 | 269/800 | 44/80 |
| Unseen layout families | 571/600 | 2/573 | 235/808 | 57/80 |

The learned threshold was 0.8 with a 0.05 winner margin. The predefined synthetic gate passed on point estimates. Both held-out families still come from the same authored generator; this does not exclude generator-specific shortcut learning. This is limited evidence: the calibrated nearest-rectangle comparator found no setting meeting the <=1% observed risk and >=100 accepted constraints and therefore rejected everything. Its forced-choice owner accuracy was 63.83% on true held-out links; the learned model's was 98.17%. This weak geometric comparator is not k2, PP-S or a mature scientific parser. Do not represent the result as beating those systems.

Both accepted errors attached a right-column number to a left-column formula, with scores 0.938 and 0.905. A high score does not establish safety under a layout shift. The descriptive binomial Wilson 95% interval for 2/573 errors is approximately 0.096%–1.264%; dependence within pages/templates makes this an optimistic simplification, not a deployment guarantee. The 1% risk target is not statistically established. Full-page success was only 57/80, and only 17/40 on staggered double columns.

Training: 240 pages, 19,435 pairs, 1,800 positive pairs, 0.146 seconds. Inference including feature extraction: about 0.35 milliseconds per held-out page, using a batch of 80 tiny pages with 5–10 formulas each. Peak process RSS was 64,052 KiB, about 63 MiB. Full run was 0.59 seconds; temporary data and results occupied about 1.6 MB. The model has 25 learned scalars; weights plus normalization would occupy 292 bytes in FP32. The actual experiment uses float64 NumPy and Python, so 292 bytes is not runtime RAM or a measured mobile package size. No PDF decoding, image model, renderer, candidate extraction, graph construction for long pages or mobile runtime is included in the timings.

`AUDIT.json` confirms 480 unique page geometries, no cross-partition duplicate geometry, no duplicate formula IDs, every true parent in the candidates, and unchanged source hash. Candidate recall is therefore 100% by this oracle construction. It says nothing about real extraction/detector recall. Source-ink conservation, prose reflow, scientific color, readable font size and scans were not measured. They must remain separate gates.

Original synthetic data can be regenerated. This public checkpoint includes source, configuration, aggregate metrics and two original-geometry error examples. It excludes model-weight files, raw paper evidence and third-party assets. The current round ended after its one frozen run; no test-informed repair was made.
