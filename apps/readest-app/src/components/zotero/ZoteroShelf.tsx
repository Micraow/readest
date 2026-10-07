'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import clsx from 'clsx';
import { useEnv } from '@/context/EnvContext';
import { useTranslation } from '@/hooks/useTranslation';
import { buildCollectionTree, isCancelled } from '@/services/zotero/api';
import { getZoteroRuntime, zoteroErrorMessage } from '@/services/zotero/runtime';
import type { ZoteroAccount } from '@/services/zotero/credentials';
import type { ZoteroProvider } from '@/services/zotero/provider';
import type {
  DownloadProgress,
  ExternalCollectionNode,
  ExternalItem,
  ExternalLibrarySnapshot,
} from '@/services/externalLibrary/types';
import ZoteroSettings from './ZoteroSettings';

export interface ZoteroShelfProps {
  onOpen: (file: File, title: string, resumeKey: string) => void;
}

type Operation = 'load' | 'refresh' | 'download' | 'clear' | null;

export default function ZoteroShelf({ onOpen }: ZoteroShelfProps) {
  const _ = useTranslation();
  const { appService } = useEnv();
  const runtime = useMemo(() => (appService ? getZoteroRuntime(appService) : null), [appService]);
  const [account, setAccount] = useState<ZoteroAccount | null>(null);
  const [provider, setProvider] = useState<ZoteroProvider | null>(null);
  const [snapshot, setSnapshot] = useState<ExternalLibrarySnapshot | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [localKeys, setLocalKeys] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState<Operation>('load');
  const [downloadKey, setDownloadKey] = useState<string | null>(null);
  const [progress, setProgress] = useState<DownloadProgress | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const operation = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const previousUserId = useRef<string | null>(null);

  const localStatus = async (
    source: ZoteroProvider,
    data: ExternalLibrarySnapshot,
  ): Promise<Set<string>> => {
    const local = new Set<string>();
    // Avoid hundreds of concurrent native filesystem IPC requests for large libraries.
    for (let start = 0; start < data.items.length; start += 20) {
      await Promise.all(
        data.items.slice(start, start + 20).map(async (item) => {
          if (await source.hasLocal(item.key)) local.add(item.key);
        }),
      );
    }
    return local;
  };

  useEffect(() => {
    if (!runtime) return;
    let disposed = false;
    const load = async () => {
      const current = ++generation.current;
      operation.current?.abort();
      const controller = new AbortController();
      operation.current = controller;
      setBusy('load');
      setError('');
      setNotice('');
      setDownloadKey(null);
      setProgress(null);
      const stale = () => disposed || current !== generation.current;
      try {
        const { account: loaded, provider: source } = await runtime.load();
        if (stale()) return;
        setAccount(loaded);
        setProvider(source);
        if (previousUserId.current !== loaded.userId) {
          // Never display the previous library with the new account's provider,
          // including when the next local-cache read fails.
          setSnapshot(null);
          setSelected(null);
          setLocalKeys(new Set());
        }
        previousUserId.current = loaded.userId;
        if (!source) {
          setSnapshot(null);
          return;
        }
        const cached = await source.loadCached();
        if (stale()) return;
        setSnapshot(cached);
        if (cached) {
          const statuses = await localStatus(source, cached);
          if (!stale()) setLocalKeys(statuses);
        } else if (loaded.connected) {
          const fresh = await source.refresh(controller.signal);
          if (stale()) return;
          setSnapshot(fresh);
          const statuses = await localStatus(source, fresh);
          if (!stale()) setLocalKeys(statuses);
        }
      } catch (error) {
        if (!stale() && !isCancelled(error)) setError(zoteroErrorMessage(error));
      } finally {
        if (!stale()) {
          setBusy(null);
          operation.current = null;
        }
      }
    };
    void load();
    const unsubscribe = runtime.subscribe(() => {
      void load();
    });
    return () => {
      disposed = true;
      generation.current++;
      operation.current?.abort();
      unsubscribe();
    };
  }, [runtime]);

  const refresh = async () => {
    if (!provider || busy) return;
    const controller = new AbortController();
    operation.current = controller;
    setBusy('refresh');
    setError('');
    setNotice('');
    try {
      const fresh = await provider.refresh(controller.signal);
      if (controller.signal.aborted) return;
      const statuses = await localStatus(provider, fresh);
      if (controller.signal.aborted || operation.current !== controller) return;
      setSnapshot(fresh);
      setLocalKeys(statuses);
      setSelected((current) =>
        fresh.collections.some((collection) => collection.key === current) ? current : null,
      );
      setNotice(_('Library refreshed'));
    } catch (error) {
      if (!isCancelled(error) && !controller.signal.aborted) setError(zoteroErrorMessage(error));
    } finally {
      if (operation.current === controller) {
        operation.current = null;
        setBusy(null);
      }
    }
  };

  const open = async (item: ExternalItem) => {
    if (!provider || busy) return;
    const controller = new AbortController();
    operation.current = controller;
    setBusy('download');
    setDownloadKey(item.key);
    setProgress(null);
    setError('');
    setNotice('');
    try {
      const document = await provider.open(item, controller.signal, (current) => {
        if (!controller.signal.aborted) setProgress(current);
      });
      if (controller.signal.aborted) return;
      setLocalKeys((keys) => new Set(keys).add(item.key));
      onOpen(document.file, document.title, document.resumeKey);
    } catch (error) {
      if (!isCancelled(error) && !controller.signal.aborted) setError(zoteroErrorMessage(error));
      else if (operation.current === controller) setNotice(_('Download cancelled'));
    } finally {
      if (operation.current === controller) {
        operation.current = null;
        setBusy(null);
        setDownloadKey(null);
        setProgress(null);
      }
    }
  };

  const clearLocal = async (item: ExternalItem) => {
    if (!provider || busy) return;
    const controller = new AbortController();
    operation.current = controller;
    setBusy('clear');
    setError('');
    setNotice('');
    try {
      await provider.clearLocal(item.key);
      if (controller.signal.aborted || operation.current !== controller) return;
      setLocalKeys((keys) => {
        const next = new Set(keys);
        next.delete(item.key);
        return next;
      });
      setNotice(
        _('Local copy cleared. You can download the PDF again; the file in Zotero is unchanged.'),
      );
    } catch (error) {
      if (!controller.signal.aborted) setError(zoteroErrorMessage(error));
    } finally {
      if (operation.current === controller) {
        operation.current = null;
        setBusy(null);
      }
    }
  };

  const tree = useMemo(() => buildCollectionTree(snapshot?.collections ?? []), [snapshot]);
  const items = useMemo(
    () =>
      snapshot?.items.filter((item) => !selected || item.collectionKeys.includes(selected)) ?? [],
    [snapshot, selected],
  );
  const collectionButton =
    'min-h-11 w-full rounded-lg px-3 py-2 text-start text-sm focus-visible:outline-2 focus-visible:outline-offset-2';
  const renderCollections = (nodes: ExternalCollectionNode[]): React.ReactNode =>
    nodes.map((node) => (
      <li key={node.key}>
        <button
          type='button'
          aria-pressed={selected === node.key}
          onClick={() => setSelected(node.key)}
          className={clsx(
            collectionButton,
            selected === node.key ? 'eink-bordered bg-base-300 font-medium' : 'hover:bg-base-200',
          )}
        >
          {node.name}
        </button>
        {node.children.length > 0 && (
          <ul className='border-base-300 ms-3 border-s ps-2'>{renderCollections(node.children)}</ul>
        )}
      </li>
    ));

  return (
    <section
      className='mx-auto flex w-full max-w-6xl flex-col gap-4 p-4 sm:p-6'
      aria-label={_('Zotero library')}
    >
      <div className='flex flex-wrap items-start justify-between gap-3'>
        <div>
          <h2 className='mb-1.5 text-lg font-semibold tracking-tight'>{_('Zotero')}</h2>
          <p className='text-base-content/70 text-sm leading-relaxed'>
            {_('Your Personal Library, with PDFs saved on this device for offline reading')}
          </p>
        </div>
        <div className='flex gap-2'>
          <button
            type='button'
            className='btn btn-ghost eink-bordered'
            onClick={() => setShowSettings((value) => !value)}
            aria-expanded={showSettings}
          >
            {_('Connection')}
          </button>
          {provider && (
            <button
              type='button'
              className='btn btn-contrast'
              disabled={!!busy || !account?.connected}
              onClick={() => void refresh()}
            >
              {_('Refresh')}
            </button>
          )}
          {(busy === 'refresh' || busy === 'download') && (
            <button
              type='button'
              className='btn btn-ghost eink-bordered'
              onClick={() => operation.current?.abort()}
            >
              {_('Cancel')}
            </button>
          )}
        </div>
      </div>
      {(showSettings || (account && !account.userId)) && (
        <div className='eink-bordered border-base-200 bg-base-100 rounded-lg border p-4'>
          <ZoteroSettings />
        </div>
      )}
      {account?.userId && !account.connected && (
        <p className='text-base-content/70 text-sm'>
          {_(
            'Offline library available. Add your API key in Connection to refresh or download PDFs.',
          )}
        </p>
      )}
      {error && (
        <p role='alert' className='eink-bordered border-base-300 rounded-lg border p-3 text-sm'>
          {_(error)}
        </p>
      )}
      {notice && (
        <p role='status' className='text-sm'>
          {notice}
        </p>
      )}
      {(busy === 'load' || busy === 'refresh') && (
        <p role='status' className='text-sm'>
          {_('Loading Zotero library…')}
        </p>
      )}
      {snapshot && (
        <div className='grid gap-4 sm:grid-cols-[minmax(10rem,15rem)_minmax(0,1fr)]'>
          <nav
            aria-label={_('Zotero collections')}
            className='eink-bordered border-base-200 bg-base-100 self-start rounded-lg border p-2'
          >
            <button
              type='button'
              aria-pressed={selected === null}
              onClick={() => setSelected(null)}
              className={clsx(
                collectionButton,
                selected === null && 'eink-bordered bg-base-300 font-medium',
              )}
            >
              {_('All items')}
            </button>
            <ul>{renderCollections(tree)}</ul>
          </nav>
          <div>
            {items.length === 0 && (
              <p className='text-base-content/70 p-4 text-sm'>{_('No items in this collection')}</p>
            )}
            <ul className='flex flex-col gap-3'>
              {items.map((item) => {
                const local = localKeys.has(item.key);
                const downloading = downloadKey === item.key;
                return (
                  <li
                    key={item.key}
                    className='eink-bordered border-base-200 bg-base-100 flex flex-col gap-2 rounded-lg border p-4'
                  >
                    <h3 className='font-medium leading-snug'>{item.title}</h3>
                    {item.authors.length > 0 && (
                      <p className='text-base-content/70 text-sm'>{item.authors.join(', ')}</p>
                    )}
                    <p className='text-base-content/70 text-sm'>
                      {[item.year, item.venue].filter(Boolean).join(' · ')}
                    </p>
                    <p className='text-sm' aria-live={downloading ? 'polite' : 'off'}>
                      {downloading
                        ? progress?.total
                          ? _('Downloading {{percent}}%', {
                              percent: String(
                                Math.floor((progress.received / progress.total) * 100),
                              ),
                            })
                          : _('Downloading PDF…')
                        : local
                          ? _('Saved offline')
                          : _('Not downloaded')}
                    </p>
                    <div className='flex flex-wrap gap-2'>
                      <button
                        type='button'
                        disabled={!!busy || (!local && !account?.connected)}
                        aria-label={
                          local
                            ? _('Open PDF: {{title}}', { title: item.title })
                            : _('Download PDF: {{title}}', { title: item.title })
                        }
                        onClick={() => void open(item)}
                        className='btn btn-contrast btn-sm min-h-11'
                      >
                        {local ? _('Open PDF') : _('Download PDF')}
                      </button>
                      {local && (
                        <button
                          type='button'
                          disabled={!!busy}
                          aria-label={_('Clear local copy: {{title}}', { title: item.title })}
                          onClick={() => void clearLocal(item)}
                          className='btn btn-ghost eink-bordered btn-sm min-h-11'
                        >
                          {_('Clear local copy')}
                        </button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      )}
      {!snapshot && account?.userId && !busy && (
        <p className='text-base-content/70 text-sm'>
          {_('No saved library yet. Connect to Zotero and refresh to load your collections.')}
        </p>
      )}
      <p className='text-base-content/60 text-xs leading-relaxed'>
        {_('Download papers to read them offline.')}
      </p>
    </section>
  );
}
