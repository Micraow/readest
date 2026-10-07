import { describe, expect, it } from 'vitest';
import { analyzeDocument, validateSourceCoverage } from '@/services/academic/layout';
import type { PageGeometry, PdfTextItem } from '@/services/academic/types';

const item = (index: number, text: string, x: number, y: number, fontSize = 10): PdfTextItem => ({
  index,
  text,
  box: { x, y, width: 220, height: fontSize },
  baseline: y + fontSize * 0.8,
  fontSize,
  fontName: 'body',
  fontFamily: 'serif',
  angle: 0,
  hasEOL: true,
});
const page = (items: PdfTextItem[], pageNumber = 1): PageGeometry => ({
  page: pageNumber,
  width: 600,
  height: 800,
  rotation: 0,
  items,
  graphics: [],
  tagged: false,
});
const analyze = (pages: PageGeometry[]) => analyzeDocument(pages, 'a'.repeat(64), '6.2.108');
const rightColumn = () => [
  item(100, 'software transport, the design uses dedicated hardware.', 330, 120),
  ...Array.from({ length: 20 }, (_, i) =>
    item(i + 101, `An independent right-column observation ${i}.`, 330, 145 + i * 18),
  ),
];

describe('academic footnote reading flow', () => {
  it('recognizes a superscript note marker without whitespace or a separating rule', () => {
    const marker = item(3, '5', 40, 710, 6);
    marker.box.width = 3;
    const p = page(
      [
        item(0, 'An earlier complete observation.', 40, 120),
        item(1, 'Another earlier complete observation.', 40, 145),
        item(2, 'Compared with conventional', 40, 690),
        marker,
        item(4, 'Alternatively, the implementation can track more state.', 43, 712, 8),
        item(5, 'This is a separate explanatory note.', 40, 722, 8),
        ...rightColumn(),
      ],
      4,
    );
    const d = analyze([p]);
    expect(d.blocks.find((b) => b.text.startsWith('Compared'))?.text).toBe(
      'Compared with conventional software transport, the design uses dedicated hardware.',
    );
    const note = d.blocks.find((b) => b.type === 'footnote');
    expect(note?.text).toContain('5Alternatively,');
    expect(note?.source[0]?.itemIndices).toEqual([3, 4, 5]);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('completes a cross-column paragraph before a ruled note and retains every note line', () => {
    const noteItems = Array.from({ length: 14 }, (_, i) =>
      item(
        i + 20,
        i ? `A further detail in the explanatory note ${i}.` : '1 A supporting note.',
        40,
        625 + i * 9,
        8,
      ),
    );
    const p = page([
      item(0, 'A complete earlier paragraph.', 40, 120),
      item(1, 'Another complete earlier paragraph.', 40, 145),
      item(2, 'Compared with conventional', 40, 600),
      ...noteItems,
      ...rightColumn(),
    ]);
    p.graphics = [{ kind: 'rule', box: { x: 40, y: 618, width: 90, height: 0.5 } }];
    const d = analyze([p]);
    const body = d.blocks.find((block) => block.text.startsWith('Compared'))!;
    expect(body.text).toBe(
      'Compared with conventional software transport, the design uses dedicated hardware.',
    );
    const note = d.blocks.find((block) => block.type === 'footnote')!;
    expect(note.text).toContain('explanatory note 13.');
    expect(note.source[0]?.itemIndices).toEqual(noteItems.map((line) => line.index));
    expect(d.blocks.indexOf(note)).toBe(d.blocks.indexOf(body) + 1);
    expect(body.source[0]?.itemIndices).toEqual([2, 100]);
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it.each([
    [10, 8],
    [11, 9],
  ])('recognizes first-page publication notes with body/note sizes %i/%i', (bodySize, noteSize) => {
    const right = rightColumn();
    right[0] = item(
      100,
      'software transport, the design uses dedicated hardware.',
      330,
      120,
      bodySize,
    );
    const p = page([
      item(0, 'An ordinary introduction.', 40, 120),
      item(1, 'Another complete paragraph.', 40, 145),
      item(2, 'Compared with conventional', 40, 464, bodySize),
      item(3, 'Manuscript received January 1, 2020; revised later.', 40, 488, noteSize),
      item(4, 'Accepted after review. This work received support.', 40, 498, noteSize),
      item(5, 'A. Author is with the Example Research Institute.', 40, 508, noteSize),
      item(6, 'The corresponding author can provide further details.', 40, 518, noteSize),
      ...right,
    ]);
    const d = analyze([p]);
    const body = d.blocks.find((block) => block.text.startsWith('Compared'))!;
    expect(body.text).toBe(
      'Compared with conventional software transport, the design uses dedicated hardware.',
    );
    const note = d.blocks.find((block) => block.type === 'footnote')!;
    expect(note.text).toContain('A. Author is with');
    expect(note.source[0]?.itemIndices).toEqual([3, 4, 5, 6]);
    expect(d.blocks.indexOf(note)).toBe(d.blocks.indexOf(body) + 1);
    expect(body.source[0]?.itemIndices).toEqual([2, 100]);
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it.each([
    '• A real intervening list item.',
    'A real intervening body paragraph.',
  ])('does not cross an intervening body or list barrier: %s', (barrier) => {
    const p = page([
      item(0, 'An ordinary introduction.', 40, 120),
      item(1, 'Compared with conventional', 40, 600),
      item(2, '1 A brief supporting note.', 40, 625, 8),
      item(3, barrier, 40, 690),
      ...rightColumn(),
    ]);
    p.graphics = [{ kind: 'rule', box: { x: 40, y: 618, width: 90, height: 0.5 } }];
    const d = analyze([p]);
    expect(d.blocks.find((block) => block.text.startsWith('Compared'))?.text).toBe(
      'Compared with conventional',
    );
    expect(d.blocks.some((block) => block.text === barrier)).toBe(true);
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('does not use a footnote alone as evidence to join paragraphs within one column', () => {
    const p = page([
      item(0, 'An ordinary introduction.', 40, 120),
      item(1, 'Compared with conventional', 40, 600),
      item(2, '1 A brief supporting note.', 40, 625, 8),
      item(3, 'software transport is discussed in a separate paragraph.', 40, 690),
    ]);
    p.graphics = [{ kind: 'rule', box: { x: 40, y: 618, width: 90, height: 0.5 } }];
    const d = analyze([p]);
    expect(d.blocks.find((block) => block.text.startsWith('Compared'))?.text).toBe(
      'Compared with conventional',
    );
    expect(d.blocks).toHaveLength(4);
    expect(validateSourceCoverage(d)).toEqual([]);
  });

  it('limits publication-note recognition to first-page, contiguous small print', () => {
    const first = page([
      item(0, 'Ordinary body text.', 40, 120),
      item(1, 'Another ordinary body paragraph.', 40, 145),
      item(2, 'Manuscript received January 1, 2020.', 40, 488, 8),
      item(3, 'Small text after a substantial gap is unrelated.', 40, 555, 8),
      item(4, 'Normal-size body text resumes.', 40, 570),
      item(5, 'A. A small ordinary list item.', 40, 585, 8),
      ...rightColumn(),
    ]);
    const second = page(
      [
        item(0, 'Manuscript received is quoted in this discussion.', 40, 488, 8),
        item(1, 'Ordinary body text defines the type size.', 40, 120),
        item(2, 'Another ordinary paragraph.', 40, 145),
      ],
      2,
    );
    const d = analyze([first, second]);
    const notes = d.blocks.filter((block) => block.type === 'footnote');
    expect(notes).toHaveLength(1);
    expect(notes[0]?.source[0]?.itemIndices).toEqual([2]);
    expect(d.blocks.find((block) => block.text.startsWith('A. A small'))?.type).toBe('list');
    expect(validateSourceCoverage(d)).toEqual([]);
  });
});
