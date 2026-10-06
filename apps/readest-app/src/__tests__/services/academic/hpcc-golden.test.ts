import { describe, expect, it } from 'vitest';
import fixture from './fixtures/hpcc-geometry.json';
import { analyzeDocument, validateSourceCoverage } from '@/services/academic/layout';
import type { PageGeometry } from '@/services/academic/types';

describe('HPCC source-derived geometry golden (synthetic labels, no paper text)', () => {
  it('preserves all algorithm rows and wide vector panels in complete visual regions', () => {
    expect(fixture.sourceSha256).toBe(
      '8199b81f7325b8797623b6c44fad90eb2664b4bc6a8e0f9bdbad7e043b02fe8a',
    );
    const document = analyzeDocument(
      fixture.pages as PageGeometry[],
      fixture.sourceSha256,
      fixture.pdfjsVersion,
    );
    const algorithm = document.blocks.find((b) => b.role === 'algorithm');
    const figure = document.blocks.find((b) => b.role === 'figure' && b.source[0]?.page === 10);
    expect(algorithm).toBeDefined();
    expect(figure).toBeDefined();
    const crop = algorithm!.source[0]!.boxes[0]!;
    expect(crop.x).toBeLessThan(318);
    expect(crop.y).toBeLessThan(287);
    expect(crop.x + crop.width).toBeGreaterThan(558);
    expect(crop.y + crop.height).toBeGreaterThan(612);
    expect(fixture.algorithmLineItemIndices).toHaveLength(27);
    expect(
      fixture.algorithmLineItemIndices.every((id) =>
        algorithm!.source[0]!.itemIndices.includes(id),
      ),
    ).toBe(true);
    const wide = figure!.source[0]!.boxes[0]!;
    expect(wide.x).toBeLessThan(56.1);
    expect(wide.y).toBeLessThan(84);
    expect(wide.x + wide.width).toBeGreaterThan(558);
    expect(wide.y + wide.height).toBeGreaterThan(260);
    expect(validateSourceCoverage(document)).toEqual([]);
  });
});
