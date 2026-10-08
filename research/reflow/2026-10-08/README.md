# Frozen reflow research checkpoint

This directory archives exploratory research. It is not integrated into the Readest application and is not a release candidate. Original glue follows the repository's AGPL license. Third-party code, weights, paper files, crops, user documents, and machine-specific paths are excluded.

The C/Python source files are byte-for-byte copies of the frozen experiments. `SOURCE-MANIFEST.json` records their hashes. `PUBLIC-*.json` configurations are sanitized exports: paths are relative to this directory and private coordination details are omitted. Their original configuration hashes are retained. This export does not modify the original experiments or their conclusions.

See `RESULTS.md` for failures and measurement limits. Every listed input is now a seen diagnostic page. Public-paper URLs and hashes are in `PUBLIC-INPUTS.json`; a public URL is not a license to redistribute a paper or use it as training data.

## Dependencies and reconstruction

The official engine is [KOReader/libk2pdfopt](https://github.com/koreader/libk2pdfopt/tree/64aa9ccfcd55921c596458cb8a7197339d5f32c3), pinned at `64aa9ccfcd55921c596458cb8a7197339d5f32c3`. `DEPENDENCIES.json` gives the exact upstream source and official Debian header-package URLs and SHA-256 values. Download these separately, verify the hashes, extract the source into the directory expected by `k2-reuse-v1/build.py`, and extract the two Debian packages into `k2-reuse-v1/deps/root` with `dpkg-deb -x`. Create `build`, `inputs`, `output`, `logs`, and `evidence` directories before running the scripts.

The recorded host had a C/C++ compiler, Tesseract 5.5.0 and Leptonica 1.84.1 shared libraries. The serial `build.py` compiles the files in upstream `lib/CMakeLists.txt`, adds the original settings bridge and PPM/JSON harness, and links the existing shared libraries. It does not modify the upstream source. Tesseract is a dependency; OCR transcription was disabled. The source build took 7.58 seconds, with compiler peak RSS 90,940 KiB on the original host. These are host observations, not cross-device promises.

The second round uses `k2-reuse-v2-default/harness.c` with the same bridge and upstream objects. Its sole engine-setting change is word spacing from -1 to -0.2, matching the actual KOReader reader default. This is otherwise a fidelity-oriented benchmark configuration, not an exact replica of every KOReader UI default.

Python execution requires PyMuPDF, Pillow and NumPy. Detector experiments additionally require a compatible PaddleX/PaddlePaddle installation and the official [PP-DocLayout-S](https://huggingface.co/PaddlePaddle/PP-DocLayout-S/tree/8ac289e66575bb9bba6e15c53719d8b15cc9b3b2) revision specified in the freeze. The model is expected under the relative `hybrid-prototype/mobile/PP-DocLayout-S` path. It is not included. Inference is forced offline and single-threaded.

The original drivers expect source PDFs and cached products at the relative locations recorded in the freezes. Inputs, intermediate rasters, detector JSON, source glyph extraction, visual audit sheets, and native libraries are intentionally absent from this public archive. Some original preparation steps were executed interactively rather than by a packaged driver. Consequently this is a source/configuration checkpoint with dependency reconstruction notes, not a self-contained one-command reproduction bundle. Reproduction must materialize the public inputs locally, verify their hashes, and independently audit the output.

## Resource and CI policy

The research budget was one CPU, at most 1 GiB process memory, less than 60 seconds per page, and less than 1 GiB additional disk per bounded experiment. This is an experiment budget, not a claim about all target user devices.

Only `research/reflow/**` is changed on a separate `research/reflow-20261008` branch. Checkpoint commit messages contain `[skip ci]`. At the base commit, application build/deploy push workflows target `main`, while Android/Linux builds also require explicit markers or manual dispatch. No release/build marker, pull request, workflow dispatch, or main-branch mutation is performed. Local Python syntax checks were run. The archived experiments ran before export; neither a fresh experiment nor an application/Android test suite was run for this backup. Skipped CI is not passing CI.

Official implementation references: [reflow API](https://github.com/koreader/libk2pdfopt/blob/64aa9ccfcd55921c596458cb8a7197339d5f32c3/lib/koptreflow.c), [context](https://github.com/koreader/libk2pdfopt/blob/64aa9ccfcd55921c596458cb8a7197339d5f32c3/lib/context.h), [K2pdfopt FAQ](https://www.willus.com/k2pdfopt/help/faq.shtml). Mature word wrapping and source rectangles do not establish mathematical structure or author-intended reading order.
