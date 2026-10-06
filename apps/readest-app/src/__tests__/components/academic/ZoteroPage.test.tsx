import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ZoteroPage from '@/app/zotero/page';

const push = vi.hoisted(() => vi.fn());
vi.mock('@/hooks/useAppRouter', () => ({ useAppRouter: () => ({ push }) }));
vi.mock('@/hooks/useTranslation', () => ({ useTranslation: () => (key: string) => key }));
vi.mock('@/hooks/useTheme', () => ({ useTheme: () => ({}) }));
vi.mock('@/hooks/useKeyDownActions', () => ({ useKeyDownActions: () => ({}) }));
vi.mock('@/store/themeStore', () => ({
  useThemeStore: (select: (value: unknown) => unknown) => select({ safeAreaInsets: null }),
}));
vi.mock('@/components/zotero/ZoteroShelf', () => ({
  default: ({ onOpen }: { onOpen: (file: File, title: string, resumeKey: string) => void }) => (
    <div data-testid='provider-shelf'>
      <input aria-label='Collection search' defaultValue='RDMA' />
      <button
        type='button'
        onClick={() => onOpen(new File(['%PDF-'], 'sample.pdf'), 'Sample paper', 'zotero:sample')}
      >
        Open sample
      </button>
    </div>
  ),
}));
vi.mock('@/components/academic/OriginalPdfView', () => ({
  default: () => <div data-testid='original-pdf'>Original PDF</div>,
}));
vi.mock('@/components/academic/AcademicReaderDialog', () => ({
  default: ({ onClose }: { onClose: () => void }) => (
    <div role='dialog' aria-label='Academic Reading Mode'>
      <button type='button' onClick={onClose}>
        Close Reading
      </button>
    </div>
  ),
}));
beforeEach(() => {
  window.history.replaceState({ __NA: true, tree: 'shelf' }, '', '/zotero');
});
afterEach(async () => {
  cleanup();
  await waitFor(() => expect(window.history.state?.readestAcademicLayers).toBeUndefined());
  push.mockClear();
});

describe('provider shelf reading integration', () => {
  it('returns to the same mounted shelf after reading without importing a Book', () => {
    render(<ZoteroPage />);
    const shelf = screen.getByTestId('provider-shelf');
    fireEvent.change(screen.getByLabelText('Collection search'), { target: { value: 'HPCC' } });
    fireEvent.click(screen.getByRole('button', { name: 'Open sample' }));
    expect(screen.getByTestId('original-pdf')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Back' }));
    expect(screen.queryByTestId('original-pdf')).toBeNull();
    expect(screen.getByTestId('provider-shelf')).toBe(shelf);
    expect((screen.getByLabelText('Collection search') as HTMLInputElement).value).toBe('HPCC');
    expect(push).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Back' }));
    expect(push).toHaveBeenCalledWith('/library');
  });

  it('browser Back closes Reading then the PDF while retaining the original view and shelf', async () => {
    const baseState = window.history.state;
    render(<ZoteroPage />);
    const shelf = screen.getByTestId('provider-shelf');
    fireEvent.change(screen.getByLabelText('Collection search'), { target: { value: 'HPCC' } });
    fireEvent.click(screen.getByRole('button', { name: 'Open sample' }));
    const original = screen.getByTestId('original-pdf');
    expect(screen.queryByRole('dialog')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'PDF / Reading' }));
    await screen.findByRole('dialog');
    await act(async () => window.history.back());
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    expect(screen.getByTestId('original-pdf')).toBe(original);
    await act(async () => window.history.back());
    await waitFor(() => expect(screen.queryByTestId('original-pdf')).toBeNull());
    expect(screen.getByTestId('provider-shelf')).toBe(shelf);
    expect((screen.getByLabelText('Collection search') as HTMLInputElement).value).toBe('HPCC');
    expect(window.history.state).toEqual(baseState);
    expect(push).not.toHaveBeenCalled();
  });
});
