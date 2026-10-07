// @vitest-environment node
import { describe, expect, it } from 'vitest';
import { findInlineBottomCut } from '../inline-pixels';

function pixels(rows: string[]) {
  const width = rows[0]!.length;
  const data = new Uint8ClampedArray(width * rows.length * 4).fill(255);
  rows.forEach((row, y) => {
    [...row].forEach((pixel, x) => {
      const value = pixel === '#' ? 0 : pixel === 'f' ? 249 : pixel === 'w' ? 250 : 255;
      const offset = (y * width + x) * 4;
      data.fill(value, offset, offset + 3);
    });
  });
  return { width, height: rows.length, data };
}

describe('inline source crop bottom separator', () => {
  it('keeps the full fraction and finds only the blank seam after the lowest baseline', () => {
    const source = pixels([
      '.##...',
      '.##...',
      '......',
      '#####.',
      '......',
      '.###..',
      '..##..',
      '......',
      '#...##',
    ]);
    const original = source.data.slice();
    expect(findInlineBottomCut(source, 5, 2)).toBe(8);
    expect(source.data).toEqual(original);
  });

  it('retains continuous g, p and j descenders until the first full-width blank seam', () => {
    const source = pixels(['###.##.#', '..#.#..#', '..#.#..#', '.##.#.##', '........', '#.##..##']);
    expect(findInlineBottomCut(source, 0, 2)).toBe(5);
  });

  it('leaves touching rows unchanged when there is no full-width blank separator', () => {
    const source = pixels(['.##.', '..#.', '#.#.', '.##.', '#...']);
    expect(findInlineBottomCut(source, 1, 2)).toBeUndefined();
  });

  it('allows a blank-only bottom margin without removing source ink', () => {
    const source = pixels(['.##.', '..#.', '....', '....']);
    expect(findInlineBottomCut(source, 1, 2)).toBe(3);
    expect(source.data.slice(3 * source.width * 4).every((value) => value === 255)).toBe(true);
  });

  it('requires a half-PDF-unit blank band at the actual render density', () => {
    const source = pixels(['.#.', '...', '.#.', '...', '...', '#.#']);
    expect(findInlineBottomCut(source, 0, 2)).toBe(2);
    expect(findInlineBottomCut(source, 0, 4)).toBe(5);
    expect(findInlineBottomCut(source, 0, 6)).toBeUndefined();
  });

  it('does not mistake faint or colored ink for a near-white separator', () => {
    const source = pixels(['###', '.f.', 'www', '#.#']);
    // A pale colored pixel is ink if even one channel falls below the threshold.
    source.data[1 * source.width * 4 + 4] = 255;
    source.data[1 * source.width * 4 + 5] = 255;
    expect(findInlineBottomCut(source, 0, 2)).toBe(3);
  });

  it('never searches before or through the row containing the lowest baseline', () => {
    const source = pixels(['###', '...', '###']);
    expect(findInlineBottomCut(source, 1, 2)).toBeUndefined();
    expect(findInlineBottomCut(source, 1.8, 2)).toBeUndefined();
  });

  it.each([
    Number.NaN,
    Number.POSITIVE_INFINITY,
    -1,
    3,
  ])('leaves the crop unchanged for a baseline outside its raster: %s', (baseline) => {
    expect(findInlineBottomCut(pixels(['###', '...', '#.#']), baseline, 2)).toBeUndefined();
  });
});
