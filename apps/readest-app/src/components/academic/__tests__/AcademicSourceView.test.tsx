import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { AcademicPdfSession } from '@/services/academic/runtime';
import AcademicSourceView from '../AcademicSourceView';

vi.mock('@/hooks/useTranslation', () => ({ useTranslation: () => (key: string) => key }));
const renderPage = vi.fn<AcademicPdfSession['renderPage']>();
const session: AcademicPdfSession = {
  pageCount: 3,
  renderPage,
  renderRegion: vi.fn(),
  analyze: vi.fn(),
  destroy: vi.fn(),
};
const pending: Array<{
  canvas: HTMLCanvasElement;
  signal: AbortSignal | undefined;
  finish: () => void;
  fail: () => void;
}> = [];
beforeEach(() => {
  vi.clearAllMocks();
  pending.length = 0;
  vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockReturnValue(360);
  renderPage.mockImplementation((_page, canvas, signal, width) => {
    canvas.width = width ?? 612;
    canvas.height = 792;
    canvas.style.width = `${width}px`;
    canvas.style.height = '466px';
    return new Promise<void>((resolve, reject) =>
      pending.push({ canvas, signal, finish: resolve, fail: () => reject(new Error('failed')) }),
    );
  });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('same-session original PDF view', () => {
  it('renders every requested page and bounds fit width without destroying the shared session', async () => {
    const onPageChange = vi.fn();
    const view = render(
      <AcademicSourceView session={session} page={1} onPageChange={onPageChange} />,
    );
    await waitFor(() => expect(pending).toHaveLength(1));
    expect(renderPage.mock.calls[0]?.[3]).toBe(360);
    await act(async () => pending[0]!.finish());
    expect(screen.getByRole('img', { name: 'Original PDF page 1' })).toBe(pending[0]!.canvas);
    fireEvent.click(screen.getByRole('button', { name: 'Next page' }));
    expect(onPageChange).toHaveBeenLastCalledWith(2);
    fireEvent.change(screen.getByRole('spinbutton', { name: 'PDF page' }), {
      target: { value: '99' },
    });
    expect(onPageChange).toHaveBeenCalledTimes(1);
    view.unmount();
    expect(pending[0]!.canvas.width).toBe(0);
    expect(pending[0]!.signal?.aborted).toBe(true);
    expect(session.destroy).not.toHaveBeenCalled();
  });

  it('keeps the last painted page until a new one succeeds and discards late cancelled renders', async () => {
    const props = { session, onPageChange: vi.fn() };
    const view = render(<AcademicSourceView {...props} page={1} />);
    await act(async () => pending[0]!.finish());
    view.rerender(<AcademicSourceView {...props} page={2} />);
    expect(pending[0]!.canvas.width).toBeGreaterThan(0);
    expect(screen.getByRole('img', { name: 'Original PDF page 1' })).toBeTruthy();
    view.rerender(<AcademicSourceView {...props} page={3} />);
    expect(pending[1]!.signal?.aborted).toBe(true);
    await act(async () => pending[2]!.finish());
    await act(async () => pending[1]!.finish());
    expect(screen.getAllByRole('img')).toHaveLength(1);
    expect(screen.getByRole('img', { name: 'Original PDF page 3' })).toBe(pending[2]!.canvas);
    expect(pending[0]!.canvas.width).toBe(0);
    expect(pending[1]!.canvas.width).toBe(0);
  });

  it('retains a readable previous page on failure, retries, and limits highlights to their source page', async () => {
    const props = {
      session,
      onPageChange: vi.fn(),
      source: { page: 1, boxes: [{ x: 10, y: 20, width: 100, height: 30 }], itemIndices: [0] },
      geometry: { width: 612, height: 792 },
    };
    const view = render(<AcademicSourceView {...props} page={1} />);
    await act(async () => pending[0]!.finish());
    expect(view.container.querySelectorAll('[data-source-highlight]')).toHaveLength(1);
    view.rerender(<AcademicSourceView {...props} page={2} />);
    await act(async () => pending[1]!.fail());
    expect(screen.getByRole('alert').textContent).toContain('Could not load this PDF page');
    expect(screen.getByRole('img', { name: 'Original PDF page 1' })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    await act(async () => pending[2]!.finish());
    expect(screen.getByRole('img', { name: 'Original PDF page 2' })).toBeTruthy();
    expect(view.container.querySelector('[data-source-highlight]')).toBeNull();
  });
});
