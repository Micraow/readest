import { describe, expect, it } from 'vitest';
import { analyzeDocument, clusterLines, validateSourceCoverage } from '@/services/academic/layout';
import type { PageGeometry, Rect, ScholarlyDocument } from '@/services/academic/types';
import hpccFixture from './fixtures/reflow-hpcc.geometry.json';
import mprdmaFixture from './fixtures/reflow-mprdma.geometry.json';

type Figure = {
  page: number;
  number: number;
  sourceBounds: Rect;
  captionItemIndices: number[];
  itemIndices: number[];
  graphicIndices: number[];
};
type ColumnBody = { page: number; gutter: number; leftIndices: number[]; rightIndices: number[] };
type FixtureDocument = {
  id: string;
  sourceSha256: string;
  pages: PageGeometry[];
  expect: {
    figures: Figure[];
    columnBody: ColumnBody[];
    inlineMath: Array<{ page: number; itemIndices: number[] }>;
  };
};
const fixture = {
  pdfjsVersion: hpccFixture.pdfjsVersion,
  documents: [hpccFixture, mprdmaFixture],
} as unknown as { pdfjsVersion: string; documents: FixtureDocument[] };
const owners = (d: ScholarlyDocument, page: number, index: number) =>
  d.blocks.filter((b) => b.source.some((s) => s.page === page && s.itemIndices.includes(index)));
const contains = (outer: Rect, inner: Rect, tolerance = 1.5) =>
  outer.x <= inner.x + tolerance &&
  outer.y <= inner.y + tolerance &&
  outer.x + outer.width >= inner.x + inner.width - tolerance &&
  outer.y + outer.height >= inner.y + inner.height - tolerance;

for (const input of fixture.documents) {
  describe(`${input.id} source-derived redacted regression`, () => {
    const d = analyzeDocument(input.pages, input.sourceSha256, fixture.pdfjsVersion);
    it('assigns every source item once or suppresses it explicitly', () => {
      expect(validateSourceCoverage(d)).toEqual([]);
    });
    for (const body of input.expect.columnBody) {
      it(`page ${body.page} keeps lines and prose blocks inside their source column`, () => {
        const p = input.pages.find((p) => p.page === body.page)!;
        const left = new Set(body.leftIndices),
          right = new Set(body.rightIndices);
        const mixes = (ids: number[]) =>
          ids.some((i) => left.has(i)) && ids.some((i) => right.has(i));
        expect(clusterLines(p).filter((line) => mixes(line.itemIndices))).toEqual([]);
        expect(
          d.blocks.filter(
            (b) =>
              b.type !== 'visual-region' &&
              b.source.some((s) => s.page === body.page && mixes(s.itemIndices)),
          ),
        ).toEqual([]);
      });
      it(`page ${body.page} finishes left-column prose before right-column prose`, () => {
        const order = (ids: number[]) =>
          ids.flatMap((id) => owners(d, body.page, id).map((b) => b.order));
        const left = order(body.leftIndices),
          right = order(body.rightIndices);
        expect(left.length).toBeGreaterThan(0);
        expect(right.length).toBeGreaterThan(0);
        expect(Math.max(...left)).toBeLessThan(Math.min(...right));
      });
      it(`page ${body.page} does not hide ordinary body text in visual crops`, () => {
        const swallowed = [...body.leftIndices, ...body.rightIndices].filter((id) =>
          owners(d, body.page, id).some((b) => b.type === 'visual-region'),
        );
        expect(swallowed).toEqual([]);
      });
    }
    for (const figure of input.expect.figures) {
      it(`page ${figure.page} figure ${figure.number} keeps every caption row, panel, and tiny mark in one local crop`, () => {
        const p = input.pages.find((p) => p.page === figure.page)!;
        const owner = owners(d, figure.page, figure.captionItemIndices[0]!).find(
          (b) => b.type === 'visual-region' && b.role === 'figure',
        );
        expect(owner).toBeDefined();
        const source = owner!.source.find((s) => s.page === figure.page)!;
        const crop = source.boxes[0]!;
        expect(figure.captionItemIndices.filter((i) => !source.itemIndices.includes(i))).toEqual(
          [],
        );
        // Numeric axis labels in the top margin can be text-suppressed. They must
        // still be inside the rendered crop; captions cannot use that exception.
        const suppressed = new Set(
          d.pages.find((p) => p.page === figure.page)!.suppressedItemIndices,
        );
        expect(
          figure.itemIndices.filter((i) => !source.itemIndices.includes(i) && !suppressed.has(i)),
        ).toEqual([]);
        expect(
          figure.itemIndices.filter(
            (i) => !contains(crop, p.items.find((item) => item.index === i)!.box),
          ),
        ).toEqual([]);
        expect(figure.graphicIndices.filter((i) => !contains(crop, p.graphics[i]!.box))).toEqual(
          [],
        );
        expect(crop.width).toBeLessThanOrEqual(figure.sourceBounds.width + 12);
        expect(crop.height).toBeLessThanOrEqual(figure.sourceBounds.height + 12);
      });
    }
    it('keeps independent figures in separate visual blocks', () => {
      const figures = input.expect.figures.map(
        (f) =>
          owners(d, f.page, f.captionItemIndices[0]!).find(
            (b) => b.type === 'visual-region' && b.role === 'figure',
          )?.id,
      );
      expect(figures.every(Boolean)).toBe(true);
      expect(new Set(figures).size).toBe(figures.length);
    });
    for (const inline of input.expect.inlineMath) {
      it(`page ${inline.page} keeps short inline mathematics in prose`, () => {
        expect(
          inline.itemIndices.filter((i) =>
            owners(d, inline.page, i).some((b) => b.type === 'visual-region'),
          ),
        ).toEqual([]);
      });
    }
    it('does not fall back to rendering an entire supported page', () => {
      expect(
        d.pages.filter((p) =>
          p.visualRegions.some((r) => r.box.width * r.box.height > p.width * p.height * 0.8),
        ),
      ).toEqual([]);
    });
  });
}

it('still uses an explicit safe fallback for genuinely three-column prose', () => {
  const p: PageGeometry = {
    page: 1,
    width: 600,
    height: 800,
    rotation: 0,
    graphics: [],
    tagged: false,
    items: Array.from({ length: 18 }, (_, i) => ({
      index: i,
      text: `Sample column prose ${i}.`,
      box: { x: 30 + Math.floor(i / 6) * 190, y: 100 + (i % 6) * 14, width: 150, height: 10 },
      baseline: 108 + (i % 6) * 14,
      fontSize: 10,
      fontName: 'body',
      fontFamily: 'serif',
      angle: 0,
      hasEOL: true,
    })),
  };
  const d = analyzeDocument([p], 'a'.repeat(64), fixture.pdfjsVersion);
  expect(d.pages[0]!.columns).toEqual([]);
  expect(
    d.blocks.some(
      (b) =>
        b.type === 'visual-region' && /Three or more text columns/.test(b.fallbackReason ?? ''),
    ),
  ).toBe(true);
  expect(validateSourceCoverage(d)).toEqual([]);
});

const syntheticItem = (
  index: number,
  text: string,
  x: number,
  y: number,
  width = 250,
  fontSize = 10,
) => ({
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
const syntheticPage = (
  items: PageGeometry['items'],
  graphics: PageGeometry['graphics'],
): PageGeometry => ({
  page: 1,
  width: 612,
  height: 792,
  rotation: 0,
  tagged: false,
  items,
  graphics,
});
const analyzeSynthetic = (page: PageGeometry) =>
  analyzeDocument([page], 'b'.repeat(64), fixture.pdfjsVersion);

describe('late-page diagram boundary regressions', () => {
  it('does not interpret a body reference to Table I as a new table caption', () => {
    // MP-RDMA page 8: a genuine wide figure is followed by two-column prose.
    const p = syntheticPage(
      [
        syntheticItem(0, 'Fig. 9. Synthetic multi-panel results.', 49, 609, 270, 8),
        ...Array.from({ length: 8 }, (_, i) =>
          syntheticItem(
            i + 1,
            'Ordinary left column text continues with several words.',
            49,
            635 + i * 13,
          ),
        ),
        ...Array.from({ length: 8 }, (_, i) =>
          syntheticItem(
            i + 9,
            i === 6
              ? 'Table I summarizes the generated state values.'
              : 'Ordinary right column text continues with several words.',
            312,
            635 + i * 13,
          ),
        ),
      ],
      [{ kind: 'form', box: { x: 50, y: 342, width: 500, height: 255 } }],
    );
    const d = analyzeSynthetic(p);
    expect(d.blocks.some((b) => b.role === 'table')).toBe(false);
    expect(owners(d, 1, 15).every((b) => b.type !== 'visual-region')).toBe(true);
    const figure = owners(d, 1, 0).find((b) => b.role === 'figure');
    expect(figure).toBeDefined();
    expect(figure!.source[0]!.boxes[0]!.y + figure!.source[0]!.boxes[0]!.height).toBeLessThan(635);
  });

  it('preserves the top panels of a tall figure instead of imposing a page-height cutoff', () => {
    // MP-RDMA page 13: seven panels reach from the top margin to a caption at y=490.
    const panels: PageGeometry['graphics'] = Array.from({ length: 7 }, (_, i) => ({
      kind: 'path',
      box: {
        x: i === 6 ? 395 : 330 + (i % 2) * 120,
        y: 60 + Math.floor(i / 2) * 108,
        width: 80,
        height: 66,
      },
    }));
    const p = syntheticPage(
      [
        syntheticItem(0, 'Fig. 23. Generated tall comparison diagram.', 312, 490, 240, 8),
        ...Array.from({ length: 12 }, (_, i) =>
          syntheticItem(
            i + 1,
            'Several ordinary left column words form normal prose.',
            49,
            175 + i * 14,
          ),
        ),
        ...Array.from({ length: 12 }, (_, i) =>
          syntheticItem(
            i + 13,
            'Several ordinary right column words form normal prose.',
            312,
            515 + i * 14,
          ),
        ),
      ],
      panels,
    );
    const d = analyzeSynthetic(p);
    const figure = owners(d, 1, 0).find((b) => b.role === 'figure');
    expect(figure).toBeDefined();
    expect(panels.every((g) => contains(figure!.source[0]!.boxes[0]!, g.box))).toBe(true);
    expect(d.blocks.filter((b) => b.type === 'visual-region')).toHaveLength(1);
  });

  it('does not turn Fig. N body references into captions or merge adjacent figures', () => {
    // MP-RDMA page 14: the right column begins with a reference to the left figure.
    const p = syntheticPage(
      [
        syntheticItem(0, 'Fig. 24. Generated first plot.', 49, 165, 240, 8),
        syntheticItem(1, 'Fig. 25. Generated second plot.', 49, 278, 240, 8),
        ...Array.from({ length: 8 }, (_, i) =>
          syntheticItem(
            i + 2,
            'Ordinary left column body uses enough words here.',
            49,
            300 + i * 14,
          ),
        ),
        ...Array.from({ length: 12 }, (_, i) =>
          syntheticItem(
            i + 10,
            i === 0
              ? 'Fig. 25 shows results using generated example values.'
              : 'Ordinary right column body uses enough words here.',
            312,
            190 + i * 14,
          ),
        ),
      ],
      [
        { kind: 'path', box: { x: 70, y: 60, width: 215, height: 80 } },
        { kind: 'path', box: { x: 70, y: 190, width: 215, height: 72 } },
      ],
    );
    const d = analyzeSynthetic(p);
    const first = owners(d, 1, 0).find((b) => b.role === 'figure');
    const second = owners(d, 1, 1).find((b) => b.role === 'figure');
    expect(first).toBeDefined();
    expect(second).toBeDefined();
    expect(first!.id).not.toBe(second!.id);
    expect(owners(d, 1, 10).every((b) => b.type !== 'visual-region')).toBe(true);
    expect(d.blocks.filter((b) => b.role === 'figure')).toHaveLength(2);
  });

  it('retains every panel of a full-width figure with a short left-aligned caption', () => {
    // MP-RDMA page 14: the caption itself is shorter than one body column.
    const panels: PageGeometry['graphics'] = Array.from({ length: 5 }, (_, i) => ({
      kind: 'path',
      box: { x: 70 + i * 96, y: 60, width: 70, height: 68 },
    }));
    const p = syntheticPage(
      [
        syntheticItem(0, 'Fig. 24. Generated five-panel plot.', 49, 165, 196, 8),
        syntheticItem(1, 'Fig. 25. Generated single plot.', 49, 278, 216, 8),
        ...Array.from({ length: 10 }, (_, i) =>
          syntheticItem(
            i + 2,
            'Ordinary left column body uses enough words here.',
            49,
            300 + i * 14,
          ),
        ),
        ...Array.from({ length: 14 }, (_, i) =>
          syntheticItem(
            i + 12,
            'Ordinary right column body uses enough words here.',
            312,
            190 + i * 14,
          ),
        ),
      ],
      [...panels, { kind: 'path', box: { x: 95, y: 190, width: 175, height: 70 } }],
    );
    const d = analyzeSynthetic(p);
    const wide = owners(d, 1, 0).find((b) => b.role === 'figure');
    expect(wide).toBeDefined();
    expect(panels.every((g) => contains(wide!.source[0]!.boxes[0]!, g.box))).toBe(true);
    expect(wide!.source[0]!.boxes[0]!.y + wide!.source[0]!.boxes[0]!.height).toBeLessThan(190);
    expect(owners(d, 1, 12).every((b) => b.type !== 'visual-region')).toBe(true);
  });
});

it('keeps an opposite-column table caption from merging three independent figures', () => {
  // MP-RDMA page 9: left figure + table, right figures stacked above prose.
  const p = syntheticPage(
    [
      syntheticItem(0, 'Fig. 10. Generated architecture.', 49, 213, 210, 8),
      syntheticItem(1, 'TABLE I', 159, 229, 31, 8),
      syntheticItem(2, 'GENERATED STATES', 140, 241, 72, 8),
      syntheticItem(3, 'Fig. 11. Generated comparison.', 312, 146, 180, 8),
      syntheticItem(4, 'Fig. 12. Generated topology.', 312, 237, 180, 8),
      ...Array.from({ length: 12 }, (_, i) =>
        syntheticItem(i + 5, 'Ordinary left column body uses enough words here.', 49, 449 + i * 14),
      ),
      ...Array.from({ length: 12 }, (_, i) =>
        syntheticItem(
          i + 17,
          'Ordinary right column body uses enough words here.',
          312,
          263 + i * 14,
        ),
      ),
    ],
    [
      { kind: 'path', box: { x: 72, y: 60, width: 208, height: 145 } },
      { kind: 'path', box: { x: 375, y: 60, width: 120, height: 75 } },
      { kind: 'path', box: { x: 375, y: 166, width: 120, height: 63 } },
      ...Array.from({ length: 20 }, (_, i) => ({
        kind: 'rule' as const,
        box: { x: 71, y: 254 + i * 9.25, width: 204, height: 0.4 },
      })),
    ],
  );
  const d = analyzeSynthetic(p);
  const blocks = [0, 1, 3, 4].map((id) => owners(d, 1, id).find((b) => b.type === 'visual-region'));
  expect(blocks.every(Boolean)).toBe(true);
  expect(blocks.map((b) => b!.role)).toEqual(['figure', 'table', 'figure', 'figure']);
  expect(new Set(blocks.map((b) => b!.id)).size).toBe(4);
  const table = blocks[1]!.source[0]!.boxes[0]!;
  expect(table.x + table.width).toBeLessThan(305);
  expect(table.y).toBeGreaterThan(220);
  expect(validateSourceCoverage(d)).toEqual([]);
});

it('preserves the full brace and every branch of a piecewise display equation', () => {
  const p = syntheticPage(
    [
      ...Array.from({ length: 8 }, (_, i) =>
        syntheticItem(i, 'Normal left column words for source layout inference.', 49, 180 + i * 14),
      ),
      syntheticItem(8, 'The following displayed rule has three possible cases.', 312, 267),
      syntheticItem(9, 'F =', 314, 319, 18),
      syntheticItem(10, '⎧', 335, 291.85, 9),
      syntheticItem(11, '⎪', 335, 301, 9),
      syntheticItem(12, '⎨', 335, 310, 9),
      syntheticItem(13, '⎪', 335, 322, 9),
      syntheticItem(14, '⎩', 335, 331, 9),
      syntheticItem(15, '0', 345, 302, 5),
      syntheticItem(16, 'if x ≤ a', 455, 302, 60),
      syntheticItem(17, 'p(x−a)/(b−a)', 345, 319, 97),
      syntheticItem(18, 'if a < x ≤ b', 455, 319, 91),
      syntheticItem(19, '1', 345, 336.55, 5),
      syntheticItem(20, 'if x > b', 455, 336.54, 58),
      syntheticItem(21, '(5)', 551, 319, 12),
      ...Array.from({ length: 8 }, (_, i) =>
        syntheticItem(
          i + 22,
          'Normal right column words continue after the equation.',
          312,
          358 + i * 14,
        ),
      ),
    ],
    [],
  );
  const d = analyzeSynthetic(p);
  const equation = owners(d, 1, 21).find((b) => b.role === 'equation');
  expect(equation).toBeDefined();
  const box = equation!.source[0]!.boxes[0]!;
  expect(
    p.items.filter((i) => i.index >= 9 && i.index <= 21).every((i) => contains(box, i.box)),
  ).toBe(true);
});

it('does not trim a fraction numerator that happens to fall in the top margin', () => {
  const p = syntheticPage(
    [
      ...Array.from({ length: 8 }, (_, i) =>
        syntheticItem(i, 'Normal left column words for source layout inference.', 49, 100 + i * 14),
      ),
      syntheticItem(8, 'A displayed fraction follows this explanatory sentence.', 312, 59),
      syntheticItem(9, 'F =', 397, 81.67, 25),
      syntheticItem(10, '2', 445.32, 74.95, 5, 9.96),
      syntheticItem(11, 'c + 2', 425.28, 88.51, 45, 9.96),
      syntheticItem(12, '(9)', 551.4, 81.66, 12, 9.96),
      ...Array.from({ length: 8 }, (_, i) =>
        syntheticItem(
          i + 13,
          'Normal right column words continue after the equation.',
          312,
          104 + i * 14,
        ),
      ),
    ],
    [{ kind: 'rule', box: { x: 425.28, y: 85, width: 45, height: 0.4 } }],
  );
  const d = analyzeSynthetic(p);
  const equation = owners(d, 1, 12).find((b) => b.role === 'equation');
  expect(equation).toBeDefined();
  expect(contains(equation!.source[0]!.boxes[0]!, p.items[10]!.box)).toBe(true);
});

it('does not absorb the preceding caption while adding nearby plot labels', () => {
  // HPCC page 11: the next drawing begins only a few points below the prior caption.
  const p = syntheticPage(
    [
      syntheticItem(0, 'Figure 10: Generated full-width comparison.', 75, 171.5, 461, 9),
      syntheticItem(1, 'Figure 11: Generated second comparison.', 54, 276, 504, 9),
      syntheticItem(2, 'axis label', 55, 190, 8, 7),
      ...Array.from({ length: 10 }, (_, i) =>
        syntheticItem(i + 3, 'Ordinary left column body uses enough words here.', 49, 303 + i * 14),
      ),
      ...Array.from({ length: 10 }, (_, i) =>
        syntheticItem(
          i + 13,
          'Ordinary right column body uses enough words here.',
          312,
          303 + i * 14,
        ),
      ),
    ],
    [
      { kind: 'path', box: { x: 70, y: 84, width: 480, height: 70 } },
      { kind: 'path', box: { x: 70, y: 184.9, width: 480, height: 75 } },
    ],
  );
  const d = analyzeSynthetic(p);
  const first = owners(d, 1, 0).find((b) => b.role === 'figure');
  const second = owners(d, 1, 1).find((b) => b.role === 'figure');
  expect(first).toBeDefined();
  expect(second).toBeDefined();
  expect(first!.id).not.toBe(second!.id);
  expect(second!.source[0]!.boxes[0]!.y).toBeGreaterThan(180);
  expect(contains(second!.source[0]!.boxes[0]!, p.items[2]!.box)).toBe(true);
});
