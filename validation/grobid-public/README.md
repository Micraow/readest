# Bounded GROBID structure baseline

This is a diagnostic research branch, not a reader implementation, model comparison sweep, production integration or release. Parse all pages of the same three hash-pinned public PDFs, then inspect ForestColl p7, Gottesman p3/p9 and Uno p1. Page 1 and adjacent pages are included as context for author and continuation review. The selected pages are already-known failures, not blind held-out samples.

## Runtime and provenance

- Official GROBID 0.9.1 **CRF-only** image, not the full deep-learning configuration. It packages the server, native parser and CRF models. Linux/amd64 image digest is pinned in manifest.json. The official Docker Hub metadata response is preserved separately with its source URL.
- Official docs: https://grobid.readthedocs.io/en/latest/Grobid-docker/ . CRF image is about 510 MB compressed; fulltext parsing recommends 4 GB RAM. This run caps the service at 2 CPU / 6 GiB, sequential requests, with a 20-minute workflow and 180-second per-document deadline. No local Docker/model download is needed to prepare the experiment.
- GROBID: Apache-2.0, https://github.com/grobidOrg/grobid/blob/0.9.1/LICENSE . Bundled pdfalto has separate GPL-2.0 licensing: https://github.com/kermitt2/pdfalto . This research run is not a license review for redistribution or integration.
- Download only the three fixed public arXiv URLs; verify exact bytes before parsing. Never copy private inputs into the bundle. No credentials, external inference services or private PDFs are involved.
- The service uses `--network none`; a stdlib client enters only that network namespace to reach loopback. No ports are published. Consolidation is explicitly zero for header, citations and funders. Offline parsing occurs after all downloads finish. The client receives a cleared environment.

## Evidence, not replacement text

Each document keeps original.pdf, raw.tei.xml, request settings/timing, native-evidence.json (independent PyMuPDF words, characters, boxes and page dimensions), and structure-proposals.json (text, individual rectangles and typed relations). Original PDFs are never changed. Source PNGs and overlays are separate. Overlay production requires matching page dimensions and unrotated source pages; coordinate mismatches are reported, not silently corrected.

The structure graph exposes containment, caption-of, ref-to-target and next-in-TEI-body-order proposals. It does not equate predicted order or matching IDs with correct order. Cross-page paragraphs retain separate rectangles. A figure envelope is explicitly not a caption box. TEI formula strings are linearized and must never be called preserved math or converted into trusted LaTeX. Source evidence is independently retained even if TEI omits it; native text extraction itself is not a proof of visible glyph or clipping completeness.

Run `python3 -m unittest -v test_analyze.py` to check evidence handling. Parse through the bounded workflow; then `python3 analyze.py` generates review pages. No per-paper heuristic, semantic text repair, name-specific branch or fixed-coordinate correction exists in the parser or analyzer.

## Preregistered manual review questions

1. All authors and affiliations on the three first pages: complete names, correct separation from titles/abstract/body, useful source coordinates. Audit names rather than counting tags.
2. ForestColl p7: four panels, shared caption, Algorithm 2 separation, and left-column final paragraph continuing at the top of the right column. Are body and caption roles distinct? Are figure callouts associated? Inspect source and adjacent pages for paragraph continuity.
3. Gottesman p3: Table 1 caption versus table rows and body; formula numbers 11 onward stay attached; prose following the formula remains complete. Mathematical superscripts/subscripts are reviewed against source, never accepted from linearized TEI.
4. Gottesman p9: Table 2 versus caption, equations 43–49 and connecting prose; no omitted or swallowed paragraph. If TEI is mathematically wrong, explicitly report the limitation.
5. Reference relations: inspect resolved targets against the actual bibliography entries, including source rectangles and raw citations. Missing targets are reported. Existence of an ID alone is not evidence of a correct reference.
6. Whole-paper parsing and selected-page review are reported separately. Cross-page continuation nodes are manually checked where they meet diagnostic pages; no inference of general accuracy from four pages.

Stop after this baseline and report concrete improvement/failure categories. Do not tune to these papers, construct a new reader or test additional model families.
