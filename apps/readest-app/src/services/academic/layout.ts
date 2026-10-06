import type {
  FontStatistics,
  LayoutColumn,
  LayoutLine,
  PageAnalysis,
  PageGeometry,
  PdfTextItem,
  Rect,
  ScholarlyBlock,
  ScholarlyDocument,
  SourceSpan,
  VisualRole,
} from './types';

export const SCHEMA_VERSION = 1;
/** Change when extraction, ordering or classification changes, not just JSON shape. */
export const PARSER_VERSION = 'academic-2';
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
  const rows: Array<{ baseline: number; size: number; items: PdfTextItem[] }> = [];
  // Main glyphs establish baseline anchors before superscripts/subscripts are attached.
  for (const item of [...items].sort(
    (a, b) =>
      b.fontSize - a.fontSize || a.baseline - b.baseline || a.box.x - b.box.x || a.index - b.index,
  )) {
    let closest: (typeof rows)[number] | undefined;
    let distance = Infinity;
    for (const row of rows) {
      const delta = Math.abs(row.baseline - item.baseline);
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
    else rows.push({ baseline: item.baseline, size: item.fontSize, items: [item] });
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
        fontSize: median(group.map((i) => i.fontSize)),
      });
      group = [];
    };
    for (const item of row.items.sort((a, b) => a.box.x - b.box.x || a.index - b.index)) {
      const previous = group[group.length - 1];
      if (previous && item.box.x - right(previous.box) > Math.max(18, row.size * 1.8)) flush();
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
}
const captionRole = (text: string): VisualRole | undefined => {
  if (/^\s*(?:Algorithm|Procedure)\s+\d+[.:\s]/i.test(text)) return 'algorithm';
  if (/^\s*Table\s+(?:\d+|[IVX]+)[.:\s]/i.test(text)) return 'table';
  if (/^\s*(?:Figure|Fig\.)\s*\d+[.:\s]/i.test(text)) return 'figure';
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
  const forms = page.graphics
    .filter(
      (g) =>
        (g.kind === 'form' || g.kind === 'image') &&
        g.box.width > font * 1.5 &&
        g.box.height > font * 1.5,
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
  // Standalone equations include nearby fragmented baselines and right-side equation numbers.
  const available = lines.filter(
    (l) =>
      !l.itemIndices.every((id) => excluded.has(id)) &&
      !regions.some((r) => centerInside(l.box, r.box)),
  );
  for (const graphic of page.graphics) {
    const rule = graphic.box;
    if (
      graphic.kind !== 'rule' ||
      rule.height > 1.5 ||
      rule.width < 5 ||
      rule.width > font * 12 ||
      regions.some((r) => centerInside(rule, r.box))
    )
      continue;
    const nearby = available.filter(
      (line) =>
        horizontalOverlap(rule, line.box) > Math.min(rule.width, line.box.width) * 0.5 &&
        line.box.width < rule.width * 2 &&
        (line.text.match(/\b[a-zA-Z]{4,}\b/g) ?? []).length < 3,
    );
    const above = nearby.filter(
      (line) => bottom(line.box) <= rule.y + font * 0.3 && bottom(line.box) >= rule.y - font * 1.6,
    );
    const below = nearby.filter(
      (line) => line.box.y >= rule.y - font * 0.3 && line.box.y <= rule.y + font * 1.6,
    );
    if (above.length && below.length)
      regions.push({
        box: padded(
          unionBoxes([rule, ...above.map((l) => l.box), ...below.map((l) => l.box)]),
          2,
          page,
        ),
        role: 'equation',
        confidence: 0.8,
        reason: 'Fraction layout retained without reconstructing mathematical notation',
      });
  }
  const mathCut = detectColumns(page, available).cut;
  for (const line of available) {
    if (regions.some((r) => centerInside(line.box, r.box))) continue;
    const math = /[=∑∫√∏≤≥≈≠∞∂∇\u0370-\u03ff\u2200-\u22ff]/.test(line.text);
    const numbered = /^\(\d+[a-z]?\)$/.test(line.text.trim());
    const fragments =
      line.itemIndices.length >= 4 && line.text.length / line.itemIndices.length < 4;
    const prose = (line.text.match(/\b[a-zA-Z]{4,}\b/g) ?? []).length;
    if (!(numbered || (math && prose < 4 && (line.box.width < page.width * 0.65 || fragments))))
      continue;
    const colLeft = mathCut !== undefined && line.box.x >= mathCut ? mathCut : 0;
    const colRight = mathCut !== undefined && line.box.x < mathCut ? mathCut : page.width;
    const hasOtherColumn = mathCut !== undefined;
    const neighbors = available.filter(
      (l) =>
        Math.abs(l.box.y - line.box.y) < font * 1.4 &&
        (!hasOtherColumn || (l.box.x >= colLeft - 2 && right(l.box) <= colRight + 5)) &&
        (l.text.match(/\b[a-zA-Z]{4,}\b/g) ?? []).length < 5,
    );
    const box = unionBoxes(neighbors.map((l) => l.box));
    regions.push({
      box: padded(box, 2, page),
      role: 'equation',
      confidence: numbered ? 0.9 : 0.65,
      reason: 'Display mathematics retained in original layout',
    });
  }
  // Merge intersecting visual detections so a source item can never be emitted twice.
  const merged: Region[] = [];
  for (const region of regions) {
    let current = region;
    for (let i = 0; i < merged.length; i++) {
      const other = merged[i]!;
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
function repeatedMargins(pages: PageGeometry[], linePages: LayoutLine[][]): Set<string> {
  const counts = new Map<string, Set<number>>();
  for (let i = 0; i < pages.length; i++) {
    for (const line of linePages[i]!) {
      if (line.box.y > pages[i]!.height * 0.105 && bottom(line.box) < pages[i]!.height * 0.92)
        continue;
      const key = `${line.box.y < pages[i]!.height / 2 ? 'top' : 'bottom'}:${marginKey(line.text)}`;
      if (line.text.length > 2) {
        const seen = counts.get(key) ?? new Set();
        seen.add(i);
        counts.set(key, seen);
      }
    }
  }
  return new Set(
    [...counts]
      .filter(([, seen]) => seen.size >= Math.max(2, Math.ceil(pages.length * 0.4)))
      .map(([key]) => key),
  );
}
function suppressedItems(
  page: PageGeometry,
  lines: LayoutLine[],
  repeated: Set<string>,
): Set<number> {
  const suppressed = new Set(page.items.filter((i) => !i.text.trim()).map((i) => i.index));
  for (const line of lines) {
    const margin = line.box.y < page.height * 0.105 || bottom(line.box) > page.height * 0.92;
    const key = `${line.box.y < page.height / 2 ? 'top' : 'bottom'}:${marginKey(line.text)}`;
    if (margin && (repeated.has(key) || /^[-–—]?\s*\d{1,4}\s*[-–—]?$/.test(line.text)))
      line.itemIndices.forEach((id) => suppressed.add(id));
  }
  return suppressed;
}
function detectColumns(
  page: PageGeometry,
  lines: LayoutLine[],
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
  if (anchors.filter((a) => a.count >= 5).length >= 3)
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
  if (/^(?:abstract|references|bibliography|acknowledg(?:e)?ments|appendix)\b/i.test(line.text))
    return true;
  if (!/^(?:[1-9]|1\d)(?:\.\d+)*\s+\p{Lu}/u.test(line.text)) return false;
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
      if (pendingType === 'heading')
        block.level = pending[0]!.fontSize > font * 1.55 ? 1 : /^\d+\.\d+/.test(block.text) ? 3 : 2;
      if (pendingType === 'list') {
        block.listItems = pending.reduce<string[]>((items, line) => {
          if (!items.length || listStart(line.text)) items.push(line.text);
          else items[items.length - 1] = joinLines([items[items.length - 1]!, line.text]);
          return items;
        }, []);
      }
      blocks.push(block);
      pending = [];
    };
    for (const line of [...group].sort((a, b) => a.box.y - b.box.y || a.box.x - b.box.x)) {
      const isHeading = heading(line, font, bodyTypeface, items);
      const footnoteRule = page.graphics.some(
        (g) =>
          g.kind === 'rule' &&
          g.box.y > page.height * 0.65 &&
          g.box.y < line.box.y &&
          line.box.y - g.box.y < font * 10 &&
          horizontalOverlap(g.box, line.box) > 0,
      );
      const isFootnote =
        line.fontSize < font * 0.87 &&
        line.box.y > page.height * 0.72 &&
        (footnoteRule || /^\d+\s/.test(line.text));
      if (/^(?:references|bibliography)\b/i.test(line.text)) references = true;
      let type: ScholarlyBlock['type'] = isFootnote
        ? 'footnote'
        : isHeading
          ? 'heading'
          : /^\[\d+\]/.test(line.text) || references
            ? 'reference'
            : listStart(line.text)
              ? 'list'
              : 'paragraph';
      const previous = pending[pending.length - 1];
      const gap = previous ? line.box.y - bottom(previous.box) : Infinity;
      const indent = previous ? line.box.x - previous.box.x : 0;
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
          (indent > font * 0.85 && /[.!?][”"')\]]?$/.test(previous.text)) ||
          Math.abs(line.fontSize - previous.fontSize) > font * 0.2);
      if (
        previous &&
        (type !== pendingType ||
          type === 'heading' ||
          startsReference ||
          newParagraph ||
          gap > font * 1.2 ||
          gap < -font * 0.7)
      )
        flush();
      pendingType = type;
      pending.push(line);
      if (type === 'heading') flush();
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
  const sorted = [...blocks].sort(
    (a, b) =>
      blockBox(a, page.page).y - blockBox(b, page.page).y ||
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
      (i) => !assigned.has(i.index) && centerInside(i.box, region.box, 0.7),
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

function mergeAcrossPages(blocks: ScholarlyBlock[], pages: PageAnalysis[]): ScholarlyBlock[] {
  const result: ScholarlyBlock[] = [];
  for (const block of blocks) {
    const previous = result[result.length - 1];
    const prevSpan = previous?.source[previous.source.length - 1],
      nextSpan = block.source[0];
    const prevPage = pages.find((p) => p.page === prevSpan?.page),
      nextPage = pages.find((p) => p.page === nextSpan?.page);
    if (
      previous?.type === 'paragraph' &&
      block.type === 'paragraph' &&
      prevSpan &&
      nextSpan &&
      nextSpan.page === prevSpan.page + 1 &&
      prevPage &&
      nextPage &&
      !/[.!?:;][”"')\]]?$/.test(previous.text) &&
      /^[a-z]/.test(block.text) &&
      Math.abs(previous.fontStats.median - block.fontStats.median) <
        previous.fontStats.median * 0.12 &&
      bottom(unionBoxes(prevSpan.boxes)) > prevPage.height * 0.78 &&
      unionBoxes(nextSpan.boxes).y < nextPage.height * 0.22 &&
      Math.abs(unionBoxes(prevSpan.boxes).width - unionBoxes(nextSpan.boxes).width) <
        prevPage.width * 0.12
    ) {
      previous.text = joinLines([previous.text, block.text]);
      previous.source.push(...block.source);
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
  const blocks = mergeAcrossPages(ordered, pages);
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
  for (const page of document.pages)
    for (const index of page.suppressedItemIndices) count(page.page, index);
  for (const block of document.blocks)
    for (const span of block.source) for (const index of span.itemIndices) count(span.page, index);
  for (const key of expected)
    if (counts.get(key) !== 1) issues.push(`Item ${key} has ${counts.get(key) ?? 0} owners`);
  return issues;
}
