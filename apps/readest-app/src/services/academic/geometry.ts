import type { PDFPageProxy } from '@pdfjs/pdf.mjs';
import type { PageGeometry, PdfGraphic, PdfTextItem, Rect } from './types';

export interface RawTextItem {
  str: string;
  transform: number[];
  width: number;
  height: number;
  fontName: string;
  hasEOL?: boolean;
}
export interface RawTextStyle {
  ascent?: number;
  descent?: number;
  fontFamily?: string;
  fontMonospace?: true;
  fontStyle?: 'italic';
  fontWeight?: 'bold';
  vertical?: boolean;
}
export interface RawPageGeometry {
  page: number;
  rotation: number;
  viewport: { width: number; height: number; transform: number[] };
  textContent: {
    items: Array<RawTextItem | { type: string }>;
    styles: Record<string, RawTextStyle>;
  };
  operators: { fnArray: number[]; argsArray: unknown[][] };
  tagged?: boolean;
}

type Matrix = [number, number, number, number, number, number];
const identity: Matrix = [1, 0, 0, 1, 0, 0];
const multiply = (a: number[], b: number[]): Matrix => [
  a[0]! * b[0]! + a[2]! * b[1]!,
  a[1]! * b[0]! + a[3]! * b[1]!,
  a[0]! * b[2]! + a[2]! * b[3]!,
  a[1]! * b[2]! + a[3]! * b[3]!,
  a[0]! * b[4]! + a[2]! * b[5]! + a[4]!,
  a[1]! * b[4]! + a[3]! * b[5]! + a[5]!,
];
const rectOf = (points: Array<[number, number]>): Rect => {
  const xs = points.map(([x]) => x),
    ys = points.map(([, y]) => y);
  const x = Math.min(...xs),
    y = Math.min(...ys);
  return { x, y, width: Math.max(...xs) - x, height: Math.max(...ys) - y };
};
const transformRect = (bounds: number[], matrix: Matrix): Rect =>
  rectOf(
    [
      [bounds[0]!, bounds[1]!],
      [bounds[2]!, bounds[1]!],
      [bounds[0]!, bounds[3]!],
      [bounds[2]!, bounds[3]!],
    ].map(([x, y]) => [
      matrix[0] * x! + matrix[2] * y! + matrix[4],
      matrix[1] * x! + matrix[3] * y! + matrix[5],
    ]),
  );
export const intersectRects = (a: Rect, b: Rect): Rect | null => {
  const x = Math.max(a.x, b.x),
    y = Math.max(a.y, b.y);
  const right = Math.min(a.x + a.width, b.x + b.width);
  const bottom = Math.min(a.y + a.height, b.y + b.height);
  return right >= x && bottom >= y ? { x, y, width: right - x, height: bottom - y } : null;
};
const numbers = (value: unknown): number[] | null => {
  const list = Array.isArray(value)
    ? value
    : ArrayBuffer.isView(value) && !(value instanceof DataView)
      ? Array.from(value as Float32Array)
      : null;
  return list?.every((value) => typeof value === 'number' && Number.isFinite(value)) ? list : null;
};

function textGeometry(
  item: RawTextItem,
  index: number,
  style: RawTextStyle,
  viewport: number[],
): PdfTextItem {
  const tx = multiply(viewport, item.transform);
  const fontSize = Math.hypot(tx[2], tx[3]);
  let angle = Math.atan2(tx[1], tx[0]);
  if (style.vertical) angle += Math.PI / 2;
  const viewportScale = Math.hypot(viewport[0]!, viewport[1]!);
  const width = (style.vertical ? item.height : item.width) * viewportScale;
  const along: [number, number] = [Math.cos(angle) * width, Math.sin(angle) * width];
  // Use the complete font-height vector (including shear), not a diagonal entry.
  const up: [number, number] = style.vertical
    ? [Math.sin(angle) * fontSize, -Math.cos(angle) * fontSize]
    : [tx[2], tx[3]];
  const ascent = typeof style.ascent === 'number' && style.ascent > 0 ? style.ascent : 0.8;
  const descent = typeof style.descent === 'number' && style.descent < 0 ? style.descent : -0.2;
  const points: Array<[number, number]> = [];
  for (const metric of [ascent, descent]) {
    const x = tx[4] + up[0] * metric,
      y = tx[5] + up[1] * metric;
    points.push([x, y], [x + along[0], y + along[1]]);
  }
  return {
    index,
    text: item.str,
    box: rectOf(points),
    baseline: tx[5],
    fontSize,
    fontName: item.fontName,
    fontFamily: style.fontFamily ?? '',
    ...(style.fontMonospace ? { fontMonospace: true as const } : {}),
    ...(style.fontStyle ? { fontStyle: style.fontStyle } : {}),
    ...(style.fontWeight ? { fontWeight: style.fontWeight } : {}),
    angle,
    hasEOL: !!item.hasEOL,
  };
}

/** Pure adapter shared by live PDF.js extraction and geometry-only regression fixtures. */
export function normalizePageGeometry(
  raw: RawPageGeometry,
  ops: Record<string, number>,
): PageGeometry {
  const { viewport } = raw;
  const pageBox: Rect = { x: 0, y: 0, width: viewport.width, height: viewport.height };
  const items: PdfTextItem[] = [];
  raw.textContent.items.forEach((item, index) => {
    if ('str' in item)
      items.push(
        textGeometry(item, index, raw.textContent.styles[item.fontName] ?? {}, viewport.transform),
      );
  });
  const graphics: PdfGraphic[] = [];
  type State = { matrix: Matrix; clip: Rect | null; lineWidth: number };
  let state: State = {
    matrix: multiply(viewport.transform, identity),
    clip: pageBox,
    lineWidth: 1,
  };
  const stack: State[] = [];
  let pendingClip = false;
  const save = () => stack.push({ ...state });
  const restore = () => {
    state = stack.pop() ?? state;
    pendingClip = false;
  };
  const clip = (box: Rect) => {
    state.clip = state.clip ? intersectRects(state.clip, box) : null;
  };
  const add = (box: Rect, kind: PdfGraphic['kind']) => {
    const clipped = state.clip && intersectRects(box, state.clip);
    if (clipped && clipped.width > 0 && clipped.height > 0) graphics.push({ box: clipped, kind });
  };
  const strokes = new Set(
    ['stroke', 'closeStroke', 'fillStroke', 'eoFillStroke', 'closeFillStroke', 'closeEOFillStroke']
      .map((name) => ops[name])
      .filter((op) => op !== undefined),
  );
  const imageOps = new Set(
    [
      'paintImageXObject',
      'paintInlineImageXObject',
      'paintImageMaskXObject',
      'paintSolidColorImageMask',
    ]
      .map((name) => ops[name])
      .filter((op) => op !== undefined),
  );
  for (let i = 0; i < raw.operators.fnArray.length; i++) {
    const op = raw.operators.fnArray[i];
    const args = raw.operators.argsArray[i] ?? [];
    if (op === ops['save']) save();
    else if (op === ops['restore']) restore();
    else if (op === ops['transform']) {
      const transform = numbers(args);
      if (transform?.length === 6) state.matrix = multiply(state.matrix, transform);
    } else if (op === ops['setLineWidth'] && typeof args[0] === 'number')
      state.lineWidth = Math.abs(args[0]);
    else if (op === ops['paintFormXObjectBegin']) {
      save();
      const matrix = numbers(args[0]),
        bbox = numbers(args[1]);
      if (matrix?.length === 6) state.matrix = multiply(state.matrix, matrix);
      if (bbox?.length === 4) {
        const box = transformRect(bbox, state.matrix);
        clip(box);
        add(box, 'form');
      }
    } else if (op === ops['paintFormXObjectEnd']) restore();
    else if (op === ops['clip'] || op === ops['eoClip']) pendingClip = true;
    else if (op === ops['constructPath']) {
      // PDF.js 6: [paintOpcode, [Float32Array path], Float32Array minMax].
      const bbox = numbers(args[2]);
      if (!bbox || bbox.length !== 4) continue;
      const box = transformRect(bbox, state.matrix);
      if (args[0] !== ops['endPath']) {
        const half = strokes.has(args[0] as number) ? state.lineWidth / 2 : 0;
        const painted = half
          ? transformRect(
              [bbox[0]! - half, bbox[1]! - half, bbox[2]! + half, bbox[3]! + half],
              state.matrix,
            )
          : box;
        const short = Math.min(painted.width, painted.height),
          long = Math.max(painted.width, painted.height);
        add(painted, short <= 2.5 && long >= 12 ? 'rule' : 'path');
      }
      if (pendingClip) {
        clip(box);
        pendingClip = false;
      }
    } else if (imageOps.has(op!)) add(transformRect([0, 0, 1, 1], state.matrix), 'image');
    else if (op === ops['paintImageXObjectRepeat'] || op === ops['paintImageMaskXObjectRepeat']) {
      const mask = op === ops['paintImageMaskXObjectRepeat'];
      const positions = numbers(args[mask ? 5 : 3]);
      const transform = mask ? numbers(args.slice(1, 5)) : [args[1], 0, 0, args[2]];
      if (positions && transform?.length === 4 && transform.every((n) => typeof n === 'number')) {
        for (let j = 0; j < positions.length; j += 2) {
          add(
            transformRect(
              [0, 0, 1, 1],
              multiply(state.matrix, [
                ...(transform as number[]),
                positions[j]!,
                positions[j + 1]!,
              ]),
            ),
            'image',
          );
        }
      }
    }
  }
  return {
    page: raw.page,
    width: viewport.width,
    height: viewport.height,
    rotation: raw.rotation,
    items,
    graphics,
    tagged: raw.tagged ?? false,
  };
}

export async function extractPageGeometry(
  page: PDFPageProxy,
  pageNumber: number,
  ops: Record<string, number>,
): Promise<PageGeometry> {
  const [textContent, operators, structure] = await Promise.all([
    page.getTextContent({ includeMarkedContent: true }),
    page.getOperatorList(),
    page.getStructTree(),
  ]);
  // getOperatorList resolves the fonts already needed for this local page.
  // FontFaceObject exposes these standard flags without fontExtraProperties.
  const styles: Record<string, RawTextStyle> = {};
  for (const [fontName, style] of Object.entries(textContent.styles)) {
    const font: unknown = page.commonObjs.has(fontName) ? page.commonObjs.get(fontName) : undefined;
    const metadata = font && typeof font === 'object' ? font : {};
    const name =
      'name' in metadata && typeof metadata.name === 'string'
        ? metadata.name.replace(/^[A-Z]{6}\+/, '')
        : '';
    // Embedded fonts may omit boolean flags while retaining their PostScript
    // name. Recognize explicit style names and established TeX font suffixes.
    // CM-Super uses documented two-letter shapes rather than the word "Bold".
    // https://ctan.org/tex-archive/fonts/ps-type1/cm-super
    const cmSuperShape = /^sf([a-z]{2})\d+$/i.exec(name)?.[1]?.toLowerCase() ?? '';
    const italic =
      ('italic' in metadata && metadata.italic === true) ||
      /italic|oblique/i.test(name) ||
      /^(?:LinLibertine|LinBiolinum)T?B?I\d*$/.test(name) ||
      /^(?:cm|lm|tx|rtx|ntx)mi\d*$/.test(name) ||
      ['sl', 'ti', 'sc', 'ci', 'bl', 'bi', 'oc', 'si', 'so', 'st', 'it', 'vi', 'fs', 'fi'].includes(
        cmSuperShape,
      );
    const bold =
      ('bold' in metadata && metadata.bold === true) ||
      /bold|demibold|semibold/i.test(name) ||
      /^(?:LinLibertine|LinBiolinum)T?BI?\d*$/.test(name) ||
      ['bx', 'bl', 'bi', 'xc', 'oc', 'rb', 'bm', 'sx', 'so'].includes(cmSuperShape);
    // PDF.js can infer a monospace fallback from a one-glyph symbol subset.
    // Only preserve confirmed text faces; CM-Super vt/vi have variable width.
    const monospace = ['tt', 'st', 'it', 'tc'].includes(cmSuperShape);
    styles[fontName] = {
      ...style,
      ...(monospace ? { fontMonospace: true as const } : {}),
      ...(italic ? { fontStyle: 'italic' as const } : {}),
      ...(bold ? { fontWeight: 'bold' as const } : {}),
    };
  }
  return normalizePageGeometry(
    {
      page: pageNumber,
      rotation: page.rotate,
      viewport: page.getViewport({ scale: 1 }),
      textContent: { ...textContent, styles },
      operators,
      tagged: !!structure,
    },
    ops,
  );
}
