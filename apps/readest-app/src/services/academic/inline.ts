import type {
  InlineRun,
  InlineTextStyle,
  LayoutLine,
  PageGeometry,
  PdfTextItem,
  Rect,
} from './types';

const right = (box: Rect) => box.x + box.width;
const bottom = (box: Rect) => box.y + box.height;
const overlap = (a: Rect, b: Rect) =>
  Math.max(0, Math.min(right(a), right(b)) - Math.max(a.x, b.x));
const median = (values: number[]) =>
  [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)] ?? 10;
const bounds = (boxes: Rect[]): Rect => {
  const x = Math.min(...boxes.map((box) => box.x)),
    y = Math.min(...boxes.map((box) => box.y));
  return {
    x,
    y,
    width: Math.max(...boxes.map(right)) - x,
    height: Math.max(...boxes.map(bottom)) - y,
  };
};
const localFont = (items: PdfTextItem[]) => {
  const ordinary = items.filter((item) => item.text.trim().length > 1);
  return Math.max(...(ordinary.length ? ordinary : items).map((item) => item.fontSize), 1);
};
const baseItems = (items: PdfTextItem[], font: number) =>
  items.filter((item) => item.fontSize >= font * 0.94);
const compact = (item: PdfTextItem, font: number) =>
  item.text.length <= 40 && (item.fontSize < font * 0.92 || /^\S{1,8}$/.test(item.text));
const unmapped = (item: PdfTextItem) =>
  /[\p{Cc}\p{Co}\uFFFD]/u.test(item.text.trim()) ||
  (item.fontMath === true && /^\p{L}{1,4}$/u.test(item.text.trim()));

/** Broken font mappings can also report a raised baseline for an ordinary-size operator. */
export function unmappedGlyphAnchors(items: PdfTextItem[]): Map<number, PdfTextItem> {
  const anchors = new Map<number, PdfTextItem>();
  for (const glyph of items.filter(unmapped)) {
    const nearby = items.filter((item) => {
      const gap =
        item.index < glyph.index ? glyph.box.x - right(item.box) : item.box.x - right(glyph.box);
      return (
        item.text.trim() &&
        !unmapped(item) &&
        item.fontSize >= glyph.fontSize * 0.94 &&
        item.fontSize <= glyph.fontSize * 1.2 &&
        Math.abs(item.baseline - glyph.baseline) <= item.fontSize &&
        gap >= -item.fontSize * 0.1 &&
        gap <= item.fontSize * 1.5
      );
    });
    // Source adjacency disambiguates two physical rows equally near a raised glyph.
    nearby.sort((a, b) => Math.abs(a.index - glyph.index) - Math.abs(b.index - glyph.index));
    if (nearby[0]) anchors.set(glyph.index, nearby[0]);
  }
  return anchors;
}

type Crop = {
  items: PdfTextItem[];
  box: Rect;
  fontSize: number;
  baseline: number;
  trimBelow?: number;
  axis?: number;
  anchorIndex?: number;
};

function unmappedCrops(page: PageGeometry, items: PdfTextItem[], occupied: Set<number>): Crop[] {
  const anchors = unmappedGlyphAnchors(items);
  const crops: Crop[] = [];
  for (const glyph of items.filter((item) => unmapped(item) && !occupied.has(item.index))) {
    const anchor = anchors.get(glyph.index) ?? glyph;
    const font = anchor.fontSize;
    const ordinary = items.filter((item) => !unmapped(item) && item.fontSize >= font * 0.87);
    const before = Math.max(
      -Infinity,
      ...ordinary.filter((item) => item.index < glyph.index).map((item) => item.index),
    );
    const after = Math.min(
      Infinity,
      ...ordinary.filter((item) => item.index > glyph.index).map((item) => item.index),
    );
    const members = items.filter((item) => {
      if (item === glyph) return true;
      return (
        !occupied.has(item.index) &&
        !unmapped(item) &&
        item.index > before &&
        item.index < after &&
        item.fontSize < font * 0.87 &&
        /^\S{1,8}$/.test(item.text) &&
        item.baseline >= anchor.baseline - font * 1.3 &&
        item.baseline <= anchor.baseline + font * 0.8 &&
        (overlap(item.box, glyph.box) > Math.min(item.box.width, glyph.box.width) * 0.4 ||
          (item.box.x >= glyph.box.x && item.box.x - right(glyph.box) <= font * 0.25))
      );
    });
    // Nominal font ascent can miss the actual ink of an unmapped operator.
    // Include its surrounding text band, then stop at neighboring rows' ink boxes.
    const area = bounds([
      ...members.map((item) => item.box),
      {
        x: glyph.box.x,
        y: anchor.baseline - font * 0.8,
        width: glyph.box.width,
        height: font * 1.1,
      },
    ]);
    const pad = font * 0.06;
    const x = Math.max(0, area.x - pad);
    const box = {
      x,
      y: Math.max(0, area.y - pad),
      width: Math.min(page.width, right(area) + pad) - x,
      height: 0,
    };
    let end = Math.min(page.height, bottom(area) + pad);
    const outside = page.items.filter(
      (item) => item.text.trim() && !members.includes(item) && overlap(item.box, box) > 0,
    );
    for (const item of outside) {
      if (item.baseline < anchor.baseline - font * 0.5 && bottom(item.box) <= anchor.baseline)
        box.y = Math.max(box.y, bottom(item.box) + pad);
      else if (item.baseline > anchor.baseline + font * 0.5 && item.box.y > anchor.baseline)
        end = Math.min(end, item.box.y - pad);
    }
    box.height = end - box.y;
    if (
      box.height <= 0 ||
      box.height > font * 3 ||
      box.width > font * 5 ||
      members.some((item) => item !== glyph && (item.box.y < box.y || bottom(item.box) > end)) ||
      outside.some(
        (item) =>
          overlap(item.box, box) > Math.min(item.box.width, box.width) * 0.4 &&
          item.box.y + item.box.height / 2 > box.y &&
          item.box.y + item.box.height / 2 < end,
      )
    )
      continue;
    members.forEach((item) => occupied.add(item.index));
    crops.push({
      items: members,
      box,
      fontSize: font,
      baseline: anchor.baseline,
      anchorIndex: anchor.index,
    });
  }
  return crops;
}

/** Only accept a crop when every visible glyph inside it belongs to this block. */
function makeCrop(
  page: PageGeometry,
  items: PdfTextItem[],
  selected: Set<number>,
  box: Rect,
  font: number,
): Crop | undefined {
  const members = items.filter(
    (item) =>
      overlap(item.box, box) > Math.min(item.box.width, box.width) * 0.4 &&
      item.box.y + item.box.height / 2 >= box.y &&
      item.box.y + item.box.height / 2 <= bottom(box),
  );
  if (members.length < 2 || members.some((item) => !selected.has(item.index))) return;
  const area = bounds([box, ...members.map((item) => item.box)]);
  if (area.width > page.width * 0.7 || area.height > font * 3) return;
  const pad = font * 0.06;
  const x = Math.max(0, area.x - pad),
    y = Math.max(0, area.y - pad);
  const padded = {
    x,
    y,
    width: Math.min(page.width, right(area) + pad) - x,
    height: Math.min(page.height, bottom(area) + pad) - y,
  };
  if (
    page.items.some(
      (item) =>
        item.text.trim() &&
        !members.includes(item) &&
        overlap(item.box, padded) > item.box.width * 0.4 &&
        item.box.y + item.box.height / 2 > padded.y &&
        item.box.y + item.box.height / 2 < bottom(padded),
    )
  )
    return;
  const outside = items.filter(
    (item) =>
      !members.includes(item) &&
      item.fontSize >= font * 0.94 &&
      Math.abs(item.baseline - (area.y + area.height / 2)) < font &&
      Math.min(Math.abs(item.box.x - right(area)), Math.abs(right(item.box) - area.x)) < font * 5,
  );
  // A nearby ordinary baseline distinguishes inline notation from adjacent body rows.
  if (!outside.length) return;
  const lowestBaseline = Math.max(...members.map((item) => item.baseline));
  const followingInk = page.items.some(
    (item) =>
      item.text.trim() &&
      !members.includes(item) &&
      item.baseline > lowestBaseline &&
      overlap(item.box, padded) > 0 &&
      item.box.y < bottom(padded) &&
      bottom(item.box) > padded.y,
  );
  return {
    items: members,
    box: padded,
    fontSize: font,
    baseline: median(outside.map((item) => item.baseline)),
    ...(followingInk ? { trimBelow: lowestBaseline } : {}),
  };
}

function sourceCrops(page: PageGeometry, items: PdfTextItem[]): Crop[] {
  const selected = new Set(items.map((item) => item.index));
  const font = localFont(items);
  const crops: Crop[] = [];
  for (const graphic of page.graphics) {
    const rule = graphic.box;
    if (
      !['rule', 'path', 'image'].includes(graphic.kind) ||
      rule.height > Math.max(1, font * 0.15) ||
      rule.width < font * 0.3 ||
      rule.width < rule.height * 4
    )
      continue;
    const nearby = items.filter(
      (item) =>
        compact(item, font) &&
        overlap(item.box, rule) > item.box.width * 0.4 &&
        Math.abs(item.baseline - rule.y) < font * 1.5,
    );
    const above = nearby.filter((item) => item.baseline < rule.y - font * 0.07);
    const below = nearby.filter((item) => item.baseline > bottom(rule) + font * 0.12);
    if (!above.length || !below.length) continue;
    const upper = Math.max(...above.map((item) => item.baseline)),
      lower = Math.min(...below.map((item) => item.baseline));
    if (lower - upper < font * 0.35 || lower - upper > font * 1.5) continue;
    const members = nearby.filter(
      (item) =>
        Math.abs(item.baseline - upper) < font * 0.3 ||
        Math.abs(item.baseline - lower) < font * 0.3,
    );
    const crop = makeCrop(
      page,
      items,
      selected,
      bounds([rule, ...members.map((item) => item.box)]),
      font,
    );
    if (crop && !crops.some((other) => other.items.some((item) => crop.items.includes(item))))
      crops.push({ ...crop, axis: rule.y + rule.height / 2 });
  }
  // A real bar bounds the complete numerator/denominator. Mere vertical overlap
  // also occurs between scripts on successive prose rows and cannot establish a fraction.
  return [
    ...crops,
    ...unmappedCrops(
      page,
      items,
      new Set(crops.flatMap((crop) => crop.items.map((item) => item.index))),
    ),
  ];
}

function styleFor(item: PdfTextItem, font: number, baseline: number): InlineTextStyle | undefined {
  const style: InlineTextStyle = {};
  const descriptor = `${item.fontName} ${item.fontFamily}`;
  if (item.fontMonospace) style.fontFamily = 'monospace';
  if (item.fontStyle || /italic|oblique/i.test(descriptor)) style.fontStyle = 'italic';
  if (item.fontWeight || /bold|semibold|demibold/i.test(descriptor)) style.fontWeight = 'bold';
  const delta = item.baseline - baseline;
  if (
    item.fontSize < font * 0.87 &&
    /^\S{1,4}$/.test(item.text.trim()) &&
    Math.abs(delta) >= font * 0.12 &&
    Math.abs(delta) < font * 0.7
  )
    style.verticalAlign = delta > 0 ? 'sub' : 'super';
  return Object.keys(style).length ? style : undefined;
}

/** Joins physical rows or continued paragraphs without discarding styles/sources. */
export function joinInlineRuns(previous: InlineRun[], next: InlineRun[]): InlineRun[] {
  if (!previous.length) return next.map((run) => ({ ...run }));
  if (!next.length) return previous.map((run) => ({ ...run }));
  const left = previous.map((run) => ({ ...run })),
    right = next.map((run) => ({ ...run }));
  const last = left[left.length - 1]!,
    first = right[0]!;
  const text = left.map((run) => run.text).join('');
  if (
    last.kind === 'text' &&
    first.kind === 'text' &&
    (text.endsWith('\u00ad') ||
      (/-$/.test(text) &&
        /^[a-z]{3,}$/.test(text.match(/(\S+)-$/)?.[1] ?? '') &&
        /^[a-z]{2}/.test(first.text)))
  )
    last.text = last.text.slice(0, -1);
  else if (
    !/-$|\s$/.test(text) &&
    !/^\s/.test(first.text) &&
    !(
      /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}，。！？：；、）】》]$/u.test(text) &&
      /^[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}，。！？：；、（【《]/u.test(
        first.text,
      )
    )
  )
    // Put inferred separators in a separate text run, never inside source alt text.
    left.push({
      kind: 'text',
      text: ' ',
      source: { page: first.source.page, boxes: [], itemIndices: [] },
    });
  return [...left, ...right];
}

/** Conservatively preserve source notation and recover only reliable text styling. */
export function buildInlineRuns(page: PageGeometry, lines: LayoutLine[]): InlineRun[] {
  const wanted = new Set(lines.flatMap((line) => line.itemIndices));
  const items = page.items.filter((item) => wanted.has(item.index) && item.text.trim());
  if (!items.length) return [];
  const detected = sourceCrops(page, items);
  const cropIds = new Set(detected.flatMap((crop) => crop.items.map((item) => item.index)));
  const anchored = detected.flatMap((crop) => {
    if (crop.anchorIndex !== undefined) {
      const anchor = lines.find((line) => line.itemIndices.includes(crop.anchorIndex!));
      return anchor ? [{ crop, anchor }] : [];
    }
    const expected = (crop.axis ?? crop.baseline - crop.fontSize * 0.25) + crop.fontSize * 0.25;
    const candidates = lines.flatMap((line) => {
      const ordinary = items.filter(
        (item) =>
          line.itemIndices.includes(item.index) &&
          !cropIds.has(item.index) &&
          item.fontSize >= crop.fontSize * 0.94 &&
          Math.abs(item.baseline - expected) < crop.fontSize * 0.5,
      );
      return ordinary.length
        ? [{ line, baseline: median(ordinary.map((item) => item.baseline)) }]
        : [];
    });
    const center = crop.box.x + crop.box.width / 2;
    const distance = (line: LayoutLine) =>
      Math.max(line.box.x - center, center - right(line.box), 0);
    const anchor = candidates.sort((a, b) => {
      const delta = Math.abs(a.baseline - expected) - Math.abs(b.baseline - expected);
      return Math.abs(delta) > crop.fontSize * 0.05 ? delta : distance(a.line) - distance(b.line);
    })[0];
    return anchor ? [{ crop: { ...crop, baseline: anchor.baseline }, anchor: anchor.line }] : [];
  });
  const crops = anchored.map(({ crop }) => crop);
  const spaces = new Map(
    page.items.filter((item) => /^\s+$/.test(item.text)).map((item) => [item.index, item]),
  );
  const cropFor = new Map(
    crops.flatMap((crop) => crop.items.map((item) => [item.index, crop] as const)),
  );
  const emitted = new Set<number>();
  let result: InlineRun[] = [];
  for (const line of lines) {
    // Numerators can occupy a separate, earlier LayoutLine. Emit the whole
    // expression on the surrounding prose baseline, never on that first glyph.
    const lineItems = items.filter(
      (item) => line.itemIndices.includes(item.index) && !cropFor.has(item.index),
    );
    const lineCrops = anchored.filter(({ anchor }) => anchor === line).map(({ crop }) => crop);
    if (!lineItems.length && !lineCrops.length) continue;
    const font = localFont(lineItems);
    const baseline = median(baseItems(lineItems, font).map((item) => item.baseline));
    const atoms = [
      ...lineItems.map((item) => ({ item, crop: undefined as Crop | undefined })),
      ...lineCrops.map((crop) => ({ item: crop.items[0]!, crop })),
    ].sort(
      (a, b) =>
        (a.crop?.box.x ?? a.item.box.x) - (b.crop?.box.x ?? b.item.box.x) ||
        a.item.index - b.item.index,
    );
    const runs: InlineRun[] = [];
    let previousBox: Rect | undefined;
    let previousText = '';
    let previousIndex: number | undefined;
    for (const { item, crop } of atoms) {
      if (emitted.has(item.index)) continue;
      const box = crop?.box ?? item.box;
      const text = crop
        ? [...crop.items]
            .sort((a, b) => a.index - b.index)
            .map((item) => item.text)
            .join(' ')
        : item.text.replace(/\s+/g, ' ');
      const explicitSpace =
        previousIndex !== undefined &&
        item.index === previousIndex + 2 &&
        spaces.has(previousIndex + 1) &&
        Math.abs(spaces.get(previousIndex + 1)!.baseline - item.baseline) < font * 0.12;
      if (
        previousBox &&
        (explicitSpace || box.x - right(previousBox) > Math.min(font, item.fontSize) * 0.17) &&
        !/\s$/.test(previousText) &&
        !/^\s|^[,.;:!?\])}]/.test(text)
      )
        runs.push({
          kind: 'text',
          text: ' ',
          source: { page: page.page, boxes: [], itemIndices: [] },
        });
      if (crop) {
        crop.items.forEach((member) => emitted.add(member.index));
        runs.push({
          kind: 'source',
          text,
          source: {
            page: page.page,
            boxes: [crop.box],
            itemIndices: crop.items.map((member) => member.index).sort((a, b) => a - b),
          },
          fontSize: crop.fontSize,
          baseline: crop.baseline,
          ...(crop.trimBelow !== undefined ? { trimBelow: crop.trimBelow } : {}),
        });
      } else {
        emitted.add(item.index);
        runs.push({
          kind: 'text',
          text,
          source: { page: page.page, boxes: [item.box], itemIndices: [item.index] },
          style: styleFor(item, font, baseline),
        });
      }
      previousBox = box;
      previousText = text;
      previousIndex = crop ? undefined : item.index;
    }
    result = joinInlineRuns(result, runs);
  }
  return result;
}
