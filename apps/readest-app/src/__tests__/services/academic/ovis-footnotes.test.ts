import { describe, expect, it } from 'vitest';
import { linkedOvisFootnoteIds } from '@/services/academic/ovisFootnotes';
import { ovisMarkdownFragmentTargets } from '@/services/academic/ovisMarkdown';
import type { ScholarlyBlock, ScholarlyDocument } from '@/services/academic/types';

const block = (id: string, type: ScholarlyBlock['type'], markdown?: string): ScholarlyBlock => ({
  id,
  type,
  text: markdown ?? '',
  markdown,
  source: [{ page: 1, boxes: [], itemIndices: [] }],
  order: 0,
  confidence: 0,
  fontStats: { median: 12, min: 12, max: 12, names: [] },
  ...(type === 'footnote' ? { footnoteMarker: '1' } : {}),
});
const documentFor = (blocks: ScholarlyBlock[]): ScholarlyDocument => ({
  schemaVersion: 1,
  parserVersion: 'synthetic-ovis',
  fingerprint: 'synthetic-footnotes',
  pageCount: 2,
  metadata: { pdfjsVersion: '', ovis: { identity: 'synthetic', coveredPages: [1, 2] } },
  pages: [],
  blocks,
  readingOrder: blocks.map((entry) => entry.id),
  sourceMap: Object.fromEntries(blocks.map((entry) => [entry.id, entry.source])),
  warnings: [],
});

describe('Ovis Markdown fragment targets', () => {
  it('reads explicit links in nested prose, lists, tables and reference-link definitions', () => {
    expect(
      ovisMarkdownFragmentTargets(
        '**See [a](#first).**\n\n- [b](#note%20two)\n\n| Note |\n| --- |\n| [c][last] |\n\n[last]: #third',
      ),
    ).toEqual(['first', 'note two', 'third']);
  });

  it.each([
    '`[1](#note)`',
    '```md\n[1](#note)\n```',
    '    [1](#note)',
    '$[1](#note)$',
    '$$[1](#note)$$',
    String.raw`\([1](#note)\)`,
    String.raw`\[[1](#note)\]`,
    '<code>[1](#note)</code>',
    '<pre>[1](#note)</pre>',
    '<a href="#note">1</a>',
    '<table><tr><td>[1](#note)</td></tr></table>',
    '![1](#note)',
    '![image with [1](#note)](image.png)',
    '[1](https://example.invalid/#note)',
    '[1](paper.pdf#note)',
    '[1](#)',
    '[1](#broken%zz)',
    '[1]',
  ])('ignores non-Markdown or nonlocal link syntax: %s', (markdown) => {
    expect(ovisMarkdownFragmentTargets(markdown)).toEqual([]);
  });

  it('keeps real links adjacent to complete math and raw code', () => {
    expect(
      ovisMarkdownFragmentTargets(
        String.raw`\([hidden](#math)\) [a](#first) <code>[hidden](#code)</code> [b](#second)`,
      ),
    ).toEqual(['first', 'second']);
  });

  it('uses rendered href entities and decodes percent escapes exactly once', () => {
    expect(
      ovisMarkdownFragmentTargets(
        '[a](&#35;note) [b](#note&amp;x) [c](#note%2520two) [d](%23note) [e](#a&percnt;20b)',
      ),
    ).toEqual(['note', 'note&x', 'note%20two', 'a b']);
  });

  it.each([
    'svg',
    'math',
    'select',
    'audio',
    'video',
  ])('requires the Markdown anchor to survive sanitation inside %s', (tag) => {
    expect(ovisMarkdownFragmentTargets(`<${tag}>[go](#note)</${tag}>`)).toEqual([]);
  });

  it('does not use a raw HTML anchor to replace a stripped Markdown entry point', () => {
    expect(
      ovisMarkdownFragmentTargets(
        '<svg>[go](#note)</svg><a href="#note" data-readest-markdown-link data-readest-markdown-link-1>Raw link</a>',
      ),
    ).toEqual([]);
  });

  it.each([
    'DATA-READEST-MARKDOWN-LINK DATA-READEST-MARKDOWN-LINK-1',
    '&#100;ata-readest-markdown-link',
    'data-readest-markdown-lin&#107;',
  ])('does not accept a raw anchor with a spoofed provenance attribute: %s', (attributes) => {
    expect(
      ovisMarkdownFragmentTargets(
        `<svg>[go](#note)</svg><a href="#note" ${attributes}>Raw link</a>`,
      ),
    ).toEqual([]);
  });

  it.each([
    '<span class="katex"><math><mtext>[go](#note)</mtext><semantics><annotation encoding="application/x-tex">x</annotation></semantics></math></span>',
    '<span class="katex"><math><semantics><annotation encoding="application/x-tex">x</annotation></semantics></math>[go](#note)</span>',
    '<span class="katex-display"><span class="katex"><math display="block"><semantics><annotation encoding="application/x-tex">x</annotation></semantics></math></span>[go](#note)</span>',
  ])('ignores a Markdown anchor removed by the existing trusted math replacement: %s', (markdown) => {
    expect(ovisMarkdownFragmentTargets(markdown)).toEqual([]);
  });

  it.each([
    '<span class="katex"><math><mtext>[go](#note)</mtext></math></span>',
    '<span class="katex-display"><span class="katex"><math><semantics><annotation encoding="application/x-tex">x</annotation></semantics></math></span>[go](#note)</span>',
  ])('retains a Markdown anchor outside the actual math replacement root: %s', (markdown) => {
    expect(ovisMarkdownFragmentTargets(markdown)).toEqual(['note']);
  });
});

describe('linked Ovis footnotes', () => {
  it('uses unique block IDs, preserves repeated markers and does not mutate the source', () => {
    const first = block('page-one-note', 'footnote', 'First complete note.');
    const second = block('page-two-note', 'footnote', 'Second complete note.');
    const document = documentFor([
      block('body-one', 'paragraph', '[1](#page-two-note) and [1](#page-one-note).'),
      first,
      block('body-two', 'paragraph', 'Continued prose.'),
      second,
    ]);
    const before = structuredClone(document);
    expect([...linkedOvisFootnoteIds(document)]).toEqual(['page-one-note', 'page-two-note']);
    expect(document).toEqual(before);
    expect(document.blocks[1]).toBe(first);
    expect(document.blocks[3]).toBe(second);
  });

  it('counts visual Markdown captions as entry points, without interpreting native caption text', () => {
    const caption = block('figure', 'visual-region', 'Caption [1](#caption-note).');
    caption.captions = [
      { role: 'figure', label: '1', text: '[1](#native-caption-note)', source: caption.source[0]! },
    ];
    const document = documentFor([
      caption,
      block('caption-note', 'footnote', 'Linked by a rendered caption.'),
      block('native-caption-note', 'footnote', 'Not a Markdown caption.'),
    ]);
    expect([...linkedOvisFootnoteIds(document)]).toEqual(['caption-note']);
  });

  it('leaves unreferenced, footnote-only, native, ambiguous and untyped notes in place', () => {
    const document = documentFor([
      block('body', 'paragraph', '[1](#duplicate) [2](#native) [3](#untyped).'),
      block('duplicate', 'footnote', 'Ambiguous note.'),
      block('duplicate', 'paragraph', 'Another block has the same ID.'),
      block('native', 'footnote'),
      block('untyped', 'paragraph', 'Not typed as a footnote.'),
      block('unreferenced', 'footnote', 'No entry point.'),
      block('footnote-only', 'footnote', 'Only another note links here.'),
      block('other-note', 'footnote', '[1](#footnote-only) [2](#other-note).'),
    ]);
    expect([...linkedOvisFootnoteIds(document)]).toEqual([]);
  });

  it('does not collect any native document footnotes, including author and affiliation notes', () => {
    const document = documentFor([
      block('authors', 'paragraph', 'Author [*](#author-note) [1](#affiliation).'),
      block('author-note', 'footnote', 'Corresponding author.'),
      block('affiliation', 'footnote', 'Example institution.'),
    ]);
    delete document.metadata.ovis;
    expect([...linkedOvisFootnoteIds(document)]).toEqual([]);
  });

  it.each([
    'id',
    'data-block-id',
  ])('keeps a note with a competing raw HTML %s target in place', (attribute) => {
    const document = documentFor([
      block('body', 'paragraph', `<span ${attribute}="note">Other target.</span> [1](#note)`),
      block('note', 'footnote', 'This ID is ambiguous in the reader.'),
    ]);
    expect([...linkedOvisFootnoteIds(document)]).toEqual([]);
  });
});
