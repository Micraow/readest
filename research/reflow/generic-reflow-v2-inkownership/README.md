# Generic reflow v2: native ink ownership checkpoint

This isolated continuation does not modify the frozen local-break-v1 or the first v2 checkpoint (`2c41e2fa79efc58a1c2be272b67d8912d56acda9`). It is **not an accepted generic reading solution**. New holdouts, including the official Traditional-Chinese nonacademic sample, remain unopened.

## Verified mechanism changes

- Native text-object alpha is partitioned into disjoint word/local owners. Every nonzero-alpha pixel, including alpha=1, is retained exactly once or explicitly quarantined. Object masks are distinct from semantic character IDs and complete-page visibility.
- Crop enlargement must stabilize actual native RGBA; tight viewports were observed to change glyph rasterization. No pixel-error tolerance or correction is used.
- Ambiguous shared-object ink may form one bounded, native-index-contiguous local interval, with fraction/script geometry closure and typed limits. The old D4 inline fraction/expression becomes one 17-character group, preserving its relative geometry. This is not a global reading-order proof.
- Independent 8-bit RGBA layer recomposition failed exact equality (control 3 pixels/max1; D4 536/max1 after viewport stabilization). The failed method/evidence are retained. Original-order native paint actions on the actual accumulated backdrop, committed through disjoint masks, have exact original-position equality on the control, D5 and D4.
- Actual static movement/scaling: D4 local group in authored flowing prose at widths 320/390/430 and fonts 20/28; D5 full native-unit reader at width390 and fonts20/28. Measured unit dimensions scale affinely with no duplicate unit boxes. WeasyPrint is explicitly not a browser/Android interaction test.
- D5 native word images preserve original typeface/weight/italics and reflow the gray-panel list. Word spacing now derives from source ink geometry; line joins use a paragraph gap median. Each boundary has a reason trace. The inherited paragraph order, selection hit geometry, figure zoom and annotation interaction remain unaccepted.

## Full old-page diagnostic exposed retained failures

| Seen input | Cold process wall / CPU | Peak process RSS | Local units | Result |
| --- | ---: | ---: | ---: | --- |
| D5-P1 | 11.0308s / 10.8691s | 190.863MiB | 426 | zero unresolved alpha; original-position replay exact; zero local source-support RGB differences; reading/interaction not accepted |
| D4-P1 | 47.4888s / 47.0017s | 211.957MiB | 995 | original-position replay exact, but 5 independent local assets fail source-support comparison |

Each is a fresh process pinned to one CPU. Includes imports, all native extraction/planning/masking, encoding, conditional interval closure, replay, 72/144dpi annotation diagnosis, all local assets and HTML/audit writes. Inputs already local; OS file cache not flushed. Includes 649 and 8,439 native renders respectively. Browser load/paint/interaction is excluded, so these are **not interactive end-to-end budget passes**. Per-phase timing is not substituted for page time. Static QA and development experiments are additional costs.

D4 failure detail: one graphic unit has 6,333 differing pixels (max channel13); four native text units have one differing pixel each (max7/9/12/9). Root cause evidence: graphic-internal light-gray rectangles were classified as flowing backgrounds; two contained path clusters and axis-label text fell outside the graphic owner. Cross-text-object superscript ink overlap escaped the per-object partition guard. These are retained failures, not amended scores. The next mechanism must close bounded graphic ownership/continuous intervals and detect cross-object support interactions; no per-page IDs may become rules.

## Annotation boundary

Three old-input Link annotations have no normal visible appearance at 72/144dpi. They still have interaction metadata. Their `/Dest` keys exist but cannot be resolved in these isolated single-page inputs; click-region/target remapping is not implemented. No targets were fetched. Opaque authored annotation control reconstructs exactly; normal partial alpha and Multiply fail the independent compositor and remain unsupported. See `ANNOTATION-RESULT.json` for the prior complete measured annotation batch. Form widgets and other appearance states are not accepted.

## Deployment baseline, not a proposed final UI

D5 currently has 426 PNGs totaling 641,102 bytes (median1,231; max58,538), 2,353,968 decoded RGBA bytes, and approximately134KB HTML. Separate files imply 426 image resources; actual browser request/decode overhead was not measured. The reader has at least three DOM elements per selectable word plus containers. A 2x source raster provides about1 sample/CSS pixel at20px, about0.71 at28px (DPR1), and half that atDPR2. Static CSS scaling is not rerasterization. Source-flat-background-baked colors are not safe for arbitrary dark backgrounds.

Generation needs a live PDFium document/page and full internal page buffers, including original font/image resources. Full-page images are internal verification/rendering buffers only, never the reading result. HTML assets can display after PDFium closes but cannot regain detail or adapt compositing to a new backdrop. A deployment design must retain a native paint/resource adapter or validated vector/font representation, render for actual font size/DPR/theme, and bound caches.

Installed Linux x86_64 `libpdfium.so` is about7.4MiB; raw package7.6MiB, Python wrapper480KiB. Research numpy/scipy directories are43MiB/110MiB, not mobile package estimates. Native binary SHA256 `224f8ece41f7e35891f11c10073b7b7062d7a18e9ef870586162a85c46130f7d`. No Android, iOS, WASM package/build size measured. PDFium/pypdfium2 license notices and build dependencies must be included; see prior v2 `DEPENDENCIES.md`.

PDFium's public glyph-path implementation maps its argument through Unicode-to-charcode. It cannot be assumed to recover original unknown glyph identity. Font-data extraction may expose a substitute rather than embedded font, and extraction does not grant font redistribution rights. Keep such resources local unless their licenses permit distribution. [Official implementation](https://pdfium.googlesource.com/pdfium/+/refs/heads/main/fpdfsdk/fpdf_edittext.cpp), [API](https://pdfium.googlesource.com/pdfium/+/refs/heads/main/public/fpdf_edit.h).

## Reproduction

Run `python -m unittest discover -s code -p 'test_*.py' -v` with the pinned dependencies in the prior checkpoint; numpy/scipy are additional research dependencies. Run `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python code/measure_page.py LOCAL_INPUT.pdf PRIVATE_OUTPUT_DIR`. Run static QA separately with WeasyPrint. No private document, native text, source crop or screenshot belongs in this public directory.

All new rules are in `code/ink_config.py` and the frozen v2 config imported read-only. Geometry, interval and spacing decisions emit private traces. No OCR/model is used. Native mapped Unicode availability is separate from verified semantics; unknown mapping is not made selectable using a fabricated character. Code is original research code under the repository license.
