import type { InlineRun, ScholarlyBlock, ScholarlyDocument, SourceSpan } from './types';

/** Offsets address the rendered slot's original text, in JavaScript UTF-16 units. */
export interface AcademicLink {
  id: string;
  start: number;
  end: number;
  target: string;
  kind: 'reference' | 'footnote';
  number: string;
}
export interface AcademicNavigation {
  links: Map<string, AcademicLink[]>;
  targets: Set<string>;
}
export const navigationElementId = (prefix: string, key: string) =>
  `${prefix}-${encodeURIComponent(key)}`;
export const contentSlotKey = (blockId: string, item?: number) =>
  JSON.stringify([blockId, item ?? null]);

interface Slot {
  key: string;
  block: ScholarlyBlock;
  text: string;
  runs?: InlineRun[];
  bibliography: boolean;
  item?: number;
}
const plainRun = (run: InlineRun) =>
  run.kind === 'text' && !run.style?.fontFamily && !run.style?.verticalAlign;
const proseBlock = (block: ScholarlyBlock) =>
  ['paragraph', 'list', 'reference', 'footnote'].includes(block.type) &&
  block.role !== 'algorithm' &&
  block.role !== 'equation';
const referenceHeading = /^\s*(?:\d+\.?\s+)?(?:references|bibliography|参考文献)\s*$/i;
const referenceStart = /^\s*\[([1-9]\d*)\]\s+(?=\S)/;
const listReferenceStart = /^\s*(?:\[([1-9]\d*)\]|([1-9]\d*)[.)])\s+(?=\S)/;

function slotsFor(document: ScholarlyDocument): Slot[] {
  let bibliography = false;
  return document.blocks.flatMap((block) => {
    if (block.type === 'heading') bibliography = referenceHeading.test(block.text);
    if (!proseBlock(block)) return [];
    const make = (text: string, runs?: InlineRun[], item?: number): Slot => ({
      key: contentSlotKey(block.id, item),
      block,
      item,
      runs,
      text: runs?.length ? runs.map((run) => run.text).join('') : text,
      bibliography: bibliography || block.type === 'reference',
    });
    return block.type === 'list'
      ? (block.listItems ?? [block.text]).map((text, item) =>
          make(text, block.listInlineRuns?.[item], item),
        )
      : [make(block.text, block.inlineRuns)];
  });
}

function plainRange(slot: Slot, start: number, end: number): boolean {
  let offset = 0;
  for (const run of slot.runs ?? []) {
    const next = offset + run.text.length;
    if (next > start && offset < end && !plainRun(run)) return false;
    offset = next;
  }
  return true;
}

/** Column identity is taken from the marker itself, since paragraphs can span columns. */
function markerLocation(document: ScholarlyDocument, source: SourceSpan): string | undefined {
  const columns = document.pages.find((page) => page.page === source.page)?.columns;
  if (!columns?.length || !source.boxes.length || !source.itemIndices.length) return;
  const matches = source.boxes.map((box) => {
    const center = box.x + box.width / 2;
    return columns.flatMap((column, index) =>
      center >= column.box.x && center <= column.box.x + column.box.width ? [index] : [],
    );
  });
  const column = matches[0]?.[0];
  if (column === undefined || matches.some((match) => match.length !== 1 || match[0] !== column))
    return;
  return `${source.page}:${column}`;
}

/** Derived only; never edits cached blocks, runs, source ownership or reading order. */
export function buildAcademicNavigation(document: ScholarlyDocument): AcademicNavigation {
  const slots = slotsFor(document);
  const navigation: AcademicNavigation = { links: new Map(), targets: new Set() };
  const references = new Map<string, Slot[]>();
  const add = (
    slot: Slot,
    start: number,
    end: number,
    target: Slot,
    kind: AcademicLink['kind'],
    number: string,
  ) => {
    const link = { id: `${slot.key}:${start}`, start, end, target: target.key, kind, number };
    navigation.links.set(slot.key, [...(navigation.links.get(slot.key) ?? []), link]);
    navigation.targets.add(target.key);
  };
  for (const slot of slots) {
    if (!slot.bibliography) continue;
    const match = (slot.item === undefined ? referenceStart : listReferenceStart).exec(slot.text);
    if (!match || !plainRange(slot, 0, match[0].length)) continue;
    const number = (match[1] ?? match[2])!;
    references.set(number, [...(references.get(number) ?? []), slot]);
  }
  for (const slot of slots) {
    for (const match of slot.text.matchAll(/\[([1-9]\d*)\]/g)) {
      const start = match.index;
      const end = start + match[0].length;
      const targets = references.get(match[1]!);
      if (targets?.length !== 1 || targets[0] === slot || !plainRange(slot, start, end)) continue;
      // Avoid array subscripts, nested brackets and mathematical/indexing expressions.
      if (
        /[\p{L}\p{N}_\[\]\\]/u.test(slot.text[start - 1] ?? '') ||
        /[\p{L}\p{N}_\[\]]/u.test(slot.text[end] ?? '') ||
        /[=+*/<>^_∑∫√≤≥]\s*$/.test(slot.text.slice(0, start)) ||
        /^\s*[=+*/<>^_∑∫√≤≥]/.test(slot.text.slice(end)) ||
        /[\p{L}\p{N}_]\(\s*$/u.test(slot.text.slice(0, start)) ||
        /\]\s*[-–—]\s*$/.test(slot.text.slice(0, start)) ||
        /^\s*[-–—]\s*\[/.test(slot.text.slice(end))
      )
        continue;
      add(slot, start, end, targets[0]!, 'reference', match[1]!);
    }
  }

  type Marker = { slot: Slot; start: number; end: number; number: string; eligible: boolean };
  const callers = new Map<string, Marker[]>();
  const notes = new Map<string, Marker[]>();
  for (const slot of slots) {
    if (!slot.runs || slot.bibliography) continue;
    let offset = 0;
    for (const [index, run] of slot.runs.entries()) {
      const start = offset;
      offset += run.text.length;
      if (run.kind !== 'text' || run.style?.verticalAlign !== 'super' || run.style.fontFamily)
        continue;
      const match = /^\s*([1-9]\d*)\s*$/.exec(run.text);
      if (!match) continue;
      const location = markerLocation(document, run.source);
      if (!location) continue;
      const number = match[1]!;
      const markerStart = start + run.text.indexOf(number);
      const before = slot.text.slice(0, start);
      const after = slot.text.slice(offset);
      const isNote = slot.block.type === 'footnote' && !before.trim();
      if (slot.block.type === 'footnote' && !isNote) continue;
      const previous = slot.runs
        .slice(0, index)
        .reverse()
        .find((entry) => entry.text.trim());
      const context = before.slice(-100);
      const contextIsPlain = plainRange(slot, Math.max(0, start - 100), start);
      const eligible = isNote
        ? /^\s*\p{L}{2}/u.test(after)
        : contextIsPlain &&
          !!previous &&
          plainRun(previous) &&
          /[.!?。！？][”’"')\]]?\s*$/.test(before) &&
          (context.match(/\p{L}{2,}/gu)?.length ?? 0) >= 2 &&
          !/[=+*/<>^_∑∫√≤≥]/.test(context) &&
          (!after.trim() || /^\s*\p{L}/u.test(after));
      const group = isNote ? notes : callers;
      const key = `${location}:${number}`;
      group.set(key, [
        ...(group.get(key) ?? []),
        { slot, start: markerStart, end: markerStart + number.length, number, eligible },
      ]);
    }
  }
  for (const [key, markers] of callers) {
    const targets = notes.get(key);
    if (markers.length !== 1 || targets?.length !== 1) continue;
    const caller = markers[0]!,
      target = targets[0]!;
    if (caller.eligible && target.eligible)
      add(caller.slot, caller.start, caller.end, target.slot, 'footnote', caller.number);
  }
  for (const links of navigation.links.values()) links.sort((a, b) => a.start - b.start);
  return navigation;
}
