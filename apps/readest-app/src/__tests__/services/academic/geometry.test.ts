import { describe, expect, it } from 'vitest';
import {
  extractPageGeometry,
  normalizePageGeometry,
  type RawPageGeometry,
  type RawTextItem,
} from '@/services/academic/geometry';

// Synthetic PDF.js 6 operator/text-content pairs. No source-paper data.
const ops = Object.fromEntries(
  [
    'save',
    'restore',
    'transform',
    'paintFormXObjectBegin',
    'paintFormXObjectEnd',
    'clip',
    'eoClip',
    'constructPath',
    'endPath',
    'beginText',
    'endText',
    'setFont',
    'setTextMatrix',
    'setTextRenderingMode',
    'showText',
    'setCharSpacing',
    'setWordSpacing',
    'setHScale',
    'setTextRise',
    'moveText',
    'nextLine',
    'setLeading',
    'setLeadingMoveText',
    'setGState',
  ].map((name, i) => [name, i + 1]),
);
type Operation = [string, ...unknown[]];
const item = (str: string, x: number, y: number): RawTextItem => ({
  str,
  transform: [10, 0, 0, 10, x, y],
  width: str.length * 5,
  height: 10,
  fontName: 'body',
});
const show = (str: string, x: number, y: number): Operation[] => [
  ['beginText'],
  ['setFont', 'body', 10],
  ['setTextMatrix', new Float32Array([1, 0, 0, 1, x, y])],
  ['showText', [...str].map((unicode) => ({ unicode, width: 500, isSpace: unicode === ' ' }))],
  ['endText'],
];
const normalize = (items: RawTextItem[], operations: Operation[]) => {
  const raw: RawPageGeometry = {
    page: 1,
    rotation: 0,
    viewport: { width: 200, height: 200, transform: [1, 0, 0, -1, 0, 200] },
    textContent: { items, styles: { body: { ascent: 0.8, descent: -0.2 } } },
    operators: {
      fnArray: operations.map(([op]) => ops[op]!),
      argsArray: operations.map(([, ...args]) => args),
    },
  };
  return normalizePageGeometry(raw, ops);
};

describe('PDF text paint visibility', () => {
  it('resolves equivalent font resources omitted from TextContent styles and marks math faces', async () => {
    const fonts = new Map([
      ['body', { name: 'ABCDEF+TextFace', fontMatrix: [0.001, 0, 0, 0.001, 0, 0] }],
      ['duplicate', { name: 'ABCDEF+TextFace', fontMatrix: [0.001, 0, 0, 0.001, 0, 0] }],
      ['math', { name: 'ABCDEF+txexs', fontMatrix: [0.001, 0, 0, 0.001, 0, 0] }],
    ]);
    const operations: Operation[] = [
      ['beginText'],
      ['setFont', 'body', 10],
      ['setTextMatrix', [1, 0, 0, 1, 20, 80]],
      ['showText', [...'abc'].map((unicode) => ({ unicode, width: 500 }))],
      ['setFont', 'duplicate', 10],
      ['showText', [...'def'].map((unicode) => ({ unicode, width: 500 }))],
      ['endText'],
      ['beginText'],
      ['setFont', 'math', 10],
      ['setTextMatrix', [1, 0, 0, 1, 20, 40]],
      ['showText', [{ unicode: 'Í', width: 500 }]],
      ['endText'],
    ];
    const page = {
      rotate: 0,
      getTextContent: async () => ({
        items: [item('abcdef', 20, 80), { ...item('Í', 20, 40), fontName: 'math' }],
        styles: { body: { ascent: 0.8, descent: -0.2 }, math: { ascent: 0.8, descent: -0.2 } },
      }),
      getOperatorList: async () => ({
        fnArray: operations.map(([op]) => ops[op]!),
        argsArray: operations.map(([, ...args]) => args),
      }),
      getStructTree: async () => null,
      getViewport: () => ({ width: 200, height: 200, transform: [1, 0, 0, -1, 0, 200] }),
      commonObjs: {
        has: (name: string) => fonts.has(name),
        get: (name: string) => fonts.get(name),
      },
    } as unknown as Parameters<typeof extractPageGeometry>[0];
    const result = await extractPageGeometry(page, 1, ops);
    expect(result.items.map((entry) => entry.text)).toEqual(['abcdef', 'Í']);
    expect(result.items[0]?.fontMath).toBeUndefined();
    expect(result.items[1]?.fontMath).toBe(true);
  });
  it('excludes cropped Form text even when it overlaps visible page prose', () => {
    const result = normalize(
      [item('hidden', 20, 20), item('label', 80, 80), item('visible', 20, 20)],
      [
        ['paintFormXObjectBegin', null, [60, 60, 130, 100]],
        ...show('hidden', 20, 20),
        ...show('label', 80, 80),
        ['paintFormXObjectEnd'],
        ...show('visible', 20, 20),
      ],
    );
    expect(result.items.map((entry) => entry.text)).toEqual(['label', 'visible']);
  });

  it('intersects nested transformed clips and restores the enclosing text visibility', () => {
    const result = normalize(
      [item('out', 60, 80), item('label', 90, 80), item('after', 70, 80)],
      [
        ['paintFormXObjectBegin', [1, 0, 0, 1, 50, 50], [0, 0, 100, 100]],
        ['save'],
        ['clip'],
        ['constructPath', ops['endPath'], [], new Float32Array([35, 20, 80, 40])],
        ...show('out', 10, 30),
        ...show('label', 40, 30),
        ['restore'],
        ...show('after', 20, 30),
        ['paintFormXObjectEnd'],
      ],
    );
    expect(result.items.map((entry) => entry.text)).toEqual(['label', 'after']);
  });

  it('preserves a partial crop as source pixels instead of reflowing hidden characters', () => {
    const result = normalize(
      [item('abcdef', 20, 80)],
      [
        ['paintFormXObjectBegin', null, [30, 60, 100, 100]],
        ...show('abcdef', 20, 80),
        ['paintFormXObjectEnd'],
      ],
    );
    expect(result.items).toEqual([]);
    expect(result.graphics.some((graphic) => graphic.box.x === 30 && graphic.box.width >= 20)).toBe(
      true,
    );
  });

  it('ignores fully off-page text and keeps an on-page clipped fragment visual', () => {
    const result = normalize(
      [item('outside', -80, 30), item('edge', -10, 70), item('body', 40, 100)],
      [...show('outside', -80, 30), ...show('edge', -10, 70), ...show('body', 40, 100)],
    );
    expect(result.items.map((entry) => entry.text)).toEqual(['body']);
    expect(result.graphics).toContainEqual({
      kind: 'form',
      box: { x: 0, y: 122, width: 10, height: 10 },
    });
  });

  it('drops invisible and clipping-only rendering modes without dropping painted text', () => {
    const result = normalize(
      [item('hidden', 20, 20), item('clip', 20, 40), item('paint', 20, 60)],
      [
        ['save'],
        ['setTextRenderingMode', 3],
        ...show('hidden', 20, 20),
        ['restore'],
        ['save'],
        ['setTextRenderingMode', 7],
        ...show('clip', 20, 40),
        ['restore'],
        ...show('paint', 20, 60),
      ],
    );
    expect(result.items.map((entry) => entry.text)).toEqual(['paint']);
  });

  it('does not reflow the hidden half of an extraction item merged across paint modes', () => {
    const result = normalize(
      [item('abcdef', 20, 80)],
      [
        ['beginText'],
        ['setFont', 'body', 10],
        ['setTextMatrix', [1, 0, 0, 1, 20, 80]],
        ['showText', [...'abc'].map((unicode) => ({ unicode, width: 500 }))],
        ['setTextRenderingMode', 3],
        ['showText', [...'def'].map((unicode) => ({ unicode, width: 500 }))],
        ['endText'],
      ],
    );
    expect(result.items).toEqual([]);
    expect(result.graphics).toContainEqual({
      kind: 'form',
      box: { x: 20, y: 112, width: 15, height: 10 },
    });
  });

  it('keeps clipped text out of prose when extraction and paint origins differ after off-page glyphs', () => {
    const result = normalize(
      [item('cropped', 20.8, 20)],
      [
        ['paintFormXObjectBegin', null, [60, 60, 130, 100]],
        ...show('cropped', 20, 20),
        ['paintFormXObjectEnd'],
      ],
    );
    expect(result.items).toEqual([]);
  });

  it('preserves an incompletely mapped item visually rather than dropping its remaining glyphs', () => {
    const result = normalize([item('abcdef', 20, 80)], [...show('abc', 20, 80)]);
    expect(result.items).toEqual([]);
    expect(result.graphics).toContainEqual({
      kind: 'form',
      box: { x: 20, y: 112, width: 30, height: 10 },
    });
  });

  it('retains visible zero-advance mathematical glyphs', () => {
    const glyph = { ...item('√', 20, 80), width: 0 };
    const result = normalize(
      [glyph],
      [
        ['beginText'],
        ['setFont', 'body', 10],
        ['setTextMatrix', [1, 0, 0, 1, 20, 80]],
        ['showText', [{ unicode: '√', width: 0 }]],
        ['endText'],
      ],
    );
    expect(result.items.map((entry) => entry.text)).toEqual(['√']);
  });

  it('respects transparent fill/stroke state, font changes in ExtGState, and restore', () => {
    const result = normalize(
      [item('hidden', 20, 20), item('stroke', 20, 40), item('restored', 20, 60)],
      [
        ['save'],
        [
          'setGState',
          [
            ['ca', 0],
            ['Font', ['body', 10]],
          ],
        ],
        ...show('hidden', 20, 20),
        ['setTextRenderingMode', 2],
        ...show('stroke', 20, 40),
        ['restore'],
        ...show('restored', 20, 60),
      ],
    );
    expect(result.items.map((entry) => entry.text)).toEqual(['stroke', 'restored']);
  });

  it('tracks kerning, spacing, horizontal scale and text rise before a clipped glyph', () => {
    const result = normalize(
      [{ ...item('A B', 20, 85), width: 28, transform: [20, 0, 0, 10, 20, 85] }],
      [
        ['paintFormXObjectBegin', null, [40, 60, 100, 100]],
        ['beginText'],
        ['setFont', 'body', 10],
        ['setHScale', 200],
        ['setTextRise', 5],
        ['setCharSpacing', 1],
        ['setWordSpacing', 2],
        ['moveText', 20, 80],
        [
          'showText',
          [
            { unicode: 'A', width: 500 },
            100,
            { unicode: ' ', width: 200, isSpace: true },
            { unicode: 'B', width: 500 },
          ],
        ],
        ['endText'],
        ['paintFormXObjectEnd'],
      ],
    );
    expect(result.items).toEqual([]);
    expect(result.graphics.some((graphic) => graphic.box.x >= 40 && graphic.box.width > 0)).toBe(
      true,
    );
  });
});
