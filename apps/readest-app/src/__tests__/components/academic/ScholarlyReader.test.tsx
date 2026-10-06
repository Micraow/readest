import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ScholarlyReader from '@/components/academic/ScholarlyReader';
import type { AcademicPdfSession } from '@/services/academic/runtime';
import type { ScholarlyBlock, ScholarlyDocument } from '@/services/academic/types';

vi.mock('@/hooks/useTranslation', () => ({ useTranslation: () => (key: string) => key }));
vi.mock('@/store/settingsStore', () => ({
  useSettingsStore: (select: (state: unknown) => unknown) =>
    select({ settings: { globalViewSettings: { defaultFontSize: 18, lineHeight: 1.6 } } }),
}));

const block = (id: string, page: number, type: ScholarlyBlock['type']): ScholarlyBlock => ({
  id,
  type,
  text: `Text from page ${page}`,
  source: [{ page, boxes: [{ x: 10, y: 20, width: 200, height: 100 }], itemIndices: [0] }],
  order: page - 1,
  confidence: 1,
  fontStats: { median: 12, min: 12, max: 12, names: [] },
  ...(type === 'visual-region' ? { role: 'figure' as const } : {}),
});
const documentFor = (blocks: ScholarlyBlock[]): ScholarlyDocument => ({
  schemaVersion: 1,
  parserVersion: 'test',
  fingerprint: 'continuous-paper',
  pageCount: 3,
  metadata: { pdfjsVersion: 'test' },
  pages: [],
  blocks,
  readingOrder: blocks.map((entry) => entry.id),
  sourceMap: Object.fromEntries(blocks.map((entry) => [entry.id, entry.source])),
  warnings: [],
});

let intersect: (visible: boolean) => void;
let resize: () => void;
let width = 360;
const disconnect = vi.fn();
const renderRegion = vi.fn<AcademicPdfSession['renderRegion']>();
const session: AcademicPdfSession = {
  renderRegion,
  renderPage: vi.fn(),
  analyze: vi.fn(),
  destroy: vi.fn(),
};
beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
  width = 360;
  vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockImplementation(() => width);
  vi.stubGlobal(
    'IntersectionObserver',
    class {
      constructor(callback: (entries: Array<{ isIntersecting: boolean }>) => void) {
        intersect = (visible) => callback([{ isIntersecting: visible }]);
      }
      observe() {}
      disconnect = disconnect;
    },
  );
  vi.stubGlobal(
    'ResizeObserver',
    class {
      constructor(callback: () => void) {
        resize = callback;
      }
      observe() {}
      disconnect = disconnect;
    },
  );
  renderRegion.mockImplementation(async (_page, _box, canvas, targetWidth) => {
    canvas.width = targetWidth * 2;
    canvas.height = targetWidth;
  });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe('continuous academic flow', () => {
  it('places paragraphs from different source pages in one article without page wrappers', () => {
    render(
      <ScholarlyReader
        document={documentFor([block('first', 1, 'paragraph'), block('second', 2, 'paragraph')])}
        session={session}
        onZoom={vi.fn()}
      />,
    );
    const first = screen.getByText('Text from page 1');
    const second = screen.getByText('Text from page 2');
    expect(first.parentElement?.tagName).toBe('ARTICLE');
    expect(second.parentElement).toBe(first.parentElement);
    expect(first.nextElementSibling).toBe(second);
    expect(first.dataset['sourcePage']).toBe('1');
    expect(second.dataset['sourcePage']).toBe('2');
    expect(screen.queryByText(/^Page \d+$/)).toBeNull();
    expect(renderRegion).not.toHaveBeenCalled();
  });

  it('renders only near the viewport and frees canvases on exit, resize and unmount', async () => {
    const visual = block('visual', 2, 'visual-region');
    const onZoom = vi.fn();
    const result = render(
      <ScholarlyReader document={documentFor([visual])} session={session} onZoom={onZoom} />,
    );
    expect(renderRegion).not.toHaveBeenCalled();
    await act(async () => intersect(true));
    const canvas = screen.getByRole('img') as HTMLCanvasElement;
    expect(renderRegion).toHaveBeenCalledTimes(1);
    expect(renderRegion.mock.calls[0]?.slice(0, 4)).toEqual([
      2,
      visual.source[0]!.boxes[0],
      canvas,
      360,
    ]);
    expect(canvas.width).toBe(720);
    const firstSignal = renderRegion.mock.calls[0]![4]!;
    await act(async () => intersect(false));
    expect(firstSignal.aborted).toBe(true);
    expect(canvas.width).toBe(0);
    expect(canvas.height).toBe(0);
    await act(async () => intersect(true));
    expect(renderRegion).toHaveBeenCalledTimes(2);
    width = 540;
    await act(async () => resize());
    expect(renderRegion.mock.calls[1]![4]!.aborted).toBe(true);
    expect(renderRegion.mock.calls[2]![3]).toBe(540);
    fireEvent.click(screen.getByRole('button', { name: 'figure: Tap to zoom' }));
    expect(onZoom).toHaveBeenCalledWith(visual);
    result.unmount();
    expect(renderRegion.mock.calls[2]![4]!.aborted).toBe(true);
    expect(canvas.width).toBe(0);
    expect(disconnect).toHaveBeenCalledTimes(2);
  });

  it('ignores a cancelled preview rejection after a fresh render succeeds', async () => {
    let reject!: (error: Error) => void;
    renderRegion.mockImplementationOnce(
      () =>
        new Promise((_resolve, fail) => {
          reject = fail;
        }),
    );
    render(
      <ScholarlyReader
        document={documentFor([block('visual', 2, 'visual-region')])}
        session={session}
        onZoom={vi.fn()}
      />,
    );
    await act(async () => intersect(true));
    await act(async () => intersect(false));
    await act(async () => intersect(true));
    await act(async () => reject(new Error('Cancelled old preview')));
    expect(screen.queryByText(/Preview unavailable/)).toBeNull();
  });

  it('restores scroll locally and flushes the latest position when Reading closes', () => {
    vi.useFakeTimers();
    const key = 'readest:academic-position:continuous-paper';
    localStorage.setItem(key, '420');
    const document = documentFor([block('first', 1, 'paragraph')]);
    const result = render(
      <ScholarlyReader document={document} session={session} onZoom={vi.fn()} />,
    );
    const scroller = screen.getByTestId('scholarly-scroll');
    expect(scroller.scrollTop).toBe(420);
    scroller.scrollTop = 725;
    fireEvent.scroll(scroller);
    result.unmount();
    expect(localStorage.getItem(key)).toBe('725');
    render(<ScholarlyReader document={document} session={session} onZoom={vi.fn()} />);
    expect(screen.getByTestId('scholarly-scroll').scrollTop).toBe(725);
    expect(localStorage.length).toBe(1);
  });

  it('preserves the first number when a numbered list continues after a visual region', () => {
    const list = { ...block('list', 2, 'list'), listItems: ['3. Third step', '4. Fourth step'] };
    render(<ScholarlyReader document={documentFor([list])} session={session} onZoom={vi.fn()} />);
    const ordered = screen.getByRole('list') as HTMLOListElement;
    expect(ordered.start).toBe(3);
    expect(screen.getAllByRole('listitem').map((item) => item.textContent)).toEqual([
      'Third step',
      'Fourth step',
    ]);
  });
});
