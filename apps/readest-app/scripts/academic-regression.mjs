/**
 * Local-only, deterministic corpus regression. No files are uploaded or downloaded.
 * Node >=22.13: node --experimental-strip-types scripts/academic-regression.mjs /path/to/pdfs [--extracted] [--output /path/report.json]
 * --extracted reuses PDF.js page-NN.json evidence beside each PDF; otherwise parses PDFs afresh.
 * Report contains counts/geometry only; PDFs and extracted text must remain outside this repository.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { performance } from 'node:perf_hooks';
import { analyzeDocument, validateSourceCoverage } from '../src/services/academic/layout.ts';
import { extractPageGeometry, normalizePageGeometry } from '../src/services/academic/geometry.ts';

const args = process.argv.slice(2);
const root = args[0];
if (!root || root.startsWith('-')) throw new Error('Supply a directory of local PDFs; this harness does not download a corpus');
const output = args.includes('--output') ? args[args.indexOf('--output') + 1] : undefined;
const extracted = args.includes('--extracted');
const require = createRequire(new URL('../../../packages/foliate-js/package.json', import.meta.url));
const pdfRoot = path.dirname(require.resolve('pdfjs-dist/package.json'));
const pdfjs = await import(path.join(pdfRoot, 'legacy/build/pdf.mjs'));
const HPCC = '8199b81f7325b8797623b6c44fad90eb2664b4bc6a8e0f9bdbad7e043b02fe8a';
function revive(value) {
  if (!value || typeof value !== 'object') return value;
  if (Array.isArray(value)) return value.map(revive);
  if (Array.isArray(value.values) && /Array$/.test(value.type)) return value.values;
  return Object.fromEntries(Object.entries(value).map(([key, val]) => [key, revive(val)]));
}
const boxContains = (box, x, y, tolerance = 3) => box.x <= x + tolerance && box.y <= y + tolerance && box.x + box.width >= x - tolerance && box.y + box.height >= y - tolerance;
function goldenChecks(document) {
  const failures = [];
  const algorithm = document.blocks.find((b) => b.role === 'algorithm' && b.source.some((s) => s.page === 6 && s.boxes.some((r) => boxContains(r, 318, 287) && boxContains(r, 558, 612))));
  const figure = document.blocks.find((b) => b.role === 'figure' && b.source.some((s) => s.page === 10 && s.boxes.some((r) => boxContains(r, 56, 84) && boxContains(r, 558, 260))));
  if (!algorithm) failures.push('HPCC Algorithm 1 is not one complete visual region');
  if (!figure) failures.push('HPCC Figure 9 panels/labels/caption are not one complete wide visual region');
  const page6 = document.pages.find((p) => p.page === 6);
  const expected = page6.items.filter((i) => /^\d{1,2}:?$/.test(i.text.trim()) && i.box.x > 319 && i.box.x < 328 && i.baseline >= 328 && i.baseline <= 607);
  const assigned = new Set(algorithm?.source.find((s) => s.page === 6)?.itemIndices ?? []);
  if (expected.length !== 27 || expected.some((i) => !assigned.has(i.index))) failures.push(`Algorithm line-number coverage is incomplete (${expected.length} extracted)`);
  const p10blocks = document.blocks.filter((b) => b.source.some((s) => s.page === 10));
  if (figure && p10blocks[0] !== figure) failures.push('Wide Figure 9 does not precede page-10 body');
  const p1 = document.pages[0];
  if (p1.columns.length !== 2) failures.push('HPCC first page two-column body not detected');
  return { failures, algorithm: algorithm?.source.find((s) => s.page === 6)?.boxes, algorithmNumberedLines: expected.length, wideFigure: figure?.source.find((s) => s.page === 10)?.boxes };
}
const files = (await fs.readdir(root)).filter((file) => file.toLowerCase().endsWith('.pdf')).sort();
if (!files.length) throw new Error('The supplied directory has no PDF files');
const results = [];
for (const file of files) {
  const start = performance.now();
  const data = new Uint8Array(await fs.readFile(path.join(root, file)));
  const fingerprint = createHash('sha256').update(data).digest('hex');
  if (file.toLowerCase() === 'hpcc.pdf' && fingerprint !== HPCC) throw new Error('hpcc.pdf differs from the agreed SHA256 golden');
  const pages = [];
  let loading;
  try {
    if (extracted) {
      const dir = path.join(root, path.basename(file, path.extname(file)));
      const evidence = (await fs.readdir(dir)).filter((name) => /^page-\d+\.json$/.test(name)).sort((a,b) => a.localeCompare(b, undefined, {numeric:true}));
      for (const name of evidence) {
        const raw = revive(JSON.parse(await fs.readFile(path.join(dir, name), 'utf8')));
        raw.operators = { fnArray: raw.operators.map((op) => pdfjs.OPS[op.fn]), argsArray: raw.operators.map((op) => op.args ?? []) };
        pages.push(normalizePageGeometry(raw, pdfjs.OPS));
      }
    } else {
      loading = pdfjs.getDocument({ data, standardFontDataUrl: `${pdfRoot}/standard_fonts/`, cMapUrl: `${pdfRoot}/cmaps/`, cMapPacked:true, wasmUrl:`${pdfRoot}/wasm/`, useSystemFonts:false });
      const pdf = await loading.promise;
      for (let n = 1; n <= pdf.numPages; n++) { const page = await pdf.getPage(n); pages.push(await extractPageGeometry(page, n, pdfjs.OPS)); page.cleanup(); }
    }
    const analyzed = performance.now();
    const document = analyzeDocument(pages, fingerprint, pdfjs.version);
    const coverage = validateSourceCoverage(document);
    const golden = fingerprint === HPCC ? goldenChecks(document) : undefined;
    const summary = { file, fingerprint, pages:pages.length, items:pages.reduce((n,p) => n+p.items.length,0), coverageErrors:coverage, blocks:document.blocks.length,
      roles:Object.fromEntries([...new Set(document.blocks.map((b) => b.role ?? b.type))].map((role) => [role,document.blocks.filter((b) => (b.role ?? b.type)===role).length])),
      visualFallbackPages:document.pages.filter((p) => p.columns.length===0 && p.visualRegions.some((r) => r.role==='unknown' && r.box.width===p.width)).map((p) => p.page),
      twoColumnPages:document.pages.filter((p) => p.columns.length===2).length,
      layoutMilliseconds:Math.round(performance.now()-analyzed), totalMilliseconds:Math.round(performance.now()-start), ...(golden?{golden}:{}),
      pageStats:document.pages.map((p) => ({page:p.page,columns:p.columns.length,blocks:p.blockIds.length,visuals:p.visualRegions.length,suppressed:p.suppressedItemIndices.length})),
    };
    results.push(summary);
    console.log(JSON.stringify({...summary,pageStats:undefined}));
    if (coverage.length || golden?.failures.length) process.exitCode = 1;
  } finally { await loading?.destroy(); }
}
const report = {pdfjsVersion:pdfjs.version,mode:extracted?'saved-pdfjs-extraction':'live-pdfjs',createdAt:new Date().toISOString(),results};
if (output) await fs.writeFile(output,JSON.stringify(report,null,2));
