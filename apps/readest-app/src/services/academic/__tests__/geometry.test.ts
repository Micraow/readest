// @vitest-environment node
import { describe, expect, it } from 'vitest';
import { normalizePageGeometry } from '../geometry';

const ops = {
  save: 10,
  restore: 11,
  transform: 12,
  setLineWidth: 2,
  stroke: 20,
  endPath: 28,
  clip: 29,
  constructPath: 91,
  paintFormXObjectBegin: 74,
  paintFormXObjectEnd: 75,
  paintImageXObject: 85,
};
const viewport = { width: 612, height: 792, transform: [1, 0, 0, -1, 0, 792] };
const textContent = { items: [], styles: {} };
const normalize = (fnArray: number[], argsArray: unknown[][]) =>
  normalizePageGeometry(
    { page: 6, rotation: 0, viewport, textContent, operators: { fnArray, argsArray } },
    ops,
  );

describe('PDF.js scale-one geometry', () => {
  it('uses font metrics and all transformed corners for rotated text', () => {
    const result = normalizePageGeometry(
      {
        page: 1,
        rotation: 0,
        viewport,
        textContent: {
          items: [
            { type: 'beginMarkedContent' },
            {
              str: 'rotated',
              transform: [0, 10, -10, 0, 120, 500],
              width: 60,
              height: 10,
              fontName: 'f',
              hasEOL: false,
            },
          ],
          styles: { f: { ascent: 0.8, descent: -0.2, fontFamily: 'serif' } },
        },
        operators: { fnArray: [], argsArray: [] },
      },
      ops,
    );
    expect(result.items[0]).toMatchObject({
      index: 1,
      fontSize: 10,
      box: { x: 112, y: 232, width: 10, height: 60 },
    });
    expect(result.items[0]?.angle).toBeCloseTo(-Math.PI / 2);
  });

  it('transforms a page rotated 90 degrees and does not derive font height from the diagonal', () => {
    const result = normalizePageGeometry(
      {
        page: 1,
        rotation: 90,
        viewport: { width: 792, height: 612, transform: [0, 1, 1, 0, 0, 0] },
        textContent: {
          items: [
            {
              str: 'test',
              transform: [10, 0, 0, 10, 100, 200],
              width: 40,
              height: 10,
              fontName: 'f',
              hasEOL: true,
            },
          ],
          styles: { f: { ascent: 0.8, descent: -0.2 } },
        },
        operators: { fnArray: [], argsArray: [] },
      },
      ops,
    );
    expect(result.items[0]).toMatchObject({
      fontSize: 10,
      box: { x: 198, y: 100, width: 10, height: 40 },
    });
  });

  it('reads v6 embedded paint op and transformed minMax for HPCC algorithm rules', () => {
    // Geometry-only regression from HPCC p6, SHA256 8199b81f...fe8a; no source text or paths.
    const result = normalize(
      [10, 12, 2, 91, 11],
      [
        [],
        [1, 0, 0, 1, 317.955, 505.011],
        [0.797],
        [20, [new Float32Array()], new Float32Array([0, 0, 240.246994, 0])],
        [],
      ],
    );
    expect(result.graphics).toHaveLength(1);
    expect(result.graphics[0]?.kind).toBe('rule');
    expect(result.graphics[0]?.box.x).toBeCloseTo(317.5565, 3);
    expect(result.graphics[0]?.box.y).toBeCloseTo(286.5905, 3);
    expect(result.graphics[0]?.box.width).toBeCloseTo(241.043994, 3);
    expect(result.graphics[0]?.box.height).toBeCloseTo(0.797, 3);
  });

  it('implicitly saves/restores form transforms and clips nested paths to form bounds', () => {
    const result = normalize(
      [12, 74, 12, 91, 75, 85],
      [
        [1, 0, 0, 1, 60, 500],
        [
          [2, 0, 0, 2, 5, 10],
          [0, 0, 100, 60],
        ],
        [1, 0, 0, 1, -10, -10],
        [22, [], new Float32Array([0, 0, 130, 100])],
        [],
        ['image'],
      ],
    );
    expect(result.graphics[0]).toEqual({
      kind: 'form',
      box: { x: 65, y: 162, width: 200, height: 120 },
    });
    expect(result.graphics[1]).toEqual({
      kind: 'path',
      box: { x: 65, y: 162, width: 200, height: 120 },
    });
    expect(result.graphics[2]).toEqual({
      kind: 'image',
      box: { x: 60, y: 291, width: 1, height: 1 },
    });
  });

  it('applies explicit path clipping without counting the clip itself as a visual', () => {
    const result = normalize(
      [29, 91, 91],
      [
        [],
        [28, [], new Float32Array([0, 0, 100, 100])],
        [22, [], new Float32Array([50, 50, 200, 200])],
      ],
    );
    expect(result.graphics).toEqual([
      { kind: 'path', box: { x: 50, y: 692, width: 50, height: 50 } },
    ]);
  });
});
