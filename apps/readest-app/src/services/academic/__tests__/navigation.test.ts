import { describe, expect, it } from 'vitest';
import { buildAcademicNavigation, contentSlotKey } from '../navigation';
import type { InlineRun, ScholarlyBlock, ScholarlyDocument, SourceSpan } from '../types';

const source = (page = 1, x = 20): SourceSpan => ({
  page,
  boxes: [{ x, y: 40, width: 10, height: 8 }],
  itemIndices: [1],
});
const run = (
  text: string,
  style?: Extract<InlineRun, { kind: 'text' }>['style'],
  x = 20,
): InlineRun => ({
  kind: 'text',
  text,
  source: source(1, x),
  style,
});
const block = (
  id: string,
  type: ScholarlyBlock['type'],
  text: string,
  inlineRuns?: InlineRun[],
): ScholarlyBlock => ({
  id,
  type,
  text,
  inlineRuns,
  source: [source()],
  order: 0,
  confidence: 1,
  fontStats: { median: 12, min: 12, max: 12, names: [] },
});
const documentFor = (blocks: ScholarlyBlock[]): ScholarlyDocument => ({
  schemaVersion: 1,
  parserVersion: 'academic-12',
  fingerprint: 'synthetic',
  pageCount: 1,
  metadata: { pdfjsVersion: 'test' },
  blocks,
  readingOrder: blocks.map((b) => b.id),
  sourceMap: Object.fromEntries(blocks.map((b) => [b.id, b.source])),
  warnings: [],
  pages: [
    {
      page: 1,
      width: 600,
      height: 800,
      rotation: 0,
      items: [],
      graphics: [],
      tagged: false,
      lines: [],
      columns: [0, 300].map((x) => ({ box: { x, y: 0, width: 250, height: 800 }, confidence: 1 })),
      visualRegions: [],
      blockIds: blocks.map((b) => b.id),
      suppressedItemIndices: [],
    },
  ],
});
const links = (document: ScholarlyDocument, id = 'body', item?: number) =>
  buildAcademicNavigation(document).links.get(contentSlotKey(id, item)) ?? [];
const reference = () => block('reference', 'reference', '[34] A. Author, A study.');
const bodyNote = (id = 'body', x = 20) =>
  block(id, 'paragraph', 'The packets were acknowledged. 5 More prose.', [
    run('The packets were acknowledged. '),
    run('5 ', { verticalAlign: 'super' }, x),
    run('More prose.'),
  ]);
const note = (id = 'note', x = 20) =>
  block(id, 'footnote', '5Alternatively, an explanation.', [
    run('5', { verticalAlign: 'super' }, x),
    run('Alternatively, an explanation.'),
  ]);

describe('local academic navigation', () => {
  it('links an exact citation to the unique numbered start without merging its continuation or changing data', () => {
    const doc = documentFor([
      block('body', 'paragraph', 'Mark at the switch [34].'),
      reference(),
      block('continuation', 'reference', 'The journal and publication date.'),
    ]);
    const before = JSON.stringify(doc);
    expect(links(doc)).toEqual([
      expect.objectContaining({
        start: 19,
        end: 23,
        target: contentSlotKey('reference'),
        kind: 'reference',
      }),
    ]);
    expect(buildAcademicNavigation(doc).targets.has(contentSlotKey('continuation'))).toBe(false);
    expect(JSON.stringify(doc)).toBe(before);
  });
  it('uses UTF-16 content-slot offsets across bold and italic runs', () => {
    const doc = documentFor([
      block('body', 'paragraph', 'ignored fallback', [
        run('📖 See ['),
        run('3', { fontWeight: 'bold' }),
        run('4', { fontStyle: 'italic' }),
        run('].'),
      ]),
      reference(),
    ]);
    expect(links(doc)[0]).toMatchObject({ start: 7, end: 11 });
  });
  it('leaves missing or duplicate bibliography numbers unlinked', () => {
    expect(
      links(
        documentFor([
          block('body', 'paragraph', 'See [34] and [35].'),
          reference(),
          block('duplicate', 'reference', '[34] Another author.'),
        ]),
      ),
    ).toEqual([]);
  });
  it('only indexes reference blocks or precise starts inside a named reference section', () => {
    const body = block('body', 'paragraph', 'See [34].');
    expect(
      links(
        documentFor([body, block('random', 'paragraph', '[34] An unrelated numbered paragraph.')]),
      ),
    ).toEqual([]);
    const doc = documentFor([
      body,
      block('heading', 'heading', 'References'),
      { ...block('list', 'list', ''), listItems: ['33. First author.', '34. Second author.'] },
      block('appendix', 'heading', 'Appendix'),
      block('other', 'paragraph', '[34] Not a reference.'),
    ]);
    expect(links(doc)[0]?.target).toBe(contentSlotKey('list', 1));
  });
  it('skips code, scripts, source crops, algorithm/equation blocks, ranges and array-like notation', () => {
    const sourceRun: InlineRun = {
      kind: 'source',
      text: '[34]',
      source: source(),
      fontSize: 12,
      baseline: 50,
    };
    const cases = [
      block('body', 'paragraph', '', [run('[34]', { fontFamily: 'monospace' })]),
      block('body', 'paragraph', '', [run('[34]', { verticalAlign: 'super' })]),
      block('body', 'paragraph', '', [run('See '), sourceRun]),
      { ...block('body', 'paragraph', 'See [34].'), role: 'algorithm' as const },
      { ...block('body', 'visual-region', '[34]'), role: 'equation' as const },
      block('body', 'paragraph', 'a[34] = x; [33–34], [34,35], [[34]]'),
      block('body', 'paragraph', 'x = [34]'),
      block('body', 'paragraph', '[34] + x'),
      block('body', 'paragraph', 'f([34])'),
      block('body', 'paragraph', 'See [34]–[35].'),
    ];
    for (const body of cases) expect(links(documentFor([body, reference()]))).toEqual([]);
  });
  it('keeps separate offsets for each list item', () => {
    const doc = documentFor([
      { ...block('body', 'list', ''), listItems: ['1. See [34].', '2. Compare [34].'] },
      reference(),
    ]);
    expect(links(doc, 'body', 0)[0]?.start).toBe(7);
    expect(links(doc, 'body', 1)[0]?.start).toBe(11);
    expect(links(doc)).toEqual([]);
  });
  it('pairs a unique punctuation-adjacent superscript note using the marker source column', () => {
    const body = bodyNote();
    body.source[0]!.boxes.push({ x: 320, y: 50, width: 200, height: 10 });
    const doc = documentFor([body, note()]);
    const before = JSON.stringify(doc);
    expect(links(doc)[0]).toMatchObject({
      kind: 'footnote',
      start: 31,
      end: 32,
      target: contentSlotKey('note'),
    });
    expect(JSON.stringify(doc)).toBe(before);
  });
  it('rejects exponents, repeated markers, duplicate notes, mismatched columns and missing geometry', () => {
    const exponent = block('body', 'paragraph', 'The value x5 is large.', [
      run('The value x'),
      run('5', { verticalAlign: 'super' }),
      run(' is large.'),
    ]);
    expect(links(documentFor([exponent, note()]))).toEqual([]);
    expect(links(documentFor([bodyNote(), bodyNote('repeat'), note()]))).toEqual([]);
    expect(links(documentFor([bodyNote(), note(), note('duplicate')]))).toEqual([]);
    expect(links(documentFor([bodyNote(), note('note', 320)]))).toEqual([]);
    const noGeometry = documentFor([bodyNote(), note()]);
    noGeometry.pages = [];
    expect(links(noGeometry)).toEqual([]);
    const math = bodyNote();
    math.inlineRuns![0] = run('x = y. ');
    expect(links(documentFor([math, note()]))).toEqual([]);
    const croppedMath = bodyNote();
    croppedMath.inlineRuns = [
      run('The value '),
      { kind: 'source', text: 'x', source: source(), fontSize: 12, baseline: 50 },
      run('. '),
      run('5', { verticalAlign: 'super' }),
    ];
    expect(links(documentFor([croppedMath, note()]))).toEqual([]);
  });
});
