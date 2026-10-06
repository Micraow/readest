'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useEnv } from '@/context/EnvContext';
import { useTranslation } from '@/hooks/useTranslation';
import BoxedList from '@/components/settings/primitives/BoxedList';
import SettingsRow from '@/components/settings/primitives/SettingsRow';
import { isCancelled } from '@/services/zotero/api';
import { getZoteroRuntime, zoteroErrorMessage } from '@/services/zotero/runtime';
import type { ZoteroAccount } from '@/services/zotero/credentials';

export interface ZoteroSettingsProps {
  onSaved?: () => void;
}

export default function ZoteroSettings({ onSaved }: ZoteroSettingsProps) {
  const _ = useTranslation();
  const { appService } = useEnv();
  const runtime = useMemo(() => (appService ? getZoteroRuntime(appService) : null), [appService]);
  const [userId, setUserId] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [account, setAccount] = useState<ZoteroAccount | null>(null);
  const [busy, setBusy] = useState<'connect' | 'disconnect' | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const active = useRef<AbortController | null>(null);

  useEffect(() => {
    let disposed = false;
    if (runtime)
      void runtime
        .load()
        .then(({ account: saved }) => {
          if (!disposed) {
            setAccount(saved);
            setUserId(saved.userId ?? '');
          }
        })
        .catch((error) => {
          if (!disposed) setError(zoteroErrorMessage(error));
        });
    return () => {
      disposed = true;
      active.current?.abort();
      active.current = null;
    };
  }, [runtime]);

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!runtime || busy) return;
    const controller = new AbortController();
    active.current = controller;
    setBusy('connect');
    setError('');
    setMessage('');
    try {
      const saved = await runtime.connect(
        { userId: userId.trim(), apiKey: apiKey.trim() },
        controller.signal,
      );
      if (controller.signal.aborted) return;
      setAccount(saved);
      setApiKey('');
      setMessage(
        saved.mode === 'secure'
          ? _('Connected. Your API key is stored in the system keychain')
          : _('Connected. Your API key is kept only for this session'),
      );
      onSaved?.();
    } catch (error) {
      if (!isCancelled(error) && active.current === controller) setError(zoteroErrorMessage(error));
    } finally {
      if (active.current === controller) {
        active.current = null;
        setBusy(null);
      }
    }
  };

  const disconnect = async () => {
    if (!runtime || busy) return;
    setBusy('disconnect');
    setError('');
    setMessage('');
    try {
      await runtime.disconnect();
      const { account: saved } = await runtime.load();
      setAccount(saved);
      setApiKey('');
      setMessage(_('Disconnected. Saved PDFs and library metadata remain on this device'));
      onSaved?.();
    } catch (error) {
      setError(zoteroErrorMessage(error));
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className='flex w-full flex-col gap-4' aria-label={_('Zotero connection')}>
      <div>
        <h2 className='mb-1.5 text-lg font-semibold tracking-tight'>{_('Zotero')}</h2>
        <p className='text-base-content/70 text-sm leading-relaxed'>
          {_('Browse your Personal Library and read PDFs from Zotero Storage')}
        </p>
      </div>
      <form onSubmit={save} className='flex flex-col gap-4'>
        <BoxedList title={_('Connection')}>
          <SettingsRow
            label={_('User ID')}
            asLabel
            className='flex-col items-stretch py-3 sm:flex-row sm:items-center'
          >
            <input
              type='text'
              inputMode='numeric'
              autoComplete='off'
              maxLength={16}
              value={userId}
              onChange={(event) => setUserId(event.target.value)}
              disabled={!!busy}
              required
              className='input eink-bordered border-base-300 w-full rounded-lg border sm:w-48'
            />
          </SettingsRow>
          <SettingsRow
            label={_('API key')}
            asLabel
            className='flex-col items-stretch py-3 sm:flex-row sm:items-center'
          >
            <input
              type='password'
              autoComplete='off'
              spellCheck={false}
              autoCapitalize='none'
              maxLength={256}
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              disabled={!!busy}
              required
              className='input eink-bordered border-base-300 w-full rounded-lg border sm:w-48'
            />
          </SettingsRow>
        </BoxedList>
        <p className='text-base-content/70 text-sm leading-relaxed'>
          {_(
            'Create a dedicated key with Personal Library read access and file access. Write access is not needed. Groups, linked files, and WebDAV are not supported.',
          )}{' '}
          <a
            href='https://www.zotero.org/settings/keys'
            target='_blank'
            rel='noopener noreferrer'
            className='underline underline-offset-2'
          >
            {_('Manage Zotero API keys')}
          </a>
        </p>
        <p className='text-base-content/70 text-sm leading-relaxed'>
          {account?.mode === 'secure'
            ? _(
                'Your API key will be saved in the system keychain and excluded from Readest cloud sync',
              )
            : _(
                'Your API key is kept only for this session. Enter it again after restarting; saved PDFs still work offline.',
              )}
        </p>
        <div className='flex flex-wrap gap-2'>
          <button
            type='submit'
            disabled={!runtime || !!busy || !userId.trim() || !apiKey.trim()}
            className='btn btn-contrast'
          >
            {busy === 'connect'
              ? _('Connecting…')
              : busy === 'disconnect'
                ? _('Disconnecting…')
                : _('Test and save')}
          </button>
          {busy === 'connect' && (
            <button
              type='button'
              className='btn btn-ghost eink-bordered'
              onClick={() => active.current?.abort()}
            >
              {_('Cancel')}
            </button>
          )}
          {account?.connected && !busy && (
            <button
              type='button'
              className='btn btn-ghost eink-bordered'
              onClick={() => void disconnect()}
            >
              {_('Disconnect')}
            </button>
          )}
        </div>
      </form>
      {error && (
        <p role='alert' className='text-error text-sm'>
          {_(error)}
        </p>
      )}
      {message && (
        <p role='status' className='text-sm'>
          {message}
        </p>
      )}
    </section>
  );
}
