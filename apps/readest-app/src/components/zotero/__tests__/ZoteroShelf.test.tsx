import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ZoteroShelf from '../ZoteroShelf';
import ZoteroSettings from '../ZoteroSettings';

const mocks = vi.hoisted(() => ({
  load: vi.fn(),
  refresh: vi.fn(),
  loadCached: vi.fn(),
  hasLocal: vi.fn(),
  open: vi.fn(),
  clearLocal: vi.fn(),
  connect: vi.fn(),
  disconnect: vi.fn(),
  subscribe: vi.fn(),
  service: {},
  listener: null as (() => void) | null,
}));
vi.mock('@/context/EnvContext', () => ({ useEnv: () => ({ appService: mocks.service }) }));
vi.mock('@/hooks/useTranslation', () => ({
  useTranslation: () => (key: string, options?: Record<string, string>) =>
    options ? key.replace(/{{(\w+)}}/g, (_, name: string) => options[name] ?? '') : key,
}));
vi.mock('@/services/zotero/runtime', () => ({
  getZoteroRuntime: () => mocks,
  zoteroErrorMessage: () => 'Connection failed',
}));
const item = {
  key: 'ITEM0001',
  version: 1,
  title: 'Academic paper',
  authors: ['Ada Lovelace'],
  year: '2025',
  venue: 'Journal',
  collectionKeys: ['CHILD001'],
};
const snapshot = {
  schema: 1,
  provider: 'zotero',
  userId: '12345',
  fetchedAt: 12345,
  collections: [
    { key: 'PARENT01', version: 1, name: 'Parent collection', parentKey: null },
    { key: 'CHILD001', version: 1, name: 'Child collection', parentKey: 'PARENT01' },
  ],
  items: [item],
};
const provider = {
  loadCached: mocks.loadCached,
  refresh: mocks.refresh,
  hasLocal: mocks.hasLocal,
  open: mocks.open,
  clearLocal: mocks.clearLocal,
};

beforeEach(() => {
  vi.clearAllMocks();
  mocks.load.mockResolvedValue({
    account: { userId: '12345', mode: 'session', connected: false },
    provider,
  });
  mocks.loadCached.mockResolvedValue(snapshot);
  mocks.refresh.mockResolvedValue(snapshot);
  mocks.hasLocal.mockResolvedValue(true);
  mocks.open.mockResolvedValue({
    file: new File(['%PDF-1.7'], 'paper.pdf', { type: 'application/pdf' }),
    title: item.title,
    resumeKey: 'zotero:12345:ITEM0001:ATTACH01',
  });
  mocks.subscribe.mockImplementation((listener: () => void) => {
    mocks.listener = listener;
    return () => {
      mocks.listener = null;
    };
  });
});
afterEach(cleanup);

describe('Zotero shelf', () => {
  it('browses cached hierarchy and opens local files without credentials or refresh', async () => {
    const onOpen = vi.fn();
    render(<ZoteroShelf onOpen={onOpen} />);
    await screen.findByText('Academic paper');
    expect(screen.getByText('Ada Lovelace')).toBeTruthy();
    expect(screen.getByText('Child collection')).toBeTruthy();
    await screen.findByText('Saved offline');
    fireEvent.click(screen.getByRole('button', { name: 'Open PDF: Academic paper' }));
    await waitFor(() =>
      expect(onOpen).toHaveBeenCalledWith(
        expect.any(File),
        item.title,
        'zotero:12345:ITEM0001:ATTACH01',
      ),
    );
    expect(mocks.refresh).not.toHaveBeenCalled();
  });
  it('filters a collection and clears only its local document', async () => {
    render(<ZoteroShelf onOpen={vi.fn()} />);
    await screen.findByText('Academic paper');
    fireEvent.click(screen.getByRole('button', { name: 'Parent collection' }));
    expect(screen.queryByText('Academic paper')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Child collection' }));
    await screen.findByText('Saved offline');
    fireEvent.click(screen.getByRole('button', { name: 'Clear local copy: Academic paper' }));
    await waitFor(() => expect(mocks.clearLocal).toHaveBeenCalledWith('ITEM0001'));
    expect(screen.getByText('Academic paper')).toBeTruthy();
  });
  it('reloads the shelf when connection settings change', async () => {
    render(<ZoteroShelf onOpen={vi.fn()} />);
    await screen.findByText('Academic paper');
    mocks.loadCached.mockResolvedValue({
      ...snapshot,
      items: [{ ...item, title: 'Another library' }],
    });
    mocks.listener?.();
    await screen.findByText('Another library');
  });
  it('removes the previous account shelf even when the new cache cannot be read', async () => {
    render(<ZoteroShelf onOpen={vi.fn()} />);
    await screen.findByText('Academic paper');
    await screen.findByText('Saved offline');
    mocks.load.mockResolvedValue({
      account: { userId: '67890', mode: 'session', connected: true },
      provider,
    });
    mocks.loadCached.mockRejectedValue(new Error('Local cache unavailable'));
    mocks.listener?.();
    await screen.findByText('Connection failed');
    expect(screen.queryByText('Academic paper')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Open PDF: Academic paper' })).toBeNull();
    expect(mocks.open).not.toHaveBeenCalled();
  });
  it('cancels an active PDF download on unmount', async () => {
    let signal: AbortSignal | undefined;
    mocks.load.mockResolvedValue({
      account: { userId: '12345', mode: 'session', connected: true },
      provider,
    });
    mocks.hasLocal.mockResolvedValue(false);
    mocks.open.mockImplementation((_item, downloadSignal: AbortSignal) => {
      signal = downloadSignal;
      return new Promise(() => {});
    });
    const { unmount } = render(<ZoteroShelf onOpen={vi.fn()} />);
    await screen.findByText('Academic paper');
    fireEvent.click(screen.getByRole('button', { name: 'Download PDF: Academic paper' }));
    await waitFor(() => expect(mocks.open).toHaveBeenCalled());
    unmount();
    expect(signal?.aborted).toBe(true);
  });
});

describe('Zotero settings', () => {
  it('discloses session-only storage, uses a password field, and clears it after saving', async () => {
    mocks.connect.mockResolvedValue({ userId: '12345', mode: 'session', connected: true });
    render(<ZoteroSettings />);
    const input = (await screen.findByLabelText('API key')) as HTMLInputElement;
    expect(input.type).toBe('password');
    await screen.findByText(/API key is kept only for this session/);
    fireEvent.change(input, { target: { value: 'private-key' } });
    fireEvent.click(screen.getByRole('button', { name: 'Test and save' }));
    await waitFor(() =>
      expect(mocks.connect).toHaveBeenCalledWith(
        { userId: '12345', apiKey: 'private-key' },
        expect.any(AbortSignal),
      ),
    );
    await waitFor(() => expect(input.value).toBe(''));
  });
});

it('shows a persistence rollback failure after Cancel instead of hiding it as cancellation', async () => {
  mocks.connect.mockImplementation(
    (_credentials, signal: AbortSignal) =>
      new Promise((_resolve, reject) => {
        signal.addEventListener('abort', () => reject(new Error('Rollback unavailable')));
      }),
  );
  render(<ZoteroSettings />);
  const input = await screen.findByLabelText('API key');
  fireEvent.change(input, { target: { value: 'private-key' } });
  fireEvent.click(screen.getByRole('button', { name: 'Test and save' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Cancel' }));
  expect(await screen.findByRole('alert')).toBeTruthy();
});
