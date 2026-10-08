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
  fontMath?: true;
  fontMatrix?: number[];
  fontPostscriptName?: string;
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
    ...(style.fontMath ? { fontMath: true as const } : {}),
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
  const graphics: PdfGraphic[] = [];
  // TextContent merges/splits paint operations and deliberately ignores clips.
  // Join it to paint-time state by glyph origin, not by showText item count.
  type Glyph = { transform: Matrix; fontName: string; text: string; box: Rect; clip: Rect | null };
  const glyphs: Glyph[] = [];
  const origins = new Map<string, number[]>();
  const originKey = (font: string, x: number, y: number) =>
    `${font}:${Math.floor(x)}:${Math.floor(y)}`;
  const sameFont = (a: string, b: string) =>
    a === b ||
    (!!raw.textContent.styles[a]?.fontPostscriptName &&
      raw.textContent.styles[a]?.fontPostscriptName ===
        raw.textContent.styles[b]?.fontPostscriptName);
  type State = {
    matrix: Matrix;
    clip: Rect | null;
    lineWidth: number;
    textMatrix: Matrix;
    lineMatrix: Matrix;
    fontName: string;
    fontSize: number;
    charSpacing: number;
    wordSpacing: number;
    hScale: number;
    rise: number;
    leading: number;
    renderingMode: number;
    fillAlpha: number;
    strokeAlpha: number;
  };
  let state: State = {
    matrix: multiply(viewport.transform, identity),
    clip: pageBox,
    lineWidth: 1,
    textMatrix: identity,
    lineMatrix: identity,
    fontName: '',
    fontSize: 0,
    charSpacing: 0,
    wordSpacing: 0,
    hScale: 1,
    rise: 0,
    leading: 0,
    renderingMode: 0,
    fillAlpha: 1,
    strokeAlpha: 1,
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
  const moveText = (x: number, y: number) => {
    state.lineMatrix = multiply(state.lineMatrix, [1, 0, 0, 1, x, y]);
    state.textMatrix = state.lineMatrix;
  };
  const showText = (values: unknown) => {
    if (!Array.isArray(values)) return;
    const style = raw.textContent.styles[state.fontName] ?? {};
    const vertical = !!style.vertical;
    const scale = state.fontSize * (style.fontMatrix?.[0] ?? 0.001);
    for (const value of values) {
      if (typeof value === 'number') {
        const offset = (-value * state.fontSize) / 1000;
        state.textMatrix = multiply(state.textMatrix, [
          1,
          0,
          0,
          1,
          vertical ? 0 : offset * state.hScale,
          vertical ? offset : 0,
        ]);
        continue;
      }
      if (
        !value ||
        typeof value !== 'object' ||
        !('width' in value) ||
        typeof value.width !== 'number'
      )
        continue;
      const unicode = 'unicode' in value && typeof value.unicode === 'string' ? value.unicode : '';
      const vmetric = 'vmetric' in value ? numbers(value.vmetric) : null;
      const advance = (vertical ? (vmetric?.[0] ?? -value.width) : value.width) * scale;
      const matrix = multiply(state.matrix, state.textMatrix);
      const transform = multiply(matrix, [
        state.fontSize * state.hScale,
        0,
        0,
        state.fontSize,
        0,
        state.rise,
      ]);
      const width = Math.abs(advance * state.hScale) * Math.hypot(matrix[0], matrix[1]);
      const height = Math.abs(advance) * Math.hypot(matrix[2], matrix[3]);
      const box = textGeometry(
        { str: unicode, transform, width, height, fontName: state.fontName },
        0,
        style,
        identity,
      ).box;
      const mode = state.renderingMode & 3;
      const painted =
        ((mode === 0 || mode === 2) && state.fillAlpha > 0) ||
        ((mode === 1 || mode === 2) && state.strokeAlpha > 0);
      const key = originKey(state.fontName, transform[4], transform[5]);
      const indices = origins.get(key) ?? [];
      indices.push(glyphs.length);
      origins.set(key, indices);
      glyphs.push({
        transform,
        fontName: state.fontName,
        text: unicode,
        box,
        clip: painted ? state.clip : null,
      });
      const spacing =
        state.charSpacing + ('isSpace' in value && value.isSpace ? state.wordSpacing : 0);
      state.textMatrix = multiply(state.textMatrix, [
        1,
        0,
        0,
        1,
        vertical ? 0 : (advance + spacing) * state.hScale,
        vertical ? advance - spacing : 0,
      ]);
    }
  };
  for (let i = 0; i < raw.operators.fnArray.length; i++) {
    const op = raw.operators.fnArray[i];
    const args = raw.operators.argsArray[i] ?? [];
    if (op === ops['save']) save();
    else if (op === ops['restore']) restore();
    else if (op === ops['transform']) {
      const transform = numbers(args);
      if (transform?.length === 6) state.matrix = multiply(state.matrix, transform);
    } else if (op === ops['beginText']) {
      state.textMatrix = state.lineMatrix = identity;
    } else if (op === ops['setFont']) {
      if (typeof args[0] === 'string' && typeof args[1] === 'number') {
        state.fontName = args[0];
        state.fontSize = args[1];
      }
    } else if (op === ops['setTextMatrix']) {
      const matrix = numbers(args[0]) ?? numbers(args);
      if (matrix?.length === 6) state.textMatrix = state.lineMatrix = matrix as Matrix;
    } else if (op === ops['moveText'] || op === ops['setLeadingMoveText']) {
      if (typeof args[0] === 'number' && typeof args[1] === 'number') {
        if (op === ops['setLeadingMoveText']) state.leading = -args[1];
        moveText(args[0], args[1]);
      }
    } else if (op === ops['nextLine']) moveText(0, -state.leading);
    else if (op === ops['setLeading'] && typeof args[0] === 'number') state.leading = args[0];
    else if (op === ops['setCharSpacing'] && typeof args[0] === 'number')
      state.charSpacing = args[0];
    else if (op === ops['setWordSpacing'] && typeof args[0] === 'number')
      state.wordSpacing = args[0];
    else if (op === ops['setHScale'] && typeof args[0] === 'number') state.hScale = args[0] / 100;
    else if (op === ops['setTextRise'] && typeof args[0] === 'number') state.rise = args[0];
    else if (op === ops['setTextRenderingMode'] && typeof args[0] === 'number')
      state.renderingMode = args[0];
    else if (op === ops['showText']) showText(args[0]);
    else if (op === ops['setGState'] && Array.isArray(args[0])) {
      for (const entry of args[0]) {
        if (!Array.isArray(entry)) continue;
        const [key, value] = entry;
        if (key === 'ca' && typeof value === 'number') state.fillAlpha = value;
        else if (key === 'CA' && typeof value === 'number') state.strokeAlpha = value;
        else if (
          key === 'Font' &&
          Array.isArray(value) &&
          typeof value[0] === 'string' &&
          typeof value[1] === 'number'
        ) {
          state.fontName = value[0];
          state.fontSize = value[1];
        }
      }
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
  const normalizedText = (text: string) => text.normalize('NFKC').replace(/\s/g, '');
  const consumed = new Set<number>();
  const positive = (box: Rect | null): box is Rect => !!box && box.width > 0 && box.height > 0;
  const contains = (outer: Rect, inner: Rect) =>
    outer.x <= inner.x + 0.05 &&
    outer.y <= inner.y + 0.05 &&
    outer.x + outer.width >= inner.x + inner.width - 0.05 &&
    outer.y + outer.height >= inner.y + inner.height - 0.05;
  raw.textContent.items.forEach((rawItem, index) => {
    if (!('str' in rawItem)) return;
    const item = textGeometry(
      rawItem,
      index,
      raw.textContent.styles[rawItem.fontName] ?? {},
      viewport.transform,
    );
    const pagePart = intersectRects(item.box, pageBox);
    // Zero-advance symbols (e.g. radical components) can still paint ink.
    if (
      !pagePart ||
      (pagePart.width === 0 && item.box.width > 0) ||
      (pagePart.height === 0 && item.box.height > 0)
    )
      return;
    const tx = multiply(viewport.transform, rawItem.transform);
    const candidates: number[] = [];
    for (let dx = -1; dx <= 1; dx++)
      for (let dy = -1; dy <= 1; dy++) {
        for (const candidate of origins.get(originKey(rawItem.fontName, tx[4] + dx, tx[5] + dy)) ??
          []) {
          const glyph = glyphs[candidate]!;
          if (
            !consumed.has(candidate) &&
            glyph.transform.every((n, axis) => Math.abs(n - tx[axis]!) < 0.05)
          )
            candidates.push(candidate);
        }
      }
    const text = normalizedText(item.text);
    const start =
      candidates.find((candidate) => text.startsWith(normalizedText(glyphs[candidate]!.text))) ??
      candidates[0];
    const visible: Rect[] = [];
    let complete = contains(pageBox, item.box);
    const along = [Math.cos(item.angle), Math.sin(item.angle)];
    const extent = raw.textContent.styles[rawItem.fontName]?.vertical
      ? rawItem.height
      : rawItem.width;
    const viewportScale = Math.hypot(viewport.transform[0]!, viewport.transform[1]!);
    const preserveUnmapped = () => {
      complete = false;
      // PDF.js may omit off-page glyphs before building TextContent, including
      // their spacing, so its next origin can differ from the painted origin.
      // Same-face/same-baseline paint scopes still bound a safe source crop.
      const scopes = new Set<Rect | null>();
      for (const glyph of glyphs) {
        const dx = glyph.transform[4] - tx[4],
          dy = glyph.transform[5] - tx[5];
        const advance = dx * along[0]! + dy * along[1]!;
        if (
          sameFont(glyph.fontName, item.fontName) &&
          glyph.transform.slice(0, 4).every((n, axis) => Math.abs(n - tx[axis]!) < 0.05) &&
          Math.abs(dx * along[1]! - dy * along[0]!) < 0.1 &&
          advance >= -item.fontSize &&
          advance <= extent * viewportScale + item.fontSize
        )
          scopes.add(glyph.clip);
      }
      if (!scopes.size) visible.push(pagePart);
      for (const scope of scopes) {
        const part = scope && intersectRects(item.box, scope);
        if (positive(part)) visible.push(part);
      }
    };
    if (start !== undefined && text) {
      let length = 0;
      for (let j = start; j < glyphs.length && length < text.length; j++) {
        const glyph = glyphs[j]!;
        const dx = glyph.transform[4] - tx[4],
          dy = glyph.transform[5] - tx[5];
        const advance = dx * along[0]! + dy * along[1]!;
        if (
          !sameFont(glyph.fontName, item.fontName) ||
          Math.abs(dx * along[1]! - dy * along[0]!) > 0.1 ||
          advance < -0.1 ||
          advance > extent * viewportScale + 0.1
        )
          break;
        consumed.add(j);
        length += normalizedText(glyph.text).length;
        const part = glyph.clip && intersectRects(glyph.box, glyph.clip);
        if (positive(part)) visible.push(part);
        if (!glyph.clip || !contains(glyph.clip, glyph.box)) complete = false;
      }
      if (length < text.length) preserveUnmapped();
    } else if (text && glyphs.length) {
      preserveUnmapped();
    } else {
      visible.push(pagePart);
    }
    if (complete) items.push(item);
    else if (visible.length) {
      // Ligatures, kerning, bidi and variable advances prevent slicing a partial
      // word by character count. Keep its visible paint as a local source crop.
      graphics.push({
        kind: 'form',
        box: rectOf(
          visible.flatMap(
            (box) =>
              [
                [box.x, box.y],
                [box.x + box.width, box.y + box.height],
              ] as Array<[number, number]>,
          ),
        ),
      });
    }
  });
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
  const fontNames = new Set(Object.keys(textContent.styles));
  // TextContent can merge equivalent font resources, omitting a style for the
  // second resource even though showText uses it. Resolve every painted face.
  operators.fnArray.forEach((op, index) => {
    const args = operators.argsArray[index] ?? [];
    if (op === ops['setFont'] && typeof args[0] === 'string') fontNames.add(args[0]);
    else if (op === ops['setGState'] && Array.isArray(args[0])) {
      for (const entry of args[0])
        if (
          Array.isArray(entry) &&
          entry[0] === 'Font' &&
          Array.isArray(entry[1]) &&
          typeof entry[1][0] === 'string'
        )
          fontNames.add(entry[1][0]);
    }
  });
  for (const fontName of fontNames) {
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
    const math = /^(?:(?:cm|lm)(?:ex|sy)\d*|(?:tx|rtx|ntx)(?:ex|sy)[a-z]*\d*)$/i.test(name);
    const fontMatrix = 'fontMatrix' in metadata ? numbers(metadata.fontMatrix) : null;
    const style =
      textContent.styles[fontName] ??
      Object.values(styles).find((style) => style.fontPostscriptName === name) ??
      {};
    styles[fontName] = {
      ...style,
      ...(name ? { fontPostscriptName: name } : {}),
      ...(fontMatrix ? { fontMatrix } : {}),
      ...(math ? { fontMath: true as const } : {}),
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
