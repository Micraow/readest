# Native set cache: exact output, no measured net benefit

**Not adopted into the complete reader request.** No new cold-page run was
started for this candidate. No new holdout or CI/browser run was consumed.

The authored control and already-seen H5/H6 stage comparisons all preserve every
asset ID, metric, alpha array and supported RGB value. Zero-alpha RGB also happened
to be identical. Every per-unit native source-support comparison remained exact.
The source renderer's physical drawing calls dropped from 13 to 7 (control),
318 to 89 (H5), and 752 to 140 (H6). The H5/H6 cache peaked at 29,082,240 bytes,
below its 32 MiB cap. Nonword groups use the frozen renderer.

However, wall/total-accounted-CPU seconds in old/new/new/old order were:

- Control: 1.476/1.394, 2.424/1.982, 1.554/1.500, 1.671/1.614.
- H5: 7.388/5.716, 6.674/5.650, 6.339/5.529, 4.893/4.300.
- H6: 10.615/10.010, 15.259/13.815, 9.121/8.689, 6.325/6.280.

Reducing render-call counts did not produce a demonstrated speedup. Rendering
and copying whole internal text-set frames replaces cheap original word clips;
this cache mechanism is therefore held as a negative performance experiment.
The internal frames are never reader output, but their cost is still real.

The first control invocation used the wrong authored PDF filename and failed
before renderer output; its measurement/error is preserved separately. Corrected
runs started from fresh output directories. All comparisons reuse existing
native plans and masks, so none is a complete/cold-page latency measurement.
`RESULT.json` preserves all samples, system load, observer CPU and sampled RSS.
Source-support equality is not a new complete reading, selection or zoom pass.
