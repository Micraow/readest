// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import type { PDFPageProxy } from '@pdfjs/pdf.mjs';
import { extractPageGeometry } from '../geometry';
import { buildInlineRuns } from '../inline';

describe('available PDF font styles', () => {
  it.each([
    ['ABCDEF+SFTT1000', 'sans-serif', true, undefined],
    ['SFST0900', 'sans-serif', true, 'italic'],
    ['SFIT1000', 'sans-serif', true, 'italic'],
    ['SFTC1200', 'sans-serif', true, undefined],
    ['SFVT1000', 'sans-serif', undefined, undefined],
    ['SFVI1000', 'sans-serif', undefined, 'italic'],
    ['SFVT1000', 'monospace', undefined, undefined],
    ['ABCDEF+txsyb', 'monospace', undefined, undefined],
    ['SFRM1000', 'serif', undefined, undefined],
    ['SFTT1000-Unknown', 'sans-serif', undefined, undefined],
    [undefined, 'sans-serif', undefined, undefined],
    [undefined, 'monospace', undefined, undefined],
  ])('preserves confirmed fixed-width family for %s / %s without guessing opaque font IDs', async (name, fontFamily, fontMonospace, fontStyle) => {
    const pdfPage = {
      rotate: 0,
      getViewport: () => ({ width: 600, height: 800, transform: [1, 0, 0, -1, 0, 800] }),
      getTextContent: async () => ({
        items: [
          {
            str: 'buffer_size',
            transform: [10, 0, 0, 10, 10, 700],
            width: 60,
            height: 10,
            fontName: 'g_d0_f12',
          },
        ],
        styles: { g_d0_f12: { fontFamily } },
      }),
      getOperatorList: async () => ({ fnArray: [], argsArray: [] }),
      getStructTree: async () => null,
      commonObjs: { has: () => true, get: () => ({ name }) },
    } as unknown as PDFPageProxy;
    const geometry = await extractPageGeometry(pdfPage, 1, {});
    const item = geometry.items[0]!;
    expect(item.fontFamily).toBe(fontFamily);
    expect(item.fontMonospace).toBe(fontMonospace);
    expect(item.fontName).toBe('g_d0_f12');
    expect(item.fontStyle).toBe(fontStyle);
    const runs = buildInlineRuns(geometry, [
      { id: 'l1', text: item.text, box: item.box, itemIndices: [0], fontSize: 10 },
    ]);
    expect(runs).toHaveLength(1);
    expect(runs[0]).toMatchObject({
      kind: 'text',
      text: 'buffer_size',
      source: { page: 1, itemIndices: [0], boxes: [item.box] },
    });
    expect(runs[0]?.kind === 'text' && runs[0].style?.fontFamily).toBe(
      fontMonospace ? 'monospace' : undefined,
    );
  });

  it('preserves explicit loaded font metadata without enabling extra font data or guessing opaque identifiers', async () => {
    const get = vi.fn<() => unknown>(() => ({ italic: true, bold: true }));
    const pdfPage = {
      rotate: 0,
      getViewport: () => ({ width: 600, height: 800, transform: [1, 0, 0, -1, 0, 800] }),
      getTextContent: async () => ({
        items: [
          {
            str: 'Styled words',
            transform: [10, 0, 0, 10, 10, 700],
            width: 60,
            height: 10,
            fontName: 'g_d0_f2',
          },
        ],
        styles: { g_d0_f2: { fontFamily: 'sans-serif' } },
      }),
      getOperatorList: async () => ({ fnArray: [], argsArray: [] }),
      getStructTree: async () => null,
      commonObjs: { has: () => true, get },
    } as unknown as PDFPageProxy;
    const geometry = await extractPageGeometry(pdfPage, 1, {});
    expect(geometry.items[0]).toMatchObject({
      fontStyle: 'italic',
      fontWeight: 'bold',
      fontName: 'g_d0_f2',
    });
    const runs = buildInlineRuns(geometry, [
      {
        id: 'l1',
        text: 'Styled words',
        box: geometry.items[0]!.box,
        itemIndices: [0],
        fontSize: 10,
      },
    ]);
    expect(runs[0]).toMatchObject({ style: { fontStyle: 'italic', fontWeight: 'bold' } });
    expect(get).toHaveBeenCalledWith('g_d0_f2');
    for (const [name, italic, bold] of [
      ['ABCDEF+LinLibertineTI', 'italic', undefined],
      ['ABCDEF+LinLibertineI7', 'italic', undefined],
      ['ABCDEF+LinLibertineTB', undefined, 'bold'],
      ['ABCDEF+rtxmi7', 'italic', undefined],
      ['ABCDEF+SFBX1000', undefined, 'bold'],
      ['ABCDEF+SFSX1000', undefined, 'bold'],
      ['ABCDEF+SFRM1000', undefined, undefined],
      ['ABCDEF+SFSS1000', undefined, undefined],
      ['ABCDEF+SFTI1000', 'italic', undefined],
      ['ABCDEF+SFSL1000', 'italic', undefined],
      ['ABCDEF+SFBI1000', 'italic', 'bold'],
      ['ABCDEF+SFBL1000', 'italic', 'bold'],
      ['Times-BoldItalic', 'italic', 'bold'],
      ['ArialMT', undefined, undefined],
    ]) {
      get.mockReturnValue({ name });
      const actual = await extractPageGeometry(pdfPage, 1, {});
      expect(actual.items[0]?.fontStyle, name).toBe(italic);
      expect(actual.items[0]?.fontWeight, name).toBe(bold);
    }
  });
});
