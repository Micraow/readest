import { describe, expect, it } from 'vitest';
import { analyzeDocument, validateSourceCoverage } from '@/services/academic/layout';
import type { PageGeometry, PdfTextItem } from '@/services/academic/types';

const text = (index: number, value: string, x: number, y: number, width: number): PdfTextItem => ({
  index,
  text: value,
  box: { x, y, width, height: 10 },
  baseline: y + 8,
  fontSize: 10,
  fontName: 'body',
  fontFamily: 'serif',
  angle: 0,
  hasEOL: true,
});
const analyze = (items: PdfTextItem[]) => {
  const page: PageGeometry = {
    page: 1,
    width: 600,
    height: 800,
    rotation: 0,
    tagged: false,
    items,
    graphics: [{ kind: 'image', box: { x: 40, y: 80, width: 500, height: 100 } }],
  };
  return analyzeDocument([page], 'caption-preview', 'test');
};

describe('caption-free previews with source-preserving zoom', () => {
  it('separates a wrapped bottom caption without losing its original zoom source', () => {
    const d = analyze([
      text(0, 'Figure 1: A long result with a caption', 40, 200, 500),
      text(1, 'that continues on a second line.', 40, 214, 400),
      text(2, 'The following paragraph remains selectable.', 40, 260, 500),
    ]);
    const figure = d.blocks.find((b) => b.role === 'figure')!;
    expect(figure.captions?.[0]?.text).toBe(
      'Figure 1: A long result with a caption that continues on a second line.',
    );
    expect(figure.previewBox).toBeDefined();
    expect(figure.previewBox!.y + figure.previewBox!.height).toBeLessThanOrEqual(200);
    expect(
      figure.source[0]!.boxes[0]!.y + figure.source[0]!.boxes[0]!.height,
    ).toBeGreaterThanOrEqual(224);
    expect(figure.source[0]!.itemIndices).toEqual([0, 1]);
    expect(d.blocks.some((b) => b.text.startsWith('The following'))).toBe(true);
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('includes caption font fragments across an otherwise empty center gutter', () => {
    const d = analyze([
      text(0, 'Figure 1: Measurements using', 40, 200, 220),
      text(1, 'the complete workload.', 300, 200, 240),
      text(2, 'The following paragraph remains selectable.', 40, 245, 500),
    ]);
    const figure = d.blocks.find((b) => b.role === 'figure')!;
    expect(figure.captions?.[0]?.text).toBe('Figure 1: Measurements using the complete workload.');
    expect(figure.captions?.[0]?.source.itemIndices).toEqual([0, 1]);
    expect(figure.previewBox).toBeDefined();
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('keeps a top caption in the source preview when separating it would remove the plot', () => {
    const d = analyze([
      text(0, 'Table I: Results.', 40, 60, 220),
      text(1, 'Value A', 80, 100, 100),
      text(2, 'Value B', 300, 100, 100),
      text(3, 'The following paragraph remains selectable.', 40, 245, 500),
    ]);
    const visual = d.blocks.find((b) => b.type === 'visual-region')!;
    expect(visual.previewBox).toBeUndefined();
    expect(validateSourceCoverage(d)).toEqual([]);
  });
});
