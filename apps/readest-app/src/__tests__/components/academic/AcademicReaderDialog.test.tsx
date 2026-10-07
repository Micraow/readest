import type { ReactNode } from 'react';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AcademicReaderDialog from '@/components/academic/AcademicReaderDialog';
import type { ScholarlyDocument } from '@/services/academic/types';
import { mockReadingLayout } from './position-test-layout';

const mocks = vi.hoisted(() => ({
  open: vi.fn(),
  analyze: vi.fn(),
  destroy: vi.fn(),
  renderRegion: vi.fn(),
  renderPage: vi.fn(),
  service: { exists: vi.fn(), readFile: vi.fn(), writeFile: vi.fn(), createDir: vi.fn() },
}));
vi.mock('@/services/academic/runtime', () => ({ openAcademicPdf: mocks.open }));
vi.mock('@/hooks/useTranslation', () => ({ useTranslation: () => (key: string) => key }));
vi.mock('@/hooks/useKeyDownActions', () => ({ useKeyDownActions: () => ({}) }));
vi.mock('@/context/EnvContext', () => ({ useEnv: () => ({ appService: mocks.service }) }));
vi.mock('@/store/settingsStore', () => ({
  useSettingsStore: (select: (state: unknown) => unknown) =>
    select({
      settings: {
        globalViewSettings: { defaultFontSize: 18, lineHeight: 1.6, serifFont: 'serif' },
      },
    }),
}));
vi.mock('@/store/themeStore', () => ({
  useThemeStore: (select: (state: unknown) => unknown) => select({ safeAreaInsets: null }),
}));
vi.mock('@/components/ModalPortal', () => ({
  default: ({ children }: { children: ReactNode }) => children,
}));
vi.mock('@/app/reader/components/ImageViewer', () => ({ default: () => <div>Image viewer</div> }));
const box = { x: 10, y: 20, width: 100, height: 20 };
const source = [{ page: 1, boxes: [box], itemIndices: [0] }];
const scholarly: ScholarlyDocument = {
  schemaVersion: 1,
  parserVersion: 'test',
  fingerprint: 'sample',
  pageCount: 1,
  metadata: { pdfjsVersion: 'test' },
  pages: [],
  blocks: [
    {
      id: 'p1-b1',
      type: 'paragraph',
      text: 'A continuous academic paragraph',
      source,
      order: 0,
      confidence: 1,
      fontStats: { median: 12, min: 12, max: 12, names: [] },
    },
  ],
  readingOrder: ['p1-b1'],
  sourceMap: { 'p1-b1': source },
  warnings: [],
};
beforeEach(() => {
  vi.clearAllMocks();
  mocks.open.mockResolvedValue({
    analyze: mocks.analyze,
    destroy: mocks.destroy,
    renderRegion: mocks.renderRegion,
    renderPage: mocks.renderPage,
  });
  mocks.analyze.mockResolvedValue(scholarly);
  mocks.destroy.mockResolvedValue(undefined);
  localStorage.clear();
});
afterEach(async () => {
  cleanup();
  await waitFor(() => expect(window.history.state?.readestAcademicLayers).toBeUndefined());
  vi.restoreAllMocks();
});
describe('manual academic reading session', () => {
  it('adjusts the current PDF typography without changing book settings or analyzing again', async () => {
    const viewSettings = { defaultFontSize: 20, lineHeight: 1.7, serifFont: 'Bitter' };
    render(
      <AcademicReaderDialog
        file={new File(['%PDF-'], 'test.pdf')}
        title='Paper'
        viewSettings={viewSettings}
        onClose={vi.fn()}
      />,
    );
    const paragraph = await screen.findByText('A continuous academic paragraph');
    fireEvent.click(screen.getByRole('button', { name: 'Reading appearance' }));
    const font = screen.getByRole('spinbutton', { name: 'Font Size' });
    expect((font as HTMLInputElement).value).toBe('20');
    expect(
      (screen.getByRole('spinbutton', { name: 'Line Spacing' }) as HTMLInputElement).value,
    ).toBe('1.7');
    fireEvent.click(
      within(screen.getByRole('group', { name: 'Font Size' })).getByRole('button', {
        name: 'Increase',
      }),
    );
    fireEvent.change(screen.getByRole('spinbutton', { name: 'Line Spacing' }), {
      target: { value: '1.4' },
    });
    expect(paragraph.closest('article')?.style.fontSize).toBe('21px');
    expect(paragraph.closest('article')?.style.lineHeight).toBe('1.4');
    expect(paragraph.closest('article')?.style.fontFamily).toContain('Bitter');
    expect(viewSettings).toEqual({ defaultFontSize: 20, lineHeight: 1.7, serifFont: 'Bitter' });
    expect(mocks.open).toHaveBeenCalledOnce();
    expect(mocks.analyze).toHaveBeenCalledOnce();
  });

  it('restores per-document typography on reopen and resets to book preferences', async () => {
    const file = new File(['%PDF-'], 'test.pdf');
    const props = {
      file,
      title: 'Paper',
      viewSettings: { defaultFontSize: 20, lineHeight: 1.7 },
      onClose: vi.fn(),
    };
    const first = render(<AcademicReaderDialog {...props} />);
    await screen.findByText('A continuous academic paragraph');
    fireEvent.click(screen.getByRole('button', { name: 'Reading appearance' }));
    fireEvent.change(screen.getByRole('spinbutton', { name: 'Font Size' }), {
      target: { value: '24' },
    });
    first.unmount();
    render(<AcademicReaderDialog {...props} />);
    const paragraph = await screen.findByText('A continuous academic paragraph');
    expect(paragraph.closest('article')?.style.fontSize).toBe('24px');
    fireEvent.click(screen.getByRole('button', { name: 'Reading appearance' }));
    fireEvent.click(screen.getByRole('button', { name: 'Reset reading appearance' }));
    expect(paragraph.closest('article')?.style.fontSize).toBe('20px');
    expect(paragraph.closest('article')?.style.lineHeight).toBe('1.7');
    expect(localStorage.getItem('readest:academic-appearance:sample')).toBeNull();
  });

  it('uses fresh preferences for a different PDF and ignores invalid saved values', async () => {
    localStorage.setItem(
      'readest:academic-appearance:sample',
      JSON.stringify({ defaultFontSize: 30, lineHeight: 2 }),
    );
    localStorage.setItem(
      'readest:academic-appearance:other',
      JSON.stringify({ defaultFontSize: -10, lineHeight: 'invalid' }),
    );
    mocks.analyze.mockResolvedValue({ ...scholarly, fingerprint: 'other' });
    render(
      <AcademicReaderDialog
        file={new File(['%PDF-'], 'other.pdf')}
        title='Other'
        onClose={vi.fn()}
      />,
    );
    const paragraph = await screen.findByText('A continuous academic paragraph');
    expect(paragraph.closest('article')?.style.fontSize).toBe('18px');
    expect(paragraph.closest('article')?.style.lineHeight).toBe('1.6');
  });

  it('closes appearance before the reader on Escape and returns focus to its button', async () => {
    const onClose = vi.fn();
    render(
      <AcademicReaderDialog
        file={new File(['%PDF-'], 'test.pdf')}
        title='Paper'
        onClose={onClose}
      />,
    );
    await screen.findByText('A continuous academic paragraph');
    const toggle = screen.getByRole('button', { name: 'Reading appearance' });
    fireEvent.click(toggle);
    expect(document.activeElement).toBe(screen.getByRole('region', { name: 'Reading appearance' }));
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('region', { name: 'Reading appearance' })).toBeNull();
    expect(onClose).not.toHaveBeenCalled();
    expect(document.activeElement).toBe(toggle);
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('closes appearance on browser Back without closing the reader', async () => {
    const onClose = vi.fn();
    render(
      <AcademicReaderDialog
        file={new File(['%PDF-'], 'test.pdf')}
        title='Paper'
        onClose={onClose}
      />,
    );
    await screen.findByText('A continuous academic paragraph');
    fireEvent.click(screen.getByRole('button', { name: 'Reading appearance' }));
    await waitFor(() => expect(window.history.state?.readestAcademicLayers).toHaveLength(1));
    window.history.back();
    await waitFor(() =>
      expect(screen.queryByRole('region', { name: 'Reading appearance' })).toBeNull(),
    );
    expect(onClose).not.toHaveBeenCalled();
  });

  it('keeps the visible paragraph in place after changing font size', async () => {
    render(
      <AcademicReaderDialog
        file={new File(['%PDF-'], 'test.pdf')}
        title='Paper'
        onClose={vi.fn()}
      />,
    );
    const paragraph = await screen.findByText('A continuous academic paragraph');
    const scroll = screen.getByTestId('scholarly-scroll');
    scroll.scrollTop = 400;
    vi.spyOn(scroll, 'getBoundingClientRect').mockReturnValue({ top: 60 } as DOMRect);
    vi.spyOn(paragraph, 'getBoundingClientRect').mockImplementation(() => {
      const changed = paragraph.closest('article')?.style.fontSize === '24px';
      return { top: changed ? 200 : 80, bottom: changed ? 400 : 240 } as DOMRect;
    });
    fireEvent.click(screen.getByRole('button', { name: 'Reading appearance' }));
    fireEvent.change(screen.getByRole('spinbutton', { name: 'Font Size' }), {
      target: { value: '24' },
    });
    expect(scroll.scrollTop).toBe(520);
  });

  it('keeps the visible character inside a long block after a font change', async () => {
    const text = '0123456789'.repeat(30);
    mocks.analyze.mockResolvedValue({
      ...scholarly,
      blocks: [{ ...scholarly.blocks[0], text }],
    });
    render(
      <AcademicReaderDialog file={new File(['%PDF-'], 'long.pdf')} title='Long' onClose={vi.fn()} />,
    );
    const paragraph = await screen.findByText(text);
    const scroll = screen.getByTestId('scholarly-scroll');
    scroll.scrollTop = 400;
    const { characterY } = mockReadingLayout(scroll, paragraph, () =>
      paragraph.closest('article')?.style.fontSize === '24px' ? 30 : 20,
    );
    expect(characterY(200)).toBe(60);
    fireEvent.scroll(scroll);
    fireEvent.click(screen.getByRole('button', { name: 'Reading appearance' }));
    fireEvent.change(screen.getByRole('spinbutton', { name: 'Font Size' }), {
      target: { value: '24' },
    });
    expect(scroll.scrollTop).toBe(600);
    expect(characterY(200)).toBe(60);
  });

  it('renders a continuous flow and releases the parser on dismissal', async () => {
    const onClose = vi.fn();
    const result = render(
      <AcademicReaderDialog
        file={new File(['%PDF-'], 'test.pdf')}
        title='Paper'
        onClose={onClose}
      />,
    );
    await screen.findByText('A continuous academic paragraph');
    expect(screen.queryByText('Page 1')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Original PDF' }));
    expect(onClose).toHaveBeenCalledOnce();
    result.unmount();
    expect(mocks.destroy).toHaveBeenCalled();
  });
  it('does not restart parsing on unrelated dialog rerenders', async () => {
    const file = new File(['%PDF-'], 'test.pdf');
    const result = render(
      <AcademicReaderDialog file={file} title='Paper' onClose={() => undefined} />,
    );
    await screen.findByText('A continuous academic paragraph');
    result.rerender(
      <AcademicReaderDialog file={file} title='Updated title' onClose={() => undefined} />,
    );
    await screen.findByText('Updated title');
    expect(mocks.open).toHaveBeenCalledTimes(1);
  });

  it('keeps Original PDF available when text layer is unsupported', async () => {
    mocks.analyze.mockRejectedValue(
      Object.assign(new Error('No text'), { name: 'NoTextLayerError' }),
    );
    const onClose = vi.fn();
    render(
      <AcademicReaderDialog
        file={new File(['%PDF-'], 'scan.pdf')}
        title='Scan'
        onClose={onClose}
      />,
    );
    await screen.findByText(/Reading mode is not available/);
    fireEvent.click(screen.getByRole('button', { name: 'Original PDF' }));
    expect(onClose).toHaveBeenCalledOnce();
  });
  it('aborts parsing and destroys a session that arrives after dismissal', async () => {
    let finish!: (value: unknown) => void;
    mocks.open.mockReturnValue(
      new Promise((resolve) => {
        finish = resolve;
      }),
    );
    const result = render(
      <AcademicReaderDialog
        file={new File(['%PDF-'], 'test.pdf')}
        title='Paper'
        onClose={() => undefined}
      />,
    );
    await waitFor(() => expect(mocks.open).toHaveBeenCalled());
    const signal = mocks.open.mock.calls[0]![1] as AbortSignal;
    result.unmount();
    expect(signal.aborted).toBe(true);
    finish({
      analyze: mocks.analyze,
      destroy: mocks.destroy,
      renderRegion: mocks.renderRegion,
      renderPage: mocks.renderPage,
    });
    await waitFor(() => expect(mocks.destroy).toHaveBeenCalled());
    expect(mocks.analyze).not.toHaveBeenCalled();
  });
});
