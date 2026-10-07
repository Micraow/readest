import { describe, expect, it } from 'vitest';
import { analyzeDocument, clusterLines, validateSourceCoverage } from '@/services/academic/layout';
import type { PageGeometry, PdfTextItem } from '@/services/academic/types';

const text = (
  index: number,
  value: string,
  x: number,
  y: number,
  width: number,
  fontSize = 10,
): PdfTextItem => ({
  index,
  text: value,
  box: { x, y, width, height: fontSize },
  baseline: y + fontSize * 0.8,
  fontSize,
  fontName: 'synthetic',
  fontFamily: 'serif',
  angle: 0,
  hasEOL: true,
});
const page = (items: PdfTextItem[]): PageGeometry => ({
  page: 1,
  width: 600,
  height: 800,
  rotation: 0,
  items,
  graphics: [],
  tagged: false,
});
const analyze = (p: PageGeometry) => analyzeDocument([p], 'synthetic-prose-boundaries', 'test');

describe('prose boundaries around headers and mathematics', () => {
  it('keeps tightly spaced spanning authors above independent body columns', () => {
    const p = page([
      text(0, 'A synthetic research title', 50, 50, 500, 18),
      text(1, 'First Author, Second Author,', 80, 100, 219, 12),
      text(2, ' Third Author, Fourth Author', 300, 100, 210, 12),
      text(3, '∗', 511, 93, 5, 8),
      ...Array.from({ length: 5 }, (_, index) =>
        text(index + 4, `Left body sentence ${index}.`, 40, 200 + index * 14, 240),
      ),
      ...Array.from({ length: 5 }, (_, index) =>
        text(
          index + 9,
          index === 0 ? 'efficient and predictable service.' : `Right body sentence ${index}.`,
          320,
          200 + index * 14,
          240,
        ),
      ),
      text(14, 'The control should concurrently', 40, 650, 240),
      text(15, 'provide', 40, 664, 240),
      text(16, '5 A contributor note.', 40, 706, 180, 8),
    ]);
    const lines = clusterLines(p);
    expect(lines.find((line) => line.itemIndices.includes(1))?.itemIndices).toEqual([1, 2, 3]);
    const d = analyze(p);
    expect(d.blocks.find((block) => block.text.includes('First Author'))?.text).toBe(
      'First Author, Second Author, Third Author, Fourth Author∗',
    );
    expect(d.pages[0]!.columns).toHaveLength(2);
    expect(d.pages[0]!.columns.every((column) => column.box.y >= 200)).toBe(true);
    const intro = d.blocks.findIndex((block) => block.text.startsWith('The control should'));
    expect(d.blocks[intro]!.text).toContain(
      'concurrently provide efficient and predictable service.',
    );
    expect(d.blocks[intro + 1]!.type).toBe('footnote');
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('keeps following prose outside oversized nominal delimiter bounds', () => {
    const brace = text(1, '⎩', 130, 150, 8);
    brace.box.height = 80;
    brace.baseline = 178;
    const p = page([
      text(0, 'The update is defined by the following expression.', 40, 120, 500),
      brace,
      text(2, 'z = a + b', 145, 170, 160),
      text(3, '(2)', 520, 170, 20),
      text(4, 'The current estimate is updated after each response.', 40, 210, 500),
      text(5, 'This explanation remains selectable prose.', 40, 224, 500),
    ]);
    const d = analyze(p);
    const equation = d.blocks.find((block) => block.role === 'equation')!;
    const crop = equation.source[0]!.boxes[0]!;
    expect(crop.y + crop.height).toBeLessThan(210);
    expect(equation.source[0]!.itemIndices).not.toContain(4);
    expect(d.blocks.find((block) => block.text.startsWith('The current estimate'))?.text).toBe(
      'The current estimate is updated after each response. This explanation remains selectable prose.',
    );
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('keeps a hyphenated mathematical prose continuation out of the next display', () => {
    const p = page([
      text(0, 'The estimate approaches the desti-', 40, 100, 480),
      text(1, 'nation point [x,y] = (a,0).', 40, 112, 480),
      text(2, 'δ = a + b', 180, 130, 160),
      text(3, '(3)', 520, 130, 20),
      text(4, 'Another ordinary paragraph begins here.', 40, 180, 480),
    ]);
    const d = analyze(p);
    expect(d.blocks[0]!.text).toBe('The estimate approaches the destination point [x,y] = (a,0).');
    expect(
      d.blocks.find((block) => block.role === 'equation')?.source[0]?.itemIndices,
    ).not.toContain(1);
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('uses a nearby fraction rule to attach the raised numerator to its prose row', () => {
    const p = page([
      text(0, 'The ratio', 40, 150, 78),
      text(1, 'a', 130, 148, 8, 7),
      text(2, 'b', 123, 156, 22, 7),
      text(3, 'is updated after each response.', 152, 150, 250),
    ]);
    p.graphics = [{ kind: 'rule', box: { x: 121, y: 155, width: 27, height: 0.4 } }];
    expect(clusterLines(p)).toHaveLength(1);
    const d = analyze(p);
    expect(d.blocks).toHaveLength(1);
    expect(d.blocks[0]!.type).toBe('paragraph');
    expect(
      d.blocks[0]!.inlineRuns?.find((run) => run.kind === 'source')?.source.itemIndices,
    ).toEqual([1, 2]);
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('keeps full-margin parameter definitions with prose connectives selectable', () => {
    const p = page([
      text(0, 'The configuration is selected for the measured workload:', 40, 100, 480),
      text(1, 'p = 8 units × a/b and q = 9 units × c/d according', 40, 112, 480),
      text(2, 'to the preceding measurement procedure.', 40, 124, 480),
    ]);
    const d = analyze(p);
    expect(d.blocks.some((block) => block.role === 'equation')).toBe(false);
    expect(d.blocks.map((block) => block.text).join(' ')).toContain(
      'p = 8 units × a/b and q = 9 units × c/d according to the preceding measurement procedure.',
    );
    expect(validateSourceCoverage(d)).toEqual([]);
  });
});
