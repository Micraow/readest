import { describe, expect, it } from 'vitest';
import {
  analyzeDocument,
  analyzeDocumentAsync,
  clusterLines,
  joinLines,
  validateSourceCoverage,
} from '@/services/academic/layout';
import type { PageGeometry, PdfTextItem } from '@/services/academic/types';

const item = (
  index: number,
  text: string,
  x: number,
  y: number,
  width = 220,
  fontSize = 10,
): PdfTextItem => ({
  index,
  text,
  box: { x, y, width, height: fontSize },
  baseline: y + fontSize * 0.8,
  fontSize,
  fontName: 'body',
  fontFamily: 'serif',
  angle: 0,
  hasEOL: true,
});
const page = (items: PdfTextItem[], pageNumber = 1): PageGeometry => ({
  page: pageNumber,
  width: 600,
  height: 800,
  rotation: 0,
  items,
  graphics: [],
  tagged: false,
});
const doc = (pages: PageGeometry[]) => analyzeDocument(pages, 'a'.repeat(64), '6.2.108');

describe('deterministic academic layout', () => {
  it('keeps consecutive bold run-in paragraph labels separate at ordinary line spacing', () => {
    const p = page([
      { ...item(0, 'Environment.', 40, 100, 70), fontWeight: 'bold' },
      item(1, 'We model a network with several devices.', 113, 100, 300),
      item(2, 'The configuration remains unchanged.', 40, 112, 280),
      { ...item(3, 'Traffic.', 40, 124, 40), fontWeight: 'bold' },
      item(4, 'We replay a measured workload.', 83, 124, 250),
      item(5, 'The complete trace is retained.', 40, 136, 250),
    ]);
    const d = doc([p]);
    expect(d.blocks.map((block) => block.type)).toEqual(['paragraph', 'paragraph']);
    expect(d.blocks[0]?.text).toContain('configuration remains unchanged.');
    expect(d.blocks[1]?.text).toMatch(/^Traffic\. We replay/);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('clusters unmapped raised operators with their own prose row without changing source geometry', () => {
    const operator = item(2, '\u0002', 95, 105, 8);
    const p = page([
      item(0, 'The preceding sentence continues here.', 40, 100),
      item(1, 'Value =', 40, 112, 50),
      operator,
      item(3, 'x is bounded.', 106, 112, 85),
      item(4, 'The following sentence continues here.', 40, 124),
    ]);
    const before = structuredClone(p.items);
    const lines = clusterLines(p);
    expect(lines).toHaveLength(3);
    expect(lines[1]?.itemIndices).toEqual([1, 2, 3]);
    expect(p.items).toEqual(before);
    const d = doc([p]);
    expect(validateSourceCoverage(d)).toEqual([]);
    expect(
      d.blocks.flatMap((block) => block.inlineRuns ?? []).find((run) => run.kind === 'source'),
    ).toMatchObject({ baseline: 120, source: { itemIndices: [2] } });
  });

  it('rejects missing inline glyphs even when the containing block owns every source item', () => {
    const d = doc([page([item(0, 'A complete source paragraph.', 40, 100)])]);
    d.blocks[0]!.inlineRuns = [];
    expect(validateSourceCoverage(d)).toContain('Inline item 1:0 has 0 owners in p1-b0');
  });
  it('clusters words and superscripts while separating column gutters', () => {
    const p = page([
      item(0, 'The', 40, 100, 15),
      item(1, 'result', 58, 100, 25),
      item(2, '2', 84, 97, 3, 6),
      item(3, 'right column', 330, 100, 120),
    ]);
    const lines = clusterLines(p);
    expect(lines).toHaveLength(2);
    expect(lines[0]?.itemIndices).toEqual([0, 1, 2]);
    expect(lines[1]?.itemIndices).toEqual([3]);
  });
  it('reads title then left column then right, without interleaving equal rows', () => {
    const p = page([
      item(0, 'A full width title', 80, 60, 450, 18),
      ...Array.from({ length: 6 }, (_, i) => item(i + 1, `Left sentence ${i}.`, 40, 130 + i * 14)),
      ...Array.from({ length: 6 }, (_, i) =>
        item(i + 7, `Right sentence ${i}.`, 330, 130 + i * 14),
      ),
    ]);
    const d = doc([p]);
    expect(d.pages[0]?.columns).toHaveLength(2);
    expect(d.blocks[0]?.text).toBe('A full width title');
    const text = d.blocks.map((b) => b.text).join(' ');
    expect(text.indexOf('Left sentence 5')).toBeLessThan(text.indexOf('Right sentence 0'));
    expect(validateSourceCoverage(d)).toEqual([]);
    expect(doc([p])).toEqual(d);
  });
  it('keeps narrow, repeatedly aligned column gutters separate before constructing lines', () => {
    // Real HPCC geometry has a 17.075 pt gutter on one row, below the old 18 pt split.
    const p = page([
      item(0, 'A title spanning the article', 90, 60, 440, 18),
      ...Array.from({ length: 6 }, (_, i) =>
        item(i + 1, `Left column sentence ${i}.`, 63.761, 130 + i * 11, 237.119, 8.9664),
      ),
      ...Array.from({ length: 6 }, (_, i) =>
        item(i + 7, `Right column sentence ${i}.`, 317.955, 130 + i * 11, 241.758, 8.9664),
      ),
    ]);
    p.width = 612;
    const d = doc([p]);
    expect(d.pages[0]?.columns).toHaveLength(2);
    expect(
      d.pages[0]?.lines
        .filter((line) => /Left/.test(line.text))
        .every((line) => !/Right/.test(line.text)),
    ).toBe(true);
    const text = d.blocks.map((block) => block.text).join(' ');
    expect(text.indexOf('Left column sentence 5.')).toBeLessThan(
      text.indexOf('Right column sentence 0.'),
    );
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('places short bibliography markers on the correct side of a narrow gutter', () => {
    const p = page(
      Array.from({ length: 6 }, (_, i) => [
        item(i * 3, `[${i + 1}] Left reference entry.`, 40, 120 + i * 12, 245, 8),
        item(i * 3 + 1, `[${i + 20}]`, 295, 120 + i * 12, 13, 8),
        item(i * 3 + 2, `Right reference entry ${i}.`, 313, 120 + i * 12, 237, 8),
      ]).flat(),
    );
    const d = doc([p]);
    expect(d.pages[0]?.lines).toHaveLength(12);
    expect(
      d.pages[0]?.lines.every(
        (line) => !(line.text.includes('Left') && line.text.includes('Right')),
      ),
    ).toBe(true);
    expect(d.blocks.find((block) => block.text.startsWith('[20]'))?.text).toBe(
      '[20] Right reference entry 0.',
    );
  });
  it('keeps run-in abstract text together and joins a wrapped article title', () => {
    const p = page([
      item(0, 'A long article title wrapping', 80, 60, 440, 24),
      item(1, 'onto a second line', 180, 89, 240, 24),
      item(2, 'Abstract— The method has low', 40, 150, 245, 9),
      item(3, 'latency and modest resource usage.', 40, 161, 245, 9),
      item(4, 'Its measurements are reproducible.', 40, 172, 245, 9),
      ...Array.from({ length: 6 }, (_, i) =>
        item(i + 5, `Right body ${i}.`, 310, 150 + i * 14, 245),
      ),
    ]);
    const d = doc([p]);
    expect(d.blocks[0]?.text).toBe('A long article title wrapping onto a second line');
    expect(d.blocks.find((block) => block.text.startsWith('Abstract'))?.text).toContain(
      'low latency',
    );
    expect(d.blocks.find((block) => block.text.startsWith('Abstract'))?.type).toBe('paragraph');
  });
  it('attaches a dropped capital only to the first body row instead of merging three baselines', () => {
    // The initial glyph occupies almost three body rows, as in the MP-RDMA introduction.
    const initial = item(0, 'M', 48.96, 444.133035, 25.99304, 27.535);
    initial.box.height = 24.89164;
    initial.baseline = 463.38;
    const body = [
      item(1, 'ODULAR designs need high through-', 76.08, 444.4161426, 224.29399, 9.9626),
      item(2, 'put and lower latency to meet increas-', 76.08, 455.33614846, 224.025, 9.9626),
      item(3, 'ing demand from clients.', 48.95981028, 466.25615432, 251.5626, 9.9626),
    ];
    body.forEach((line, index) => {
      line.box.height = 9.1257416;
      line.baseline = 451.38 + index * 10.92000586;
    });
    const d = doc([page([initial, ...body])]);
    expect(d.pages[0]?.lines).toHaveLength(3);
    expect(d.blocks).toHaveLength(1);
    expect(d.blocks[0]?.type).toBe('paragraph');
    expect(d.blocks[0]?.text).toBe(
      'MODULAR designs need high throughput and lower latency to meet increasing demand from clients.',
    );
    expect(d.blocks[0]?.source[0]?.itemIndices).toEqual([0, 1, 2, 3]);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('preserves a ruled algorithm with every numbered line in one crop', () => {
    const p = page([
      item(0, 'Algorithm 1: Local procedure', 330, 201, 220),
      ...Array.from({ length: 27 }, (_, i) =>
        item(i + 1, `${i + 1}: operation(x)`, 334, 240 + i * 10, 210),
      ),
      item(28, 'Prose following the algorithm.', 330, 540),
    ]);
    p.graphics = [200, 230, 520].map((y) => ({
      kind: 'rule',
      box: { x: 330, y, width: 225, height: 0.5 },
    }));
    const d = doc([p]);
    const algorithm = d.blocks.find((b) => b.role === 'algorithm');
    expect(algorithm?.source[0]?.itemIndices).toHaveLength(28);
    expect(algorithm?.source[0]?.boxes[0]?.y).toBeLessThanOrEqual(200);
    expect(algorithm?.source[0]?.boxes[0]?.height ?? 0).toBeGreaterThanOrEqual(320);
    expect(d.blocks.some((b) => b.text === 'Prose following the algorithm.')).toBe(true);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('groups eight vector panels and shared caption before two-column prose', () => {
    const p = page([
      item(0, 'Figure 9: Eight panels', 115, 258, 380),
      ...Array.from({ length: 8 }, (_, i) =>
        item(i + 1, `(${i})`, 56 + (i % 4) * 126, 155 + Math.floor(i / 4) * 80, 45),
      ),
      ...Array.from({ length: 6 }, (_, i) => item(i + 9, `Left text ${i}.`, 40, 300 + i * 14)),
      ...Array.from({ length: 6 }, (_, i) => item(i + 15, `Right text ${i}.`, 330, 300 + i * 14)),
    ]);
    p.graphics = Array.from({ length: 8 }, (_, i) => ({
      kind: 'form',
      box: { x: 56 + (i % 4) * 126, y: 84 + Math.floor(i / 4) * 80, width: 120, height: 68 },
    }));
    const d = doc([p]);
    expect(d.blocks[0]?.role).toBe('figure');
    expect(d.blocks[0]?.source[0]?.itemIndices).toHaveLength(9);
    expect(d.blocks[0]?.source[0]?.boxes[0]?.width).toBeGreaterThan(490);
    expect(d.pages[0]?.columns).toHaveLength(2);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('uses separate captions to bound adjacent figures and retains every caption row', () => {
    const p = page([
      item(0, 'Figure 1: Left panels', 40, 170, 245, 9),
      item(1, 'Figure 2: Right panels with a wrapped', 310, 180, 245, 9),
      item(2, 'caption continuing on the next line.', 310, 191, 210, 9),
      ...Array.from({ length: 6 }, (_, i) =>
        item(i + 3, `Left prose ${i}.`, 40, 230 + i * 14, 245),
      ),
      ...Array.from({ length: 6 }, (_, i) =>
        item(i + 9, `Right prose ${i}.`, 310, 230 + i * 14, 245),
      ),
    ]);
    p.graphics = [40, 170, 310, 440].map((x) => ({
      kind: 'form',
      box: { x, y: 90, width: 115, height: 65 },
    }));
    const d = doc([p]);
    const figures = d.blocks.filter((block) => block.role === 'figure');
    expect(figures).toHaveLength(2);
    expect(figures[0]?.source[0]?.itemIndices).toContain(0);
    expect(figures[1]?.source[0]?.itemIndices).toEqual([1, 2]);
    expect(figures.every((block) => block.source[0]!.boxes[0]!.width < 300)).toBe(true);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('keeps disconnected diagram pieces and small labels with their shared caption', () => {
    const p = page([
      item(0, 'Fig. 2. A chart above the diagram.', 310, 140, 190, 8),
      item(1, 'Fig. 3. Packet header with two panels', 310, 300, 245, 8),
      item(2, 'and a wrapped caption.', 310, 310, 180, 8),
      ...Array.from({ length: 8 }, (_, i) =>
        item(i + 3, `Left prose ${i}.`, 40, 220 + i * 14, 245),
      ),
      ...Array.from({ length: 5 }, (_, i) =>
        item(i + 11, `Right prose ${i}.`, 310, 340 + i * 14, 245),
      ),
    ]);
    p.graphics = [
      { kind: 'path', box: { x: 380, y: 70, width: 100, height: 60 } },
      { kind: 'image', box: { x: 333, y: 178, width: 65, height: 20 } },
      { kind: 'image', box: { x: 475, y: 178, width: 65, height: 20 } },
      { kind: 'path', box: { x: 333, y: 242, width: 207, height: 30 } },
      { kind: 'path', box: { x: 404, y: 165, width: 3, height: 5 } },
    ];
    const d = doc([p]);
    const figures = d.blocks.filter((block) => block.role === 'figure');
    expect(figures).toHaveLength(2);
    const diagram = figures.find((block) => block.source[0]?.itemIndices.includes(1));
    expect(diagram?.source[0]?.itemIndices).toEqual([1, 2]);
    expect(diagram?.source[0]?.boxes[0]?.y).toBeLessThanOrEqual(165);
    expect(diagram?.source[0]?.boxes[0]?.height).toBeGreaterThan(145);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('recognizes a standalone Roman table label without treating a table reference as a caption', () => {
    const p = page([
      item(0, 'TABLE I', 135, 100, 35, 8),
      item(1, 'MEASURED VALUES', 100, 111, 110, 8),
      item(2, 'Name     Value', 50, 137, 200, 8),
      item(3, 'Sample      12', 50, 153, 200, 8),
      item(4, 'Table I summarizes the results of this measurement.', 40, 200, 245),
      item(5, 'Further prose belongs outside the source table.', 40, 214, 245),
    ]);
    p.graphics = [130, 146, 167].map((y) => ({
      kind: 'rule',
      box: { x: 40, y, width: 245, height: 0.5 },
    }));
    const d = doc([p]);
    const tables = d.blocks.filter((block) => block.role === 'table');
    expect(tables).toHaveLength(1);
    expect(tables[0]?.source[0]?.itemIndices).toContain(0);
    expect(tables[0]?.source[0]?.itemIndices).not.toContain(4);
    expect(
      d.blocks.some(
        (block) => block.type !== 'visual-region' && block.text.startsWith('Table I summarizes'),
      ),
    ).toBe(true);
  });
  it('keeps thin-rule diagrams whose components are individually smaller than body text', () => {
    const p = page([
      item(0, 'Fig. 5. A compact window diagram.', 310, 105, 220, 8),
      ...Array.from({ length: 6 }, (_, i) =>
        item(i + 1, `Left body sentence ${i}.`, 40, 150 + i * 14, 245),
      ),
      ...Array.from({ length: 6 }, (_, i) =>
        item(i + 7, `Right body sentence ${i}.`, 310, 150 + i * 14, 245),
      ),
    ]);
    p.graphics = [
      { kind: 'rule', box: { x: 321, y: 72, width: 231, height: 1 } },
      ...Array.from({ length: 15 }, (_, i) => ({
        kind: 'path' as const,
        box: { x: 330 + i * 14, y: 84, width: 9, height: 5 },
      })),
    ];
    const d = doc([p]);
    expect(d.blocks.find((block) => block.role === 'figure')?.source[0]?.itemIndices).toContain(0);
  });
  it('suppresses repeated headers and page numbers, preserving source coverage', () => {
    const pages = [1, 2, 3].map((n) =>
      page(
        [
          item(0, 'Journal of examples 2026', 40, 30),
          item(1, `Body on page ${n}.`, 40, 140),
          item(2, `${n}`, 290, 765, 10),
          item(3, ' ', 40, 160, 10),
        ],
        n,
      ),
    );
    const d = doc(pages);
    expect(
      d.pages.every(
        (p) =>
          p.suppressedItemIndices.includes(0) &&
          p.suppressedItemIndices.includes(2) &&
          p.suppressedItemIndices.includes(3),
      ),
    ).toBe(true);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('joins only conservative line-end hyphens and soft hyphens', () => {
    expect(joinLines(['An inter-', 'connection works.'])).toBe('An interconnection works.');
    expect(joinLines(['The end-to-', 'end system.'])).toBe('The end-to-end system.');
    expect(joinLines(['Use GPU-', 'Based design.'])).toBe('Use GPU-Based design.');
    expect(joinLines(['A soft\u00ad', 'hyphen.'])).toBe('A softhyphen.');
  });
  it('removes inset alternating running headers before joining continued paragraphs', () => {
    const pages = [1, 2, 3, 4].map((n) =>
      page(
        [
          item(0, n % 2 ? 'Synthetic journal title' : 'Example contributors', 170, 96, 250, 9),
          item(1, `${n}`, n % 2 ? 550 : 40, 96, 8, 9),
          item(
            2,
            n === 1 ? 'An unfinished sentence, which' : 'continues on this page.',
            40,
            n === 1 ? 700 : 180,
            500,
          ),
          item(3, '8', 60, 130, 6, 7),
        ],
        n,
      ),
    );
    // The header is separated from the plot; the unrelated number inside the
    // plot must remain. Text immediately adjacent to a plot is tested below.
    pages.forEach((p) =>
      p.graphics.push({ kind: 'image', box: { x: 40, y: 125, width: 500, height: 35 } }),
    );
    const d = doc(pages);
    expect(
      d.pages.every(
        (p) => p.suppressedItemIndices.includes(0) && p.suppressedItemIndices.includes(1),
      ),
    ).toBe(true);
    expect(d.pages.every((p) => !p.suppressedItemIndices.includes(3))).toBe(true);
    expect(d.blocks.some((b) => b.text.includes('which continues on this page.'))).toBe(true);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('preserves repeated plot text and a larger first-page title in the inset band', () => {
    const pages = [1, 2, 3].map((n) =>
      page(
        [
          item(0, 'Repeated plot label', 90, 96, 250, 9),
          item(1, 'A complete body paragraph.', 40, 240, 500),
        ],
        n,
      ),
    );
    pages.forEach((p) =>
      p.graphics.push({ kind: 'image', box: { x: 60, y: 90, width: 440, height: 100 } }),
    );
    const first = page(
      [
        item(0, 'Repeated plot label', 70, 96, 450, 20),
        item(1, 'Ordinary article text.', 40, 240, 500),
      ],
      4,
    );
    const d = doc([...pages, first]);
    expect(d.pages.every((p) => !p.suppressedItemIndices.includes(0))).toBe(true);
  });
  it('keeps a wrapped numeric assignment in prose while preserving numbered lists', () => {
    const d = doc([
      page([
        item(0, 'In this experiment we set the selected retry count =', 40, 200, 450),
        item(1, '5. We compare the two methods.', 40, 214, 450),
        item(2, 'The following steps are required:', 40, 250, 450),
        item(3, '1. Prepare the input.', 40, 270, 450),
        item(4, '2. Check the result.', 40, 284, 450),
      ]),
    ]);
    expect(d.blocks[0]?.type).toBe('paragraph');
    expect(d.blocks[0]?.text).toBe(
      'In this experiment we set the selected retry count = 5. We compare the two methods.',
    );
    expect(d.blocks.find((b) => b.type === 'list')?.listItems).toEqual([
      '1. Prepare the input.',
      '2. Check the result.',
    ]);
  });
  it('retains a repeated shared legend immediately above paired plots', () => {
    const pages = [1, 2, 3].map((n) => {
      const p = page(
        [
          item(0, 'Control and treatment', 275, 96, 150, 9),
          item(1, `Figure ${n * 2 - 1}: First measurement.`, 80, 220, 265, 11),
          item(2, `Figure ${n * 2}: Second measurement.`, 353, 220, 265, 11),
          item(3, 'The body explains these results.', 70, 260, 560, 11),
        ],
        n,
      );
      p.width = 700;
      p.graphics.push(
        ...[80, 353].map((x) => ({
          kind: 'path' as const,
          box: { x, y: 114, width: 265, height: 86 },
        })),
      );
      return p;
    });
    const d = doc(pages);
    expect(d.pages.every((p) => !p.suppressedItemIndices.includes(0))).toBe(true);
    expect(d.blocks.filter((b) => b.role === 'figure')).toHaveLength(3);
    expect(
      d.blocks
        .filter((b) => b.role === 'figure')
        .every((b) => b.source[0]?.itemIndices.includes(0)),
    ).toBe(true);
  });
  it('does not remove repeated first body lines with normal line spacing', () => {
    const d = doc(
      [1, 2, 3].map((n) =>
        page(
          [
            item(0, 'The experiment begins with identical conditions', 40, 96, 500),
            item(1, 'and measures a different response each time.', 40, 110, 500),
          ],
          n,
        ),
      ),
    );
    expect(d.pages.every((p) => !p.suppressedItemIndices.includes(0))).toBe(true);
  });
  it('classifies headings, lists, references and footnotes without dropping raw items', () => {
    const p = page([
      item(0, '1 Introduction', 40, 100, 300, 16),
      item(1, 'An ordinary paragraph.', 40, 130, 420),
      item(2, '• First point', 40, 170, 420),
      item(3, '• Second point', 40, 190, 420),
      item(4, 'References', 40, 240, 200, 15),
      item(5, '[1] Example Author. A title.', 40, 270, 420),
      item(6, '1 A brief note.', 40, 710, 420, 7),
    ]);
    p.graphics = [{ kind: 'rule', box: { x: 40, y: 700, width: 100, height: 0.5 } }];
    const d = doc([p]);
    expect(d.blocks.map((b) => b.type)).toEqual(
      expect.arrayContaining(['heading', 'paragraph', 'list', 'reference', 'footnote']),
    );
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it.each([8, 16])('keeps a %i-prefixed body continuation in its paragraph', (count) => {
    // HPCC page 3 PDF.js geometry: narrow glyph boxes leave a 6.861 pt gap,
    // despite an ordinary 10.959 pt baseline advance. Labels are synthetic.
    const body = [
      'The evaluation includes several machines and',
      `${count} Edge nodes joined by fast links. We deliberately choose`,
      'representative traffic for the remaining measurements.',
    ].map((text, index) => ({
      ...item(index, text, 317.955, 600.987288 + index * 10.959, 240.249128832, 8.9664),
      box: {
        x: 317.955,
        y: 600.987288 + index * 10.959,
        width: 240.249128832,
        height: 4.0976448,
      },
      baseline: 605.067 + index * 10.959,
      fontName: 'g_d0_f6',
      fontFamily: 'sans-serif',
    }));
    const p = page(body, 3);
    p.width = 612;
    p.height = 792;
    const d = doc([p]);
    expect(d.blocks).toHaveLength(1);
    expect(d.blocks[0]?.type).toBe('paragraph');
    expect(d.blocks[0]?.text).toBe(body.map((i) => i.text).join(' '));
    expect(d.blocks[0]?.source[0]?.itemIndices).toEqual([0, 1, 2]);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('requires font evidence for numbered headings and retains opaque same-size heading styles', () => {
    const p = page([
      item(0, 'An ordinary body paragraph provides the dominant font.', 40, 100, 420),
      item(1, '2 Section title', 40, 150, 120, 10.8),
      item(2, 'More ordinary body prose supplies a reliable font sample.', 40, 180, 420),
      item(3, '2.1', 40, 220, 14),
      { ...item(4, 'Opaque styled title', 60, 220, 150), fontName: 'g_d0_f5' },
      item(5, 'A body-sized numbered sentence stays ordinary even when isolated.', 40, 250, 420),
      item(6, '8 More machines appear in the experiment.', 40, 290, 280),
      { ...item(7, '16', 40, 330, 12), fontName: 'g_d0_f5' },
      item(8, 'Workers appear with only their count emphasized.', 56, 330, 300),
    ]);
    const d = doc([p]);
    expect(d.blocks.filter((b) => b.type === 'heading').map((b) => [b.text, b.level])).toEqual([
      ['2 Section title', 2],
      ['2.1 Opaque styled title', 3],
    ]);
    expect(d.blocks.find((b) => b.text.startsWith('8 More'))?.type).toBe('paragraph');
    expect(d.blocks.find((b) => b.text.startsWith('16 Workers'))?.type).toBe('paragraph');
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('retains distinctly styled numbered run-in headings before same-baseline body text', () => {
    const p = page([
      item(0, 'Ordinary body prose establishes the document typeface.', 40, 100, 420),
      { ...item(1, '3.2.1', 40, 140, 22), fontName: 'g_d4_f21' },
      { ...item(2, 'Device behavior.', 72, 140, 85), fontName: 'g_d4_f21' },
      item(3, 'The rest of this line is ordinary paragraph prose.', 161, 140, 250),
      item(4, 'More body text continues on a later baseline.', 40, 154, 420),
    ]);
    const d = doc([p]);
    expect(d.blocks[1]?.type).toBe('heading');
    expect(d.blocks[1]?.level).toBe(3);
    expect(d.blocks[1]?.text).toBe(
      '3.2.1 Device behavior. The rest of this line is ordinary paragraph prose.',
    );
    expect(d.blocks[1]?.source[0]?.itemIndices).toEqual([1, 2, 3]);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('keeps an emphasized numbered paragraph lead and its unindented continuation together', () => {
    const p = page([
      item(0, 'Ordinary body prose establishes the document typeface.', 40, 100, 420),
      { ...item(1, '1) Tracking', 50, 140, 49), fontStyle: 'italic' as const },
      { ...item(2, 'received data:', 103, 140, 66), fontStyle: 'italic' as const },
      item(3, 'The receiver', 173, 140, 65),
      item(4, 'records each arrival in a compact data structure.', 40, 154, 420),
      item(5, '1) Ordinary item: the first instruction.', 40, 190, 250),
      item(6, '2) Another item: the second instruction.', 40, 204, 250),
    ]);
    const d = doc([p]);
    const paragraph = d.blocks.find((block) =>
      block.source.some((span) => span.itemIndices.includes(1)),
    )!;
    expect(paragraph.type).toBe('paragraph');
    expect(paragraph.text).toBe(
      '1) Tracking received data: The receiver records each arrival in a compact data structure.',
    );
    expect(paragraph.source[0]!.itemIndices).toEqual([1, 2, 3, 4]);
    expect(paragraph.inlineRuns?.find((run) => run.text === '1) Tracking')).toMatchObject({
      style: { fontStyle: 'italic' },
    });
    expect(d.blocks.find((block) => block.type === 'list')?.listItems).toEqual([
      '1) Ordinary item: the first instruction.',
      '2) Another item: the second instruction.',
    ]);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('retains display math as a visual region', () => {
    const p = page([
      item(0, 'A prose introduction.', 40, 120, 480),
      item(1, 'x = ∑ a² / b', 180, 170, 130),
      item(2, '(1)', 520, 170, 20),
      item(3, 'More ordinary prose.', 40, 220, 480),
    ]);
    const d = doc([p]);
    expect(d.blocks.some((b) => b.role === 'equation')).toBe(true);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('keeps short inline-math continuations and parameter prose in the text flow', () => {
    const p = page([
      item(0, 'A small loss can lead to a dramatic throughput degradation', 40, 120, 245),
      item(1, '(e.g., <≈60%) [2].', 40, 132, 80),
      item(2, 'Second, a single path cannot use the whole network.', 40, 144, 245),
      item(3, 'We select timing parameters from the prior experiment', 40, 180, 245),
      item(4, 'paper; Ti = 300μs, Td = 4μs, Ti = 900μs,', 40, 192, 245),
      item(5, 'and compare the results using the same workload.', 40, 204, 245),
      ...Array.from({ length: 6 }, (_, i) =>
        item(i + 6, `Right column body ${i}.`, 310, 120 + i * 14, 245),
      ),
    ]);
    const d = doc([p]);
    expect(d.blocks.filter((block) => block.role === 'equation')).toHaveLength(0);
    expect(d.blocks.map((block) => block.text).join(' ')).toContain('(e.g., <≈60%) [2].');
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('falls back conservatively for rotated body and textless scans', () => {
    const p = page([item(0, 'Rotated body text', 40, 150, 200)]);
    p.items[0]!.angle = Math.PI / 2;
    const d = doc([p, page([], 2)]);
    expect(d.blocks.every((b) => b.type === 'visual-region')).toBe(true);
    expect(d.pages[1]?.unsupportedReason).toMatch(/extractable/i);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('merges only compatible unfinished cross-page paragraphs and retains both spans', () => {
    const p1 = page([
      item(0, 'This unfinished paragraph continues', 40, 680, 480),
      item(1, 'across the', 40, 694, 480),
    ]);
    const p2 = page([item(0, 'next page before ending.', 40, 100, 480)], 2);
    const d = doc([p1, p2]);
    expect(d.blocks).toHaveLength(1);
    expect(d.blocks[0]?.source).toHaveLength(2);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('keeps simultaneous equations in separate columns and does not label years as headings', () => {
    const p = page([
      ...Array.from({ length: 4 }, (_, i) => item(i, `Left sentence ${i}.`, 40, 120 + i * 14)),
      ...Array.from({ length: 4 }, (_, i) =>
        item(i + 4, `Right sentence ${i}.`, 330, 120 + i * 14),
      ),
      item(8, 'x = a + b', 100, 220, 100),
      item(9, '(1)', 265, 220, 20),
      item(10, 'y = c + d', 380, 220, 100),
      item(11, '(2)', 555, 220, 20),
      item(12, '2019 Conference proceedings are here.', 40, 280),
      item(13, '60 Senders are used for the experiment.', 330, 280),
    ]);
    const d = doc([p]);
    const equations = d.blocks.filter((b) => b.role === 'equation');
    expect(equations).toHaveLength(2);
    expect(equations.every((b) => b.source[0]!.boxes[0]!.width < 300)).toBe(true);
    expect(d.blocks.find((b) => b.text.startsWith('2019'))?.type).toBe('paragraph');
    expect(d.blocks.find((b) => b.text.startsWith('60'))?.type).toBe('paragraph');
  });
  it('keeps wrapped list items together and carries the reference section across pages', () => {
    const p1 = page([
      item(0, '• A long first item', 40, 120, 420),
      item(1, 'continues on this line.', 52, 134, 408),
      item(2, '• Second item.', 40, 154, 420),
      item(3, 'References', 40, 600, 200, 15),
      item(4, '[1] A source title', 40, 630, 420),
    ]);
    const p2 = page(
      [
        item(0, 'and the rest of its citation.', 40, 100, 420),
        item(1, '[2] The next reference.', 40, 140, 420),
      ],
      2,
    );
    const d = doc([p1, p2]);
    expect(d.blocks.find((b) => b.type === 'list')?.listItems).toEqual([
      '• A long first item continues on this line.',
      '• Second item.',
    ]);
    expect(d.blocks.find((b) => b.text.startsWith('and the rest'))?.type).toBe('reference');
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('uses a complete-page visual fallback for three-column ambiguity', () => {
    const p = page(
      [40, 230, 420].flatMap((x, c) =>
        Array.from({ length: 6 }, (_, i) =>
          item(c * 6 + i, `Column ${c} sentence.`, x, 120 + i * 14, 140),
        ),
      ),
    );
    const d = doc([p]);
    expect(d.blocks).toHaveLength(1);
    expect(d.blocks[0]?.type).toBe('visual-region');
    expect(d.blocks[0]?.fallbackReason).toMatch(/three or more/i);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('keeps compact three-column prose out of the two-column path', () => {
    const p = page(
      [50, 205, 360].flatMap((x, c) =>
        Array.from({ length: 6 }, (_, i) =>
          item(c * 6 + i, `Column ${c} sentence.`, x, 100 + i * 14, 130),
        ),
      ),
    );
    const d = doc([p]);
    expect(d.pages[0]?.columns).toEqual([]);
    expect(d.blocks[0]?.fallbackReason).toMatch(/three or more/i);
  });
  it('keeps independently captioned figures separate without any body text columns', () => {
    const p = page([
      item(0, 'Figure 1. First measured plot.', 40, 220, 190),
      item(1, 'Figure 2. Second measured plot.', 360, 220, 190),
    ]);
    p.graphics = [40, 360].map((x) => ({
      kind: 'image',
      box: { x, y: 100, width: 200, height: 100 },
    }));
    const d = doc([p]);
    const figures = d.blocks.filter((block) => block.role === 'figure');
    expect(figures).toHaveLength(2);
    expect(figures.map((block) => block.source[0]?.itemIndices)).toEqual([[0], [1]]);
  });
  for (const captionWidth of [230, 265]) {
    it(`keeps nearby independently captioned plots separate above single-column prose (${captionWidth})`, () => {
      const p = page([
        item(0, 'Figure 12: First experiment.', 80, 220, captionWidth, 11),
        item(1, 'Figure 13: Second experiment.', 353, 220, captionWidth, 11),
        ...Array.from({ length: 8 }, (_, i) =>
          item(
            i + 2,
            `Ordinary body prose continues in one column with observation ${i}.`,
            70,
            233 + i * 14,
            560,
            11,
          ),
        ),
      ]);
      p.width = 700;
      p.graphics = [80, 353].map((x) => ({
        kind: 'path',
        box: { x, y: 100, width: 265, height: 100 },
      }));
      const d = doc([p]);
      const figures = d.blocks.filter((block) => block.role === 'figure');
      expect(d.pages[0]?.lines.filter((line) => /^Figure/.test(line.text))).toHaveLength(2);
      expect(figures).toHaveLength(2);
      expect(figures.map((block) => block.source[0]?.itemIndices)).toEqual([[0], [1]]);
      expect(figures.map((block) => block.captions?.map((caption) => caption.label))).toEqual([
        ['12'],
        ['13'],
      ]);
      expect(
        figures.every((block) => {
          const box = block.source[0]!.boxes[0]!;
          return box.y + box.height < 233;
        }),
      ).toBe(true);
      expect(
        d.blocks
          .filter((block) => block.type === 'paragraph')
          .flatMap((block) => block.source[0]!.itemIndices),
      ).toEqual([2, 3, 4, 5, 6, 7, 8, 9]);
      expect(d.pages[0]?.columns).toHaveLength(1);
      expect(validateSourceCoverage(d)).toEqual([]);
    });
  }
  it('recognizes independent caption starts fragmented by PDF font runs', () => {
    const p = page([
      item(0, 'Figure', 80, 220, 30, 11),
      item(1, '12:', 114, 220, 18, 11),
      item(2, 'First experiment.', 136, 220, 204, 11),
      item(3, 'Fig.', 353, 220, 20, 11),
      item(4, '13:', 377, 220, 18, 11),
      item(5, 'Second experiment.', 399, 220, 219, 11),
      item(
        6,
        'Figure 12 and Figure 13 are ordinary inline references in this paragraph.',
        70,
        260,
        560,
        11,
      ),
    ]);
    p.width = 700;
    const lines = clusterLines(p);
    expect(lines.map((line) => line.itemIndices)).toEqual([[0, 1, 2], [3, 4, 5], [6]]);
    expect(lines[0]?.text).toBe('Figure 12: First experiment.');
    expect(lines[1]?.text).toBe('Fig. 13: Second experiment.');
  });
  it('retains a shared legend and both caption associations in one visual', () => {
    const p = page([
      item(0, 'Figure 12: First measured plot.', 80, 220, 265, 11),
      item(1, 'Figure 13: Second measured plot.', 353, 220, 265, 11),
      item(2, 'with a continued explanation.', 353, 233, 185, 11),
      item(3, 'Control and treatment', 275, 82, 150, 9),
      item(
        4,
        'The second result in Figure 13 supplies the first useful observation.',
        70,
        260,
        560,
        11,
      ),
      item(
        5,
        'The first result in Figure 12 supplies a later useful observation.',
        70,
        300,
        560,
        11,
      ),
    ]);
    p.width = 700;
    p.graphics = [80, 353].map((x) => ({
      kind: 'path',
      box: { x, y: 100, width: 265, height: 100 },
    }));
    const d = doc([p]);
    const figures = d.blocks.filter((block) => block.role === 'figure');
    expect(figures).toHaveLength(1);
    expect(figures[0]?.source[0]?.itemIndices).toEqual([0, 1, 2, 3]);
    const firstMention = d.blocks.findIndex((block) => block.text.startsWith('The second result'));
    expect(d.blocks.indexOf(figures[0]!)).toBeLessThan(firstMention);
    expect(
      figures[0]?.captions?.map((caption) => ({
        label: caption.label,
        ids: caption.source.itemIndices,
      })),
    ).toEqual([
      { label: '12', ids: [0] },
      { label: '13', ids: [1, 2] },
    ]);
    expect(figures[0]?.captions?.[1]?.text).toBe(
      'Figure 13: Second measured plot. with a continued explanation.',
    );
    const crop = figures[0]!.source[0]!.boxes[0]!;
    expect(crop.y).toBeLessThanOrEqual(82);
    expect(crop.x).toBeLessThanOrEqual(80);
    expect(crop.x + crop.width).toBeGreaterThanOrEqual(618);
    expect(crop.y + crop.height).toBeGreaterThanOrEqual(244);
    expect(crop.y + crop.height).toBeLessThan(260);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('yields on long documents and stops at the next page after cancellation', async () => {
    const pages = Array.from({ length: 120 }, (_, n) =>
      page(
        Array.from({ length: 20 }, (_, i) =>
          item(i, 'A simple sentence for a long document.', 40, 120 + i * 14, 480),
        ),
        n + 1,
      ),
    );
    const controller = new AbortController();
    const progress: number[] = [];
    let timerRan = false;
    setTimeout(() => {
      timerRan = true;
    }, 0);
    await expect(
      analyzeDocumentAsync(pages, 'a'.repeat(64), '6.2.108', controller.signal, (completed) => {
        progress.push(completed);
        if (completed === 2) controller.abort();
      }),
    ).rejects.toMatchObject({ name: 'AbortError' });
    expect(timerRan).toBe(true);
    expect(progress).toEqual([1, 2]);
  });
  it('preserves an unnumbered fraction and Greek-only display expression', () => {
    const p = page([
      item(0, 'Ordinary surrounding prose.', 40, 120, 480),
      item(1, 'a + b', 220, 170, 70),
      item(2, 'c + d', 220, 188, 70),
      item(3, 'α² + β²', 200, 240, 120),
      item(4, 'More surrounding prose.', 40, 290, 480),
    ]);
    p.graphics = [{ kind: 'rule', box: { x: 216, y: 184, width: 78, height: 0.4 } }];
    const d = doc([p]);
    expect(d.blocks.filter((b) => b.role === 'equation')).toHaveLength(2);
    expect(d.blocks.some((b) => b.type === 'paragraph' && b.text.includes('a + b'))).toBe(false);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('cancels the yielding analysis path', async () => {
    const controller = new AbortController();
    controller.abort();
    await expect(
      analyzeDocumentAsync([page([])], 'a'.repeat(64), '6.2.108', controller.signal),
    ).rejects.toMatchObject({ name: 'AbortError' });
  });
});

it('does not attach a figure caption to a conservatively merged table region', () => {
  const p = page([
    item(0, 'Table 1: Synthetic values.', 40, 100),
    item(1, 'Figure 1: Synthetic illustration.', 40, 180),
    item(2, 'Figure 1 is discussed in this paragraph.', 40, 250),
    item(3, 'Table 1 is discussed in another paragraph.', 40, 280),
  ]);
  p.graphics.push({ kind: 'image', box: { x: 40, y: 120, width: 220, height: 50 } });
  const d = doc([p]);
  const region = d.blocks.find((b) => b.type === 'visual-region')!;
  expect(region.role).toBe('table');
  expect((region.captions ?? []).every((caption) => caption.role === region.role)).toBe(true);
  expect(region.order).toBeLessThan(d.blocks.find((b) => b.text.startsWith('Figure 1 is'))!.order);
  expect(validateSourceCoverage(d)).toEqual([]);
});

it('preserves the existing independent crops for three captioned plots above single-column prose', () => {
  const p = page([
    ...[40, 330, 620].map((x, i) => item(i, `Figure ${i + 1}: Synthetic plot.`, x, 180)),
    ...Array.from({ length: 8 }, (_, i) =>
      item(3 + i, `Full-width body line ${i}.`, 40, 220 + i * 14, 830),
    ),
  ]);
  p.width = 900;
  p.graphics = [40, 330, 620].map((x) => ({
    kind: 'image',
    box: { x, y: 80, width: 220, height: 80 },
  }));
  const d = doc([p]);
  const figures = d.blocks.filter((b) => b.role === 'figure');
  expect(figures).toHaveLength(3);
  expect(figures.flatMap((b) => b.captions?.map((c) => c.label) ?? [])).toEqual(['1', '2', '3']);
  expect(figures.every((b) => b.source[0]!.boxes[0]!.width < 250)).toBe(true);
  expect(validateSourceCoverage(d)).toEqual([]);
});
