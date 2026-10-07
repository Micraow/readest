import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AcademicReadingButton from '@/components/academic/AcademicReadingButton';
import AcademicReaderDialog from '@/components/academic/AcademicReaderDialog';
import { eventDispatcher } from '@/utils/event';
import type { AcademicPdfSession } from '@/services/academic/runtime';
import type { ScholarlyDocument } from '@/services/academic/types';

const mocks = vi.hoisted(() => ({
  open: vi.fn(),
  acquire: vi.fn(),
  release: vi.fn(),
  service: {
    isAndroidApp: true,
    exists: vi.fn(),
    readFile: vi.fn(),
    writeFile: vi.fn(),
    createDir: vi.fn(),
  },
}));
vi.mock('@/services/academic/runtime', () => ({ openAcademicPdf: mocks.open }));
vi.mock('@/hooks/useTranslation', () => ({ useTranslation: () => (key: string) => key }));
vi.mock('@/context/EnvContext', () => ({ useEnv: () => ({ appService: mocks.service }) }));
vi.mock('@/store/deviceStore', () => ({
  useDeviceControlStore: () => ({
    acquireBackKeyInterception: mocks.acquire,
    releaseBackKeyInterception: mocks.release,
  }),
}));
vi.mock('@/store/settingsStore', () => ({
  useSettingsStore: (select: (state: unknown) => unknown) =>
    select({ settings: { globalViewSettings: { defaultFontSize: 18, lineHeight: 1.6 } } }),
}));
vi.mock('@/store/themeStore', () => ({
  useThemeStore: (select?: (state: unknown) => unknown) => {
    const state = {
      safeAreaInsets: null,
      isIPhoneDuo: false,
      systemUIVisible: true,
      statusBarHeight: 0,
    };
    return select ? select(state) : state;
  },
}));
vi.mock('@/app/reader/components/ImageContextMenu', () => ({ ImageMenu: () => null }));
vi.mock('@/utils/share', () => ({ canShareText: () => false }));

const source = [{ page: 1, boxes: [{ x: 10, y: 20, width: 200, height: 100 }], itemIndices: [0] }];
const scholarly: ScholarlyDocument = {
  schemaVersion: 1,
  parserVersion: 'test',
  fingerprint: 'lifecycle-paper',
  pageCount: 1,
  metadata: { pdfjsVersion: 'test' },
  pages: [
    {
      page: 1,
      width: 612,
      height: 792,
      rotation: 0,
      tagged: false,
      items: [],
      graphics: [],
      lines: [],
      columns: [],
      visualRegions: [],
      blockIds: ['figure'],
      suppressedItemIndices: [],
    },
  ],
  blocks: [
    {
      id: 'figure',
      type: 'visual-region',
      role: 'figure',
      text: '',
      source,
      order: 0,
      confidence: 1,
      fontStats: { median: 12, min: 12, max: 12, names: [] },
    },
  ],
  readingOrder: ['figure'],
  sourceMap: { figure: source },
  warnings: [],
};
const createSession = () => ({
  analyze: vi.fn<AcademicPdfSession['analyze']>().mockResolvedValue(scholarly),
  destroy: vi.fn<AcademicPdfSession['destroy']>().mockResolvedValue(undefined),
  renderRegion: vi.fn<AcademicPdfSession['renderRegion']>().mockResolvedValue(undefined),
  renderPage: vi.fn<AcademicPdfSession['renderPage']>().mockResolvedValue(undefined),
});
let session: ReturnType<typeof createSession>;
const createURL = vi.fn<typeof URL.createObjectURL>();
const revokeURL = vi.fn<typeof URL.revokeObjectURL>();
beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  window.history.replaceState({ __NA: true, tree: { route: 'unchanged' } }, '', '/reader/test');
  session = createSession();
  mocks.open.mockResolvedValue(session);
  createURL.mockReturnValue('blob:academic-region');
  vi.stubGlobal(
    'IntersectionObserver',
    class {
      observe() {}
      disconnect() {}
    },
  );
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      disconnect() {}
    },
  );
  vi.spyOn(URL, 'createObjectURL').mockImplementation(createURL);
  vi.spyOn(URL, 'revokeObjectURL').mockImplementation(revokeURL);
  vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation((callback) =>
    callback(new Blob(['png'])),
  );
});
afterEach(async () => {
  cleanup();
  // History traversal is asynchronous; let dismissal finish before the next case.
  await waitFor(() => expect(window.history.state?.readestAcademicLayers).toBeUndefined());
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});
const openReading = async () => {
  const onOpenChange = vi.fn();
  const result = render(
    <AcademicReadingButton
      file={new File(['%PDF-'], 'paper.pdf')}
      title='Paper'
      onOpenChange={onOpenChange}
    />,
  );
  expect(mocks.open).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'PDF / Reading' }));
  await screen.findByRole('button', { name: 'Figure: Tap to zoom' }, { timeout: 5000 });
  return { ...result, onOpenChange };
};
const zoom = async () => {
  fireEvent.click(screen.getByRole('button', { name: 'Figure: Tap to zoom' }));
  return screen.findByRole('button', { name: 'Image viewer' });
};
const nativeBack = () =>
  act(() => {
    expect(eventDispatcher.dispatchSync('native-key-down', { keyName: 'Back' })).toBe(true);
  });

describe('academic dialog lifecycle and navigation', () => {
  const withReferences = () => {
    const paragraph = {
      ...scholarly.blocks[0]!,
      type: 'paragraph' as const,
      role: undefined,
      id: 'body',
      text: 'See [34].',
    };
    const reference = {
      ...paragraph,
      type: 'reference' as const,
      id: 'reference',
      text: '[34] A study with [35].',
    };
    const second = { ...reference, id: 'reference-35', text: '[35] Another study.' };
    session.analyze.mockResolvedValue({
      ...scholarly,
      blocks: [paragraph, reference, second, ...scholarly.blocks],
    });
  };

  it('closes zoom and appearance before returning references, then closes Reading on native Back', async () => {
    withReferences();
    await openReading();
    const link = screen.getAllByRole('link')[0]!;
    link.focus();
    fireEvent.click(link);
    expect(screen.getByRole('button', { name: 'Back to reading' })).toBeTruthy();
    await zoom();
    nativeBack();
    expect(screen.queryByRole('button', { name: 'Image viewer' })).toBeNull();
    expect(screen.getByRole('button', { name: 'Back to reading' })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Reading appearance' }));
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(
      screen.getByRole('button', { name: 'Reading appearance' }).getAttribute('aria-expanded'),
    ).toBe('false');
    expect(screen.getByRole('button', { name: 'Back to reading' })).toBeTruthy();
    nativeBack();
    expect(screen.queryByRole('button', { name: 'Back to reading' })).toBeNull();
    expect(window.document.activeElement).toBe(link);
    expect(screen.getByRole('dialog')).toBeTruthy();
    nativeBack();
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('supports immediate Return/rejump, nested browser Back, obsolete Forward and reopening', async () => {
    withReferences();
    const baseState = window.history.state;
    await openReading();
    const link = screen.getAllByRole('link')[0]!;
    fireEvent.click(link);
    fireEvent.click(screen.getByRole('button', { name: 'Back to reading' }));
    fireEvent.click(link);
    await waitFor(() => expect(window.history.state.readestAcademicLayers).toHaveLength(2));
    fireEvent.click(screen.getAllByRole('link')[1]!);
    await waitFor(() => expect(window.history.state.readestAcademicLayers).toHaveLength(3));
    await act(async () => window.history.back());
    await waitFor(() => expect(window.history.state.readestAcademicLayers).toHaveLength(2));
    expect(screen.getByRole('button', { name: 'Back to reading' })).toBeTruthy();
    await act(async () => window.history.back());
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: 'Back to reading' })).toBeNull(),
    );
    expect(screen.getByRole('dialog')).toBeTruthy();
    await act(async () => window.history.forward());
    await waitFor(() => expect(window.history.state.readestAcademicLayers).toHaveLength(1));
    expect(screen.queryByRole('button', { name: 'Back to reading' })).toBeNull();
    fireEvent.click(link);
    fireEvent.click(screen.getByRole('button', { name: 'Close Reading Mode' }));
    await waitFor(() => expect(window.history.state).toEqual(baseState));
    fireEvent.click(screen.getByRole('button', { name: 'PDF / Reading' }));
    await screen.findAllByRole('link');
    expect(screen.queryByRole('button', { name: 'Back to reading' })).toBeNull();
    expect(session.analyze).toHaveBeenCalledTimes(2);
  });

  it('includes reference links in the dialog keyboard focus loop', async () => {
    withReferences();
    await openReading();
    vi.spyOn(HTMLElement.prototype, 'getClientRects').mockReturnValue([
      { width: 10 },
    ] as unknown as DOMRectList);
    // Disable the trailing figure so a reference is the last keyboard stop.
    const first = screen.getByRole('button', { name: 'Original PDF' });
    const links = screen.getAllByRole('link');
    const figure = screen.getByRole('button', { name: 'Figure: Tap to zoom' });
    (figure as HTMLButtonElement).disabled = true;
    links.at(-1)!.focus();
    fireEvent.keyDown(window, { key: 'Tab' });
    expect(window.document.activeElement).toBe(first);
    fireEvent.keyDown(window, { key: 'Tab', shiftKey: true });
    expect(window.document.activeElement).toBe(links.at(-1));
  });

  it('opens only on request and repeatedly releases each parser session', async () => {
    const { onOpenChange } = await openReading();
    expect(mocks.open).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: 'Original PDF' }));
    expect(screen.queryByRole('dialog')).toBeNull();
    await waitFor(() => expect(session.destroy).toHaveBeenCalledOnce());
    fireEvent.click(screen.getByRole('button', { name: 'PDF / Reading' }));
    await screen.findByRole('button', { name: 'Figure: Tap to zoom' });
    expect(mocks.open).toHaveBeenCalledTimes(2);
    fireEvent.click(screen.getByRole('button', { name: 'Close Reading Mode' }));
    expect(session.destroy).toHaveBeenCalledTimes(2);
    expect(onOpenChange.mock.calls).toEqual([[true], [false], [true], [false]]);
  });

  it('reuses real ImageViewer zoom/pan and closes only the top layer on Escape/native Back', async () => {
    await openReading();
    const scroller = screen.getByTestId('scholarly-scroll');
    scroller.scrollTop = 625;
    const viewer = await zoom();
    const img = viewer.querySelector('img')!;
    fireEvent.doubleClick(img);
    expect(img.style.transform).toContain('scale(2)');
    fireEvent.mouseDown(img, { clientX: 100, clientY: 100 });
    fireEvent.mouseMove(window, { clientX: 160, clientY: 130 });
    expect(img.style.transform).toContain('translate(30px, 15px)');
    fireEvent.mouseUp(window);
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('button', { name: 'Image viewer' })).toBeNull();
    expect(screen.getByRole('dialog')).toBeTruthy();
    expect(screen.getByTestId('scholarly-scroll')).toBe(scroller);
    expect(scroller.scrollTop).toBe(625);
    expect(revokeURL).toHaveBeenCalledWith('blob:academic-region');
    await zoom();
    nativeBack();
    expect(screen.queryByRole('button', { name: 'Image viewer' })).toBeNull();
    expect(screen.getByRole('dialog')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Inspect layout' }));
    expect(screen.getByLabelText('Academic PDF Layout Inspector')).toBeTruthy();
    nativeBack();
    expect(screen.queryByLabelText('Academic PDF Layout Inspector')).toBeNull();
    expect(screen.getByRole('dialog')).toBeTruthy();
    nativeBack();
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(localStorage.getItem('readest:academic-position:lifecycle-paper')).toBe('625');
    expect(mocks.acquire.mock.calls.length).toBe(mocks.release.mock.calls.length);
  });

  it('ignores a cancelled high-resolution render and releases its canvas', async () => {
    await openReading();
    let finish!: () => void;
    session.renderRegion.mockImplementationOnce(
      () =>
        new Promise<void>((resolve) => {
          finish = resolve;
        }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Figure: Tap to zoom' }));
    const signal = session.renderRegion.mock.calls[0]![4]!;
    const canvas = session.renderRegion.mock.calls[0]![2];
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(signal.aborted).toBe(true);
    await act(async () => finish());
    expect(createURL).not.toHaveBeenCalled();
    expect(canvas.width).toBe(0);
    expect(canvas.height).toBe(0);
    await zoom();
    expect(createURL).toHaveBeenCalledTimes(1);
  });

  it('retries with a fresh parser after failure', async () => {
    session.analyze.mockRejectedValueOnce(new Error('Transient read failed'));
    render(
      <AcademicReaderDialog
        file={new File(['%PDF-'], 'paper.pdf')}
        title='Paper'
        onClose={vi.fn()}
      />,
    );
    await screen.findByText(/Could not open reading mode/);
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    await screen.findByRole('button', { name: 'Figure: Tap to zoom' });
    expect(session.destroy).toHaveBeenCalledOnce();
    expect(mocks.open).toHaveBeenCalledTimes(2);
  });

  it('cancels pending zoom before opening the layout inspector', async () => {
    await openReading();
    let finish!: () => void;
    session.renderRegion.mockImplementationOnce(
      () =>
        new Promise<void>((resolve) => {
          finish = resolve;
        }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Figure: Tap to zoom' }));
    const signal = session.renderRegion.mock.calls[0]![4]!;
    fireEvent.click(screen.getByRole('button', { name: 'Inspect layout' }));
    expect(signal.aborted).toBe(true);
    await act(async () => finish());
    expect(screen.queryByRole('button', { name: 'Image viewer' })).toBeNull();
    expect(screen.getByLabelText('Academic PDF Layout Inspector')).toBeTruthy();
    nativeBack();
    expect(screen.queryByLabelText('Academic PDF Layout Inspector')).toBeNull();
    expect(screen.getByRole('dialog')).toBeTruthy();
  });

  it('does not create a raster URL when dismissal interrupts canvas encoding', async () => {
    const result = await openReading();
    let finish!: BlobCallback;
    vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation((callback) => {
      finish = callback;
    });
    fireEvent.click(screen.getByRole('button', { name: 'Figure: Tap to zoom' }));
    await waitFor(() => expect(finish).toBeDefined());
    const canvas = session.renderRegion.mock.calls[0]![2];
    result.unmount();
    await act(async () => finish(new Blob(['png'])));
    expect(createURL).not.toHaveBeenCalled();
    expect(canvas.width).toBe(0);
    expect(canvas.height).toBe(0);
  });

  it('browser Back dismisses zoom before Reading while preserving Next history state', async () => {
    const baseState = window.history.state;
    await openReading();
    await zoom();
    expect(window.history.state.__NA).toBe(true);
    expect(window.history.state.tree).toEqual(baseState.tree);
    await act(async () => window.history.back());
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Image viewer' })).toBeNull());
    expect(screen.getByRole('dialog')).toBeTruthy();
    await act(async () => window.history.back());
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    expect(window.history.state).toEqual(baseState);
  });

  it('normal close removes same-URL overlay entries even during rapid reopen', async () => {
    const baseState = window.history.state;
    await openReading();
    fireEvent.click(screen.getByRole('button', { name: 'Original PDF' }));
    fireEvent.click(screen.getByRole('button', { name: 'PDF / Reading' }));
    await screen.findByRole('button', { name: 'Figure: Tap to zoom' });
    await waitFor(() => expect(window.history.state.readestAcademicLayers).toHaveLength(1));
    expect(screen.getByRole('dialog')).toBeTruthy();
    expect(window.history.state).not.toEqual(baseState);
    fireEvent.click(screen.getByRole('button', { name: 'Close Reading Mode' }));
    await waitFor(() => expect(window.history.state).toEqual(baseState));
  });

  it('Forward skips a closed Reading entry without automatically restarting analysis', async () => {
    const baseState = window.history.state;
    await openReading();
    fireEvent.click(screen.getByRole('button', { name: 'Original PDF' }));
    await waitFor(() => expect(window.history.state).toEqual(baseState));
    const popped = new Promise<void>((resolve) =>
      window.addEventListener('popstate', () => resolve(), { once: true }),
    );
    await act(async () => {
      window.history.forward();
      await popped;
    });
    await waitFor(() => expect(window.history.state).toEqual(baseState));
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(mocks.open).toHaveBeenCalledTimes(1);
  });

  it('does not publish analysis from a dismissed/replaced source', async () => {
    let finish!: (document: ScholarlyDocument) => void;
    session.analyze.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const first = new File(['%PDF-one'], 'first.pdf');
    const second = new File(['%PDF-two'], 'second.pdf');
    const result = render(<AcademicReaderDialog file={first} title='First' onClose={vi.fn()} />);
    await waitFor(() => expect(session.analyze).toHaveBeenCalled());
    const signal = session.analyze.mock.calls[0]![2]!;
    result.rerender(<AcademicReaderDialog file={second} title='Second' onClose={vi.fn()} />);
    await screen.findByRole('button', { name: 'Figure: Tap to zoom' });
    expect(signal.aborted).toBe(true);
    await act(async () =>
      finish({
        ...scholarly,
        blocks: [{ ...scholarly.blocks[0]!, type: 'paragraph', text: 'Stale first document' }],
      }),
    );
    expect(screen.queryByText('Stale first document')).toBeNull();
    expect(screen.getByRole('button', { name: 'Figure: Tap to zoom' })).toBeTruthy();
  });

  it('clears old zoom state when the source file changes', async () => {
    const result = render(
      <AcademicReaderDialog
        file={new File(['%PDF-'], 'first.pdf')}
        title='First'
        onClose={vi.fn()}
      />,
    );
    await screen.findByRole('button', { name: 'Figure: Tap to zoom' });
    await zoom();
    result.rerender(
      <AcademicReaderDialog
        file={new File(['%PDF-'], 'second.pdf')}
        title='Second'
        onClose={vi.fn()}
      />,
    );
    await screen.findByRole('button', { name: 'Figure: Tap to zoom' });
    expect(screen.queryByRole('button', { name: 'Image viewer' })).toBeNull();
    expect(revokeURL).toHaveBeenCalledWith('blob:academic-region');
  });
});
