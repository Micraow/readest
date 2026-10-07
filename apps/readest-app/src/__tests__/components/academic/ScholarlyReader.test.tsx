import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ScholarlyReader from '@/components/academic/ScholarlyReader';
import type { AcademicPdfSession } from '@/services/academic/runtime';
import type { ScholarlyBlock, ScholarlyDocument } from '@/services/academic/types';
import { useThemeStore } from '@/store/themeStore';

vi.mock('@/hooks/useTranslation', () => ({ useTranslation: () => (key: string) => key }));
vi.mock('@/store/themeStore', async () => {
  const { create } = await import('zustand');
  return { useThemeStore: create(() => ({ isDarkMode: false })) };
});
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
  useThemeStore.setState({ isDarkMode: false });
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
afterEach(async () => {
  cleanup();
  vi.useRealTimers();
  await waitFor(() => expect(window.history.state?.readestAcademicLayers).toBeUndefined());
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe('continuous academic flow', () => {
  it('themes equations live while leaving figures, source geometry and zoom unchanged', async () => {
    vi.stubGlobal('IntersectionObserver', undefined);
    const equation = { ...block('equation', 1, 'visual-region'), role: 'equation' as const };
    const figure = block('figure', 2, 'visual-region');
    const scholarly = documentFor([equation, figure]);
    const before = JSON.stringify(scholarly);
    const onZoom = vi.fn();
    render(<ScholarlyReader document={scholarly} session={session} onZoom={onZoom} />);
    await waitFor(() => expect(renderRegion).toHaveBeenCalledTimes(2));
    const formula = screen.getByRole('img', { name: 'Equation: Tap to zoom' });
    const artwork = screen.getByRole('img', { name: 'Figure: Tap to zoom' });
    const originalArtwork = artwork.outerHTML;
    expect(formula.style.mixBlendMode).toBe('multiply');
    expect(formula.closest('button')?.classList.contains('bg-white')).toBe(false);
    expect(artwork.closest('button')?.classList.contains('bg-white')).toBe(true);
    act(() => useThemeStore.setState({ isDarkMode: true }));
    expect(formula.style.filter).toBe('invert(100%) hue-rotate(180deg)');
    expect(formula.style.mixBlendMode).toBe('screen');
    expect(artwork.outerHTML).toBe(originalArtwork);
    expect(artwork.style.filter).toBe('');
    expect(artwork.style.mixBlendMode).toBe('');
    expect(renderRegion).toHaveBeenCalledTimes(2);
    expect(session.analyze).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Equation: Tap to zoom' }));
    expect(onZoom).toHaveBeenLastCalledWith(equation);
    fireEvent.click(screen.getByRole('button', { name: 'Figure: Tap to zoom' }));
    expect(onZoom).toHaveBeenLastCalledWith(figure);
    act(() => useThemeStore.setState({ isDarkMode: false }));
    expect(formula.style.filter).toBe('');
    expect(formula.style.mixBlendMode).toBe('multiply');
    expect(artwork.outerHTML).toBe(originalArtwork);
    expect(renderRegion).toHaveBeenCalledTimes(2);
    expect(JSON.stringify(scholarly)).toBe(before);
  });

  it('returns to the clicked text and focus after font changes, with a bounded nested jump history', async () => {
    const body = { ...block('body', 1, 'paragraph'), text: 'See [34].' };
    const first = { ...block('first-ref', 2, 'reference'), text: '[34] First study. See [35].' };
    const second = { ...block('second-ref', 3, 'reference'), text: '[35] Second study.' };
    const doc = documentFor([body, first, second]);
    const view = render(<ScholarlyReader document={doc} session={session} onZoom={vi.fn()} />);
    const scroller = screen.getByTestId('scholarly-scroll');
    const rect = (top: number) => ({
      top,
      bottom: top + 20,
      left: 0,
      right: 100,
      width: 100,
      height: 20,
      x: 0,
      y: top,
      toJSON() {},
    });
    const rootTop = () => (screen.queryByRole('button', { name: 'Back to reading' }) ? 140 : 100);
    vi.spyOn(scroller, 'getBoundingClientRect').mockImplementation(() => rect(rootTop()));
    const origin = screen.getAllByRole('link')[0]!;
    const nested = screen.getAllByRole('link')[1]!;
    const y = () => parseFloat(view.container.querySelector('article')!.style.fontSize);
    vi.spyOn(origin, 'getBoundingClientRect').mockImplementation(() =>
      rect(rootTop() + y() * 20 - scroller.scrollTop),
    );
    vi.spyOn(nested, 'getBoundingClientRect').mockImplementation(() =>
      rect(rootTop() + y() * 100 + 50 - scroller.scrollTop),
    );
    const firstTarget = view.container.querySelector<HTMLElement>('[data-block-id="first-ref"]')!;
    const secondTarget = view.container.querySelector<HTMLElement>('[data-block-id="second-ref"]')!;
    vi.spyOn(firstTarget, 'getBoundingClientRect').mockImplementation(() =>
      rect(rootTop() + y() * 100 - scroller.scrollTop),
    );
    vi.spyOn(secondTarget, 'getBoundingClientRect').mockImplementation(() =>
      rect(rootTop() + y() * 200 - scroller.scrollTop),
    );
    scroller.scrollTop = 300;
    origin.focus();
    fireEvent.click(origin);
    expect(window.document.activeElement).toBe(firstTarget);
    expect(scroller.scrollTop).toBe(1788);
    expect(window.history.state.readestAcademicLayers).toHaveLength(1);
    fireEvent.click(origin);
    expect(window.history.state.readestAcademicLayers).toHaveLength(1);
    nested.focus();
    fireEvent.click(nested);
    expect(window.history.state.readestAcademicLayers).toHaveLength(2);
    expect(window.document.activeElement).toBe(secondTarget);
    fireEvent.click(screen.getByRole('button', { name: 'Back to reading' }));
    expect(window.document.activeElement).toBe(nested);
    expect(scroller.scrollTop).toBe(1788);
    await waitFor(() => expect(window.history.state.readestAcademicLayers).toHaveLength(1));
    view.rerender(
      <ScholarlyReader
        document={doc}
        session={session}
        onZoom={vi.fn()}
        viewSettings={{ defaultFontSize: 24 }}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Back to reading' }));
    expect(window.document.activeElement).toBe(origin);
    expect(scroller.scrollTop).toBe(420);
    expect(origin.getBoundingClientRect().top - scroller.getBoundingClientRect().top).toBe(60);
    expect(screen.queryByRole('button', { name: 'Back to reading' })).toBeNull();
    await waitFor(() => expect(window.history.state?.readestAcademicLayers).toBeUndefined());
  });

  it('jumps from a superscript footnote marker and returns without changing selectable text', () => {
    const body = {
      ...block('body', 1, 'paragraph'),
      text: 'The packets were acknowledged. 5 More prose.',
    };
    const note = { ...block('note', 1, 'footnote'), text: '5Alternatively, an explanation.' };
    const doc = documentFor([
      {
        ...body,
        inlineRuns: [
          { kind: 'text', text: 'The packets were acknowledged. ', source: body.source[0]! },
          { kind: 'text', text: '5 ', source: body.source[0]!, style: { verticalAlign: 'super' } },
          { kind: 'text', text: 'More prose.', source: body.source[0]! },
        ],
      },
      {
        ...note,
        inlineRuns: [
          { kind: 'text', text: '5', source: note.source[0]!, style: { verticalAlign: 'super' } },
          { kind: 'text', text: 'Alternatively, an explanation.', source: note.source[0]! },
        ],
      },
    ]);
    doc.pages = [
      {
        page: 1,
        width: 600,
        height: 800,
        rotation: 0,
        tagged: false,
        items: [],
        graphics: [],
        lines: [],
        columns: [{ box: { x: 0, y: 0, width: 300, height: 800 }, confidence: 1 }],
        visualRegions: [],
        blockIds: ['body', 'note'],
        suppressedItemIndices: [],
      },
    ];
    const before = JSON.stringify(doc);
    const view = render(<ScholarlyReader document={doc} session={session} onZoom={vi.fn()} />);
    const link = screen.getByRole('link');
    expect(link.querySelector('sup')?.textContent).toBe('5');
    expect(view.container.querySelector('article')?.textContent).toBe(body.text + note.text);
    link.focus();
    fireEvent.click(link);
    expect(window.document.activeElement).toBe(screen.getByRole('note'));
    fireEvent.click(screen.getByRole('button', { name: 'Back to reading' }));
    expect(window.document.activeElement).toBe(link);
    expect(JSON.stringify(doc)).toBe(before);
  });

  it('identifies a footnote as a separate note without suggesting a clickable destination', () => {
    const note = block('note', 1, 'footnote');
    note.text = '7An additional detail.';
    note.inlineRuns = [
      { kind: 'text', text: '7', source: note.source[0]!, style: { verticalAlign: 'super' } },
      { kind: 'text', text: 'An additional detail.', source: note.source[0]! },
    ];
    render(<ScholarlyReader document={documentFor([note])} session={session} onZoom={vi.fn()} />);
    const rendered = screen.getByRole('note');
    expect(rendered.textContent).toBe('7An additional detail.');
    expect(rendered.querySelector('sup')?.textContent).toBe('7');
    expect(screen.queryByRole('link')).toBeNull();
    expect(screen.queryByRole('button')).toBeNull();
  });
  it('keeps adjacent source-row plots together while retaining both selectable captions', () => {
    const figures = [0, 1].map((index) => {
      const figure = block(`figure-${index}`, 2, 'visual-region');
      figure.source[0]!.boxes[0] = { x: 10 + index * 150, y: 20, width: 140, height: 100 };
      figure.previewBox = { ...figure.source[0]!.boxes[0]!, height: 60 };
      figure.captions = [
        {
          role: 'figure' as const,
          label: String(index + 1),
          text: `Figure ${index + 1}: Result.`,
          source: {
            page: 2,
            boxes: [{ x: 10 + index * 150, y: 85, width: 140, height: 20 }],
            itemIndices: [index],
          },
        },
      ];
      return figure;
    });
    const result = render(
      <ScholarlyReader document={documentFor(figures)} session={session} onZoom={vi.fn()} />,
    );
    const elements = result.container.querySelectorAll('figure');
    expect(elements).toHaveLength(2);
    expect(elements[0]!.parentElement).toBe(elements[1]!.parentElement);
    expect(elements[0]!.parentElement?.classList.contains('grid')).toBe(true);
    expect(screen.getAllByText(/Figure [12]: Result/)).toHaveLength(2);
  });
  it('renders a selectable caption once, scales a small chart to the reading font and zooms the full source', async () => {
    const visual = block('captioned', 2, 'visual-region');
    visual.previewBox = { x: 10, y: 20, width: 120, height: 60 };
    visual.captions = [
      {
        role: 'figure',
        label: '1',
        text: 'Figure 1: A selectable caption.',
        source: { page: 2, boxes: [{ x: 10, y: 85, width: 120, height: 20 }], itemIndices: [0] },
      },
    ];
    const onZoom = vi.fn();
    render(<ScholarlyReader document={documentFor([visual])} session={session} onZoom={onZoom} />);
    await act(async () => intersect(true));
    expect(renderRegion.mock.calls.at(-1)?.[1]).toEqual(visual.previewBox);
    expect(renderRegion.mock.calls.at(-1)?.[3]).toBe(180);
    expect(
      screen.getByText('Figure 1: A selectable caption.').closest('figcaption'),
    ).not.toBeNull();
    fireEvent.click(screen.getByRole('button'));
    expect(onZoom).toHaveBeenCalledWith(visual);
    expect(visual.source[0]!.boxes[0]!.height).toBe(100);
  });
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
    fireEvent.click(screen.getByRole('button', { name: 'Figure: Tap to zoom' }));
    expect(onZoom).toHaveBeenCalledWith(visual);
    result.unmount();
    expect(renderRegion.mock.calls[2]![4]!.aborted).toBe(true);
    expect(canvas.width).toBe(0);
    expect(disconnect).toHaveBeenCalledTimes(2);
  });

  it('keeps short equations at reading font scale, centered and zoomable', async () => {
    const equation = { ...block('equation', 2, 'visual-region'), role: 'equation' as const };
    equation.source[0]!.boxes[0] = { x: 10, y: 20, width: 80, height: 20 };
    const onZoom = vi.fn();
    const result = render(
      <ScholarlyReader document={documentFor([equation])} session={session} onZoom={onZoom} />,
    );
    await act(async () => intersect(true));
    const preview = screen.getByRole('button', { name: 'Equation: Tap to zoom' });
    expect(preview.style.maxWidth).toBe('120px');
    expect(preview.classList.contains('mx-auto')).toBe(true);
    expect(renderRegion.mock.calls.at(-1)?.[3]).toBe(120);
    fireEvent.click(preview);
    expect(onZoom).toHaveBeenCalledWith(equation);

    result.rerender(
      <ScholarlyReader
        document={documentFor([equation])}
        session={session}
        onZoom={onZoom}
        viewSettings={{ defaultFontSize: 24 }}
      />,
    );
    expect(preview.style.maxWidth).toBe('160px');
    expect(renderRegion.mock.calls.at(-1)?.[3]).toBe(160);
  });

  it('fits long equations to the available flow width without imposing equation scaling on figures', async () => {
    const equation = { ...block('long-equation', 2, 'visual-region'), role: 'equation' as const };
    equation.source[0]!.boxes[0] = { x: 10, y: 20, width: 400, height: 20 };
    const result = render(
      <ScholarlyReader document={documentFor([equation])} session={session} onZoom={vi.fn()} />,
    );
    await act(async () => intersect(true));
    expect(screen.getByRole('button').style.maxWidth).toBe('600px');
    expect(renderRegion.mock.calls.at(-1)?.[3]).toBe(360);
    width = 220;
    await act(async () => resize());
    expect(renderRegion.mock.calls.at(-1)?.[3]).toBe(220);
    result.unmount();

    render(
      <ScholarlyReader
        document={documentFor([block('figure', 2, 'visual-region')])}
        session={session}
        onZoom={vi.fn()}
      />,
    );
    await act(async () => intersect(true));
    expect(screen.getByRole('button').style.maxWidth).toBe('');
    expect(renderRegion.mock.calls.at(-1)?.[3]).toBe(220);
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
    expect(screen.queryByText(/Could not load the image/)).toBeNull();
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
