import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import AcademicReadingButton from '@/components/academic/AcademicReadingButton';
import { eventDispatcher } from '@/utils/event';

const mocks = vi.hoisted(() => ({
  loaded: vi.fn(),
  finish: null as (() => void) | null,
  acquire: vi.fn(),
  release: vi.fn(),
  service: { isAndroidApp: true },
}));
vi.mock('@/components/academic/AcademicReaderDialog', async () => {
  mocks.loaded();
  await new Promise<void>((resolve) => {
    mocks.finish = resolve;
  });
  return { default: () => <div role='dialog'>Loaded dialog</div> };
});
vi.mock('@/hooks/useTranslation', () => ({ useTranslation: () => (key: string) => key }));
vi.mock('@/context/EnvContext', () => ({ useEnv: () => ({ appService: mocks.service }) }));
vi.mock('@/store/deviceStore', () => ({
  useDeviceControlStore: () => ({
    acquireBackKeyInterception: mocks.acquire,
    releaseBackKeyInterception: mocks.release,
  }),
}));
afterEach(async () => {
  cleanup();
  mocks.finish?.();
  await waitFor(() => expect(window.history.state?.readestAcademicLayers).toBeUndefined());
});

describe('manual Reading chunk loading', () => {
  it('handles native Back and Escape while the lazy dialog is still loading', async () => {
    const onOpenChange = vi.fn();
    render(
      <AcademicReadingButton
        file={new File(['%PDF-'], 'paper.pdf')}
        title='Paper'
        onOpenChange={onOpenChange}
      />,
    );
    expect(mocks.loaded).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'PDF / Reading' }));
    await screen.findByRole('button', { name: 'Cancel' });
    await waitFor(() => expect(mocks.loaded).toHaveBeenCalledOnce());
    let consumed = false;
    act(() => {
      consumed = eventDispatcher.dispatchSync('native-key-down', { keyName: 'Back' });
    });
    expect(consumed).toBe(true);
    expect(screen.queryByRole('button', { name: 'Cancel' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'PDF / Reading' }));
    await screen.findByRole('button', { name: 'Cancel' });
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('button', { name: 'Cancel' })).toBeNull();
    await act(async () => mocks.finish?.());
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(onOpenChange.mock.calls).toEqual([[true], [false], [true], [false]]);
    expect(mocks.acquire.mock.calls.length).toBe(mocks.release.mock.calls.length);
  });
});
