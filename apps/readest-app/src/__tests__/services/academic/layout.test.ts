import { describe, expect, it } from 'vitest';
import {
  analyzeDocument,
  analyzeDocumentAsync,
  clusterLines,
  joinLines,
  validateSourceCoverage,
} from '@/services/academic/layout';
import type { PageGeometry, PdfTextItem } from '@/services/academic/types';

const item = (
  index: number,
  text: string,
  x: number,
  y: number,
  width = 220,
  fontSize = 10,
): PdfTextItem => ({
  index,
  text,
  box: { x, y, width, height: fontSize },
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
const doc = (pages: PageGeometry[]) => analyzeDocument(pages, 'a'.repeat(64), '6.2.108');

describe('deterministic academic layout', () => {
  it('clusters words and superscripts while separating column gutters', () => {
    const p = page([
      item(0, 'The', 40, 100, 15),
      item(1, 'result', 58, 100, 25),
      item(2, '2', 84, 97, 3, 6),
      item(3, 'right column', 330, 100, 120),
    ]);
    const lines = clusterLines(p);
    expect(lines).toHaveLength(2);
    expect(lines[0]?.itemIndices).toEqual([0, 1, 2]);
    expect(lines[1]?.itemIndices).toEqual([3]);
  });
  it('reads title then left column then right, without interleaving equal rows', () => {
    const p = page([
      item(0, 'A full width title', 80, 60, 450, 18),
      ...Array.from({ length: 6 }, (_, i) => item(i + 1, `Left sentence ${i}.`, 40, 130 + i * 14)),
      ...Array.from({ length: 6 }, (_, i) =>
        item(i + 7, `Right sentence ${i}.`, 330, 130 + i * 14),
      ),
    ]);
    const d = doc([p]);
    expect(d.pages[0]?.columns).toHaveLength(2);
    expect(d.blocks[0]?.text).toBe('A full width title');
    const text = d.blocks.map((b) => b.text).join(' ');
    expect(text.indexOf('Left sentence 5')).toBeLessThan(text.indexOf('Right sentence 0'));
    expect(validateSourceCoverage(d)).toEqual([]);
    expect(doc([p])).toEqual(d);
  });
  it('preserves a ruled algorithm with every numbered line in one crop', () => {
    const p = page([
      item(0, 'Algorithm 1: Local procedure', 330, 201, 220),
      ...Array.from({ length: 27 }, (_, i) =>
        item(i + 1, `${i + 1}: operation(x)`, 334, 240 + i * 10, 210),
      ),
      item(28, 'Prose following the algorithm.', 330, 540),
    ]);
    p.graphics = [200, 230, 520].map((y) => ({
      kind: 'rule',
      box: { x: 330, y, width: 225, height: 0.5 },
    }));
    const d = doc([p]);
    const algorithm = d.blocks.find((b) => b.role === 'algorithm');
    expect(algorithm?.source[0]?.itemIndices).toHaveLength(28);
    expect(algorithm?.source[0]?.boxes[0]?.y).toBeLessThanOrEqual(200);
    expect(algorithm?.source[0]?.boxes[0]?.height ?? 0).toBeGreaterThanOrEqual(320);
    expect(d.blocks.some((b) => b.text === 'Prose following the algorithm.')).toBe(true);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('groups eight vector panels and shared caption before two-column prose', () => {
    const p = page([
      item(0, 'Figure 9: Eight panels', 115, 258, 380),
      ...Array.from({ length: 8 }, (_, i) =>
        item(i + 1, `(${i})`, 56 + (i % 4) * 126, 155 + Math.floor(i / 4) * 80, 45),
      ),
      ...Array.from({ length: 6 }, (_, i) => item(i + 9, `Left text ${i}.`, 40, 300 + i * 14)),
      ...Array.from({ length: 6 }, (_, i) => item(i + 15, `Right text ${i}.`, 330, 300 + i * 14)),
    ]);
    p.graphics = Array.from({ length: 8 }, (_, i) => ({
      kind: 'form',
      box: { x: 56 + (i % 4) * 126, y: 84 + Math.floor(i / 4) * 80, width: 120, height: 68 },
    }));
    const d = doc([p]);
    expect(d.blocks[0]?.role).toBe('figure');
    expect(d.blocks[0]?.source[0]?.itemIndices).toHaveLength(9);
    expect(d.blocks[0]?.source[0]?.boxes[0]?.width).toBeGreaterThan(490);
    expect(d.pages[0]?.columns).toHaveLength(2);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('suppresses repeated headers and page numbers, preserving source coverage', () => {
    const pages = [1, 2, 3].map((n) =>
      page(
        [
          item(0, 'Journal of examples 2026', 40, 30),
          item(1, `Body on page ${n}.`, 40, 140),
          item(2, `${n}`, 290, 765, 10),
          item(3, ' ', 40, 160, 10),
        ],
        n,
      ),
    );
    const d = doc(pages);
    expect(
      d.pages.every(
        (p) =>
          p.suppressedItemIndices.includes(0) &&
          p.suppressedItemIndices.includes(2) &&
          p.suppressedItemIndices.includes(3),
      ),
    ).toBe(true);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('joins only conservative line-end hyphens and soft hyphens', () => {
    expect(joinLines(['An inter-', 'connection works.'])).toBe('An interconnection works.');
    expect(joinLines(['The end-to-', 'end system.'])).toBe('The end-to-end system.');
    expect(joinLines(['Use GPU-', 'Based design.'])).toBe('Use GPU-Based design.');
    expect(joinLines(['A soft\u00ad', 'hyphen.'])).toBe('A softhyphen.');
  });
  it('classifies headings, lists, references and footnotes without dropping raw items', () => {
    const p = page([
      item(0, '1 Introduction', 40, 100, 300, 16),
      item(1, 'An ordinary paragraph.', 40, 130, 420),
      item(2, '• First point', 40, 170, 420),
      item(3, '• Second point', 40, 190, 420),
      item(4, 'References', 40, 240, 200, 15),
      item(5, '[1] Example Author. A title.', 40, 270, 420),
      item(6, '1 A brief note.', 40, 710, 420, 7),
    ]);
    p.graphics = [{ kind: 'rule', box: { x: 40, y: 700, width: 100, height: 0.5 } }];
    const d = doc([p]);
    expect(d.blocks.map((b) => b.type)).toEqual(
      expect.arrayContaining(['heading', 'paragraph', 'list', 'reference', 'footnote']),
    );
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it.each([8, 16])('keeps a %i-prefixed body continuation in its paragraph', (count) => {
    // HPCC page 3 PDF.js geometry: narrow glyph boxes leave a 6.861 pt gap,
    // despite an ordinary 10.959 pt baseline advance. Labels are synthetic.
    const body = [
      'The evaluation includes several machines and',
      `${count} Edge nodes joined by fast links. We deliberately choose`,
      'representative traffic for the remaining measurements.',
    ].map((text, index) => ({
      ...item(index, text, 317.955, 600.987288 + index * 10.959, 240.249128832, 8.9664),
      box: {
        x: 317.955,
        y: 600.987288 + index * 10.959,
        width: 240.249128832,
        height: 4.0976448,
      },
      baseline: 605.067 + index * 10.959,
      fontName: 'g_d0_f6',
      fontFamily: 'sans-serif',
    }));
    const p = page(body, 3);
    p.width = 612;
    p.height = 792;
    const d = doc([p]);
    expect(d.blocks).toHaveLength(1);
    expect(d.blocks[0]?.type).toBe('paragraph');
    expect(d.blocks[0]?.text).toBe(body.map((i) => i.text).join(' '));
    expect(d.blocks[0]?.source[0]?.itemIndices).toEqual([0, 1, 2]);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('requires font evidence for numbered headings and retains opaque same-size heading styles', () => {
    const p = page([
      item(0, 'An ordinary body paragraph provides the dominant font.', 40, 100, 420),
      item(1, '2 Section title', 40, 150, 120, 10.8),
      item(2, 'More ordinary body prose supplies a reliable font sample.', 40, 180, 420),
      item(3, '2.1', 40, 220, 14),
      { ...item(4, 'Opaque styled title', 60, 220, 150), fontName: 'g_d0_f5' },
      item(5, 'A body-sized numbered sentence stays ordinary even when isolated.', 40, 250, 420),
      item(6, '8 More machines appear in the experiment.', 40, 290, 280),
      { ...item(7, '16', 40, 330, 12), fontName: 'g_d0_f5' },
      item(8, 'Workers appear with only their count emphasized.', 56, 330, 300),
    ]);
    const d = doc([p]);
    expect(d.blocks.filter((b) => b.type === 'heading').map((b) => [b.text, b.level])).toEqual([
      ['2 Section title', 2],
      ['2.1 Opaque styled title', 3],
    ]);
    expect(d.blocks.find((b) => b.text.startsWith('8 More'))?.type).toBe('paragraph');
    expect(d.blocks.find((b) => b.text.startsWith('16 Workers'))?.type).toBe('paragraph');
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('retains distinctly styled numbered run-in headings before same-baseline body text', () => {
    const p = page([
      item(0, 'Ordinary body prose establishes the document typeface.', 40, 100, 420),
      { ...item(1, '3.2.1', 40, 140, 22), fontName: 'g_d4_f21' },
      { ...item(2, 'Device behavior.', 72, 140, 85), fontName: 'g_d4_f21' },
      item(3, 'The rest of this line is ordinary paragraph prose.', 161, 140, 250),
      item(4, 'More body text continues on a later baseline.', 40, 154, 420),
    ]);
    const d = doc([p]);
    expect(d.blocks[1]?.type).toBe('heading');
    expect(d.blocks[1]?.level).toBe(3);
    expect(d.blocks[1]?.text).toBe(
      '3.2.1 Device behavior. The rest of this line is ordinary paragraph prose.',
    );
    expect(d.blocks[1]?.source[0]?.itemIndices).toEqual([1, 2, 3]);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('retains display math as a visual region', () => {
    const p = page([
      item(0, 'A prose introduction.', 40, 120, 480),
      item(1, 'x = ∑ a² / b', 180, 170, 130),
      item(2, '(1)', 520, 170, 20),
      item(3, 'More ordinary prose.', 40, 220, 480),
    ]);
    const d = doc([p]);
    expect(d.blocks.some((b) => b.role === 'equation')).toBe(true);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('falls back conservatively for rotated body and textless scans', () => {
    const p = page([item(0, 'Rotated body text', 40, 150, 200)]);
    p.items[0]!.angle = Math.PI / 2;
    const d = doc([p, page([], 2)]);
    expect(d.blocks.every((b) => b.type === 'visual-region')).toBe(true);
    expect(d.pages[1]?.unsupportedReason).toMatch(/extractable/i);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('merges only compatible unfinished cross-page paragraphs and retains both spans', () => {
    const p1 = page([
      item(0, 'This unfinished paragraph continues', 40, 680, 480),
      item(1, 'across the', 40, 694, 480),
    ]);
    const p2 = page([item(0, 'next page before ending.', 40, 100, 480)], 2);
    const d = doc([p1, p2]);
    expect(d.blocks).toHaveLength(1);
    expect(d.blocks[0]?.source).toHaveLength(2);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('keeps simultaneous equations in separate columns and does not label years as headings', () => {
    const p = page([
      ...Array.from({ length: 4 }, (_, i) => item(i, `Left sentence ${i}.`, 40, 120 + i * 14)),
      ...Array.from({ length: 4 }, (_, i) =>
        item(i + 4, `Right sentence ${i}.`, 330, 120 + i * 14),
      ),
      item(8, 'x = a + b', 100, 220, 100),
      item(9, '(1)', 265, 220, 20),
      item(10, 'y = c + d', 380, 220, 100),
      item(11, '(2)', 555, 220, 20),
      item(12, '2019 Conference proceedings are here.', 40, 280),
      item(13, '60 Senders are used for the experiment.', 330, 280),
    ]);
    const d = doc([p]);
    const equations = d.blocks.filter((b) => b.role === 'equation');
    expect(equations).toHaveLength(2);
    expect(equations.every((b) => b.source[0]!.boxes[0]!.width < 300)).toBe(true);
    expect(d.blocks.find((b) => b.text.startsWith('2019'))?.type).toBe('paragraph');
    expect(d.blocks.find((b) => b.text.startsWith('60'))?.type).toBe('paragraph');
  });
  it('keeps wrapped list items together and carries the reference section across pages', () => {
    const p1 = page([
      item(0, '• A long first item', 40, 120, 420),
      item(1, 'continues on this line.', 52, 134, 408),
      item(2, '• Second item.', 40, 154, 420),
      item(3, 'References', 40, 600, 200, 15),
      item(4, '[1] A source title', 40, 630, 420),
    ]);
    const p2 = page(
      [
        item(0, 'and the rest of its citation.', 40, 100, 420),
        item(1, '[2] The next reference.', 40, 140, 420),
      ],
      2,
    );
    const d = doc([p1, p2]);
    expect(d.blocks.find((b) => b.type === 'list')?.listItems).toEqual([
      '• A long first item continues on this line.',
      '• Second item.',
    ]);
    expect(d.blocks.find((b) => b.text.startsWith('and the rest'))?.type).toBe('reference');
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('uses a complete-page visual fallback for three-column ambiguity', () => {
    const p = page(
      [40, 230, 420].flatMap((x, c) =>
        Array.from({ length: 6 }, (_, i) =>
          item(c * 6 + i, `Column ${c} sentence.`, x, 120 + i * 14, 140),
        ),
      ),
    );
    const d = doc([p]);
    expect(d.blocks).toHaveLength(1);
    expect(d.blocks[0]?.type).toBe('visual-region');
    expect(d.blocks[0]?.fallbackReason).toMatch(/three or more/i);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('yields on long documents and stops at the next page after cancellation', async () => {
    const pages = Array.from({ length: 120 }, (_, n) =>
      page(
        Array.from({ length: 20 }, (_, i) =>
          item(i, 'A simple sentence for a long document.', 40, 120 + i * 14, 480),
        ),
        n + 1,
      ),
    );
    const controller = new AbortController();
    const progress: number[] = [];
    let timerRan = false;
    setTimeout(() => {
      timerRan = true;
    }, 0);
    await expect(
      analyzeDocumentAsync(pages, 'a'.repeat(64), '6.2.108', controller.signal, (completed) => {
        progress.push(completed);
        if (completed === 2) controller.abort();
      }),
    ).rejects.toMatchObject({ name: 'AbortError' });
    expect(timerRan).toBe(true);
    expect(progress).toEqual([1, 2]);
  });
  it('preserves an unnumbered fraction and Greek-only display expression', () => {
    const p = page([
      item(0, 'Ordinary surrounding prose.', 40, 120, 480),
      item(1, 'a + b', 220, 170, 70),
      item(2, 'c + d', 220, 188, 70),
      item(3, 'α² + β²', 200, 240, 120),
      item(4, 'More surrounding prose.', 40, 290, 480),
    ]);
    p.graphics = [{ kind: 'rule', box: { x: 216, y: 184, width: 78, height: 0.4 } }];
    const d = doc([p]);
    expect(d.blocks.filter((b) => b.role === 'equation')).toHaveLength(2);
    expect(d.blocks.some((b) => b.type === 'paragraph' && b.text.includes('a + b'))).toBe(false);
    expect(validateSourceCoverage(d)).toEqual([]);
  });
  it('cancels the yielding analysis path', async () => {
    const controller = new AbortController();
    controller.abort();
    await expect(
      analyzeDocumentAsync([page([])], 'a'.repeat(64), '6.2.108', controller.signal),
    ).rejects.toMatchObject({ name: 'AbortError' });
  });
});
