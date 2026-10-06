import { describe, expect, it } from 'vitest';
import { analyzeDocument, validateSourceCoverage } from '@/services/academic/layout';
import type { PageGeometry, PdfTextItem } from '@/services/academic/types';

const item = (
  index: number,
  text: string,
  x: number,
  y: number,
  width: number,
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
const analyze = (items: PdfTextItem[], graphics: PageGeometry['graphics'] = []) =>
  analyzeDocument(
    [
      {
        page: 1,
        width: 612,
        height: 792,
        rotation: 0,
        tagged: false,
        graphics,
        items: [
          ...Array.from({ length: 10 }, (_, i) =>
            item(
              i,
              'Normal left column prose establishes the body geometry.',
              49,
              100 + i * 14,
              251,
            ),
          ),
          ...Array.from({ length: 10 }, (_, i) =>
            item(
              i + 10,
              'Normal right column prose establishes the body geometry.',
              312,
              100 + i * 14,
              251,
            ),
          ),
          ...items,
        ],
      },
    ],
    'c'.repeat(64),
    '6.2.108',
  );

describe('display mathematics requires complete block geometry', () => {
  it('keeps a separated equals-sign fragment inside its surrounding settings paragraph', () => {
    const d = analyze([
      item(20, 'Our experiment selects several related parameter settings.', 312, 400, 251),
      item(21, '(Kmin, Kmax, Pmax)', 312, 411, 100),
      item(22, '=', 440, 411, 8),
      item(23, '(20, 200, 0.2), and', 475, 411, 88),
      item(24, '(Kmin, Kmax, Pmax) = (10, 50, 0.8). Results follow.', 312, 422, 251),
      item(25, 'The measured behavior agrees with the expected results.', 312, 433, 251),
    ]);
    expect(d.blocks.filter((b) => b.role === 'equation')).toEqual([]);
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('keeps elevated summation signs and limits attached to their inline prose', () => {
    const d = analyze([
      item(20, 'The total amount sent along each physical path', 49, 400, 251),
      item(21, '∑', 138, 403, 11),
      item(22, 'is given by c = i wki. We use this value for analysis.', 49, 411, 251),
      item(23, 'The remaining discussion uses the same definition.', 49, 422, 251),
    ]);
    expect(d.blocks.filter((b) => b.role === 'equation')).toEqual([]);
  });

  it('keeps reference URLs with query parameters as text', () => {
    const d = analyze([
      item(20, '[42] Example. Generated reference with an online source.', 312, 400, 251, 8),
      item(21, 'Available: https://example.org/page?product_family=', 330, 409, 232, 8),
      item(22, '162&mtag=network_card', 330, 418, 118, 8),
      item(23, '[43] Another generated reference follows this entry.', 312, 427, 251, 8),
    ]);
    expect(d.blocks.filter((b) => b.role === 'equation')).toEqual([]);
  });

  it('keeps an inline fraction inside a sentence rather than creating a partial visual block', () => {
    const d = analyze(
      [
        item(20, 'We use the expression', 49, 400, 104),
        item(21, 'a + b', 160, 395, 30),
        item(22, 'c + d', 160, 407, 30),
        item(23, 'to obtain the total.', 197, 400, 102),
        item(24, 'The following sentence continues the same discussion.', 49, 422, 251),
      ],
      [{ kind: 'rule', box: { x: 160, y: 405, width: 30, height: 0.4 } }],
    );
    expect(d.blocks.filter((b) => b.role === 'equation')).toEqual([]);
  });

  it('preserves an isolated unnumbered stacked fraction as one complete display', () => {
    const d = analyze(
      [
        item(20, 'A standalone expression follows this explanation.', 312, 380, 251),
        item(21, 'a + b', 405, 410, 35),
        item(22, 'c + d', 405, 424, 35),
        item(23, 'The discussion resumes below the expression.', 312, 455, 251),
      ],
      [{ kind: 'rule', box: { x: 405, y: 422, width: 35, height: 0.4 } }],
    );
    const equations = d.blocks.filter((b) => b.role === 'equation');
    expect(equations).toHaveLength(1);
    expect(equations[0]!.source[0]!.itemIndices).toEqual([21, 22]);
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('keeps a tight unnumbered display and its raised brackets without swallowing introductory prose', () => {
    const d = analyze([
      item(20, 'Thus', 312, 400, 22),
      item(21, '(', 431, 404, 3, 8),
      item(22, ')−1', 464, 404, 13, 8),
      item(23, 'a', 449, 411, 5, 8),
      item(24, 'U = b 1 −', 380, 417, 49, 8),
      item(25, 'R', 449, 424, 5, 8),
      item(26, 'The following sentence discusses convergence of the method.', 312, 435, 251),
    ]);
    const equation = d.blocks.find((b) => b.role === 'equation');
    expect(equation?.source[0]?.itemIndices).toEqual([21, 22, 23, 24, 25]);
  });

  it('ends numbered displays before nearby inline sums introduced by prose', () => {
    const d = analyze([
      item(20, 'An explanation introduces the displayed relationship.', 312, 380, 251),
      item(21, 'a = b/c', 395, 411, 65),
      item(22, '(12)', 548, 411, 15),
      item(23, '∑', 351, 422, 10),
      item(24, 'Since', 322, 430, 22),
      item(25, 'c =', 377, 430, 25),
      item(26, 'w', 440, 430, 6),
      item(27, 'i=1', 355, 437, 13, 7),
      item(28, 'the remaining prose discusses the rate relationship.', 312, 442, 251),
    ]);
    const equation = d.blocks.find((b) => b.role === 'equation');
    expect(equation?.source[0]?.itemIndices).toEqual([21, 22]);
  });

  it('allows for a stretchy brace tail that renders below its PDF text box', () => {
    // Source-rendered MP-RDMA brace descends ~7pt below PDF.js's nominal box.
    const brace = item(22, '⎩', 335, 330.73, 8.86, 9.9626);
    const d = analyze([
      item(20, 'An explanation introduces the three possible cases.', 312, 280, 251),
      item(21, 'F =', 314, 319, 18),
      brace,
      item(23, 'if x > b', 454, 336.54, 57),
      item(24, '1', 345, 336.55, 5),
      item(25, '(5)', 551, 319, 12),
      item(26, 'The following sentence discusses this piecewise model.', 312, 358, 251),
    ]);
    const box = d.blocks.find((b) => b.role === 'equation')!.source[0]!.boxes[0]!;
    expect(box.y + box.height).toBeGreaterThanOrEqual(brace.baseline + brace.fontSize);
    expect(box.y + box.height).toBeLessThan(358);
  });

  it('keeps preceding prose pixels out of a display with an overestimated delimiter ascent', () => {
    const intro = item(20, 'The preceding explanation ends here.', 312, 400, 140);
    const d = analyze([
      intro,
      item(21, '(', 455, 409, 7),
      item(22, ')', 495, 409, 7),
      item(23, 'a', 473, 418, 5),
      item(24, 'F = b /', 358, 424, 87),
      item(25, 'c', 473, 432, 5),
      item(26, 'The next sentence continues the mathematical discussion.', 312, 450, 251),
    ]);
    const equation = d.blocks.find((b) => b.role === 'equation')!;
    expect(equation.source[0]!.boxes[0]!.y).toBeGreaterThan(intro.box.y + intro.box.height);
    expect(equation.source[0]!.itemIndices).toEqual([21, 22, 23, 24, 25]);
  });
});
