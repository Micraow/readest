'use client';

import { useCallback, useState } from 'react';
import { useAppRouter } from '@/hooks/useAppRouter';
import { useTranslation } from '@/hooks/useTranslation';
import { useTheme } from '@/hooks/useTheme';
import { useThemeStore } from '@/store/themeStore';
import { useKeyDownActions } from '@/hooks/useKeyDownActions';
import { useEnv } from '@/context/EnvContext';
import { useAuth } from '@/context/AuthContext';
import { useSettingsStore } from '@/store/settingsStore';
import { useLibraryStore } from '@/store/libraryStore';
import { setBookGroup } from '@/utils/book';
import { navigateToReader } from '@/utils/nav';
import { queueOPDSBookUploads } from '@/services/opds/cloudUpload';
import { eventDispatcher } from '@/utils/event';
import type { Book } from '@/types/book';
import type { ExternalItem } from '@/services/externalLibrary/types';
import ZoteroShelf from '@/components/zotero/ZoteroShelf';

export default function ZoteroPage() {
  const _ = useTranslation();
  const router = useAppRouter();
  const { appService, envConfig } = useEnv();
  const { user } = useAuth();
  const insets = useThemeStore((state) => state.safeAreaInsets);
  const [reading, setReading] = useState(false);
  useTheme({ systemUIVisible: true, themeScope: 'library' });
  useKeyDownActions({ enabled: !reading, onCancel: () => router.push('/library') });

  /**
   * Import a downloaded Zotero PDF into the local library and place it in a
   * group named after its Zotero collection, then offer to open it. Identity
   * is the PDF's partialMD5, so re-downloading an item already on the shelf
   * returns the existing row instead of a duplicate.
   */
  const handleDownload = useCallback(
    async (file: File, title: string, _item: ExternalItem, collectionName: string) => {
      if (!appService) return;
      const { library, updateBooks } = useLibraryStore.getState();
      const book: Book | null = await appService.importBook(file, library);
      if (!book) return;
      if (collectionName) {
        const groupName = `Zotero/${collectionName}`;
        const { getGroupId } = useLibraryStore.getState();
        setBookGroup(book, getGroupId(groupName), groupName);
      }
      await updateBooks(envConfig, [book]);
      queueOPDSBookUploads(!!user, useSettingsStore.getState().settings, [book]);
      eventDispatcher.dispatch('toast', {
        message: _('Added to library: {{title}}', { title: book.title || title }),
        timeout: 3000,
        type: 'success',
      });
      return book;
    },
    [appService, envConfig, user, _],
  );

  const handleOpen = useCallback(
    async (file: File, title: string, item: ExternalItem, collectionName: string) => {
      setReading(true);
      try {
        const book = await handleDownload(file, title, item, collectionName);
        if (book) navigateToReader(router, [book.hash]);
      } finally {
        setReading(false);
      }
    },
    [handleDownload, router],
  );

  return (
    <main
      className='full-height bg-base-100 text-base-content flex flex-col'
      style={{ paddingTop: insets?.top ?? 0, paddingBottom: insets?.bottom ?? 0 }}
    >
      <header className='border-base-300 flex min-h-14 items-center gap-3 border-b px-3'>
        <button
          type='button'
          className='btn btn-circle btn-ghost eink-bordered'
          aria-label={_('Back')}
          onClick={() => router.push('/library')}
        >
          ‹
        </button>
        <h1 className='min-w-0 flex-1 truncate font-semibold'>{_('Zotero Library')}</h1>
      </header>
      <div className='min-h-0 flex-1 overflow-auto'>
        <ZoteroShelf onDownload={handleDownload} onOpen={handleOpen} />
      </div>
    </main>
  );
}
