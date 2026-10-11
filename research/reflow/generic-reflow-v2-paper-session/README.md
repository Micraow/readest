# Explicit original-page / experimental-reflow paper session

A standalone research shell for complete, caller-pinned PDFs. It does not replace
the regular Readest reader, modify a library, or certify arbitrary PDF extraction.

## Two deliberately separate modes

- **Original page:** every PDF page remains available in its original visual
  layout, rendered directly at 2x from the complete pinned source PDF. The image
  can be zoomed and panned within its own viewport. It has no inferred text layer,
  search index, semantic-copy claim, or new interactive reference links. The whole
  unchanged original PDF remains downloadable.
- **Experimental reflow:** only an explicitly supplied, HTML-hash-pinned local
  reader may appear as an optional page mode. The builder checks its extracted
  source-page hash against the corresponding zero-based page of the complete
  original. The current capability label is partial probes only, never a whole
  page/paper pass. Existing unknown-content copy refusals remain inside the reader.

Displaying an original page is an honest source-reading capability, not a fallback
that converts a failed reflow experiment into a successful one. Reader experiments
can therefore progress independently of full-document navigation.

## Source and lifecycle contracts

The UI carries document PDF hash, zero-based source page index, and mode in each
page identity. It atomically changes reader/source state after the new resource is
ready. Failed or superseded requests retain the last valid page; stale prepared
resources dispose rather than commit. Closing aborts pending work, releases blob
URLs, removes the iframe, and disables document controls. Reopening restores the
last explicitly read source page in memory; there is no cross-session persistence.

A native token can return to its page's original source rectangle. Re-entering the
experimental reader returns to that token. Source mapping is restricted to the
explicitly supported unrotated candidate contract. A connected iframe must not be
removed/reinserted during commit: that reloads its document and destroys attached
source-return listeners. The authored regression protects this node identity.

Changing reader font size clears selections and triggers the existing geometry
refresh. Source zoom and narrow-column sizing do not change PDF content or word
order. Closing/reopening is not claimed to measure browser garbage collection.

## Build and serve

`build_paper_session.py CONFIG OUT` accepts a private JSON list of exact source
paths, SHA-256 hashes, page counts, document labels, and optional pinned reader
folders. Output includes the unchanged PDFs, original page PNGs, an explicit
manifest, an enumerated asset allowlist, and a private build receipt. Keep these
source-containing outputs private; only original code and authored tests belong
in a public repository.

`serve_paper_session.py OUT --port PORT` serves only frozen, hash-checked asset
bytes on 127.0.0.1. It has no directory listing or route-to-filesystem fallback.
The browser checks source/candidate hashes before use. External origins, objects,
forms, and base-URL changes are denied by CSP. Candidate HTML is trusted original
project code supplied by the builder, not an untrusted HTML import format.

## Validation

Run `node code/test_paper_session.mjs` and
`python -m unittest discover -s code -p test_paper_builder.py` with pypdf and
pypdfium2 installed. Authored controls cover full page-index coverage, malicious
routes, missing provenance, stale async loads, failed-page preservation, resource
ownership, closing, source pin/count failures, and connected iframe identity.
These controls do not replace actual browser source navigation, native copy,
source-return, width, or lifecycle checks. Real-paper receipts stay private.
