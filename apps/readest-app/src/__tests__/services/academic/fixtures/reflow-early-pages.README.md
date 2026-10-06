# Early-page reflow regression geometry

This fixture retains source-derived text/graphic bounding boxes from the public author-hosted HPCC PDF, pages 3–4, and MP-RDMA PDF pages 1–3. It contains no PDF bytes, original vector paths, paper prose, author identities, or contact details. Prose glyphs are replaced with generated `x` labels, preserving word lengths, case, spacing, punctuation, font identity distinctions, and line metrics. Numerals and Greek variables are changed. Only generic `Figure`, `Fig.`, `Abstract`, and `Index Terms` classification markers remain.

Sources (public author copies, acquired 2026-10-06):

- HPCC: https://liyuliang001.github.io/publications/hpcc.pdf — SHA256 `8199b81f7325b8797623b6c44fad90eb2664b4bc6a8e0f9bdbad7e043b02fe8a`
- MP-RDMA, IEEE/ACM ToN 2019, DOI 10.1109/TNET.2019.2948917: https://1989chenguo.github.io/Publications/MPRDMA-ToN19.pdf — SHA256 `1622088345c08283aa4b920f5f43c461c044043012c3587ea9599c00ff26d3c1`

Additional supplied-PDF regression geometry and its document-specific assertions are retained locally only. They are not included in this public fixture set.

The fixture was extracted with PDF.js 6.2.108. Coordinates are rounded to five decimal places. Expectations identify source items and graphic bounding boxes, including very small marks; they do not depend on reproducing the source prose. Numeric axis labels can be explicitly text-suppressed at a page margin, but the rendered figure crop must still contain their ink boxes. Complete caption ownership has no such exception.

The companion tests cover column-safe lines and paragraphs, left-before-right body order, separate adjacent figures, full caption continuations, complete multi-panel diagrams, local crop boundaries, inline mathematics, exact source ownership, and safe fallback for genuinely three-column prose. These semantic tests supplement pixel comparisons: passing them alone does not verify the rendered reader or prove a crop matches the original paper visually.

Public availability is not a redistribution license. Acquire PDFs separately for local visual checks; do not bundle them or extracted paper text with this repository.
