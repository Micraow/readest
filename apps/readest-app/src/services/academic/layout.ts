import type {
  FontStatistics,
  InlineRun,
  LayoutColumn,
  LayoutLine,
  PageAnalysis,
  PageGeometry,
  PdfTextItem,
  Rect,
  ScholarlyBlock,
  ScholarlyDocument,
  SourceSpan,
  VisualCaption,
  VisualRole,
} from './types';
import { buildInlineRuns, joinInlineRuns, unmappedGlyphAnchors } from './inline.ts';

export const SCHEMA_VERSION = 1;
/** Change when extraction, ordering or classification changes, not just JSON shape. */
export const PARSER_VERSION = 'academic-12';
const right = (r: Rect) => r.x + r.width;
const bottom = (r: Rect) => r.y + r.height;
const median = (values: number[]) => {
  const sorted = values.filter(Number.isFinite).sort((a, b) => a - b);
  return sorted.length ? sorted[Math.floor(sorted.length / 2)]! : 10;
};
const horizontalOverlap = (a: Rect, b: Rect) =>
  Math.max(0, Math.min(right(a), right(b)) - Math.max(a.x, b.x));
const verticalOverlap = (a: Rect, b: Rect) =>
  Math.max(0, Math.min(bottom(a), bottom(b)) - Math.max(a.y, b.y));
export function unionBoxes(boxes: Rect[]): Rect {
  if (!boxes.length) return { x: 0, y: 0, width: 0, height: 0 };
  const x = Math.min(...boxes.map((r) => r.x));
  const y = Math.min(...boxes.map((r) => r.y));
  return {
    x,
    y,
    width: Math.max(...boxes.map(right)) - x,
    height: Math.max(...boxes.map(bottom)) - y,
  };
}
function padded(box: Rect, pad: number, page: PageGeometry): Rect {
  const x = Math.max(0, box.x - pad),
    y = Math.max(0, box.y - pad);
  return {
    x,
    y,
    width: Math.max(0, Math.min(page.width, right(box) + pad) - x),
    height: Math.max(0, Math.min(page.height, bottom(box) + pad) - y),
  };
}
function centerInside(item: Rect, region: Rect, slack = 0): boolean {
  const x = item.x + item.width / 2,
    y = item.y + item.height / 2;
  return (
    x >= region.x - slack &&
    x <= right(region) + slack &&
    y >= region.y - slack &&
    y <= bottom(region) + slack
  );
}
const isHorizontal = (item: PdfTextItem) =>
  Math.abs(Math.sin(item.angle)) < 0.12 && Math.cos(item.angle) > 0.9;
const bodyFont = (items: PdfTextItem[]) =>
  median(items.filter((i) => i.text.trim().length > 8).map((i) => i.fontSize));

function lineText(items: PdfTextItem[]): string {
  let result = '';
  let previous: PdfTextItem | undefined;
  for (const item of items) {
    const gap = previous ? item.box.x - right(previous.box) : 0;
    const space =
      previous &&
      gap > Math.min(previous.fontSize, item.fontSize) * 0.17 &&
      !/\s$/.test(result) &&
      !/^\s|^[,.;:!?\])}]/.test(item.text);
    result += `${space ? ' ' : ''}${item.text}`;
    previous = item;
  }
  return result.replace(/\s+/g, ' ').trim();
}

/** Stable baseline clustering, then split spatially disconnected runs before column detection. */
export function clusterLines(page: PageGeometry, excluded: Set<number> = new Set()): LayoutLine[] {
  const items = page.items.filter((i) => i.text.trim() && !excluded.has(i.index));
  const font = bodyFont(items);
  const glyphAnchors = unmappedGlyphAnchors(items);
  const baselineOf = (item: PdfTextItem) => glyphAnchors.get(item.index)?.baseline ?? item.baseline;
  const dropCaps = new Map<PdfTextItem, PdfTextItem>();
  for (const initial of items) {
    if (!/^\p{Lu}$/u.test(initial.text) || initial.fontSize < font * 1.7) continue;
    const firstRun = items.find(
      (item) =>
        item.fontSize < initial.fontSize * 0.7 &&
        item.fontSize >= font * 0.9 &&
        (item.text.match(/\p{L}{3,}/gu) ?? []).length >= 3 &&
        Math.abs(item.box.y - initial.box.y) < font * 0.5 &&
        item.box.x >= right(initial.box) - 0.5 &&
        item.box.x - right(initial.box) < font * 0.6,
    );
    if (firstRun) dropCaps.set(initial, firstRun);
  }
  const rows: Array<{ baseline: number; size: number; items: PdfTextItem[] }> = [];
  // Main glyphs establish baseline anchors before superscripts/subscripts are attached.
  for (const item of items
    .filter((item) => !dropCaps.has(item))
    .sort(
      (a, b) =>
        b.fontSize - a.fontSize ||
        baselineOf(a) - baselineOf(b) ||
        a.box.x - b.box.x ||
        a.index - b.index,
    )) {
    let closest: (typeof rows)[number] | undefined;
    let distance = Infinity;
    for (const row of rows) {
      const delta = Math.abs(row.baseline - baselineOf(item));
      const tolerance =
        item.fontSize < row.size * 0.82 ? row.size * 0.65 : Math.max(1.6, row.size * 0.25);
      // Superscripts attach only to a nearby run, not a different column on the same row.
      const nearby =
        item.fontSize >= row.size * 0.82 ||
        row.items.some(
          (i) => item.box.x < right(i.box) + row.size && right(item.box) > i.box.x - row.size,
        );
      if (delta <= tolerance && delta < distance && nearby) {
        closest = row;
        distance = delta;
      }
    }
    if (closest) closest.items.push(item);
    else rows.push({ baseline: baselineOf(item), size: item.fontSize, items: [item] });
  }
  // A dropped capital spans several baselines. Attach it only after ordinary
  // rows exist, so its larger font cannot merge those rows into one x-sorted line.
  for (const [initial, firstRun] of dropCaps)
    rows.find((row) => row.items.includes(firstRun))!.items.push(initial);
  // Infer a recurring gutter from separate text runs before joining a baseline.
  // A fixed word-gap threshold alone joins real two-column lines with narrow gutters.
  const rawLines = items.map((item) => ({
    id: `item-${item.index}`,
    text: item.text,
    box: item.box,
    itemIndices: [item.index],
    fontSize: item.fontSize,
  }));
  const candidate = detectColumns(page, rawLines, false).cut;
  let gutter: number | undefined;
  let support = 2;
  if (candidate !== undefined) {
    const font = bodyFont(items);
    // Long runs locate the column neighborhood, but short reference markers can
    // sit inside that estimate. Snap to whitespace shared by complete baselines.
    for (let cut = Math.floor(candidate - font * 2); cut <= candidate + font * 2; cut++) {
      const count = rows.filter((row) => {
        if (row.items.some((item) => item.box.x < cut && right(item.box) > cut)) return false;
        const left = row.items.filter((item) => right(item.box) <= cut);
        const rhs = row.items.filter((item) => item.box.x >= cut);
        return (
          left.length &&
          rhs.length &&
          unionBoxes(left.map((item) => item.box)).width > page.width * 0.13 &&
          unionBoxes(rhs.map((item) => item.box)).width > page.width * 0.13
        );
      }).length;
      if (
        count > support ||
        (count === support &&
          gutter !== undefined &&
          Math.abs(cut - candidate) < Math.abs(gutter - candidate))
      ) {
        support = count;
        gutter = cut;
      }
    }
  }
  const lines: LayoutLine[] = [];
  for (const row of rows) {
    let group: PdfTextItem[] = [];
    const flush = () => {
      if (!group.length) return;
      lines.push({
        id: '',
        text: lineText(group),
        box: unionBoxes(group.map((i) => i.box)),
        itemIndices: group.map((i) => i.index),
        fontSize: median(group.filter((item) => !dropCaps.has(item)).map((i) => i.fontSize)),
      });
      group = [];
    };
    const ordered = row.items.sort((a, b) => a.box.x - b.box.x || a.index - b.index);
    for (const [index, item] of ordered.entries()) {
      const previous = group[group.length - 1];
      if (
        previous &&
        ((captionRole(lineText(group)) && captionRole(lineText(ordered.slice(index)))) ||
          item.box.x - right(previous.box) > Math.max(18, row.size * 1.8) ||
          (gutter !== undefined && right(previous.box) <= gutter && item.box.x >= gutter))
      )
        flush();
      group.push(item);
    }
    flush();
  }
  return lines
    .sort((a, b) => a.box.y - b.box.y || a.box.x - b.box.x || a.itemIndices[0]! - b.itemIndices[0]!)
    .map((line, index) => ({ ...line, id: `p${page.page}-l${index}` }));
}

/** Preserve compounds; remove only a lowercase word fragment's first discretionary hyphen. */
export function joinLines(lines: string[]): string {
  return lines.reduce((text, next) => {
    const trimmed = next.trim();
    if (!text) return trimmed;
    if (text.endsWith('\u00ad')) return text.slice(0, -1) + trimmed;
    if (/-$/.test(text)) {
      const lastWord = text.match(/(\S+)-$/)?.[1] ?? '';
      if (/^[a-z]{3,}$/.test(lastWord) && /^[a-z]{2}/.test(trimmed))
        return text.slice(0, -1) + trimmed;
      return text + trimmed;
    }
    return `${text} ${trimmed}`;
  }, '');
}

interface Region {
  box: Rect;
  role: VisualRole;
  confidence: number;
  reason?: string;
  captionIds?: string[];
}
const captionRole = (text: string): VisualRole | undefined => {
  if (/^\s*(?:Algorithm|Procedure)\s+\d+[.:\s]/i.test(text)) return 'algorithm';
  if (/^\s*Table\s+(?:\d+|[IVX]+)(?:[.:](?:\s|$)|\s*$)/i.test(text)) return 'table';
  if (/^\s*(?:Figure|Fig\.)\s*\d+(?:[.:](?:\s|$)|\s*$)/i.test(text)) return 'figure';
  return undefined;
};
function connected(a: Rect, b: Rect, gap: number): boolean {
  const dx = Math.max(0, a.x - right(b), b.x - right(a));
  const dy = Math.max(0, a.y - bottom(b), b.y - bottom(a));
  return dx <= gap && dy <= gap && (horizontalOverlap(a, b) > 0 || verticalOverlap(a, b) > 0);
}
function groupRects(rects: Rect[], gap: number): Rect[] {
  const groups: Rect[] = [];
  for (const rect of rects) {
    let box = rect;
    for (let i = 0; i < groups.length; i++) {
      if (connected(box, groups[i]!, gap)) {
        box = unionBoxes([box, groups.splice(i, 1)[0]!]);
        i = -1;
      }
    }
    groups.push(box);
  }
  return groups;
}
function captionBox(
  caption: LayoutLine,
  lines: LayoutLine[],
  page: PageGeometry,
  visual?: Rect,
): Rect {
  let box = caption.box;
  const width = visual?.width ?? caption.box.width;
  for (const next of lines) {
    if (next.id === caption.id || next.box.y < caption.box.y + caption.fontSize * 0.6) continue;
    const gap = next.box.y - bottom(box);
    if (gap < -1 || gap > caption.fontSize * 0.7) continue;
    if (
      Math.abs(next.fontSize - caption.fontSize) > caption.fontSize * 0.15 ||
      captionRole(next.text)
    )
      continue;
    const anchor = visual ?? caption.box;
    if (
      next.box.x < anchor.x - 12 ||
      right(next.box) > right(anchor) + 12 ||
      next.box.width > width + 25
    )
      continue;
    // Captions rarely extend beyond five rows. Bound it before nearby body text.
    if (bottom(next.box) - caption.box.y > caption.fontSize * 5.8) break;
    box = unionBoxes([box, next.box]);
  }
  return padded(box, 1.5, page);
}

function detectVisualRegions(
  page: PageGeometry,
  lines: LayoutLine[],
  excluded: Set<number>,
): Region[] {
  const font = bodyFont(page.items);
  const regions: Region[] = [];
  const captions = lines.filter((line) => captionRole(line.text));
  const rules = page.graphics
    .filter((g) => g.kind === 'rule' && g.box.width > font * 5 && g.box.height < font * 0.5)
    .map((g) => g.box);
  // Algorithms are bounded by their outer horizontal rules, not by row text heuristics.
  for (const caption of captions.filter((l) => captionRole(l.text) === 'algorithm')) {
    const candidates = rules.filter(
      (r) =>
        horizontalOverlap(r, caption.box) > Math.min(r.width, caption.box.width) * 0.65 &&
        r.width >= caption.box.width * 0.75,
    );
    const top = candidates
      .filter((r) => r.y <= caption.box.y + 3 && caption.box.y - r.y < font * 4)
      .sort((a, b) => b.y - a.y)[0];
    const below = candidates.filter(
      (r) =>
        r.y > bottom(caption.box) &&
        (!top || (Math.abs(r.x - top.x) < 5 && Math.abs(r.width - top.width) < 10)),
    );
    const end = below
      .filter((r) => r.y - caption.box.y < page.height * 0.65)
      .sort((a, b) => b.y - a.y)[0];
    if (top && end && end.y - top.y > font * 4)
      regions.push({
        box: padded(unionBoxes([top, end, caption.box]), 1.5, page),
        role: 'algorithm',
        confidence: 0.98,
      });
    else {
      // A detected algorithm without safe bounds is ambiguous; retain its column band.
      const x = caption.box.x < page.width / 2 ? Math.max(0, caption.box.x - 4) : page.width / 2;
      const nextHeading = lines.find(
        (l) => l.box.y > caption.box.y + font * 4 && l.box.x >= x && l.fontSize > font * 1.2,
      );
      regions.push({
        box: {
          x,
          y: Math.max(0, caption.box.y - 4),
          width: Math.min(page.width - x, page.width / 2 - 20),
          height: (nextHeading?.box.y ?? page.height * 0.92) - caption.box.y + 4,
        },
        role: 'algorithm',
        confidence: 0.45,
        reason: 'Algorithm boundaries are uncertain; original column region retained',
      });
    }
  }
  // A shared caption establishes the figure boundary before graphics are grouped.
  // Mere geometric proximity merges adjacent column figures, while filtering out
  // small image/path components loses diagram labels and disconnected panels.
  const figureColumns = detectColumns(page, lines);
  for (const caption of captions.filter((line) => captionRole(line.text) === 'figure')) {
    if (regions.some((region) => region.captionIds?.includes(caption.id))) continue;
    const peers = captions.filter(
      (other) =>
        other !== caption &&
        captionRole(other.text) === 'figure' &&
        Math.abs(other.box.y - caption.box.y) < font * 4 &&
        horizontalOverlap(other.box, caption.box) === 0,
    );
    let cut = figureColumns.cut;
    // A local pair has a reliable split; more captions keep the existing path-based fallback.
    if (cut === undefined && peers.length > 1) continue;
    let sharedCaptions = [caption];
    let sharedTop: number | undefined;
    // A local pair of captions is independent of the page's prose columns.
    // Keep a shared legend intact when it crosses their local boundary above the plots.
    if (cut === undefined && peers.length === 1) {
      const pair = [caption, peers[0]!].sort((a, b) => a.box.x - b.box.x);
      let localCut = (right(pair[0]!.box) + pair[1]!.box.x) / 2;
      const captionTop = Math.min(...pair.map((line) => line.box.y));
      const cores = page.graphics.filter(
        (graphic) =>
          graphic.box.width > font * 3 &&
          graphic.box.height > font * 3 &&
          bottom(graphic.box) <= captionTop + 2 &&
          captionTop - bottom(graphic.box) < font * 8,
      );
      const leftEdge = Math.max(
        ...cores
          .filter((graphic) => graphic.box.x + graphic.box.width / 2 < localCut)
          .map((graphic) => right(graphic.box)),
      );
      const rightEdge = Math.min(
        ...cores
          .filter((graphic) => graphic.box.x + graphic.box.width / 2 >= localCut)
          .map((graphic) => graphic.box.x),
      );
      if (Number.isFinite(leftEdge) && Number.isFinite(rightEdge) && leftEdge < rightEdge)
        localCut = (leftEdge + rightEdge) / 2;
      const coreTop = Math.min(...cores.map((graphic) => graphic.box.y));
      const sharedLegend = page.items.filter(
        (item) =>
          !excluded.has(item.index) &&
          item.text.trim() &&
          isHorizontal(item) &&
          item.box.x < localCut &&
          right(item.box) > localCut &&
          item.box.y >= coreTop - font * 2 &&
          bottom(item.box) <= coreTop + font * 0.35 &&
          (item.text.match(/\b[a-zA-Z]{4,}\b/g) ?? []).length < 6,
      );
      if (sharedLegend.length) {
        sharedCaptions = pair;
        sharedTop = Math.min(...sharedLegend.map((item) => item.box.y));
      } else cut = localCut;
    }
    let wide = cut === undefined || (caption.box.x < cut - 2 && right(caption.box) > cut + 2);
    if (!wide && cut !== undefined) {
      const leftCaption = caption.box.x < cut;
      const sameSide = (box: Rect) => box.x + box.width / 2 < cut === leftCaption;
      const preceding = Math.max(
        page.height * 0.05,
        ...captions
          .filter((line) => line.box.y < caption.box.y && sameSide(line.box))
          .map((line) => bottom(line.box)),
      );
      const bandGraphics = page.graphics.filter(
        (graphic) => graphic.box.y >= preceding && bottom(graphic.box) <= caption.box.y + 2,
      );
      const oppositeBody = lines.filter(
        (line) =>
          !sameSide(line.box) &&
          line.box.y >= preceding &&
          !captionRole(line.text) &&
          line.fontSize >= font * 0.94 &&
          (line.text.match(/\b[a-zA-Z]{4,}\b/g) ?? []).length >= 6,
      );
      const oppositeBodyStart = Math.min(...oppositeBody.map((line) => line.box.y));
      const oppositeCaption = captions.some(
        (line) =>
          line !== caption &&
          !sameSide(line.box) &&
          line.box.y >= preceding &&
          line.box.y < oppositeBodyStart,
      );
      const oppositeProse = oppositeBodyStart < caption.box.y;
      // A short, left-aligned shared caption can label a full-width panel grid.
      // Independent captions or prose in the opposite column prevent widening.
      wide =
        !oppositeCaption &&
        !oppositeProse &&
        unionBoxes(bandGraphics.map((graphic) => graphic.box)).width > page.width * 0.65;
    }
    const scopeLeft = wide || caption.box.x < cut! ? 0 : cut!;
    const scopeRight = wide || caption.box.x >= cut! ? page.width : cut!;
    const inColumn = (box: Rect) => box.x >= scopeLeft - 2 && right(box) <= scopeRight + 2;
    const column =
      !wide && figureColumns.cut !== undefined
        ? figureColumns.columns[caption.box.x >= cut! ? 1 : 0]?.box
        : undefined;
    const priorCaptions = captions.filter(
      (line) => line !== caption && line.box.y < caption.box.y && inColumn(line.box),
    );
    const priorProse = lines.filter(
      (line) =>
        line.box.y < caption.box.y &&
        inColumn(line.box) &&
        !captionRole(line.text) &&
        line.fontSize >= font * 0.94 &&
        (line.text.match(/\b[a-zA-Z]{4,}\b/g) ?? []).length >= 6,
    );
    const lowerBound = Math.max(
      page.height * 0.05,
      ...priorCaptions.map((line) => bottom(captionBox(line, lines, page, column))),
      ...priorProse.map((line) => bottom(line.box)),
    );
    const components = page.graphics.filter(
      (graphic) =>
        inColumn(graphic.box) &&
        graphic.box.y >= lowerBound - 1 &&
        bottom(graphic.box) <= caption.box.y + 2 &&
        !regions.some((region) => centerInside(graphic.box, region.box)),
    );
    const drawing = unionBoxes(components.map((graphic) => graphic.box));
    if (
      drawing.width < font * 3 ||
      drawing.height < font ||
      caption.box.y - bottom(drawing) > font * 6
    )
      continue;
    const captionBounds =
      sharedCaptions.length > 1
        ? unionBoxes(sharedCaptions.map((line) => captionBox(line, lines, page, line.box)))
        : captionBox(caption, lines, page, column ?? drawing);
    const labelTop = Math.min(drawing.y, sharedTop ?? drawing.y) - font * 0.6;
    const labelBand: Rect = {
      x: scopeLeft,
      y: labelTop,
      width: scopeRight - scopeLeft,
      height: bottom(captionBounds) - labelTop,
    };
    // Text glyphs (especially rotated axis labels and ticks) need not occur in a
    // graphics operator's bounds. Include the associated text in the figure band.
    const labels = page.items.filter(
      (item) => item.text.trim() && centerInside(item.box, labelBand),
    );
    let box = unionBoxes([drawing, captionBounds, ...labels.map((item) => item.box)]);
    if (column) {
      // Retain the original column's centering when the caption is wider on one side.
      const x = Math.min(column.x, box.x);
      box = { ...box, x, width: Math.max(right(column), right(box)) - x };
    }
    let crop = padded(box, 2, page);
    if (peers.length && figureColumns.cut === undefined) {
      // Captions can abut prose. Padding must not repaint the following body row.
      const followingTop = Math.min(
        ...lines
          .filter(
            (line) =>
              line.box.y >= bottom(captionBounds) - 1.5 &&
              !captionRole(line.text) &&
              horizontalOverlap(line.box, box) > font,
          )
          .map((line) => line.box.y),
      );
      crop = { ...crop, height: Math.min(bottom(crop), followingTop - 0.5) - crop.y };
    }
    regions.push({
      box: crop,
      role: 'figure',
      confidence: 0.94,
      captionIds: sharedCaptions.map((line) => line.id),
    });
  }
  const forms = page.graphics
    .filter(
      (g) =>
        (g.kind === 'form' || g.kind === 'image') &&
        g.box.width > font * 1.5 &&
        g.box.height > font * 1.5 &&
        !regions.some((region) => centerInside(g.box, region.box)),
    )
    .map((g) => g.box);
  // Nearby panels and their labels must form a full-width band before column inference.
  for (const form of groupRects(forms, Math.max(28, font * 3))) {
    if (regions.some((r) => centerInside(form, r.box))) continue;
    const caption = captions
      .filter((l) => {
        const role = captionRole(l.text);
        return (
          (role === 'figure' || role === 'table') &&
          horizontalOverlap(form, l.box) > Math.min(form.width, l.box.width) * 0.45 &&
          l.box.y - bottom(form) >= -font &&
          l.box.y - bottom(form) < font * 6
        );
      })
      .sort((a, b) => Math.abs(a.box.y - bottom(form)) - Math.abs(b.box.y - bottom(form)))[0];
    const box = caption ? unionBoxes([form, captionBox(caption, lines, page, form)]) : form;
    regions.push({
      box: padded(box, 2, page),
      role: caption ? captionRole(caption.text)! : 'figure',
      confidence: caption ? 0.94 : 0.78,
    });
  }
  // Path-only drawings are common in born-digital PDFs without Form XObjects.
  const paths = page.graphics
    .filter(
      (g) =>
        g.kind === 'path' &&
        g.box.width > font &&
        g.box.height > font &&
        !regions.some((r) => centerInside(g.box, r.box)),
    )
    .map((g) => g.box);
  for (const path of groupRects(paths, font)) {
    if (path.width < font * 4 || path.height < font * 2) continue;
    const caption = captions.find(
      (l) =>
        horizontalOverlap(path, l.box) > Math.min(path.width, l.box.width) * 0.5 &&
        l.box.y - bottom(path) >= -font &&
        l.box.y - bottom(path) < font * 5,
    );
    regions.push({
      box: padded(
        caption ? unionBoxes([path, captionBox(caption, lines, page, path)]) : path,
        2,
        page,
      ),
      role: caption ? captionRole(caption.text)! : 'unknown',
      confidence: caption ? 0.84 : 0.6,
      ...(!caption ? { reason: 'Vector drawing retained without a reliable semantic label' } : {}),
    });
  }
  // Ruled tables have a caption above or below a group of aligned horizontal rules.
  for (const caption of captions.filter(
    (l) => captionRole(l.text) === 'table' && !regions.some((r) => centerInside(l.box, r.box)),
  )) {
    const nearby = rules.filter(
      (r) =>
        horizontalOverlap(r, caption.box) > Math.min(r.width, caption.box.width) * 0.5 &&
        Math.abs(r.y - caption.box.y) < page.height * 0.34,
    );
    const above = nearby.filter((r) => r.y < caption.box.y).sort((a, b) => b.y - a.y);
    const below = nearby.filter((r) => r.y > bottom(caption.box)).sort((a, b) => a.y - b.y);
    const direction =
      (below[0]?.y ?? Infinity) - bottom(caption.box) < caption.box.y - (above[0]?.y ?? -Infinity)
        ? below
        : above;
    const edge = direction[0];
    const aligned = edge
      ? direction.filter((r) => Math.abs(r.x - edge.x) < 8 && Math.abs(r.width - edge.width) < 12)
      : [];
    if (aligned.length >= 2)
      regions.push({
        box: padded(unionBoxes([captionBox(caption, lines, page), ...aligned]), 2, page),
        role: 'table',
        confidence: 0.9,
      });
    else {
      // Preserve the local table band rather than hallucinating cells from word positions.
      const candidates = lines.filter(
        (l) =>
          Math.abs(l.box.y - caption.box.y) < font * 9 &&
          horizontalOverlap(l.box, caption.box) > 0 &&
          l.fontSize <= caption.fontSize * 1.15,
      );
      regions.push({
        box: padded(unionBoxes([caption.box, ...candidates.map((l) => l.box)]), 2, page),
        role: 'table',
        confidence: 0.4,
        reason: 'Unruled table boundaries uncertain; local source region retained',
      });
    }
  }
  // Display math is a column-local block, not an isolated symbol or baseline.
  const available = lines.filter(
    (line) =>
      !line.itemIndices.every((id) => excluded.has(id)) &&
      !regions.some((region) => centerInside(line.box, region.box)),
  );
  const mathColumns = detectColumns(page, available);
  const mathCut = mathColumns.cut;
  const itemByIndex = new Map(page.items.map((item) => [item.index, item]));
  const mathSymbol = /[=+−∑∫√∏≤≥≈≠∞∂∇\u0370-\u03ff\u2200-\u22ff]/;
  for (const [columnIndex, { box: column }] of mathColumns.columns.entries()) {
    const colLeft = mathCut !== undefined && columnIndex === 1 ? mathCut : 0;
    const colRight = mathCut !== undefined && columnIndex === 0 ? mathCut : page.width;
    // A numeric numerator may have been mistaken for a margin page number. It
    // still contributes to crop geometry when connected to a genuine display.
    const columnLines = lines.filter(
      (line) =>
        line.box.x >= colLeft - 2 &&
        right(line.box) <= colRight + 5 &&
        (!line.itemIndices.every((id) => excluded.has(id)) || /^\d+$/.test(line.text)) &&
        !regions.some((region) => centerInside(line.box, region.box)),
    );
    const hasNumber = (line: LayoutLine) =>
      line.itemIndices.some((id) => {
        const item = itemByIndex.get(id)!;
        return /^\(\d+[a-z]?\)$/.test(item.text.trim()) && item.box.x > right(column) - font * 3;
      });
    const prose = columnLines.filter((line) => {
      if (hasNumber(line)) return false;
      const words = (line.text.match(/\b[a-zA-Z]{4,}\b/g) ?? []).length;
      const connectiveWords = (
        line.text.match(
          /\b(?:the|a|an|we|is|are|be|for|to|from|with|where|since|thus|and|of|by|as|at)\b/gi,
        ) ?? []
      ).length;
      return (
        /https?:|www\.|[?&][\w-]+=/.test(line.text) ||
        /^(?:where|since|thus|and|but|hence)\b/i.test(line.text) ||
        words >= 4 ||
        (line.box.x < column.x + font * 1.4 &&
          (connectiveWords >= 2 ||
            (!mathSymbol.test(line.text) && /\b[a-zA-Z]{3,}\b/.test(line.text))))
      );
    });
    const midline = (line: LayoutLine) => line.box.y + line.box.height / 2;
    const inlineRows = prose.filter((text) =>
      columnLines.some(
        (line) => /=/.test(line.text) && Math.abs(midline(line) - midline(text)) < font * 0.65,
      ),
    );
    const fragments = columnLines.filter(
      (line) =>
        !prose.includes(line) &&
        !inlineRows.some((text) => Math.abs(midline(text) - midline(line)) < font * 1.3),
    );
    const groups: LayoutLine[][] = [];
    for (const line of fragments.sort((a, b) => a.box.y - b.box.y)) {
      const previous = groups[groups.length - 1];
      const previousBottom = previous
        ? Math.max(...previous.map((part) => bottom(part.box)))
        : -Infinity;
      const proseBetween = prose.some(
        (text) => text.box.y >= previousBottom && text.box.y <= line.box.y,
      );
      if (previous && !proseBetween && line.box.y - previousBottom <= font * 0.9)
        previous.push(line);
      else groups.push([line]);
    }
    for (const group of groups) {
      const box = unionBoxes(group.map((line) => line.box));
      const numbered = group.some(hasNumber);
      const fractionRules = page.graphics.filter(
        ({ kind, box: rule }) =>
          kind === 'rule' &&
          rule.height <= 1.5 &&
          rule.width >= 5 &&
          rule.width <= font * 12 &&
          rule.y >= box.y &&
          bottom(rule) <= bottom(box) &&
          horizontalOverlap(rule, box) > Math.min(rule.width, box.width) * 0.5 &&
          group.some(
            (line) =>
              bottom(line.box) <= rule.y + font * 0.3 && horizontalOverlap(rule, line.box) > 0,
          ) &&
          group.some(
            (line) => line.box.y >= rule.y - font * 0.3 && horizontalOverlap(rule, line.box) > 0,
          ),
      );
      if (!group.some((line) => mathSymbol.test(line.text)) && !fractionRules.length) continue;
      if (!numbered) {
        const equalities = group.filter((line) => /=/.test(line.text));
        const baselines = equalities.length ? equalities.map(midline) : [box.y + box.height / 2];
        // Reassemble the whole local row before testing indentation and spacing.
        // Inline sums, settings tuples and fractions touch their prose row even
        // when PDF text extraction splits a standalone '=' or raised operator.
        // Compare the expression's main row, not the top of its tall brackets:
        // a display's ascenders can overlap a preceding short prose line.
        const inline = prose.some((line) =>
          baselines.some((baseline) => Math.abs(midline(line) - baseline) < font * 1.3),
        );
        if (inline || (!equalities.length && box.x < column.x + font * 1.3)) continue;
      }
      // Stretchy brace bottoms can descend beyond the nominal PDF font box.
      const delimiterTails = group
        .flatMap((line) => line.itemIndices)
        .flatMap((id) => {
          const item = itemByIndex.get(id)!;
          return /[⎩⎭]/.test(item.text)
            ? [{ ...item.box, height: item.baseline + item.fontSize - item.box.y }]
            : [];
        });
      const crop = padded(
        unionBoxes([box, ...delimiterTails, ...fractionRules.map((graphic) => graphic.box)]),
        2,
        page,
      );
      // Delimiter ascent boxes may overlap the previous prose line although
      // their painted glyphs do not. Keep that line's ink out of the crop.
      const precedingBottom = Math.max(
        0,
        ...prose
          .filter((line) => line.box.y < box.y && horizontalOverlap(line.box, crop) > 0)
          .map((line) => bottom(line.box) + 0.5),
      );
      const cropTop = Math.max(crop.y, Math.min(precedingBottom, ...group.map(midline)));
      regions.push({
        box: { ...crop, y: cropTop, height: bottom(crop) - cropTop },
        role: 'equation',
        confidence: numbered ? 0.9 : 0.75,
        reason: 'Display mathematics retained in original layout',
      });
    }
  }
  // Merge intersecting visual detections so a source item can never be emitted twice.
  const merged: Region[] = [];
  for (const region of regions) {
    let current = region;
    for (let i = 0; i < merged.length; i++) {
      const other = merged[i]!;
      // Padding can overlap between two separately captioned figures. That is not
      // evidence that their panels belong to one visual block.
      if (
        current.captionIds?.length &&
        other.captionIds?.length &&
        !current.captionIds.some((id) => other.captionIds!.includes(id))
      )
        continue;
      if (
        horizontalOverlap(current.box, other.box) > 1 &&
        verticalOverlap(current.box, other.box) > 1
      ) {
        const priority: VisualRole[] = ['algorithm', 'table', 'figure', 'equation', 'unknown'];
        current = {
          ...current,
          box: unionBoxes([current.box, other.box]),
          role:
            priority.indexOf(current.role) <= priority.indexOf(other.role)
              ? current.role
              : other.role,
          confidence: Math.min(current.confidence, other.confidence),
          reason: current.reason ?? other.reason,
          captionIds: [...new Set([...(current.captionIds ?? []), ...(other.captionIds ?? [])])],
        };
        merged.splice(i, 1);
        i = -1;
      }
    }
    merged.push(current);
  }
  return merged.sort((a, b) => a.box.y - b.box.y || a.box.x - b.box.x);
}

function marginKey(text: string): string {
  return text.toLowerCase().replace(/\d+/g, '#').replace(/\s+/g, ' ').trim();
}
// Some proceedings put running heads below the usual margin band. Only
// consider the first text row, at body size or smaller, outside plot graphics.
function insetHeaderRow(page: PageGeometry, lines: LayoutLine[]): LayoutLine[] {
  const firstY = Math.min(...lines.map((line) => line.box.y));
  const font = bodyFont(page.items);
  const nextY = Math.min(
    ...lines.filter((line) => line.box.y > firstY + font * 0.4).map((line) => line.box.y),
  );
  return lines.filter(
    (line) =>
      line.box.y >= page.height * 0.105 &&
      line.box.y <= page.height * 0.16 &&
      Math.abs(line.box.y - firstY) < font * 0.4 &&
      line.fontSize <= font * 1.1 &&
      nextY - bottom(line.box) > font * 0.6 &&
      !page.graphics.some(
        (graphic) =>
          graphic.kind !== 'rule' &&
          horizontalOverlap(graphic.box, line.box) > 0 &&
          (verticalOverlap(graphic.box, line.box) > 0 ||
            (graphic.box.y >= bottom(line.box) &&
              graphic.box.y - bottom(line.box) < line.fontSize * 1.25)),
      ),
  );
}
function repeatedMargins(pages: PageGeometry[], linePages: LayoutLine[][]): Set<string> {
  const counts = new Map<string, Set<number>>();
  const insetPositions = new Map<string, number[]>();
  for (let i = 0; i < pages.length; i++) {
    const inset = new Set(insetHeaderRow(pages[i]!, linePages[i]!));
    for (const line of linePages[i]!) {
      if (
        !inset.has(line) &&
        line.box.y > pages[i]!.height * 0.105 &&
        bottom(line.box) < pages[i]!.height * 0.92
      )
        continue;
      const side = inset.has(line)
        ? 'inset-top'
        : line.box.y < pages[i]!.height / 2
          ? 'top'
          : 'bottom';
      const key = `${side}:${marginKey(line.text)}`;
      if (line.text.length > 2) {
        const seen = counts.get(key) ?? new Set();
        seen.add(i);
        counts.set(key, seen);
        if (inset.has(line)) {
          const positions = insetPositions.get(key) ?? [];
          positions.push(line.box.y / pages[i]!.height);
          insetPositions.set(key, positions);
        }
      }
    }
  }
  return new Set(
    [...counts]
      .filter(([key, seen]) => {
        const positions = insetPositions.get(key);
        return (
          seen.size >= Math.max(2, Math.ceil(pages.length * 0.4)) &&
          (!positions || Math.max(...positions) - Math.min(...positions) < 0.006)
        );
      })
      .map(([key]) => key),
  );
}
function suppressedItems(
  page: PageGeometry,
  lines: LayoutLine[],
  repeated: Set<string>,
): Set<number> {
  const suppressed = new Set(page.items.filter((i) => !i.text.trim()).map((i) => i.index));
  const inset = insetHeaderRow(page, lines);
  const runningHeads = inset.filter((line) => repeated.has(`inset-top:${marginKey(line.text)}`));
  for (const line of lines) {
    const margin = line.box.y < page.height * 0.105 || bottom(line.box) > page.height * 0.92;
    const key = `${line.box.y < page.height / 2 ? 'top' : 'bottom'}:${marginKey(line.text)}`;
    const pageNumber = /^[-–—]?\s*\d{1,4}\s*[-–—]?$/.test(line.text);
    const insetMargin =
      runningHeads.includes(line) ||
      (pageNumber &&
        inset.includes(line) &&
        runningHeads.some(
          (head) =>
            Math.abs(head.box.y - line.box.y) < head.fontSize * 0.4 &&
            Math.abs(head.fontSize - line.fontSize) < head.fontSize * 0.2,
        ));
    if (insetMargin || (margin && (repeated.has(key) || pageNumber)))
      line.itemIndices.forEach((id) => suppressed.add(id));
  }
  return suppressed;
}
function detectColumns(
  page: PageGeometry,
  lines: LayoutLine[],
  checkColumnCount = true,
): { columns: LayoutColumn[]; cut?: number; ambiguous?: string } {
  const font = bodyFont(page.items);
  const body = lines.filter(
    (l) =>
      l.box.width > page.width * 0.13 && l.box.width < page.width * 0.6 && l.fontSize < font * 1.23,
  );
  // Three long, independently aligned columns are outside this conservative first version.
  const anchors: Array<{ x: number; count: number }> = [];
  for (const line of body.filter((l) => l.box.width < page.width * 0.29)) {
    const anchor = anchors.find((a) => Math.abs(a.x - line.box.x) < font * 1.5);
    if (anchor) anchor.count++;
    else anchors.push({ x: line.box.x, count: 1 });
  }
  // Raw PDF runs can be style fragments within one line; only completed lines
  // establish independently aligned columns for this ambiguity guard.
  if (checkColumnCount && anchors.filter((a) => a.count >= 5).length >= 3)
    return { columns: [], ambiguous: 'Three or more text columns are not safely supported' };
  let best: { cut: number; score: number; left: LayoutLine[]; right: LayoutLine[] } | undefined;
  for (let cut = page.width * 0.36; cut <= page.width * 0.64; cut += 2) {
    const left = body.filter((l) => right(l.box) <= cut + 2);
    const rhs = body.filter((l) => l.box.x >= cut - 2);
    const crossings = body.length - left.length - rhs.length;
    if (left.length < 3 || rhs.length < 3 || crossings > Math.max(1, body.length * 0.12)) continue;
    const leftEdge = Math.max(...left.map((l) => right(l.box)));
    const rightEdge = Math.min(...rhs.map((l) => l.box.x));
    if (rightEdge - leftEdge < font * 0.7) continue;
    // Do not reinterpret two of three columns as one oversized column.
    if (
      leftEdge - Math.min(...left.map((l) => l.box.x)) > page.width * 0.49 ||
      Math.max(...rhs.map((l) => right(l.box))) - rightEdge > page.width * 0.49
    )
      continue;
    const score =
      Math.min(left.length, rhs.length) -
      crossings * 3 -
      Math.abs(cut - page.width / 2) / page.width;
    if (!best || score > best.score)
      best = { cut: (leftEdge + rightEdge) / 2, score, left, right: rhs };
  }
  if (best)
    return {
      cut: best.cut,
      columns: [best.left, best.right].map((list) => ({
        box: unionBoxes(list.map((l) => l.box)),
        confidence: 0.9,
      })),
    };
  return {
    columns: lines.length ? [{ box: unionBoxes(lines.map((l) => l.box)), confidence: 0.8 }] : [],
  };
}
function fontStatistics(items: PdfTextItem[]): FontStatistics {
  const sizes = items.map((i) => i.fontSize).filter((v) => v > 0);
  return {
    median: median(sizes),
    min: sizes.length ? Math.min(...sizes) : 0,
    max: sizes.length ? Math.max(...sizes) : 0,
    names: [...new Set(items.map((i) => i.fontName))].sort(),
  };
}
function blockBox(block: ScholarlyBlock, page: number): Rect {
  return unionBoxes(block.source.filter((s) => s.page === page).flatMap((s) => s.boxes));
}
function makeBlock(
  page: PageGeometry,
  ids: number[],
  boxes: Rect[],
  text: string,
  type: ScholarlyBlock['type'],
  confidence: number,
): ScholarlyBlock {
  const wanted = new Set(ids);
  return {
    id: '',
    type,
    text,
    source: [{ page: page.page, boxes, itemIndices: [...wanted].sort((a, b) => a - b) }],
    order: -1,
    confidence,
    fontStats: fontStatistics(page.items.filter((i) => wanted.has(i.index))),
  };
}
function heading(
  line: LayoutLine,
  font: number,
  bodyTypeface: string | undefined,
  items: Map<number, PdfTextItem>,
): boolean {
  if (line.fontSize >= font * 1.16 && line.text.length < 180) return true;
  if (line.fontSize < font * 0.94 || line.text.length >= 100) return false;
  if (
    /^abstract\s*[:—–-]?\s*$/i.test(line.text) ||
    /^(?:references|bibliography|acknowledg(?:e)?ments|appendix)\b/i.test(line.text)
  )
    return true;
  if (!/^(?:(?:[1-9]|1\d)(?:\.\d+)*\s+|[A-Z]\.\s+)\p{Lu}/u.test(line.text)) return false;
  // A number can begin a body continuation. Require size or style evidence;
  // PDF.js font identifiers are opaque, so compare with the dominant body face.
  if (line.fontSize >= font * 1.08) return true;
  const leadingStyle: PdfTextItem[] = [];
  let inStyledPrefix = true;
  let characters = 0,
    styled = 0;
  for (const index of line.itemIndices) {
    const item = items.get(index)!;
    const length = item.text.trim().length;
    characters += length;
    if (bodyTypeface && item.fontName && item.fontName !== bodyTypeface) {
      styled += length;
      if (inStyledPrefix) leadingStyle.push(item);
    } else inStyledPrefix = false;
  }
  // An emphasized number or word alone does not make the whole line a heading.
  // Run-in headings may instead have a complete styled label before body prose.
  return (
    (characters > 0 && styled >= characters * 0.8) ||
    /^(?:[1-9]|1\d)(?:\.\d+)*\s+\p{Lu}.+[.:]$/u.test(lineText(leadingStyle))
  );
}
const listStart = (s: string) => /^(?:[•●▪◦‣–]\s*|[-*]\s+|\d+[.)]\s+|[a-z][.)]\s+)/i.test(s);
function textBlocks(page: PageGeometry, lines: LayoutLine[], cut?: number): ScholarlyBlock[] {
  const font = bodyFont(page.items);
  const items = new Map(page.items.map((item) => [item.index, item]));
  const proseSize = (line: LayoutLine) => {
    const runs = line.itemIndices
      .map((id) => items.get(id)!)
      .filter((item) => item.text.trim().length > 8);
    return runs.length ? median(runs.map((item) => item.fontSize)) : line.fontSize;
  };
  const numberedParagraphLead = (line: LayoutLine) => {
    if (!/^\d+[.)]\s/.test(line.text)) return false;
    const runs = line.itemIndices.map((id) => items.get(id)!).filter((item) => item.text.trim());
    const colon = runs.findIndex((item) => /:$/.test(item.text.trim()));
    const emphasized = (item: PdfTextItem) =>
      !!(
        item.fontStyle ||
        item.fontWeight ||
        /italic|oblique|bold|semibold|demibold/i.test(`${item.fontName} ${item.fontFamily}`)
      );
    return (
      colon >= 0 &&
      runs.slice(0, colon + 1).every(emphasized) &&
      runs.slice(colon + 1).some((item) => !emphasized(item) && /\p{L}{2,}/u.test(item.text))
    );
  };
  const boldParagraphLead = (line: LayoutLine) => {
    const runs = line.itemIndices.map((id) => items.get(id)!).filter((item) => item.text.trim());
    const firstOrdinary = runs.findIndex((item) => item.fontWeight !== 'bold');
    if (firstOrdinary <= 0) return false;
    const label = runs
      .slice(0, firstOrdinary)
      .map((item) => item.text)
      .join('');
    return label.length < 100 && /^\p{L}/u.test(label) && /[.:]$/.test(label.trim());
  };
  const typefaces = new Map<string, number>();
  for (const item of page.items) {
    if (Math.abs(item.fontSize - font) > font * 0.06) continue;
    typefaces.set(item.fontName, (typefaces.get(item.fontName) ?? 0) + item.text.trim().length);
  }
  const bodyTypeface = [...typefaces].sort((a, b) => b[1] - a[1])[0]?.[0];
  const blocks: ScholarlyBlock[] = [];
  const groups = cut
    ? [
        lines.filter((l) => right(l.box) <= cut + 2),
        lines.filter((l) => l.box.x >= cut - 2),
        lines.filter((l) => l.box.x < cut - 2 && right(l.box) > cut + 2),
      ]
    : [lines];
  for (const group of groups) {
    const orderedLines = [...group].sort((a, b) => a.box.y - b.box.y || a.box.x - b.box.x);
    const rowGaps = orderedLines
      .slice(1)
      .flatMap((line, index) => {
        const previous = orderedLines[index]!;
        const gap = line.box.y - bottom(previous.box);
        return gap >= 0 &&
          gap < font * 1.2 &&
          Math.abs(line.fontSize - font) < font * 0.1 &&
          Math.abs(previous.fontSize - font) < font * 0.1
          ? [gap]
          : [];
      })
      .sort((a, b) => a - b);
    const normalGap = rowGaps[Math.floor((rowGaps.length - 1) / 2)] ?? font * 0.25;
    let pending: LayoutLine[] = [],
      pendingType: ScholarlyBlock['type'] = 'paragraph';
    let references = false;
    const flush = () => {
      if (!pending.length) return;
      const block = makeBlock(
        page,
        pending.flatMap((l) => l.itemIndices),
        pending.map((l) => l.box),
        joinLines(pending.map((l) => l.text)),
        pendingType,
        pendingType === 'heading' ? 0.85 : 0.88,
      );
      block.inlineRuns = buildInlineRuns(page, pending);
      if (pendingType === 'heading')
        block.level = pending[0]!.fontSize > font * 1.55 ? 1 : /^\d+\.\d+/.test(block.text) ? 3 : 2;
      if (pendingType === 'list') {
        block.listItems = pending.reduce<string[]>((items, line) => {
          if (!items.length || listStart(line.text)) items.push(line.text);
          else items[items.length - 1] = joinLines([items[items.length - 1]!, line.text]);
          return items;
        }, []);
        const groups = pending.reduce<LayoutLine[][]>((groups, line) => {
          if (!groups.length || listStart(line.text)) groups.push([line]);
          else groups[groups.length - 1]!.push(line);
          return groups;
        }, []);
        block.listInlineRuns = groups.map((lines) => buildInlineRuns(page, lines));
      }
      blocks.push(block);
      pending = [];
    };
    for (const [lineIndex, line] of orderedLines.entries()) {
      const previous = pending[pending.length - 1];
      const isHeading = heading(line, font, bodyTypeface, items);
      const firstItem = items.get(line.itemIndices[0]!);
      const superscriptNoteMarker =
        firstItem &&
        /^\d{1,3}$/.test(firstItem.text.trim()) &&
        firstItem.fontSize < line.fontSize * 0.85;
      const footnoteRule = page.graphics.some(
        (g) =>
          g.kind === 'rule' &&
          g.box.y > page.height * 0.65 &&
          g.box.y < line.box.y &&
          line.box.y - g.box.y < font * 10 &&
          horizontalOverlap(g.box, line.box) > 0,
      );
      const isFootnote: boolean =
        (line.fontSize < font * 0.87 &&
          line.box.y > page.height * 0.72 &&
          (footnoteRule || /^\d+\s/.test(line.text) || !!superscriptNoteMarker)) ||
        // First-page publication notes may start halfway down the column
        // without a rule. Compare with local body size, since the abstract can
        // lower the page median. Author initials in this run are not list markers.
        (page.page === 1 &&
          line.box.y > page.height * 0.5 &&
          /^Manuscript received\b/i.test(line.text) &&
          pendingType === 'paragraph' &&
          previous !== undefined &&
          line.fontSize < previous.fontSize * 0.87) ||
        (pendingType === 'footnote' &&
          previous !== undefined &&
          line.fontSize < font * 0.94 &&
          line.box.y - bottom(previous.box) >= -font * 0.4 &&
          line.box.y - bottom(previous.box) < font * 1.2 &&
          Math.abs(line.fontSize - previous.fontSize) < previous.fontSize * 0.06 &&
          horizontalOverlap(line.box, previous.box) > 0);
      if (/^(?:references|bibliography)\b/i.test(line.text)) references = true;
      let type: ScholarlyBlock['type'] = isFootnote
        ? 'footnote'
        : isHeading
          ? 'heading'
          : /^\[\d+\]/.test(line.text) || references
            ? 'reference'
            : listStart(line.text) && !numberedParagraphLead(line)
              ? 'list'
              : 'paragraph';
      const droppedInitial = previous?.itemIndices.some((id) => {
        const item = items.get(id)!;
        return /^\p{Lu}$/u.test(item.text) && item.fontSize > previous.fontSize * 1.7;
      });
      const previousBottom = previous
        ? previous.box.y +
          (droppedInitial
            ? Math.min(previous.box.height, previous.fontSize * 1.35)
            : previous.box.height)
        : 0;
      const gap = previous ? line.box.y - previousBottom : Infinity;
      const indent = previous ? line.box.x - previous.box.x : 0;
      const ordinaryBaseline = (row: LayoutLine) => {
        const main = row.itemIndices
          .map((id) => items.get(id)!)
          .filter((item) => item.fontSize >= font * 0.9);
        return main.length ? median(main.map((item) => item.baseline)) : undefined;
      };
      const previousBaseline = previous && ordinaryBaseline(previous);
      const currentBaseline = ordinaryBaseline(line);
      const samePhysicalRow =
        previous &&
        previousBaseline !== undefined &&
        currentBaseline !== undefined &&
        Math.abs(previousBaseline - currentBaseline) < font * 0.2 &&
        line.box.x >= right(previous.box) - 0.5 &&
        line.box.x - right(previous.box) < font * 1.5;
      // A numeric value wrapped after an assignment is prose, even when a
      // sentence-ending period makes it resemble the start of a numbered list.
      if (
        type === 'list' &&
        /^\d+\.\s/.test(line.text) &&
        pendingType === 'paragraph' &&
        previous &&
        /=\s*$/.test(previous.text) &&
        gap >= -font * 0.4 &&
        gap < font * 0.8 &&
        Math.abs(indent) < font * 0.5 &&
        Math.abs(line.fontSize - previous.fontSize) < font * 0.12
      )
        type = 'paragraph';
      // A wrapped explanatory dash continues its unfinished sentence. It is not
      // a new bullet just because PDF line wrapping put the dash at the margin.
      if (
        type === 'list' &&
        /^–\s/.test(line.text) &&
        !/^–\s/.test(
          orderedLines
            .slice(lineIndex + 1)
            .find(
              (next) =>
                next.box.x <= line.box.x + font * 0.4 && next.box.y - line.box.y < font * 12,
            )?.text ?? '',
        ) &&
        pendingType === 'paragraph' &&
        previous &&
        !/[.!?:;][”\"')\]]?$/.test(previous.text) &&
        gap >= -font * 0.4 &&
        gap < font * 0.8 &&
        Math.abs(line.fontSize - previous.fontSize) < font * 0.12
      )
        type = 'paragraph';
      if (
        type === 'paragraph' &&
        pendingType === 'list' &&
        pending.length &&
        line.box.x > pending[0]!.box.x + font * 0.4 &&
        gap < font * 0.8 &&
        gap > -font * 0.4
      )
        type = 'list';
      const startsReference = type === 'reference' && /^\[\d+\]/.test(line.text);
      const newParagraph =
        previous &&
        type === 'paragraph' &&
        (gap > font * 0.85 ||
          (boldParagraphLead(line) && /[.!?][”"')\]]?$/.test(previous.text)) ||
          (gap > Math.max(font * 0.35, normalGap + font * 0.18) &&
            /[.!?][”"')\]]?$/.test(previous.text)) ||
          (indent > font * 0.85 && /[.!?][”"')\]]?$/.test(previous.text)) ||
          Math.abs(proseSize(line) - proseSize(previous)) > font * 0.2);
      const wrappedTitle =
        previous &&
        type === 'heading' &&
        pendingType === 'heading' &&
        line.fontSize > font * 1.55 &&
        Math.abs(line.fontSize - previous.fontSize) < line.fontSize * 0.05 &&
        gap < line.fontSize * 0.7 &&
        gap >= -line.fontSize * 0.2;
      if (
        previous &&
        (type !== pendingType ||
          (type === 'heading' && !wrappedTitle) ||
          startsReference ||
          (!samePhysicalRow && (newParagraph || gap > font * 1.2 || gap < -font * 0.7)))
      )
        flush();
      pendingType = type;
      pending.push(line);
      if (type === 'heading' && line.fontSize <= font * 1.55) flush();
    }
    flush();
  }
  return blocks;
}
function readingOrder(
  blocks: ScholarlyBlock[],
  page: PageGeometry,
  cut?: number,
): ScholarlyBlock[] {
  // Adjacent plots can have different top edges. Their aligned captions identify
  // one source row, whose reading order is left-to-right rather than tallest-first.
  const rowTop = new Map<ScholarlyBlock, number>();
  const captionRows: ScholarlyBlock[][] = [];
  for (const block of blocks.filter((b) => isFloat(b) && b.captions?.length)) {
    const captionY = Math.min(...block.captions!.flatMap((c) => c.source.boxes.map((b) => b.y)));
    const row = captionRows.find((members) =>
      members.every((member) => {
        const peerY = Math.min(...member.captions!.flatMap((c) => c.source.boxes.map((b) => b.y)));
        const box = blockBox(block, page.page),
          peer = blockBox(member, page.page);
        return (
          Math.abs(captionY - peerY) <
            Math.min(block.fontStats.median, member.fontStats.median) * 0.6 &&
          horizontalOverlap(box, peer) < Math.min(box.width, peer.width) * 0.03 &&
          verticalOverlap(box, peer) > Math.min(box.height, peer.height) * 0.5
        );
      }),
    );
    if (row) row.push(block);
    else captionRows.push([block]);
  }
  for (const row of captionRows) {
    const y = Math.min(...row.map((block) => blockBox(block, page.page).y));
    for (const block of row) rowTop.set(block, y);
  }
  const sorted = [...blocks].sort(
    (a, b) =>
      (rowTop.get(a) ?? blockBox(a, page.page).y) - (rowTop.get(b) ?? blockBox(b, page.page).y) ||
      blockBox(a, page.page).x - blockBox(b, page.page).x,
  );
  if (cut === undefined) return sorted;
  const spans = sorted.filter((b) => {
    const box = blockBox(b, page.page);
    return box.x < cut - 2 && right(box) > cut + 2;
  });
  let rest = sorted.filter((b) => !spans.includes(b));
  const ordered: ScholarlyBlock[] = [];
  const columns = (list: ScholarlyBlock[]) =>
    list.sort((a, b) => {
      const aa = blockBox(a, page.page),
        bb = blockBox(b, page.page);
      return Number(aa.x >= cut) - Number(bb.x >= cut) || aa.y - bb.y || aa.x - bb.x;
    });
  for (const span of spans) {
    const y = blockBox(span, page.page).y;
    ordered.push(...columns(rest.filter((b) => blockBox(b, page.page).y < y)), span);
    rest = rest.filter((b) => blockBox(b, page.page).y >= y);
  }
  return [...ordered, ...columns(rest)];
}

function analyzePage(
  page: PageGeometry,
  lines: LayoutLine[],
  repeated: Set<string>,
): { page: PageAnalysis; blocks: ScholarlyBlock[] } {
  const suppressed = suppressedItems(page, lines, repeated);
  const usable = page.items.filter((i) => i.text.trim() && !suppressed.has(i.index));
  const fallback = (reason: string, unavailable = false) => {
    const box = { x: 0, y: 0, width: page.width, height: page.height };
    const block = makeBlock(
      page,
      page.items.filter((i) => !suppressed.has(i.index)).map((i) => i.index),
      [box],
      '',
      'visual-region',
      0.2,
    );
    block.role = 'unknown';
    block.fallbackReason = reason;
    return {
      page: {
        ...page,
        lines,
        columns: [],
        visualRegions: [{ box, role: 'unknown' as const, confidence: 0.2 }],
        blockIds: [],
        suppressedItemIndices: [...suppressed],
        ...(unavailable ? { unsupportedReason: reason } : {}),
      },
      blocks: [block],
    };
  };
  if (!usable.length) return fallback('No extractable text layer on this page', true);
  // Prevent pathological operator/text counts from exhausting line clustering or speculative ordering.
  if (page.items.length > 6000 || page.graphics.length > 10000)
    return fallback('Page complexity exceeds safe reflow limits');
  let regions = detectVisualRegions(page, lines, suppressed);
  const assigned = new Set(suppressed);
  const blocks: ScholarlyBlock[] = [];
  for (const region of regions) {
    const items = page.items.filter(
      (i) => !assigned.has(i.index) && centerInside(i.box, region.box),
    );
    items.forEach((i) => assigned.add(i.index));
    const block = makeBlock(
      page,
      items.map((i) => i.index),
      [region.box],
      '',
      'visual-region',
      region.confidence,
    );
    block.role = region.role;
    const owned = new Set(items.map((item) => item.index));
    const associated = lines.filter(
      (line) =>
        (region.role === 'figure' || region.role === 'table') &&
        captionRole(line.text) === region.role &&
        line.itemIndices.every((id) => owned.has(id)) &&
        (!region.captionIds?.length || region.captionIds.includes(line.id)),
    );
    const visualCaptions: VisualCaption[] = associated.flatMap((line) => {
      const label = line.text.match(/^\s*(?:Figure|Fig\.|Table)\s*(\d+|[IVX]+)(?:[.:\s]|$)/i)?.[1];
      const role = captionRole(line.text);
      if (!label || (role !== 'figure' && role !== 'table')) return [];
      // The prose gutter is not a caption boundary. Use the visual's width,
      // splitting it only where another independently labelled caption begins.
      const peers = associated.filter(
        (peer) => peer !== line && Math.abs(peer.box.y - line.box.y) < line.fontSize * 0.6,
      );
      const leftPeer = peers.filter((peer) => peer.box.x < line.box.x).at(-1);
      const rightPeer = peers.find((peer) => peer.box.x > line.box.x);
      const x = leftPeer ? (right(leftPeer.box) + line.box.x) / 2 : region.box.x;
      const end = rightPeer ? (right(line.box) + rightPeer.box.x) / 2 : right(region.box);
      const anchor = { ...line.box, x, width: end - x };
      const bounds = captionBox({ ...line, box: anchor }, lines, page, anchor);
      const captionItems = items.filter((item) => centerInside(item.box, bounds));
      const captionLines = clusterLines({ ...page, items: captionItems });
      return [
        {
          role,
          label,
          text: joinLines(captionLines.map((part) => part.text)),
          inlineRuns: buildInlineRuns(page, captionLines),
          source: {
            page: page.page,
            boxes: [unionBoxes(captionItems.map((item) => item.box))],
            itemIndices: captionItems.map((item) => item.index),
          },
        },
      ];
    });
    if (visualCaptions.length) {
      block.captions = visualCaptions;
      const captionY = Math.min(
        ...visualCaptions.flatMap((caption) => caption.source.boxes.map((box) => box.y)),
      );
      const captionIds = new Set(visualCaptions.flatMap((caption) => caption.source.itemIndices));
      const content = items.filter((item) => !captionIds.has(item.index));
      const graphicBelow = page.graphics.some(
        (graphic) =>
          graphic.kind !== 'form' &&
          graphic.box.height > 2 &&
          graphic.box.y >= captionY - 1 &&
          centerInside(graphic.box, region.box),
      );
      // Keep top/mixed captions in their original crop. A safe bottom caption
      // can be selectable prose, while zoom always retains the full source.
      if (
        (region.role === 'figure' || region.role === 'table') &&
        captionY > region.box.y + block.fontStats.median * 2 &&
        !graphicBelow &&
        content.every((item) => bottom(item.box) < captionY - 0.5)
      ) {
        block.previewBox = { ...region.box, height: captionY - region.box.y - 1 };
      }
    }
    block.fallbackReason = region.reason;
    blocks.push(block);
  }
  const remaining = page.items.filter((i) => !assigned.has(i.index) && i.text.trim());
  if (
    remaining.filter((i) => !isHorizontal(i)).length > Math.max(1, remaining.length * 0.04) ||
    (remaining.length === 1 && !isHorizontal(remaining[0]!))
  )
    return fallback('Rotated or vertical body text has ambiguous reading order');
  const bodyLines = clusterLines(page, assigned);
  const columns = detectColumns(page, bodyLines);
  if (columns.ambiguous) return fallback(columns.ambiguous);
  // Dense overlapping baselines outside known visuals cannot safely become prose.
  const overlaps = bodyLines.filter((l, i) =>
    bodyLines
      .slice(i + 1, i + 8)
      .some(
        (n) =>
          verticalOverlap(l.box, n.box) > Math.min(l.box.height, n.box.height) * 0.7 &&
          horizontalOverlap(l.box, n.box) > Math.min(l.box.width, n.box.width) * 0.6,
      ),
  ).length;
  if (overlaps > Math.max(4, bodyLines.length * 0.15))
    return fallback('Overlapping text makes page reading order uncertain');
  blocks.push(...textBlocks(page, bodyLines, columns.cut));
  regions = regions.filter((r) => r.box.width > 0 && r.box.height > 0);
  return {
    page: {
      ...page,
      lines,
      columns: columns.columns,
      visualRegions: regions.map(({ box, role, confidence }) => ({ box, role, confidence })),
      blockIds: [],
      suppressedItemIndices: [...suppressed].sort((a, b) => a - b),
    },
    blocks: readingOrder(blocks, page, columns.cut),
  };
}

const isFloat = (block: ScholarlyBlock) =>
  block.type === 'visual-region' && (block.role === 'figure' || block.role === 'table');

function proseFont(block: ScholarlyBlock, pages: PageAnalysis[]): number {
  const sizes = block.source.flatMap((span) => {
    const ids = new Set(span.itemIndices);
    return (
      pages
        .find((page) => page.page === span.page)
        ?.items.filter((item) => ids.has(item.index) && item.text.trim().length > 8)
        .map((item) => item.fontSize) ?? []
    );
  });
  return sizes.length ? median(sizes) : block.fontStats.median;
}

function sourceColumn(page: PageAnalysis, box: Rect): { box: Rect; index: number } | undefined {
  const candidates = page.columns.map((column, index) => ({ ...column, index }));
  return candidates.sort(
    (a, b) => horizontalOverlap(b.box, box) - horizontalOverlap(a.box, box),
  )[0];
}

function continuesProse(
  previous: ScholarlyBlock,
  next: ScholarlyBlock,
  pages: PageAnalysis[],
  interruptions: ScholarlyBlock[],
  blocks: ScholarlyBlock[],
): boolean {
  // A repeated mixed-case variable can start the next column without starting
  // a new sentence. Ordinary capitalized words still form a conservative break.
  const leadingIdentifier = next.text.match(/^([A-Z][a-z0-9]+[A-Z]\w*)\b/)?.[1];
  const repeatedIdentifier =
    leadingIdentifier &&
    previous.text.match(/\b[A-Za-z][A-Za-z0-9_]*\b/g)?.some((word) => word === leadingIdentifier);
  if (
    previous.type !== 'paragraph' ||
    next.type !== 'paragraph' ||
    /[.!?:;][”"')\]]?$/.test(previous.text) ||
    (!/^[a-z]/.test(next.text) && !repeatedIdentifier)
  )
    return false;
  const prevSpan = previous.source.at(-1),
    nextSpan = next.source[0];
  if (!prevSpan || !nextSpan) return false;
  const prevPage = pages.find((p) => p.page === prevSpan.page);
  const nextPage = pages.find((p) => p.page === nextSpan.page);
  const prevBox = prevSpan.boxes.at(-1),
    nextBox = nextSpan.boxes[0];
  if (!prevPage || !nextPage || !prevBox || !nextBox) return false;
  const prevColumn = sourceColumn(prevPage, prevBox),
    nextColumn = sourceColumn(nextPage, nextBox);
  const font = proseFont(previous, pages);
  if (
    !prevColumn ||
    !nextColumn ||
    Math.abs(font - proseFont(next, pages)) >= font * 0.12 ||
    nextBox.x > nextColumn.box.x + font * 0.75 ||
    Math.abs(prevColumn.box.width - nextColumn.box.width) >= prevPage.width * 0.15
  )
    return false;
  const nextPageFlow =
    nextSpan.page === prevSpan.page + 1 &&
    prevColumn.index === prevPage.columns.length - 1 &&
    nextColumn.index === 0;
  const nextColumnFlow =
    nextSpan.page === prevSpan.page && nextColumn.index === prevColumn.index + 1;
  if (nextPageFlow || nextColumnFlow) {
    // Notes occupy source-column space but remain separate reading-flow blocks.
    // Use text source boxes to retain real body/list barriers and ignore spanning
    // footer text, which was never part of the detected body column.
    const columnBottom = interruptions.some((block) => block.type === 'footnote')
      ? Math.max(
          bottom(prevBox),
          ...blocks
            .filter((block) => block.type !== 'footnote' && block.type !== 'visual-region')
            .flatMap((block) => block.source.filter((span) => span.page === prevSpan.page))
            .flatMap((span) => span.boxes)
            .filter(
              (box) => box.x >= prevColumn.box.x - 2 && right(box) <= right(prevColumn.box) + 2,
            )
            .map(bottom),
        )
      : bottom(prevColumn.box);
    // The top of the *body column* can be far below the page top because of a float.
    return (
      bottom(prevBox) >= columnBottom - font * 1.5 && nextBox.y <= nextColumn.box.y + font * 0.75
    );
  }
  return (
    interruptions.some(isFloat) &&
    !interruptions.some((block) => block.role === 'algorithm') &&
    nextSpan.page === prevSpan.page &&
    nextColumn.index === prevColumn.index &&
    nextBox.y > bottom(prevBox) &&
    interruptions.every((block) => block.source.every((span) => span.page === nextSpan.page))
  );
}

function mergeAcrossFlow(blocks: ScholarlyBlock[], pages: PageAnalysis[]): ScholarlyBlock[] {
  const result: ScholarlyBlock[] = [];
  for (const block of blocks) {
    let index = result.length - 1;
    while (
      index >= 0 &&
      (isFloat(result[index]!) ||
        result[index]!.type === 'footnote' ||
        result[index]!.role === 'algorithm')
    )
      index--;
    const previous = result[index];
    if (
      previous?.type === 'paragraph' &&
      /:\s*$/.test(previous.text) &&
      block.role === 'equation' &&
      result.slice(index + 1).every((entry) => isFloat(entry) || entry.type === 'footnote')
    ) {
      const before = previous.source.at(-1),
        after = block.source[0];
      const p = pages.find((page) => page.page === before?.page);
      const a = before?.boxes.at(-1),
        b = after?.boxes[0];
      if (
        p &&
        a &&
        b &&
        before?.page === after?.page &&
        sourceColumn(p, a)?.index === sourceColumn(p, b)?.index &&
        b.y >= bottom(a) - 1 &&
        b.y - bottom(a) < proseFont(previous, pages) * 3
      ) {
        // A display expression completes its introducing sentence before a
        // float/note deferred while the preceding paragraph crossed columns.
        result.splice(index + 1, 0, block);
        continue;
      }
    }
    if (previous && continuesProse(previous, block, pages, result.slice(index + 1), blocks)) {
      previous.text = joinLines([previous.text, block.text]);
      previous.inlineRuns = joinInlineRuns(previous.inlineRuns ?? [], block.inlineRuns ?? []);
      for (const span of block.source) {
        const existing = previous.source.find((s) => s.page === span.page);
        if (existing) {
          existing.boxes.push(...span.boxes);
          existing.itemIndices.push(...span.itemIndices);
        } else previous.source.push(span);
      }
      previous.confidence = Math.min(previous.confidence, block.confidence, 0.82);
    } else result.push(block);
  }
  return result;
}

function finalize(
  results: Array<{ page: PageAnalysis; blocks: ScholarlyBlock[] }>,
  fingerprint: string,
  pdfjsVersion: string,
): ScholarlyDocument {
  const pages = results.map((r) => r.page);
  const ordered = results.flatMap((r) => r.blocks);
  let references = false;
  for (const block of ordered) {
    if (block.type === 'heading') references = /^(?:references|bibliography)\b/i.test(block.text);
    else if (references && block.type === 'paragraph') block.type = 'reference';
  }
  // Preserve source-near float order; only finish an interrupted paragraph first.
  const blocks = mergeAcrossFlow(ordered, pages);
  const sourceMap: Record<string, SourceSpan[]> = {};
  for (let order = 0; order < blocks.length; order++) {
    const block = blocks[order]!;
    block.id = `p${block.source[0]?.page ?? 0}-b${order}`;
    block.order = order;
    sourceMap[block.id] = block.source;
    for (const span of block.source)
      pages.find((p) => p.page === span.page)?.blockIds.push(block.id);
  }
  const warnings = [
    ...new Set(blocks.filter((b) => b.fallbackReason).map((b) => b.fallbackReason!)),
  ];
  const document: ScholarlyDocument = {
    schemaVersion: SCHEMA_VERSION,
    parserVersion: PARSER_VERSION,
    fingerprint,
    pageCount: pages.length,
    metadata: { pdfjsVersion },
    pages,
    blocks,
    readingOrder: blocks.map((b) => b.id),
    sourceMap,
    warnings,
  };
  const issues = validateSourceCoverage(document);
  if (issues.length)
    throw new Error(`Academic source coverage failure: ${issues.slice(0, 3).join('; ')}`);
  return document;
}
/** Pure deterministic analysis, suitable for a worker and geometry regression fixtures. */
export function analyzeDocument(
  pages: PageGeometry[],
  fingerprint: string,
  pdfjsVersion: string,
): ScholarlyDocument {
  const lines = pages.map((p) => (p.items.length > 6000 ? [] : clusterLines(p)));
  const repeated = repeatedMargins(pages, lines);
  return finalize(
    pages.map((p, i) => analyzePage(p, lines[i]!, repeated)),
    fingerprint,
    pdfjsVersion,
  );
}
const abort = (signal?: AbortSignal) => {
  if (signal?.aborted) throw new DOMException('Academic analysis cancelled', 'AbortError');
};
const yieldTask = () => new Promise<void>((resolve) => setTimeout(resolve, 0));
/** Main-thread fallback deliberately yields between every page in both passes. */
export async function analyzeDocumentAsync(
  pages: PageGeometry[],
  fingerprint: string,
  pdfjsVersion: string,
  signal?: AbortSignal,
  onProgress?: (completed: number, total: number) => void,
): Promise<ScholarlyDocument> {
  const lines: LayoutLine[][] = [];
  for (const page of pages) {
    abort(signal);
    lines.push(page.items.length > 6000 ? [] : clusterLines(page));
    await yieldTask();
  }
  const repeated = repeatedMargins(pages, lines);
  const results: Array<{ page: PageAnalysis; blocks: ScholarlyBlock[] }> = [];
  for (let i = 0; i < pages.length; i++) {
    abort(signal);
    results.push(analyzePage(pages[i]!, lines[i]!, repeated));
    onProgress?.(i + 1, pages.length);
    await yieldTask();
  }
  abort(signal);
  return finalize(results, fingerprint, pdfjsVersion);
}

/** Every original PDF.js item belongs exactly once to a block or an explicit suppression. */
export function validateSourceCoverage(document: ScholarlyDocument): string[] {
  const issues: string[] = [];
  const counts = new Map<string, number>();
  const expected = new Set(
    document.pages.flatMap((p) => p.items.map((i) => `${p.page}:${i.index}`)),
  );
  const count = (page: number, index: number) => {
    const key = `${page}:${index}`;
    counts.set(key, (counts.get(key) ?? 0) + 1);
    if (!expected.has(key)) issues.push(`Unknown item ${key}`);
  };
  const checkInline = (runs: InlineRun[] | undefined, sources: SourceSpan[], label: string) => {
    if (!runs) return;
    const owned = new Set(
      sources.flatMap((span) => span.itemIndices.map((id) => `${span.page}:${id}`)),
    );
    const seen = new Map<string, number>();
    for (const run of runs)
      for (const id of run.source.itemIndices) {
        const key = `${run.source.page}:${id}`;
        if (!owned.has(key)) issues.push(`Unknown inline item ${key} in ${label}`);
        seen.set(key, (seen.get(key) ?? 0) + 1);
      }
    for (const key of owned)
      if (seen.get(key) !== 1)
        issues.push(`Inline item ${key} has ${seen.get(key) ?? 0} owners in ${label}`);
  };
  for (const page of document.pages)
    for (const index of page.suppressedItemIndices) count(page.page, index);
  for (const block of document.blocks) {
    for (const span of block.source) for (const index of span.itemIndices) count(span.page, index);
    checkInline(block.inlineRuns, block.source, block.id);
    checkInline(block.listInlineRuns?.flat(), block.source, block.id);
    for (const caption of block.captions ?? [])
      checkInline(caption.inlineRuns, [caption.source], block.id);
  }
  for (const key of expected)
    if (counts.get(key) !== 1) issues.push(`Item ${key} has ${counts.get(key) ?? 0} owners`);
  return issues;
}
