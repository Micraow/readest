import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ScholarlyReader from '@/components/academic/ScholarlyReader';
import { captureReadingAnchor } from '@/components/academic/readingAnchor';
import { fingerprintFile, type AcademicStorage } from '@/services/academic/cache';
import { importOvisBundle, readOvisCache, type OvisBundle } from '@/services/academic/ovis';
import type { AcademicPdfSession } from '@/services/academic/runtime';
import type { ScholarlyBlock, ScholarlyDocument } from '@/services/academic/types';
import { mockReadingLayout } from './position-test-layout';

vi.mock('@/hooks/useTranslation', () => ({ useTranslation: () => (key: string) => key }));
vi.mock('@/store/settingsStore', () => ({
  useSettingsStore: (select: (state: unknown) => unknown) =>
    select({ settings: { globalViewSettings: { defaultFontSize: 18, lineHeight: 1.6 } } }),
}));
vi.mock('@/store/themeStore', () => ({ useThemeStore: () => false }));

const session: AcademicPdfSession = {
  renderRegion: vi.fn(async () => {}),
  renderPage: vi.fn(),
  analyze: vi.fn(),
  destroy: vi.fn(),
};
const block = (
  id: string,
  page: number,
  type: ScholarlyBlock['type'],
  markdown?: string,
): ScholarlyBlock => ({
  id,
  type,
  markdown,
  text: markdown ?? 'Native text.',
  source: [{ page, boxes: [], itemIndices: [] }],
  order: 0,
  confidence: 0,
  fontStats: { median: 12, min: 12, max: 12, names: [] },
  ...(type === 'footnote' ? { footnoteMarker: '1' } : {}),
});
const documentFor = (blocks: ScholarlyBlock[]): ScholarlyDocument => ({
  schemaVersion: 1,
  parserVersion: 'synthetic-ovis',
  fingerprint: 'synthetic-footnote-flow',
  pageCount: 2,
  metadata: { pdfjsVersion: '', ovis: { identity: 'synthetic', coveredPages: [1, 2] } },
  pages: [],
  blocks,
  readingOrder: blocks.map((entry) => entry.id),
  sourceMap: Object.fromEntries(blocks.map((entry) => [entry.id, entry.source])),
  warnings: [],
});
const blockIds = (root: Element) =>
  Array.from(
    root.querySelectorAll<HTMLElement>('[data-block-id]'),
    (node) => node.dataset['blockId'],
  );

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      disconnect() {}
    },
  );
  vi.stubGlobal(
    'IntersectionObserver',
    class {
      observe() {}
      disconnect() {}
    },
  );
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('linked Ovis footnotes in continuous reading', () => {
  it('keeps two-page prose together and preserves complete notes, repeated markers, links and cache', async () => {
    const pdf = new Blob(['synthetic two-page PDF']);
    const bundle: OvisBundle = {
      format: 'readest-ovis-reflow',
      version: 1,
      pdfSha256: await fingerprintFile(pdf),
      pageCount: 2,
      identity: {
        modelSha256: 'a'.repeat(64),
        projectorSha256: 'b'.repeat(64),
        promptSha256: 'c'.repeat(64),
        runtimeRevision: 'd'.repeat(40),
        configuration: { fixture: 'synthetic linked footnotes' },
      },
      pages: [
        {
          page: 1,
          width: 600,
          height: 800,
          blocks: [
            {
              id: 'body-one',
              kind: 'markdown',
              markdown: 'The first half [1](#first-note) continues',
            },
            {
              id: 'first-note',
              kind: 'footnote',
              marker: '1',
              markdown:
                'A complete note with $x^2$.\n\n| Key | Value |\n| --- | --- |\n| a | 2 |\n\n[Return](#body-one)',
            },
          ],
        },
        {
          page: 2,
          width: 600,
          height: 800,
          blocks: [
            {
              id: 'body-two',
              kind: 'markdown',
              markdown: 'on the next source page [1](#second-note).',
            },
            {
              id: 'second-note',
              kind: 'footnote',
              marker: '1',
              markdown: 'A distinct note. [Return](#body-two)',
            },
          ],
        },
      ],
    };
    const files = new Map<string, string>();
    const storage: AcademicStorage = {
      exists: vi.fn(async (path) => files.has(path)),
      readFile: vi.fn(async (path) => files.get(path)!),
      writeFile: vi.fn(async (path, _base, content) => {
        files.set(path, String(content));
      }),
      createDir: vi.fn(async () => {}),
    };
    const originalBundle = structuredClone(bundle);
    const document = await importOvisBundle(pdf, bundle, storage);
    const before = structuredClone(document);
    const cachedFiles = [...files.entries()];
    const writes = vi.mocked(storage.writeFile).mock.calls.length;
    const view = render(<ScholarlyReader document={document} session={session} onZoom={vi.fn()} />);
    const article = view.container.querySelector('article')!;
    expect(blockIds(article)).toEqual(['body-one', 'body-two', 'first-note', 'second-note']);
    expect(
      Array.from(article.querySelectorAll('*')).some((element) =>
        element.getAttributeNames().some((name) => name.startsWith('data-readest-markdown-link')),
      ),
    ).toBe(false);
    const notes = screen.getByRole('region', { name: 'Notes' });
    expect(blockIds(notes)).toEqual(['first-note', 'second-note']);
    expect(within(notes).getAllByRole('note')).toHaveLength(2);
    expect(notes.querySelectorAll('sup')).toHaveLength(2);
    expect(notes.querySelector('.katex')).not.toBeNull();
    expect(within(notes).getByRole('table').textContent).toContain('Value');
    const first = within(notes).getAllByRole('note')[0]!;
    expect(first.getAttribute('id')).toBe('first-note');
    expect(first.getAttribute('data-source-page')).toBe('1');
    const scroll = vi.fn();
    Object.defineProperty(first, 'scrollIntoView', { configurable: true, value: scroll });
    fireEvent.click(article.querySelector('[href="#first-note"]')!);
    expect(scroll).toHaveBeenCalledWith({ block: 'start' });
    expect(window.document.activeElement).toBe(first);
    const origin = article.querySelector<HTMLElement>('[data-block-id="body-one"]')!;
    const returnScroll = vi.fn();
    Object.defineProperty(origin, 'scrollIntoView', { configurable: true, value: returnScroll });
    fireEvent.click(within(first).getByRole('link', { name: 'Return' }));
    expect(returnScroll).toHaveBeenCalledWith({ block: 'start' });
    expect(window.document.activeElement).toBe(origin);
    expect(document).toEqual(before);
    expect(bundle).toEqual(originalBundle);
    expect([...files.entries()]).toEqual(cachedFiles);
    expect(storage.writeFile).toHaveBeenCalledTimes(writes);
    expect(await readOvisCache(pdf, storage)).toEqual(before);
  });

  it('leaves unlinked notes in place and never inserts an empty Notes section', () => {
    const document = documentFor([
      block('body-one', 1, 'paragraph', '`[1](#unlinked)` and $[1](#unlinked)$.'),
      block('unlinked', 1, 'footnote', 'Still between the source paragraphs.'),
      block('body-two', 2, 'paragraph', 'Continuation.'),
    ]);
    const view = render(<ScholarlyReader document={document} session={session} onZoom={vi.fn()} />);
    expect(blockIds(view.container)).toEqual(document.readingOrder);
    expect(screen.queryByRole('region', { name: 'Notes' })).toBeNull();
    expect(screen.queryByRole('heading', { name: 'Notes' })).toBeNull();
  });

  it('does not regroup source visuals that were separated by a collected note', () => {
    const figures = [0, 1].map((index) => {
      const figure = block(`figure-${index}`, 1, 'visual-region', 'Caption [1](#note).');
      figure.role = 'figure';
      figure.previewBox = { x: index * 150, y: 20, width: 140, height: 60 };
      figure.source[0]!.boxes = [figure.previewBox];
      figure.captions = [
        {
          role: 'figure',
          label: String(index),
          text: 'Synthetic caption.',
          source: {
            page: 1,
            boxes: [{ x: index * 150, y: 85, width: 140, height: 20 }],
            itemIndices: [],
          },
        },
      ];
      return figure;
    });
    const document = documentFor([
      figures[0]!,
      block('note', 1, 'footnote', 'Caption-linked note.'),
      figures[1]!,
    ]);
    const view = render(<ScholarlyReader document={document} session={session} onZoom={vi.fn()} />);
    expect(blockIds(view.container)).toEqual(['figure-0', 'figure-1', 'note']);
    expect(view.container.querySelectorAll('figure')).toHaveLength(2);
    expect(view.container.querySelector('article .grid')).toBeNull();
    expect(within(screen.getByRole('region', { name: 'Notes' })).getByRole('note')).toBeDefined();
  });

  it('keeps the Notes label outside block text and preserves note character anchors on font changes', () => {
    const document = documentFor([
      block('body', 1, 'paragraph', 'Read [1](#note).'),
      block('note', 1, 'footnote', 'A longer synthetic note for the preserved character anchor.'),
    ]);
    const view = render(<ScholarlyReader document={document} session={session} onZoom={vi.fn()} />);
    const heading = screen.getByRole('heading', { name: 'Notes' });
    expect(heading.closest('[data-block-id]')).toBeNull();
    const note = screen.getByRole('note');
    expect(note.textContent).toBe(`1${document.blocks[1]!.markdown}\n`);
    const scroller = screen.getByTestId('scholarly-scroll');
    let height = 20;
    mockReadingLayout(scroller, note, () => height);
    scroller.scrollTop = 40;
    expect(captureReadingAnchor(scroller)).toMatchObject({ blockId: 'note', textOffset: 20 });
    height = 30;
    view.rerender(
      <ScholarlyReader
        document={document}
        session={session}
        onZoom={vi.fn()}
        viewSettings={{ defaultFontSize: 24 }}
      />,
    );
    scroller.scrollTop = 60;
    expect(captureReadingAnchor(scroller)).toMatchObject({ blockId: 'note', textOffset: 20 });
    expect(screen.getByRole('note').textContent).toBe(note.textContent);
  });

  it('keeps native author and affiliation footnotes in their original flow', () => {
    const document = documentFor([
      block('authors', 1, 'paragraph', 'Authors [*](#author-note).'),
      block('author-note', 1, 'footnote', 'Author details.'),
      block('affiliation', 1, 'footnote', 'Institution details.'),
      block('body', 2, 'paragraph', 'Body.'),
    ]);
    delete document.metadata.ovis;
    const view = render(<ScholarlyReader document={document} session={session} onZoom={vi.fn()} />);
    expect(blockIds(view.container)).toEqual(document.readingOrder);
    expect(screen.queryByRole('region', { name: 'Notes' })).toBeNull();
  });
});
