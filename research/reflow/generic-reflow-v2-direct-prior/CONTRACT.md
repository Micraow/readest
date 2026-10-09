# Direct existing-model inference, frozen comparison plan

The existing optional PP-DocLayout-S weak prior has measured whole-process
startup costs that dominate recent page requests. This experiment calls the
same installed Paddle Inference backend directly rather than importing the
whole PaddleX application. No model is downloaded, trained, quantized, replaced
or treated as ground truth. This is an execution-path experiment, not a new
reading-order model evaluation or new blind document test.

## Acceptance, defined before direct execution

1. Same PDFium 4x annotation-disabled page input, graph/weights/config hashes,
   CPU backend, one thread and graph optimization settings. Preserve the old
   wrapper and all measured failures.
2. Exact native input pixels and tensor preprocessing. Model YAML drives resize,
   interpolation, normalization and label vocabulary. Unsupported preprocessing,
   output shapes or optional postprocessors must refuse, not silently approximate.
3. Final ordered class/score/coordinate records must be JSON-value identical to
   the installed PaddleX path. Original installed implementation and version
   hashes are recorded. Compatibility geometry rules are typed config, explicitly
   attributed and traced; they do not become invisible new PDF heuristics.
4. First compare authored control and already seen H5/H6. If an implementation
   mismatch occurs, preserve output, diagnose generically and version the fix.
   No new holdout is opened to tune the adapter.
5. Once equivalent, measure fresh-process A-B-B-A old/direct pairs on one CPU,
   same supervisor CPU included, with total CPU/RSS/wall/load. Page render,
   imports, model load, infer, output write all belong to this stage. OS cache is
   not flushed; no warm in-process model reuse. Report every run, including
   slower ones. Adoption needs CPU/wall reduction without changed predictions;
   a partial-stage gain cannot establish the full cold page budget.
6. Integrate into a NEW complete candidate only after these tests. The old blind
   batch remains 0/2; the previous 60-second page timeouts remain failures.

## Provenance and limits

Official Paddle Inference documentation:
https://www.paddlepaddle.org.cn/inference/master/guides/introduction/index_intro.html
Installed Paddle 3.3.1 and PaddleX 3.7.2 source are the exact compatibility
reference. PaddleX is Apache-2.0:
https://github.com/PaddlePaddle/PaddleX/blob/v3.7.2/LICENSE
The adapter is newly written, with compatibility behavior derived from that
licensed reference. No private source document/text/regions are published.
The installed Paddle package is still a large desktop/server runtime; removing
PaddleX imports is not proof of a small cross-platform Readest deployment.
