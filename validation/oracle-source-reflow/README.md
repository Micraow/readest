# Oracle source-preserving reflow experiment

This is an isolated rendering experiment. `oracle.json` is explicit human/reference
semantic structure INPUT, not the output of an automatic parser. There are no
paper-name/page-number branches in the source-unit compiler or renderer.

Selected public source: https://arxiv.org/pdf/0904.2557v1
SHA-256: 2d53b60b7616defa1af51a1ad623c0febec565e583b7c1584212436226b3be29

## Scope

Page 3: body before/after equation 11 and the Pauli-group paragraph. Page 9:
whole 8-row, 9-column operator table plus caption, and the paragraphs/equations
44–45. Omitted sections are explicit excerpt gaps, not document-coverage claims.

The compiler accepts typed nodes, ordered source lines, word/inline group
ownership and baseline anchors. It partitions original page raster pixels at
white gaps, trims blank pixels only, and protects complete formulas/tables.
Native font boxes are not crop boxes: CMSY font extents cross neighboring lines.
Source windows are reference input precisely to isolate rendering from that
unresolved segmentation problem. All scientific glyphs come from source pixels.

The desktop reference data was manually refined from independently recorded
regions and inspected source pixels. This paper is a development case, not a
holdout. Pixel ownership tests establish only the selected windows' coverage;
they do not prove that the windows or semantic groups are correct.

## Local build

Use Python 3 with PyMuPDF 1.26.6 and Pillow 12.3.0, then:

    python prepare.py source.pdf --oracle oracle.json --out .
    python render.py --dir .
    python -m unittest -v test_prepare.py
    node validate.mjs --check-fixture

Open index.html with its fixture.js and interaction.js siblings. The reader works
without network access after source preparation. `npm test` is reserved for an
authorized, sandbox-enabled Chromium environment. Local browser restriction was
not bypassed. GitHub CI fetches only the immutable public PDF from arXiv.

## Checks and limitations

- At 390 px, body words rewrap at 20 and 28 px while inline groups stay intact.
- Whole equations and table retain reading scale; wide objects scroll horizontally.
  Clicking gives a complete original-object preview plus its original page anchor.
- Duplicate native ownership, clipped line edges, and overlapping dark source pixels
  are rejected. Each visible source unit has a page, bbox, role and stable source hash.
- Full-source raster remains available for independent glyph/relationship review.
- One original Sim-/ilarly line-end hyphen and forced line break are retained.
  No source ink is removed, but that line boundary is a known readability defect.
- The visual body is raster content, not selectable text. A separate native-text
  panel is explicitly unverified: scripts flatten, ligatures remain, and protected
  object text is not reconstructed. Accessibility/copy/search are not solved.
- Raster scaling, storage cost, Android latency/memory, automatic structure recovery,
  complete-document reading order, and production integration remain untested.
- Offline CSS snapshots are not Chromium or Android QA. Chromium evidence must
  come from the exact reviewed code and actual CI run, including scroll endpoints,
  complete object preview, source anchors and font changes.

No model inference, cloud OCR, private papers, production app code, release changes,
or independent Codex task/CLI/API are part of this experiment.
