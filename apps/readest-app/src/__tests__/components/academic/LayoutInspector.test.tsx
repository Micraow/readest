import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import LayoutInspector from '@/components/academic/LayoutInspector';
import type { ScholarlyDocument } from '@/services/academic/types';

const box = { x: 10, y: 20, width: 100, height: 12 };
const source = [{ page: 1, boxes: [box], itemIndices: [0] }];
const document: ScholarlyDocument = {
  schemaVersion: 1,
  parserVersion: 'test',
  fingerprint: 'sample',
  pageCount: 1,
  metadata: { pdfjsVersion: '6.2.108' },
  readingOrder: ['p1-b1'],
  warnings: [],
  sourceMap: { 'p1-b1': source },
  pages: [
    {
      page: 1,
      width: 612,
      height: 792,
      rotation: 0,
      tagged: false,
      items: [
        {
          index: 0,
          text: 'Example paragraph',
          box,
          baseline: 30,
          fontSize: 12,
          fontName: 'Body',
          fontFamily: 'serif',
          angle: 0,
          hasEOL: true,
        },
      ],
      graphics: [],
      lines: [{ id: 'p1-l1', text: 'Example paragraph', box, itemIndices: [0], fontSize: 12 }],
      columns: [{ box, confidence: 1 }],
      visualRegions: [],
      blockIds: ['p1-b1'],
      suppressedItemIndices: [],
    },
  ],
  blocks: [
    {
      id: 'p1-b1',
      type: 'paragraph',
      text: 'Example paragraph',
      source,
      order: 0,
      confidence: 0.9,
      fontStats: { min: 12, max: 12, median: 12, names: ['Body'] },
    },
  ],
};
afterEach(cleanup);
describe('layout inspector before classification integration', () => {
  it('independently toggles raw boxes and shows block source, fonts and reading order', () => {
    render(<LayoutInspector document={document} onClose={() => undefined} />);
    expect(screen.getAllByTestId('raw-item-box')).toHaveLength(1);
    fireEvent.click(screen.getByLabelText('Raw text items'));
    expect(screen.queryByTestId('raw-item-box')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Inspect block 1 paragraph' }));
    expect(screen.getByTestId('block-details').textContent).toContain('Example paragraph');
    expect(screen.getByTestId('block-details').textContent).toContain('itemIndices');
    expect(screen.getByTestId('block-details').textContent).toContain('Body');
    expect(screen.getByTestId('block-details').textContent).toContain('0.9');
  });
});
