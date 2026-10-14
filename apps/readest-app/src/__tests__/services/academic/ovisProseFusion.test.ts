import { describe, expect, it } from 'vitest';
import { previewNativeProseFusion } from '@/services/academic/ovisProseFusion';
import type { OvisBundle } from '@/services/academic/ovis';
import type { ScholarlyDocument, ScholarlyBlock } from '@/services/academic/types';

const prose =
  'The experiment examines ordinary network behavior across several independent runs using a carefully controlled workload. Every measurement follows the same procedure and records the observed result without changing the original sample. These repeated observations provide a useful basis for comparing the behavior of different systems under similar operating conditions.';
const second =
  'Another investigation considers how individual machines respond when the surrounding environment changes during operation. The study collects detailed observations over an extended interval and compares the recorded behavior against a stable baseline. This approach helps distinguish temporary fluctuations from persistent patterns while preserving the evidence required for later independent review.';
const hash = 'a'.repeat(64);
function fixture(texts = [prose]) {
  const blocks: ScholarlyBlock[] = texts.map((text, i) => {
    const source = {
      page: 1,
      boxes: [{ x: 20, y: 30 + i * 100, width: 200, height: 60 }],
      itemIndices: [i],
    };
    return {
      id: `native-${i}`,
      type: 'paragraph',
      text,
      source: [source],
      order: i,
      confidence: 0.88,
      fontStats: { median: 10, min: 10, max: 10, names: ['body'] },
      inlineRuns: [{ kind: 'text', text, source }],
    };
  });
  const native: ScholarlyDocument = {
    schemaVersion: 1,
    parserVersion: 'synthetic',
    fingerprint: hash,
    pageCount: 1,
    metadata: { pdfjsVersion: 'synthetic' },
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
        tagged: false,
        items: blocks.map((b, i) => ({
          index: i,
          text: b.text,
          box: b.source[0]!.boxes[0]!,
          baseline: 40 + i * 100,
          fontSize: 10,
          fontName: 'body',
          fontFamily: 'serif',
          angle: 0,
          hasEOL: true,
        })),
        graphics: [],
        lines: [],
        columns: [
          { box: { x: 10, y: 0, width: 220, height: 800 }, confidence: 0.9 },
          { box: { x: 300, y: 0, width: 220, height: 800 }, confidence: 0.9 },
        ],
        visualRegions: [],
        blockIds: blocks.map((b) => b.id),
        suppressedItemIndices: [],
      },
    ],
  };
  const bundle: OvisBundle = {
    format: 'readest-ovis-reflow',
    version: 1,
    pdfSha256: hash,
    pageCount: 1,
    identity: {
      modelSha256: hash,
      projectorSha256: hash,
      promptSha256: hash,
      runtimeRevision: 'b'.repeat(40),
      configuration: {},
    },
    pages: [
      {
        page: 1,
        width: 600,
        height: 800,
        blocks: texts.map((markdown, i) => ({ id: `ovis-${i}`, kind: 'markdown', markdown })),
      },
    ],
  };
  return { native, bundle };
}
const ovisText = (bundle: OvisBundle, text: string, index = 0) => {
  bundle.pages[0]!.blocks[index] = { id: `ovis-${index}`, kind: 'markdown', markdown: text };
};

describe('experimental native prose fusion', () => {
  it('repairs one interior lowercase OCR substitution and records both sources without mutation', () => {
    const { bundle, native } = fixture();
    ovisText(bundle, prose.replace('controlled', 'controiled'));
    const original = JSON.stringify({ bundle, native });
    const result = previewNativeProseFusion(bundle, native);
    expect(result.decisions[0]).toMatchObject({
      action: 'native',
      nativeBlockId: 'native-0',
      original: prose.replace('controlled', 'controiled'),
      replacement: prose,
    });
    expect(result.pages[0]!.blocks[0]).toMatchObject({ markdown: prose });
    expect(result.decisions[0]!.source).toEqual(native.blocks[0]!.source);
    expect(JSON.stringify({ bundle, native })).toBe(original);
  });
  it('fails closed on a different PDF or page geometry', () => {
    const { bundle, native } = fixture();
    native.fingerprint = 'c'.repeat(64);
    expect(() => previewNativeProseFusion(bundle, native)).toThrow(/same PDF/);
    native.fingerprint = hash;
    native.pages[0]!.width += 10;
    expect(() => previewNativeProseFusion(bundle, native)).toThrow(/geometry/);
  });
  it.each([
    ' $x^2$',
    ' \\(x\\)',
    ' <table><tr><td>data</td></tr></table>',
    ' [3](#note)',
    ' x²',
    ' α',
    ' `code`',
  ])('keeps complex Markdown unchanged: %s', (suffix) => {
    const { bundle, native } = fixture();
    ovisText(bundle, prose + suffix);
    const result = previewNativeProseFusion(bundle, native);
    expect(result.decisions[0]!.action).toBe('ovis');
    expect(result.decisions[0]!.reason).toBe('complex-or-short-content');
    expect(result.pages).toEqual(bundle.pages);
  });
  it.each([
    'symbol-font',
    'source-run',
    'superscript',
    'no-runs',
    'low-confidence',
    'cross-column',
    'missing-glyph',
    'inconsistent-runs',
  ])('rejects unsafe native evidence: %s', (variant) => {
    const { bundle, native } = fixture();
    if (variant === 'symbol-font') native.pages[0]!.items[0]!.fontMath = true;
    if (variant === 'source-run')
      native.blocks[0]!.inlineRuns = [
        {
          kind: 'source',
          text: prose,
          source: native.blocks[0]!.source[0]!,
          fontSize: 10,
          baseline: 20,
        },
      ];
    if (variant === 'superscript')
      native.blocks[0]!.inlineRuns![0] = {
        kind: 'text',
        text: prose,
        source: native.blocks[0]!.source[0]!,
        style: { verticalAlign: 'super' },
      };
    if (variant === 'no-runs') native.blocks[0]!.inlineRuns = undefined;
    if (variant === 'low-confidence') native.blocks[0]!.confidence = 0.4;
    if (variant === 'cross-column')
      native.blocks[0]!.source[0]!.boxes.push({ x: 310, y: 60, width: 200, height: 50 });
    if (variant === 'missing-glyph') native.pages[0]!.items = [];
    if (variant === 'inconsistent-runs') native.blocks[0]!.inlineRuns![0]!.text += ' extra';
    expect(previewNativeProseFusion(bundle, native).decisions[0]!.action).toBe('ovis');
  });
  it('rejects duplicated native or Ovis paragraphs instead of choosing the first', () => {
    const { bundle, native } = fixture([prose, prose]);
    expect(
      previewNativeProseFusion(bundle, native).decisions.every((d) => d.action === 'ovis'),
    ).toBe(true);
    native.blocks.pop();
    native.readingOrder.pop();
    expect(
      previewNativeProseFusion(bundle, native).decisions.every((d) => d.action === 'ovis'),
    ).toBe(true);
  });
  it('counts ambiguous Ovis matches when checking reverse uniqueness', () => {
    const { bundle, native } = fixture([prose, prose.replace('controlled', 'controiled')]);
    ovisText(bundle, prose.replace('original', 'originai'), 0);
    ovisText(bundle, prose, 1);
    expect(
      previewNativeProseFusion(bundle, native).decisions.every((d) => d.action === 'ovis'),
    ).toBe(true);
  });
  it.each([
    'billion',
    'miilion',
  ])('never changes a written quantity from %s to million', (quantity) => {
    const text = prose.replace(
      'controlled workload.',
      'controlled workload of one million measurements.',
    );
    const { bundle, native } = fixture([text]);
    ovisText(bundle, text.replace('million', quantity));
    expect(previewNativeProseFusion(bundle, native).decisions[0]!.action).toBe('ovis');
  });
  it('rejects reversed paragraph order and a match on another page', () => {
    const { bundle, native } = fixture([prose, second]);
    native.readingOrder.reverse();
    expect(
      previewNativeProseFusion(bundle, native).decisions.every((d) => d.action === 'ovis'),
    ).toBe(true);
    native.readingOrder.reverse();
    native.blocks[0]!.source[0]!.page = 2;
    expect(previewNativeProseFusion(bundle, native).decisions[0]!.action).toBe('ovis');
  });
  it.each([
    [' 128 GPUs [18].', ' 129 GPUs [18].'],
    [' cites results [18].', ' cites results [19].'],
    [' uses Acme systems.', ' uses Axme systems.'],
    [' supports re-entry.', ' supports reentry.'],
    [' should not fail.', ' should now fail.'],
  ])('never fixes protected numbers, names, hyphens or short words', (ending, changed) => {
    const text = prose.replace('These repeated', ending + ' These repeated');
    const { bundle, native } = fixture([text]);
    ovisText(bundle, text.replace(ending, changed));
    expect(previewNativeProseFusion(bundle, native).decisions[0]!.action).toBe('ovis');
  });
  it.each(['\n\n', '  \n', '\n    '])('preserves Markdown structure marked by %j', (separator) => {
    const { bundle, native } = fixture();
    ovisText(bundle, prose.replace('Every measurement', separator + 'Every measurement'));
    expect(previewNativeProseFusion(bundle, native).decisions[0]!.action).toBe('ovis');
  });
  it.each([' \t', '   \t'])('rejects space-prefixed tab indentation %j', (prefix) => {
    const { bundle, native } = fixture();
    ovisText(bundle, prefix + prose);
    expect(previewNativeProseFusion(bundle, native).decisions[0]!.action).toBe('ovis');
  });
  it('preserves CR-only paragraph boundaries', () => {
    const { bundle, native } = fixture();
    ovisText(bundle, prose.replace('Every', '\r\rEvery'));
    expect(previewNativeProseFusion(bundle, native).decisions[0]!.action).toBe('ovis');
  });
  it('preserves a written ordinal even when its OCR error resembles i/l', () => {
    const text = prose.replace(
      'controlled workload.',
      'controlled workload from the fifteenth experiment.',
    );
    const { bundle, native } = fixture([text]);
    ovisText(bundle, text.replace('fifteenth', 'flfteenth'));
    expect(previewNativeProseFusion(bundle, native).decisions[0]!.action).toBe('ovis');
  });
  it('permits whitespace and common ligature normalization without collapsing superscripts', () => {
    const { bundle, native } = fixture();
    ovisText(bundle, prose.replace('different', 'diﬀerent').replace('Every', '\nEvery'));
    expect(previewNativeProseFusion(bundle, native).decisions[0]!.action).toBe('native');
  });
  it('preserves visual and footnote blocks exactly', () => {
    const { bundle, native } = fixture();
    bundle.pages[0]!.blocks.push(
      {
        id: 'visual',
        kind: 'visual',
        role: 'equation',
        box: { x: 20, y: 400, width: 100, height: 30 },
      },
      { id: 'note', kind: 'footnote', marker: '1', markdown: prose },
    );
    expect(previewNativeProseFusion(bundle, native).pages[0]!.blocks.slice(1)).toEqual(
      bundle.pages[0]!.blocks.slice(1),
    );
  });
});
