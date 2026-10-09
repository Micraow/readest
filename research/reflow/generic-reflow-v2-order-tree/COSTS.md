# Costs and deployment boundary

Both runs below used the same already-local D4 PDF bytes, one allowed CPU, fresh Python processes, the already-installed official PP-S files, and local offline inference. OS file caches were not flushed. No original document left the machine. Measurements are single diagnostic observations, not percentile guarantees.

| Variant | Wall seconds | CPU seconds | RSS MiB | Outcome |
| --- | ---: | ---: | ---: | --- |
| Model retained in page process | 60.077 | 58.182 | 628.516 process high-water | Killed at 60s; partial output, failed |
| Model subprocess exited before native work | 52.669 | 51.674 including waited child | 676.258 sampled process-family peak | Complete offline HTML/evidence generation |

Second run also set `OMP_WAIT_POLICY=PASSIVE` and `KMP_BLOCKTIME=0`; do not attribute all differences solely to process isolation. Both set CPU affinity and one-thread BLAS/OpenMP limits. The first failure and its logs are preserved. Its completed model phase took 24.585s and native ownership 11.485s; the next closure phase had not completed at timeout.

Successful complete pipeline phases: model process including startup/exit 19.471s; native ownership 8.216s; within-object closure 6.927s; graphic closure 1.898s; cross-object closure 3.309s; verified priors 1.303s; fractions 1.464s; source-position replay 1.963s; tree 0.352s; native local render/encode 5.289s; inline/paragraph HTML 0.731s. Import/final write/wrapper overhead accounts for the remaining wall time. These phases are not each a page latency. Actual native render calls: 1,777 initial ownership, 3,088 final replay, 716 local-unit rendering (plus closure work within its measured phases).

The successful model child recorded 18.255s import/setup/page body, including 3.329s model creation and 0.843s predict/result recording. The 19.471s enclosing phase also includes child startup and shutdown. Parent CPU 32.511s plus waited-child CPU 18.983s is consistent with the wrapper's terminal wait4 CPU 51.674s after finalization. The wrapper's sampled instantaneous-family CPU maximum 32.67s is **not total CPU**, because exited children disappear from sampling; use terminal CPU for the budget.

Included: imports, source open/raster, cold model, all native ownership/closure/replay, local assets/PNG encoding, hierarchical reading tree, composite bundles, HTML and audit writes. Excluded: acquisition, installation, browser startup/load/paint, font controls, selection, zoom and runtime cache handling in a real Readest app. Thus **the 60s interactive-page budget has not passed**. A separate 390px 20/28px WeasyPrint static audit took 12.413s unpinned; it is extra QA cost, not hidden inside the successful generation time.

## Deployment burden

Local research directories (not mobile install measurements): Paddle 3.3.1 about 716MiB; PaddleX 3.7.2 about 18MiB, plus other Python dependencies. Model weights 4,804,904B, graph 339,876B, config 1,579B. Native PDFium library about 7.4MiB as recorded in the prior checkpoint. This is not a proven small mobile runtime. The optional region model helps this seen page, but no generalized model net-benefit claim is made.

PDFium source document, font resources and native handles must stay alive during rendering; phases release their instances. The prototype repeatedly reopens the document. It is Python/Linux research, not a ready browser/WASM/iOS/Android integration. Page processing peaks below 1GiB here, but installation size, application resident memory and platform builds are unmeasured.

No new model weights were downloaded for this experiment. One unused ONNX Runtime 1.31.0 wheel (~23.8MB) was downloaded during alternative-runtime exploration, not installed or used; that overhead is not part of a page run. The historical 83MB/20.7M-parameter reading-order head was not used; this smaller PP-S detector serves a different region-proposal role.
