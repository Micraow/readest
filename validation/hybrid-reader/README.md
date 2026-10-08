# Synthetic hybrid-reader browser validation

This isolated experiment copies the self-authored prototype HTML without changing
the application or claiming the prototype is ready for integration. All fixture
text and SVG graphics are invented for this test. No PDFs, extracted paper text,
source-page images, private corpus data, or model weights are included.

The runner uses a fresh sandbox-enabled Chromium process, a runner-local server,
and a browser request allowlist containing only that server. It produces desktop,
large-font, dark-theme, zoom-dialog, and mobile screenshots plus a JSON report.
The workflow has read-only repository permissions, no secrets, no deployment,
and a ten-minute timeout. It runs only on the independent validation branch.

Run from this directory:

```
npm ci --ignore-scripts --no-audit --no-fund
npx playwright install --with-deps chromium
npm run check:fixture
npm test
```

Screenshots and report are written to `evidence/`. Passing this lane verifies
Chromium interactions and these synthetic layouts, not PDF semantic quality,
Readest's native application shell, or Android behavior. The original prototype
remains unsuitable for release until those separate issues are resolved.
