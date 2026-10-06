import { expect, it } from 'vitest';
import { analyzeDocument, validateSourceCoverage } from '@/services/academic/layout';
import type { PageGeometry, PdfTextItem } from '@/services/academic/types';

const item = (
  index: number,
  text: string,
  x: number,
  y: number,
  width: number,
  height = 10,
): PdfTextItem => ({
  index,
  text,
  box: { x, y, width, height },
  baseline: y + height * 0.8,
  fontSize: 10,
  fontName: 'body',
  fontFamily: 'serif',
  angle: 0,
  hasEOL: true,
});

it('keeps prose outside a visual crop as text rather than capturing it with assignment slack', () => {
  // MP-RDMA page 4: the preceding prose center is 0.53 pt above the padded
  // display crop. A fixed graphic isolates ownership from math classification.
  const prose = item(6, 'For each returned ACK:', 58.91961, 417.77156, 105.79185, 9.00619);
  const page: PageGeometry = {
    page: 1,
    width: 612,
    height: 792,
    rotation: 0,
    tagged: false,
    graphics: [
      {
        kind: 'form',
        box: { x: 76.92004, y: 424.80516, width: 179.34274, height: 30.89203 },
      },
    ],
    items: [
      ...Array.from({ length: 6 }, (_, i) =>
        item(i, 'Normal body words establish the nearby column.', 49, 200 + i * 14, 251),
      ),
      prose,
    ],
  };
  const document = analyzeDocument([page], 'd'.repeat(64), '6.2.108');
  const visual = document.blocks.find((block) => block.type === 'visual-region');
  expect(visual).toBeDefined();
  expect(prose.box.y + prose.box.height / 2).toBeLessThan(visual!.source[0]!.boxes[0]!.y);
  const owner = document.blocks.find((block) =>
    block.source.some((source) => source.itemIndices.includes(prose.index)),
  );
  expect(owner?.type).toBe('paragraph');
  expect(owner?.text).toContain(prose.text);
  expect(validateSourceCoverage(document)).toEqual([]);
});
