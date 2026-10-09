# Offline experimental entry for Readest

## What is integrated

`apps/readest-app/public/research/reflow-viewer.html` is a generated, unlinked
static research entry. Its intended application URL is `/research/reflow-viewer.html`.
It embeds the exact shared native vector painter, formula layout, selection layer
and trial interactions. No default reader, normal PDF open path, library state,
account, network service or Reading mode button is changed. This file's placement
is implemented; serving it in a complete Readest web/Tauri build and real-browser
interaction remain unverified in this sparse research checkout.

The inspected application seam is `src/components/academic/AcademicReadingButton.tsx`,
which lazy-loads `AcademicReaderDialog`; `src/app/zotero/page.tsx` uses that button
beside `OriginalPdfView`. Future native-vector integration belongs behind an explicit
experimental choice there, not in the ordinary `Reader` or default PDF loader.
This entry does not claim to have made that deeper integration.

## Run and regenerate

Generate the public entry from original source (requires Python, Pillow, Node for
focused tests; generation itself launches no server):

```
python research/reflow/generic-reflow-v2-viewer-entry/code/build_entry.py apps/readest-app/public/research/reflow-viewer.html
```

Open the entry from a normal Readest development build, or open the generated HTML
locally, then choose a private precomputed JSON bundle with schema
`readest-reflow-research-v1`. Import is explicit and memory-only. A standalone
private recovery package contains both original PDFs, reference images, native
reader payloads, mapping inputs and one self-contained bundle; none belong here.

The supported scope is at most two already prepared pages and 16 MiB per bundle.
There is no arbitrary-PDF extraction, model execution, background upload, persistent
storage, original-PDF modification, or cold-pipeline performance claim.

## Input and security boundary

Imported JSON is untrusted data. The validator rejects active SVG/HTML/script URLs,
external assets, malformed PNG headers/dimensions, invalid PDF URI types, forbidden
prototype keys, excessive nesting/counts/string size, non-finite/huge geometry,
unknown affine operations, external canvas filters, bad resource IDs, malformed
formula hierarchy and inconsistent text maps. Every offered font is preflighted
before replacing a working document. Dynamic labels use `textContent`.

The generated document carries a hash-authorized script CSP, `default-src 'none'`,
`connect-src 'none'`, `img-src data:`, `object-src 'none'`, no external scripts/fonts,
and no imported HTML execution. PDF data is offered only as an original download.
The CSP is a static enforceable contract; browser enforcement/network observation
must still be checked in the real-browser acceptance batch.

## Evidence and remaining gates

The actual generated module initializes and imports both real H5/H6 prepared pages
in a DOM harness, selects/copies an eligible paragraph, clears selection on font
change, changes pages, and preserves the current reader on an invalid import.
Network API traps record zero attempts. Canvas and image decoding are faked in this
harness, so this is runtime integration evidence, not visual/browser proof. It caught
and fixed a genuine existing startup bug: calling `textContent` as a function.

Real H5/H6 bundles pass full validation and all twelve font/width layout combinations.
Hostile-bundle controls cover the boundaries above. Mapping remains conservative:
H5 285 eligible / 26 refused tokens; H6 682 / 64. Unknown formulas are visible and
source-linked but copied ranges touching them refuse. Unicode agreement is not a
semantic certificate. Cold H6 >60 s and earlier blind 0/2 results remain unchanged.

Before normal-reader adoption: real mouse/keyboard copy, source-dialog focus,
selection alignment, CSP/no-network observation, Readest full build and platform
smoke tests. Do not retry the previously denied browser-launch route to obtain them.
