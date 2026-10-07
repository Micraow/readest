import { describe, expect, it } from 'vitest';
import { analyzeDocument, validateSourceCoverage } from '@/services/academic/layout';
import type { PageGeometry, PdfTextItem } from '@/services/academic/types';

const item = (index: number, text: string, x: number, y: number, width = 220): PdfTextItem => ({
  index,
  text,
  box: { x, y, width, height: 10 },
  baseline: y + 8,
  fontSize: 10,
  fontName: 'body',
  fontFamily: 'serif',
  angle: 0,
  hasEOL: true,
});
const page = (page: number, items: PdfTextItem[]): PageGeometry => ({
  page,
  width: 600,
  height: 800,
  rotation: 0,
  items,
  graphics: [],
  tagged: false,
});
const floatingPage = (pageNumber = 2) => {
  const p = page(pageNumber, [
    item(0, 'Figure 1: Synthetic measurement.', 40, 170),
    item(1, 'consists of several connected switches.', 40, 205),
    item(2, 'Figure 1 summarizes the measurements.', 50, 235),
    item(3, 'The complete comparison is reproducible.', 40, 249),
    item(4, 'Another paragraph begins here.', 50, 280),
  ]);
  p.graphics.push({ kind: 'image', box: { x: 40, y: 45, width: 220, height: 115 } });
  return p;
};
const analyze = (pages: PageGeometry[]) => analyzeDocument(pages, 'synthetic-flow', 'test');

describe('continuous prose around floating figures', () => {
  it('keeps a display equation beside its introducing paragraph before deferred floats', () => {
    const first = page(1, [item(0, 'This leads to', 40, 700)]);
    const next = floatingPage();
    next.items = [
      item(0, 'Figure 1: Synthetic measurement.', 40, 170),
      item(1, 'the available value:', 40, 205),
      item(2, 'z = a + b', 80, 235, 100),
      item(3, 'The next paragraph explains the result.', 50, 280),
    ];
    const d = analyze([first, next]);
    const intro = d.blocks.findIndex((b) => b.text === 'This leads to the available value:');
    expect(intro).toBeGreaterThanOrEqual(0);
    expect(d.blocks[intro + 1]?.role).toBe('equation');
    expect(d.blocks[intro + 2]?.role).toBe('figure');
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('uses surrounding prose size to continue a script-dense line across a floating figure', () => {
    const left = Array.from({ length: 6 }, (_, i) =>
      item(i, i === 5 ? 'The result is' : `Left observation ${i}.`, 40, 300 + i * 14),
    );
    const prefix = item(6, 'continuing with rates', 40, 384, 120);
    const scripts = Array.from({ length: 12 }, (_, i) => ({
      ...item(7 + i, String(i % 10), 163 + i * 4, 388.4, 3),
      fontSize: 7,
      baseline: 394,
      box: { x: 163 + i * 4, y: 388.4, width: 3, height: 7 },
    }));
    const p = page(1, [
      ...left,
      prefix,
      ...scripts,
      item(19, 'is the input', 216, 384, 44),
      item(20, 'Figure 1: Synthetic result.', 330, 170),
      item(21, 'rate for the model.', 330, 205),
      ...Array.from({ length: 5 }, (_, i) =>
        item(22 + i, `Right observation ${i}.`, 330, 240 + i * 14),
      ),
    ]);
    p.graphics.push({ kind: 'image', box: { x: 330, y: 45, width: 220, height: 115 } });
    const d = analyze([p]);
    const joined = d.blocks.find((b) => b.text.includes('is the input rate for the model.'));
    expect(joined).toBeDefined();
    expect(joined?.text).toContain('The result is continuing with rates');
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('separates a styled lettered section heading from a wrapped first paragraph', () => {
    const p = page(1, [
      ...Array.from({ length: 6 }, (_, i) =>
        item(i, `Normal body observation ${i}.`, 40, 100 + i * 14),
      ),
      { ...item(6, 'C. Out-of-Order Selection', 40, 240), fontName: 'section-italic' },
      item(7, 'The method considers paral-', 50, 265),
      item(8, 'lelism in the network.', 40, 279),
      item(9, 'A. First ordinary option', 40, 320),
      item(10, 'B. Second ordinary option', 40, 334),
    ]);
    const d = analyze([p]);
    expect(d.blocks.find((b) => b.text === 'C. Out-of-Order Selection')?.type).toBe('heading');
    expect(d.blocks.find((b) => b.text.includes('parallelism in the network.'))?.type).toBe(
      'paragraph',
    );
    expect(d.blocks.find((b) => b.text.startsWith('A. First ordinary'))?.type).toBe('list');
  });
  it.each([
    ['Packets with a higher', 'cost are rerouted.'],
    [
      'Packets below QueueCost leave directly, while packets with a higher',
      'QueueCost are rerouted.',
    ],
  ])('joins a cross-page sentence around a floating algorithm: %s', (before, after) => {
    const first = page(1, [item(0, before, 40, 700)]);
    const next = page(2, [
      item(0, 'Algorithm 1: Synthetic forwarding procedure.', 40, 70),
      item(1, '1. Inspect the queue and forward the packet.', 40, 100),
      item(2, after, 40, 205),
      item(3, 'The next paragraph explains the result.', 50, 235),
    ]);
    next.graphics.push(
      ...[65, 160].map((y) => ({
        kind: 'rule' as const,
        box: { x: 40, y, width: 220, height: 0.5 },
      })),
    );
    const d = analyze([first, next]);
    const joined = d.blocks.find((b) => b.text === `${before} ${after}`);
    expect(joined).toBeDefined();
    expect(joined?.source.map((s) => s.page)).toEqual([1, 2]);
    const algorithm = d.blocks.find((b) => b.role === 'algorithm');
    expect(algorithm).toBeDefined();
    expect(d.blocks.indexOf(algorithm!)).toBeGreaterThan(d.blocks.indexOf(joined!));
    expect(algorithm?.source[0]?.itemIndices).toContain(0);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('keeps a same-column algorithm as a boundary even beside a floating figure', () => {
    const p = page(1, [
      item(0, 'This introduction ends with', 40, 100),
      item(1, 'Algorithm 1: Synthetic procedure.', 40, 150),
      item(2, 'Figure 1: Synthetic result.', 40, 290),
      item(3, 'a separate continuation below the procedure.', 40, 330),
    ]);
    p.graphics.push(
      { kind: 'image', box: { x: 40, y: 120, width: 220, height: 20 } },
      { kind: 'image', box: { x: 40, y: 210, width: 220, height: 70 } },
      ...[145, 195].map((y) => ({
        kind: 'rule' as const,
        box: { x: 40, y, width: 220, height: 0.5 },
      })),
    );
    const d = analyze([p]);
    expect(d.blocks.filter((b) => b.type === 'paragraph').map((b) => b.text)).toEqual([
      'This introduction ends with',
      'a separate continuation below the procedure.',
    ]);
    expect(d.blocks.some((b) => b.role === 'algorithm')).toBe(true);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('finishes the interrupted paragraph before its nearby float without moving it to a later citation', () => {
    const first = page(1, [item(0, 'A deployment group, which', 40, 700)]);
    const d = analyze([first, floatingPage()]);
    expect(d.blocks[0]?.text).toBe(
      'A deployment group, which consists of several connected switches.',
    );
    expect(d.blocks[0]?.source.map((s) => s.page)).toEqual([1, 2]);
    const figure = d.blocks.findIndex((b) => b.role === 'figure');
    const reference = d.blocks.findIndex((b) => b.text.startsWith('Figure 1 summarizes'));
    expect(figure).toBe(1);
    expect(figure).toBeLessThan(reference);
    expect(d.blocks[reference]?.text).toContain('The complete comparison is reproducible.');
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('keeps a wrapped explanatory dash in prose rather than inventing a list', () => {
    const first = page(1, [
      item(0, 'The network has three layers', 50, 680),
      item(1, '– edge, aggregation and core. A group, which', 40, 694),
    ]);
    const d = analyze([first, floatingPage()]);
    expect(d.blocks[0]?.type).toBe('paragraph');
    expect(d.blocks[0]?.text).toBe(
      'The network has three layers – edge, aggregation and core. A group, which consists of several connected switches.',
    );
    expect(d.blocks.some((b) => b.type === 'list')).toBe(false);
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('does not mistake Figure 10 for a reference to Figure 1', () => {
    const next = floatingPage(1);
    next.items[2]!.text = 'Figure 10 is discussed in this paragraph.';
    const d = analyze([next]);
    expect(d.blocks.findIndex((b) => b.role === 'figure')).toBeLessThan(
      d.blocks.findIndex((b) => b.text.startsWith('Figure 10')),
    );
  });

  it('keeps the source position regardless of later integer or decimal references', () => {
    const next = floatingPage(1);
    next.items[0]!.text = 'Figure 2: Synthetic measurements.';
    next.items[2]!.text = 'As Figure 2.1 showed, an earlier result was different.';
    next.items[4]!.text = 'Figure 2 is discussed in this complete paragraph.';
    const d = analyze([next]);
    expect(d.blocks[0]?.role).toBe('figure');
  });

  it.each([
    'Figures 2 and 3',
    'Figures 2–3',
  ])('keeps grouped floats in source order before a later %s citation', (reference) => {
    const p = page(1, [
      item(0, 'Figure 2: One result.', 40, 80),
      item(1, 'Figure 3: Another result.', 40, 190),
      item(2, `${reference} summarize the measurements.`, 40, 230),
    ]);
    p.graphics.push(
      { kind: 'image', box: { x: 40, y: 20, width: 220, height: 50 } },
      { kind: 'image', box: { x: 40, y: 110, width: 220, height: 70 } },
    );
    const d = analyze([p]);
    expect(d.blocks.map((b) => b.type)).toEqual(['visual-region', 'visual-region', 'paragraph']);
    expect(d.blocks[0]?.source[0]?.itemIndices).toContain(0);
    expect(d.blocks[1]?.source[0]?.itemIndices).toContain(1);
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('retains a Roman-numbered table at its source boundary', () => {
    const next = floatingPage(1);
    next.items[0]!.text = 'Table I: Synthetic measurements.';
    next.items[2]!.text = 'Table I summarizes the measurements.';
    const d = analyze([next]);
    expect(d.blocks[0]?.role).toBe('table');
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('keeps adjacent figures left-to-right despite unequal plot heights and reversed discussion order', () => {
    const p = page(1, [
      item(0, 'Figure 3: Left measurement.', 40, 200, 220),
      item(1, 'Figure 4: Right measurement.', 330, 200, 220),
      item(2, 'Figure 4 is discussed first in this paragraph.', 40, 240, 510),
      item(3, 'Figure 3 is discussed in a later paragraph.', 50, 280, 500),
    ]);
    p.graphics.push(
      { kind: 'image', box: { x: 40, y: 100, width: 220, height: 85 } },
      { kind: 'image', box: { x: 330, y: 75, width: 220, height: 110 } },
    );
    const d = analyze([p]);
    expect(
      d.blocks.filter((b) => b.role === 'figure').flatMap((b) => b.captions!.map((c) => c.label)),
    ).toEqual(['3', '4']);
    expect(d.blocks.slice(0, 2).every((b) => b.type === 'visual-region')).toBe(true);
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('preserves consecutive dash list items even when their introduction has no colon', () => {
    const d = analyze([
      page(1, [
        item(0, 'Available options', 40, 200),
        item(1, '– first choice', 40, 214),
        item(2, '– second choice', 40, 228),
      ]),
    ]);
    expect(d.blocks.find((b) => b.type === 'list')?.listItems).toHaveLength(2);
  });

  it('does not turn uniform wider leading into a paragraph break after every sentence', () => {
    const d = analyze([
      page(1, [
        item(0, 'The first sentence ends here.', 40, 200),
        item(1, 'The next sentence shares the paragraph.', 40, 216),
        item(2, 'The final sentence does too.', 40, 232),
      ]),
    ]);
    expect(d.blocks).toHaveLength(1);
  });

  it('separates complete discussion paragraphs with modest additional line spacing', () => {
    const d = analyze([
      page(1, [
        item(0, 'Throughput is discussed in Figure 2.', 40, 200),
        item(1, 'This completes the first discussion.', 40, 214),
        item(2, 'Latency is discussed in Figure 3.', 40, 230),
      ]),
    ]);
    expect(d.blocks.filter((b) => b.type === 'paragraph').map((b) => b.text)).toEqual([
      'Throughput is discussed in Figure 2. This completes the first discussion.',
      'Latency is discussed in Figure 3.',
    ]);
  });

  it('keeps real dash lists after a colon and does not join a new capitalized paragraph', () => {
    const first = page(1, [
      item(0, 'The choices are:', 40, 650),
      item(1, '– first choice', 40, 670),
      item(2, '– second choice', 40, 684),
    ]);
    const next = floatingPage();
    next.items[1]!.text = 'Independent findings begin here.';
    const d = analyze([first, next]);
    expect(d.blocks.find((b) => b.type === 'list')?.listItems).toHaveLength(2);
    expect(d.blocks.some((b) => b.text === 'Independent findings begin here.')).toBe(true);
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('continues an unfinished sentence across columns while retaining a single page source entry', () => {
    const p = page(1, [
      ...Array.from({ length: 6 }, (_, i) =>
        item(i, i === 5 ? 'The result continues with' : `Left observation ${i}.`, 40, 300 + i * 14),
      ),
      item(6, 'Figure 1: Synthetic result.', 330, 170),
      item(7, 'the remaining observations.', 330, 205),
      ...Array.from({ length: 5 }, (_, i) =>
        item(8 + i, `Right observation ${i}.`, 330, 240 + i * 14),
      ),
    ]);
    p.graphics.push({ kind: 'image', box: { x: 330, y: 45, width: 220, height: 115 } });
    const d = analyze([p]);
    expect(d.pages[0]?.columns).toHaveLength(2);
    const joined = d.blocks.find((b) =>
      b.text.includes('The result continues with the remaining observations.'),
    );
    expect(joined).toBeDefined();
    expect(joined?.source).toHaveLength(1);
    expect(new Set(d.pages[0]?.blockIds).size).toBe(d.pages[0]?.blockIds.length);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
});
