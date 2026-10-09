# Compact intermediate JSON: useful local saving, H6 still times out

All pages below are already-seen diagnosis. The original blind batch stays **0/2**.
No frozen file was edited. No CI or browser verification ran.

- Fourteen authored JSON cases retain parsed values, Unicode and negative zero;
  nonfinite-value refusal is retained. The standard json module is untouched.
- One existing H6 plan shrinks from 10,491,688 to 5,913,095 bytes. A-B-B-A
  encode/write/read wall seconds: 3.100, 1.197, 0.661, 1.679. These are wire
  microbenchmarks, not complete page times.
- Attempt 1 H5 reached generated target assets but failed a reporting function
  name collision at 31.626s. H6 reached 60.080s and was killed. Both are failures.
- After the reporting-only alias fix, new complete H5 took **29.298s wall,
  28.414s total accounted CPU, 536.3 MiB sampled peak RSS**. H6 again timed out,
  **60.079s wall, 57.600s CPU, 536.9 MiB**. It was not resumed into success.
- H5's final parsed reader payload and all eleven 28px/DPR2 native-renderer PNGs
  exactly match the previously reviewed integrated version. This is output
  equivalence; it does not settle copy, browser layout or focus/zoom acceptance.

A separate cached-plan H6 target-asset cProfile run completed at **42.462s wall,
42.026s total CPU, 369.7 MiB**. Startup/lazy imports, 133 bitmap allocations
(6.634s self time), native drawing and image encoding are measurable costs.
The compact installer's getattr introspection itself caused foreign modules'
optional lazy imports; its 4.058s cumulative time is retained as a defect, not
excluded from the timed requests. The next isolated components experiment avoids
that introspection and evaluates the already-installed image backend.

`RESULT.json` retains every full request, stage time, observer CPU and load.
Shared-host load varies; one 29s H5 result does not prove a stable speedup over
one 42s prior request. H6 has no complete budget pass. Runtime deployment size,
source hyphenation and small wide formulas are still unresolved, and the strict
H5 moved-alpha numerical differences remain recorded in formula-hierarchy.
