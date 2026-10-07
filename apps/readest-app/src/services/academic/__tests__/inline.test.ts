// @vitest-environment node
import { describe, expect, it } from 'vitest';
import { buildInlineRuns, joinInlineRuns } from '../inline';
import type { LayoutLine, PageGeometry, PdfTextItem } from '../types';

const item = (
  index: number,
  text: string,
  x: number,
  baseline = 100,
  fontSize = 10,
  width = text.length * fontSize * 0.5,
): PdfTextItem => ({
  index,
  text,
  box: { x, y: baseline - fontSize * 0.8, width, height: fontSize },
  baseline,
  fontSize,
  fontName: 'opaque-id',
  fontFamily: 'serif',
  angle: 0,
  hasEOL: false,
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
const line = (items: PdfTextItem[]): LayoutLine => ({
  id: 'line',
  text: items.map((i) => i.text).join(' '),
  box: { x: 10, y: 80, width: 400, height: 30 },
  fontSize: 10,
  itemIndices: items.map((i) => i.index),
});

describe('source-preserving inline content', () => {
  it('anchors adjacent body-size fractions to prose rather than to each other', () => {
    const body = item(0, 'A ratio is', 10, 112, 10, 45);
    const numerator = [
      item(1, 'a', 60, 108),
      item(2, '+', 65, 108),
      item(3, 'b', 70, 108),
      item(5, 'd', 85, 108),
      item(6, '+', 90, 108),
      item(7, 'e', 95, 108),
    ];
    const denominators = [item(4, 'c', 65, 117), item(8, 'f', 90, 117)];
    const geometry = page([body, ...numerator, ...denominators]);
    geometry.graphics = [59, 84].map((x) => ({
      kind: 'rule',
      box: { x, y: 110, width: 17, height: 0.4 },
    }));
    const runs = buildInlineRuns(geometry, [line(numerator), line([body, ...denominators])]);
    expect(runs.filter((run) => run.kind === 'source')).toHaveLength(2);
    expect(runs.flatMap((run) => run.source.itemIndices).sort()).toEqual([
      0, 1, 2, 3, 4, 5, 6, 7, 8,
    ]);
    expect(runs.map((run) => (run.kind === 'source' ? '[fraction]' : run.text)).join('')).toBe(
      'A ratio is [fraction] [fraction]',
    );
  });
  it('places a fraction on its prose baseline even when its numerator is a separate earlier line', () => {
    const earlier = item(0, 'Earlier prose.', 10, 100, 10, 80);
    const prefix = item(1, 'by a factor of k =', 10, 112, 10, 100);
    const numerator = item(2, 'm', 120, 108, 7, 15);
    const denominator = item(3, 'n', 120, 116, 7, 15);
    const suffix = item(4, '= r', 145, 112, 10, 30);
    const geometry = page([earlier, prefix, numerator, denominator, suffix]);
    geometry.graphics.push({ kind: 'rule', box: { x: 119, y: 110, width: 17, height: 0.4 } });
    const runs = buildInlineRuns(geometry, [
      line([earlier]),
      line([numerator]),
      line([prefix, denominator, suffix]),
    ]);
    expect(runs.map((run) => (run.kind === 'source' ? '[fraction]' : run.text)).join('')).toBe(
      'Earlier prose. by a factor of k = [fraction] = r',
    );
    expect(runs.flatMap((run) => run.source.itemIndices).sort()).toEqual([0, 1, 2, 3, 4]);
  });
  it('never pairs scripts from adjacent prose baselines into a fraction', () => {
    const first = [
      item(0, 'First T', 10, 100, 10, 35),
      item(1, 'exp', 45, 103, 7),
      item(2, 'is given.', 65),
    ];
    const second = [
      item(3, 'Other R', 10, 112, 10, 35),
      item(4, 'line', 45, 115, 7),
      item(5, 'is known.', 65, 112),
    ];
    const runs = buildInlineRuns(page([...first, ...second]), [line(first), line(second)]);
    expect(runs.every((run) => run.kind === 'text')).toBe(true);
    expect(runs.map((run) => run.text).join('')).toContain('Other Rline');
  });

  it('keeps an entire fraction with parentheses when its thin bar is an image', () => {
    const items = [
      item(0, 'Rate is', 10),
      item(1, 'W', 55, 96, 7),
      item(2, '(', 59, 96, 7),
      item(3, 't', 63, 96, 7),
      item(4, ')', 67, 96, 7),
      item(5, 'R', 55, 105, 7),
      item(6, '(', 59, 105, 7),
      item(7, 't', 63, 105, 7),
      item(8, ')', 67, 105, 7),
      item(9, 'in this case.', 80),
    ];
    const geometry = page(items);
    geometry.graphics.push({ kind: 'image', box: { x: 54, y: 98.5, width: 18, height: 0.5 } });
    const crops = buildInlineRuns(geometry, [line(items)]).filter((run) => run.kind === 'source');
    expect(crops).toHaveLength(1);
    expect(crops[0]!.source.itemIndices).toEqual([1, 2, 3, 4, 5, 6, 7, 8]);
  });
  it('keeps a stacked fraction local while preserving selectable surrounding prose', () => {
    const items = [
      item(0, 'A ratio', 10),
      item(1, 'a+b', 55, 96, 7, 22),
      item(2, 'c+d', 55, 105, 7, 22),
      item(3, 'is bounded.', 85),
    ];
    const geometry = page(items);
    geometry.graphics.push({ kind: 'rule', box: { x: 54, y: 98.5, width: 24, height: 0.5 } });
    const runs = buildInlineRuns(geometry, [line(items)]);
    const crop = runs.find((run) => run.kind === 'source');
    expect(crop).toMatchObject({
      source: { page: 1, itemIndices: [1, 2] },
      fontSize: 10,
      baseline: 100,
    });
    expect(crop?.source.boxes[0]?.width).toBeLessThan(30);
    expect(
      runs
        .filter((run) => run.kind === 'text')
        .map((run) => run.text)
        .join(''),
    ).toContain('is bounded.');
    expect(runs.flatMap((run) => run.source.itemIndices).sort()).toEqual([0, 1, 2, 3]);
  });

  it('keeps short subscript and superscript runs as styled selectable text', () => {
    const items = [
      item(0, 'Let x', 10),
      item(1, 'i', 35, 103, 7),
      item(2, '2', 39, 96, 7),
      item(3, 'vary.', 48),
    ];
    const runs = buildInlineRuns(page(items), [line(items)]);
    expect(runs.find((run) => run.text === 'i')).toMatchObject({
      kind: 'text',
      style: { verticalAlign: 'sub' },
    });
    expect(runs.find((run) => run.text === '2')).toMatchObject({
      kind: 'text',
      style: { verticalAlign: 'super' },
    });
    expect(runs.every((run) => run.kind === 'text')).toBe(true);
  });

  it('does not invent a fraction from ambiguous overlap without a source bar', () => {
    const items = [
      item(0, 'Value', 10),
      item(1, 'm+n', 45, 95, 7, 18),
      item(2, 'p', 51, 104, 7),
      item(3, 'is known.', 70),
    ];
    const runs = buildInlineRuns(page(items), [line(items)]);
    expect(runs.every((run) => run.kind === 'text')).toBe(true);
    expect(runs.flatMap((run) => run.source.itemIndices)).toEqual([0, 1, 2, 3]);
  });

  it('does not mistake neighboring ordinary lines or an underline for a fraction', () => {
    const first = item(0, 'An ordinary line', 10),
      second = item(1, 'Another ordinary line', 10, 114);
    const geometry = page([first, second]);
    geometry.graphics.push({ kind: 'rule', box: { x: 10, y: 103, width: 75, height: 0.5 } });
    const runs = buildInlineRuns(geometry, [line([first]), line([second])]);
    expect(runs.every((run) => run.kind === 'text')).toBe(true);
    expect(runs.map((run) => run.text).join('')).toBe('An ordinary line Another ordinary line');
  });

  it('does not crop text owned by another block', () => {
    const own = [item(0, 'Ratio', 10), item(1, 'a', 45, 96, 7)];
    const geometry = page([...own, item(2, 'b', 45, 104, 7)]);
    geometry.graphics.push({ kind: 'rule', box: { x: 44, y: 99, width: 6, height: 0.4 } });
    expect(buildInlineRuns(geometry, [line(own)]).every((run) => run.kind === 'text')).toBe(true);
  });

  it('uses explicit font descriptors without interpreting opaque PDF font identifiers', () => {
    const normal = item(0, 'Ordinary', 10),
      styled = { ...item(1, 'emphasis', 54), fontName: 'Times-BoldItalic' };
    const runs = buildInlineRuns(page([normal, styled]), [line([normal, styled])]);
    expect(runs[0]?.kind === 'text' && runs[0].style?.fontStyle).toBeUndefined();
    expect(runs.find((run) => run.text === 'emphasis')).toMatchObject({
      style: { fontStyle: 'italic', fontWeight: 'bold' },
    });
  });

  it('joins wrapped words without losing styled runs or source ownership', () => {
    const first = item(0, 'fragmen-', 10),
      next = item(1, 'tation', 10, 112);
    const geometry = page([first, next]);
    const left = buildInlineRuns(geometry, [line([first])]),
      right = buildInlineRuns(geometry, [line([next])]);
    const runs = joinInlineRuns(left, right);
    expect(runs.map((run) => run.text).join('')).toBe('fragmentation');
    expect(runs.flatMap((run) => run.source.itemIndices)).toEqual([0, 1]);
    expect(left[0]?.text).toBe('fragmen-');
  });

  it('preserves explicit PDF word spacing across a tight font change', () => {
    const first = item(0, 'the variable', 10),
      space = item(1, ' ', 70, 100, 10, 0.1),
      next = item(2, 'q', 70.8);
    const geometry = page([first, space, next]);
    const runs = buildInlineRuns(geometry, [line([first, next])]);
    expect(runs.map((run) => run.text).join('')).toBe('the variable q');
  });
});
