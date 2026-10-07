import type { ReactNode } from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AcademicReaderDialog from '@/components/academic/AcademicReaderDialog';
import type { ScholarlyDocument } from '@/services/academic/types';

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
afterEach(cleanup);
describe('manual academic reading session', () => {
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
