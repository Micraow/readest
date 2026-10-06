import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import OriginalPdfView from '@/components/academic/OriginalPdfView';

const mocks = vi.hoisted(() => ({
  open: vi.fn(),
  viewOpen: vi.fn(),
  destroy: vi.fn(),
  next: vi.fn(),
  prev: vi.fn(),
  close: vi.fn(),
}));
vi.mock('@/libs/document', () => ({
  DocumentLoader: class {
    open = mocks.open;
  },
}));
vi.mock('foliate-js/view.js', () => ({}));
vi.mock('@/hooks/useTranslation', () => ({ useTranslation: () => (key: string) => key }));
vi.mock('@/context/EnvContext', () => ({ useEnv: () => ({ appService: null }) }));
vi.mock('@/store/settingsStore', () => ({
  useSettingsStore: (selector: (state: unknown) => unknown) =>
    selector({ settings: { globalViewSettings: { zoomMode: 'fit-page', zoomLevel: 100 } } }),
}));
vi.mock('@/store/themeStore', () => ({
  useThemeStore: (selector: (state: unknown) => unknown) => selector({ themeCode: 'light' }),
}));
vi.mock('@/utils/style', () => ({ getPDFPageColors: () => undefined }));

beforeEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
  mocks.viewOpen.mockResolvedValue(undefined);
  mocks.open.mockResolvedValue({ book: { sections: [{}, {}], destroy: mocks.destroy } });
  const original = document.createElement.bind(document);
  vi.spyOn(document, 'createElement').mockImplementation(
    (tag: string, options?: ElementCreationOptions) => {
      const node = original(tag, options);
      if (tag === 'foliate-view')
        Object.assign(node, {
          open: mocks.viewOpen,
          init: vi.fn(),
          close: mocks.close,
          next: mocks.next,
          prev: mocks.prev,
          goTo: vi.fn(),
          renderer: original('div'),
        });
      return node;
    },
  );
});

describe('provider original PDF surface', () => {
  it('uses Foliate, navigates, and releases the document on close', async () => {
    const view = render(
      <OriginalPdfView file={new File(['%PDF-'], 'paper.pdf')} resumeKey='sample' />,
    );
    await waitFor(() =>
      expect(
        (screen.getByRole('button', { name: 'Next page' }) as HTMLButtonElement).disabled,
      ).toBe(false),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Next page' }));
    expect(mocks.next).toHaveBeenCalledOnce();
    view.unmount();
    expect(mocks.close).toHaveBeenCalledOnce();
    expect(mocks.destroy).toHaveBeenCalledOnce();
  });

  it('waits for an in-flight Foliate open before destroying it', async () => {
    let finish!: () => void;
    mocks.viewOpen.mockReturnValue(
      new Promise<void>((resolve) => {
        finish = resolve;
      }),
    );
    const view = render(
      <OriginalPdfView file={new File(['%PDF-'], 'paper.pdf')} resumeKey='sample' />,
    );
    await waitFor(() => expect(mocks.viewOpen).toHaveBeenCalled());
    view.unmount();
    expect(mocks.close).not.toHaveBeenCalled();
    finish();
    await waitFor(() => expect(mocks.close).toHaveBeenCalledOnce());
    expect(mocks.destroy).toHaveBeenCalledOnce();
  });

  it('destroys a document that resolves after the reader was dismissed', async () => {
    let resolve!: (value: unknown) => void;
    mocks.open.mockReturnValue(
      new Promise((done) => {
        resolve = done;
      }),
    );
    const view = render(
      <OriginalPdfView file={new File(['%PDF-'], 'paper.pdf')} resumeKey='sample' />,
    );
    await waitFor(() => expect(mocks.open).toHaveBeenCalled());
    view.unmount();
    resolve({ book: { sections: [], destroy: mocks.destroy } });
    await waitFor(() => expect(mocks.destroy).toHaveBeenCalledOnce());
    expect(document.querySelector('foliate-view')).toBeNull();
  });
});
