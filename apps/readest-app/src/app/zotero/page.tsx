'use client';

import { useState } from 'react';
import { useAppRouter } from '@/hooks/useAppRouter';
import { useTranslation } from '@/hooks/useTranslation';
import { useTheme } from '@/hooks/useTheme';
import { useThemeStore } from '@/store/themeStore';
import { useKeyDownActions } from '@/hooks/useKeyDownActions';
import ZoteroShelf from '@/components/zotero/ZoteroShelf';
import OriginalPdfView from '@/components/academic/OriginalPdfView';
import AcademicReadingButton from '@/components/academic/AcademicReadingButton';
import { useAcademicHistory } from '@/components/academic/useAcademicHistory';

export default function ZoteroPage() {
  const _ = useTranslation();
  const router = useAppRouter();
  const insets = useThemeStore((state) => state.safeAreaInsets);
  const [opened, setOpened] = useState<{ file: File; title: string; resumeKey: string } | null>(
    null,
  );
  const [readingOpen, setReadingOpen] = useState(false);
  useTheme({ systemUIVisible: true, themeScope: opened ? 'reader' : 'library' });
  const goBack = () => (opened ? setOpened(null) : router.push('/library'));
  useAcademicHistory(!!opened, () => setOpened(null));
  useKeyDownActions({ enabled: !readingOpen, onCancel: goBack });

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
          onClick={goBack}
        >
          ‹
        </button>
        <h1 className='min-w-0 flex-1 truncate font-semibold'>
          {opened?.title ?? _('Zotero Library')}
        </h1>
        {opened && (
          <AcademicReadingButton
            file={opened.file}
            title={opened.title}
            onOpenChange={setReadingOpen}
          />
        )}
      </header>
      {/* Keep the collection path and scroll position when returning from a paper. */}
      <div className={opened ? 'hidden' : 'min-h-0 flex-1 overflow-auto'}>
        <ZoteroShelf onOpen={(file, title, resumeKey) => setOpened({ file, title, resumeKey })} />
      </div>
      {opened && (
        <div className='min-h-0 flex-1'>
          <OriginalPdfView {...opened} />
        </div>
      )}
    </main>
  );
}
