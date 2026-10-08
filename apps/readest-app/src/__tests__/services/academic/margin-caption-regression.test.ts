import { describe, expect, it } from 'vitest';
import {
  analyzeDocument,
  clusterLines,
  joinLines,
  validateSourceCoverage,
} from '@/services/academic/layout';
import type { PageGeometry, PdfTextItem } from '@/services/academic/types';

const text = (
  index: number,
  value: string,
  x: number,
  y: number,
  width = 220,
  size = 10,
): PdfTextItem => ({
  index,
  text: value,
  box: { x, y, width, height: size },
  baseline: y + size * 0.8,
  fontSize: size,
  fontName: 'body',
  fontFamily: 'serif',
  angle: 0,
  hasEOL: true,
});
const page = (items: PdfTextItem[]): PageGeometry => ({
  page: 1,
  width: 600,
  height: 800,
  rotation: 0,
  tagged: false,
  items,
  graphics: [],
});
const analyze = (p: PageGeometry) => analyzeDocument([p], 'synthetic-margins-captions', 'test');

describe('margins and multi-caption figure bands', () => {
  it('does not cluster a rotated margin stamp with ordinary body baselines', () => {
    const stamp = {
      ...text(9, 'arXiv:0000.00000v1', 15, 210, 20, 20),
      angle: -Math.PI / 2,
      baseline: 557,
      box: { x: 15, y: 210, width: 20, height: 340 },
    };
    const p = page([
      text(0, 'The abstract starts here.', 50, 220),
      text(1, 'The introduction starts here.', 50, 532),
      text(2, 'A continuous body sentence starts', 50, 544),
      text(3, 'and finishes on the next line.', 50, 556),
      stamp,
    ]);
    const d = analyze(p);
    expect(d.blocks.map((b) => b.text).join(' ')).toBe(
      'The abstract starts here. The introduction starts here. A continuous body sentence starts and finishes on the next line.',
    );
    expect(d.pages[0]?.suppressedItemIndices).toContain(9);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('suppresses isolated centered page numbers just below inset body bottoms', () => {
    const p = page([
      text(0, 'Earlier body text sets the paragraph size.', 50, 100),
      text(1, 'This sentence ends near the page bottom.', 50, 692),
      text(2, '1', 297, 715, 5, 8),
    ]);
    const d = analyze(p);
    expect(d.pages[0]?.suppressedItemIndices).toContain(2);
    expect(d.blocks.map((b) => b.text).join(' ')).not.toMatch(/\b1\b/);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('does not extend a display crop to an already suppressed footer number', () => {
    const p = page([
      text(0, 'Ordinary body prose establishes the typography.', 40, 100, 480),
      text(1, 'The calculation uses the following relation.', 40, 660, 480),
      text(2, 'x = y + z', 90, 688, 150),
      text(3, '+ t', 90, 702, 30, 8),
      text(4, '1', 297, 715, 5, 8),
    ]);
    const d = analyze(p);
    expect(d.pages[0]?.suppressedItemIndices).toContain(4);
    const equation = d.blocks.find((b) => b.role === 'equation');
    expect(equation).toBeDefined();
    const box = equation!.source[0]!.boxes[0]!;
    expect(box.y + box.height).toBeLessThan(715);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('keeps small subscripts with nearby body words rather than a remote footnote baseline', () => {
    const p = page([
      text(0, 'An earlier body paragraph.', 40, 100),
      text(1, 'Another body paragraph.', 40, 120),
      text(2, 'Body variable v', 40, 680, 100),
      text(3, '1', 142, 685.4, 4, 7),
      text(4, 'continues here.', 148, 680, 105),
      text(5, 'A distant footnote line.', 330, 684.6, 220, 8),
    ]);
    const lines = clusterLines(p);
    expect(lines.find((l) => l.itemIndices.includes(2))?.itemIndices).toEqual([2, 3, 4]);
  });
  it('joins CJK line endings without introducing word spaces', () => {
    expect(joinLines(['一个连续的中', '文句子。'])).toBe('一个连续的中文句子。');
    expect(joinLines(['第一句。', '第二句。'])).toBe('第一句。第二句。');
    expect(joinLines(['换行处', '（说明）'])).toBe('换行处（说明）');
    expect(joinLines(['An ordinary English', 'sentence.'])).toBe('An ordinary English sentence.');
  });
  it('does not classify body prose as a footnote because a fraction has many small glyphs', () => {
    const p = page([
      text(0, 'Earlier ordinary body text.', 40, 100),
      text(1, 'Another ordinary body row.', 40, 120),
      text(2, 'The next body ratio uses', 40, 590, 120),
      ...Array.from({ length: 5 }, (_, i) =>
        text(3 + i, String.fromCharCode(97 + i), 164 + i * 5, 587, 4, 7),
      ),
      text(8, 'z', 174, 598, 4, 7),
      text(9, 'ordinary words.', 198, 590, 95),
    ]);
    p.graphics = [
      { kind: 'rule', box: { x: 160, y: 559, width: 28, height: 0.5 } },
      { kind: 'rule', box: { x: 163, y: 595, width: 28, height: 0.5 } },
    ];
    const d = analyze(p);
    expect(d.blocks.some((b) => b.type === 'footnote')).toBe(false);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('keeps three independently labeled captions in one shared figure band without duplicating pixels', () => {
    const p = page([
      text(0, 'Figure 1: First result', 40, 250, 130),
      text(1, 'finishes here.', 40, 262, 90),
      text(2, 'Figure 2: Second result', 195, 250, 130),
      text(3, 'finishes separately.', 195, 262, 125),
      text(4, 'Figure 3: Third result', 350, 250, 200),
      text(5, 'has its own continuation.', 350, 262, 190),
      ...Array.from({ length: 6 }, (_, i) =>
        text(20 + i, `Left body observation ${i}.`, 40, 310 + i * 14),
      ),
      ...Array.from({ length: 6 }, (_, i) =>
        text(30 + i, `Right body observation ${i}.`, 330, 310 + i * 14),
      ),
    ]);
    p.graphics = [40, 195, 350].map((x) => ({
      kind: 'image',
      box: { x, y: 100, width: 130, height: 130 },
    }));
    const d = analyze(p);
    const figures = d.blocks.filter((b) => b.role === 'figure');
    expect(figures.every((b) => b.source.some((s) => s.itemIndices.length))).toBe(true);
    const captions = figures.flatMap((b) => b.captions ?? []);
    expect(captions.map((c) => c.text)).toEqual([
      'Figure 1: First result finishes here.',
      'Figure 2: Second result finishes separately.',
      'Figure 3: Third result has its own continuation.',
    ]);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('keeps a shared legend spanning four panels in one unduplicated figure row', () => {
    const p = page([
      ...[40, 175, 310, 445].flatMap((x, i) => [
        text(i * 2, `Figure ${i + 1}: Result`, x, 240, 120),
        text(i * 2 + 1, 'Continued caption.', x, 254, 115),
      ]),
      text(10, 'Shared legend', 285, 90, 65, 7),
      ...Array.from({ length: 6 }, (_, i) =>
        text(20 + i, `Left body observation ${i}.`, 40, 310 + i * 14, 240),
      ),
      ...Array.from({ length: 6 }, (_, i) =>
        text(30 + i, `Right body observation ${i}.`, 320, 310 + i * 14, 240),
      ),
    ]);
    p.graphics = [50, 185, 320, 455].map((x) => ({
      kind: 'image',
      box: { x, y: 110, width: 100, height: 115 },
    }));
    p.graphics.push(
      ...[270, 355].map((x) => ({
        kind: 'path' as const,
        box: { x, y: 90, width: 10, height: 7 },
      })),
    );
    const d = analyze(p);
    const figures = d.blocks.filter((b) => b.role === 'figure');
    expect(figures).toHaveLength(1);
    expect(figures[0]?.captions?.map((c) => c.label)).toEqual(['1', '2', '3', '4']);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('orders neighboring captions left to right despite slightly staggered caption tops', () => {
    const p = page([
      text(0, 'Figure 1: First.', 40, 204, 120),
      text(1, 'Figure 2: Second.', 195, 200, 120),
      text(2, 'Figure 3: Third.', 350, 203, 190),
      text(3, 'An ordinary following body paragraph.', 40, 270, 500),
    ]);
    p.graphics = [{ kind: 'image', box: { x: 40, y: 90, width: 500, height: 100 } }];
    const d = analyze(p);
    expect(
      d.blocks
        .filter((b) => b.role === 'figure')
        .flatMap((b) => b.captions ?? [])
        .map((c) => c.label),
    ).toEqual(['1', '2', '3']);
  });
  it('retains caption rows whose font metrics have short ink boxes', () => {
    const captions = [
      text(0, 'Figure 1: The first caption line.', 40, 200, 220),
      text(1, 'Its second caption line.', 40, 212, 220),
    ];
    captions.forEach((item) => {
      item.box.height = 4.5;
      item.baseline = item.box.y + 4.5;
    });
    const p = page([
      ...captions,
      text(2, 'The following body paragraph starts here.', 40, 250, 500),
    ]);
    p.graphics = [{ kind: 'image', box: { x: 40, y: 90, width: 220, height: 90 } }];
    const d = analyze(p);
    expect(d.blocks.find((b) => b.role === 'figure')?.captions?.[0]?.text).toBe(
      'Figure 1: The first caption line. Its second caption line.',
    );
    const preview = d.blocks.find((b) => b.role === 'figure')?.previewBox;
    expect(preview!.y + preview!.height).toBeLessThanOrEqual(196.3);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
});
